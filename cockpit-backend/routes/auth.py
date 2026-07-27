"""
认证路由 - 登录/登出/改密/获取用户信息
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db, User
from auth import (
    verify_password, hash_password, create_token, decode_token,
    check_lockout, record_login_attempt, log_operation,
    get_current_user, validate_password_strength,
)
from config import settings

router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)


# ==================== 请求模型 ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePwdRequest(BaseModel):
    old_password: str
    new_password: str


class ManualChangePwdRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


# ==================== 响应模型 ====================

class LoginResponse(BaseModel):
    token: str
    username: str
    name: str
    dept: str
    scope: str
    is_first_login: bool


class UserInfoResponse(BaseModel):
    username: str
    name: str
    dept: str
    scope: str
    is_first_login: bool


# ==================== 路由 ====================

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    - 5次失败后锁定15分钟
    - 返回JWT令牌
    """
    username = req.username.strip().lower()
    client_ip = request.client.host if request.client else "unknown"

    # 1. 检查锁定状态
    lockout = check_lockout(db, username)
    if lockout["locked"]:
        raise HTTPException(
            status_code=429,
            detail=f"账号已被锁定，请{lockout['remaining_minutes']}分钟后再试"
        )

    # 2. 查找用户
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        record_login_attempt(db, username, client_ip, False)
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")

    # 3. 验证密码
    if not verify_password(req.password, user.password_hash):
        record_login_attempt(db, username, client_ip, False)
        
        # 再次检查是否触发锁定
        lockout = check_lockout(db, username)
        if lockout["locked"]:
            raise HTTPException(
                status_code=429,
                detail=f"密码错误次数过多，账号已被锁定{settings.LOCKOUT_MINUTES}分钟"
            )
        
        remaining = settings.MAX_LOGIN_ATTEMPTS - lockout["failed_count"]
        raise HTTPException(
            status_code=401,
            detail=f"密码错误，还剩{remaining}次尝试机会"
        )

    # 4. 登录成功
    record_login_attempt(db, username, client_ip, True)
    log_operation(db, username, "login", client_ip)

    token = create_token(username)
    return LoginResponse(
        token=token,
        username=user.username,
        name=user.name,
        dept=user.dept,
        scope=user.scope,
        is_first_login=user.is_first_login,
    )


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    """登出（JWT无状态，前端删除令牌即可，后端仅记录日志）"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            username = decode_token(token)
            client_ip = request.client.host if request.client else "unknown"
            log_operation(db, username, "logout", client_ip)
        except:
            pass
    return {"message": "已登出"}


@router.get("/me", response_model=UserInfoResponse)
async def get_user_info(token: str = Depends(security), db: Session = Depends(get_db)):
    """获取当前登录用户信息"""
    user = get_current_user(token.credentials, db)
    return UserInfoResponse(
        username=user.username,
        name=user.name,
        dept=user.dept,
        scope=user.scope,
        is_first_login=user.is_first_login,
    )


@router.post("/change-password")
@limiter.limit("3/minute")
async def change_password(
    req: ChangePwdRequest,
    request: Request,
    token: str = Depends(security),
    db: Session = Depends(get_db),
):
    """首次登录或主动修改密码（已登录状态）"""
    user = get_current_user(token.credentials, db)
    client_ip = request.client.host if request.client else "unknown"

    # 首次登录改密时跳过旧密码验证（用户已经通过登录验证）
    if not user.is_first_login:
        # 非首次登录，需要验证旧密码
        if not verify_password(req.old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="旧密码错误")

    # 密码复杂度校验
    err = validate_password_strength(req.new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if req.new_password == req.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

    # 更新密码
    user.password_hash = hash_password(req.new_password)
    user.is_first_login = False
    db.commit()
    log_operation(db, user.username, "change_pwd", client_ip, "self-service (logged in)")

    return {"message": "密码修改成功"}


@router.post("/change-password-manual")
@limiter.limit("3/minute")
async def change_password_manual(
    req: ManualChangePwdRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """从登录页主动修改密码（未登录状态，需验证旧密码）"""
    username = req.username.strip().lower()
    client_ip = request.client.host if request.client else "unknown"

    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查锁定
    lockout = check_lockout(db, username)
    if lockout["locked"]:
        raise HTTPException(
            status_code=429,
            detail=f"账号已被锁定，请{lockout['remaining_minutes']}分钟后再试"
        )

    # 验证旧密码
    if not verify_password(req.old_password, user.password_hash):
        record_login_attempt(db, username, client_ip, False)
        raise HTTPException(status_code=400, detail="旧密码错误")

    # 密码复杂度
    err = validate_password_strength(req.new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if req.new_password == req.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

    user.password_hash = hash_password(req.new_password)
    user.is_first_login = False
    db.commit()
    record_login_attempt(db, username, client_ip, True)
    log_operation(db, username, "change_pwd", client_ip, "self-service (from login page)")

    return {"message": "密码修改成功，请使用新密码登录"}


@router.get("/users")
@limiter.limit("30/minute")
async def get_users(request: Request, token: str = Depends(security), db: Session = Depends(get_db)):
    """获取用户名册（仅登录用户可用，按权限范围过滤）"""
    user = get_current_user(token.credentials, db)

    # 查询所有活跃用户
    users = db.query(User).filter(User.is_active == True).all()

    result = {}
    for u in users:
        # 区县权限只能看到自己
        if user.scope != "全市" and u.username != user.username:
            continue
        result[u.username] = {
            "name": u.name,
            "dept": u.dept,
            "scope": u.scope,
        }

    return result
