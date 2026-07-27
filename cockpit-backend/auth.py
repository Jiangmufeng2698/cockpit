"""
认证模块 - JWT令牌 + bcrypt密码哈希 + 暴力破解防护
"""
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from config import settings
from database import User, LoginAttempt, OperationLog


# ==================== 密码哈希 ====================

def hash_password(plain_password: str) -> str:
    """bcrypt哈希密码"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def validate_password_strength(password: str) -> str | None:
    """
    密码复杂度校验，返回错误信息或None
    """
    if len(password) < settings.PWD_MIN_LENGTH:
        return f"密码至少需要{settings.PWD_MIN_LENGTH}位"
    if settings.PWD_REQUIRE_LETTER and not any(c.isalpha() for c in password):
        return "密码必须包含字母"
    if settings.PWD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return "密码必须包含数字"
    if password == "123456":
        return "密码不能使用默认密码"
    return None


# ==================== JWT令牌 ====================

def create_token(username: str) -> str:
    """生成JWT令牌"""
    payload = {
        "sub": username,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    """解析JWT令牌，返回username"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")


# ==================== 暴力破解防护 ====================

def check_lockout(db: Session, username: str) -> dict:
    """
    检查账号是否被锁定
    返回 {"locked": bool, "remaining_minutes": int, "failed_count": int}
    """
    cutoff = datetime.utcnow() - timedelta(minutes=settings.LOCKOUT_MINUTES)
    
    # 查询最近N分钟内的失败次数
    recent_failures = db.query(LoginAttempt).filter(
        LoginAttempt.username == username,
        LoginAttempt.success == False,
        LoginAttempt.attempted_at >= cutoff,
    ).order_by(desc(LoginAttempt.attempted_at)).all()
    
    if len(recent_failures) >= settings.MAX_LOGIN_ATTEMPTS:
        last_attempt = recent_failures[0].attempted_at
        unlock_time = last_attempt + timedelta(minutes=settings.LOCKOUT_MINUTES)
        remaining = (unlock_time - datetime.utcnow()).total_seconds() / 60
        return {
            "locked": True,
            "remaining_minutes": max(1, int(remaining)),
            "failed_count": len(recent_failures),
        }
    
    return {"locked": False, "remaining_minutes": 0, "failed_count": len(recent_failures)}


def record_login_attempt(db: Session, username: str, ip: str, success: bool):
    """记录登录尝试"""
    log = LoginAttempt(username=username, ip_address=ip, success=success)
    db.add(log)
    db.commit()


def log_operation(db: Session, username: str, action: str, ip: str = None, detail: str = None):
    """记录操作日志"""
    log = OperationLog(username=username, action=action, ip_address=ip, detail=detail)
    db.add(log)
    db.commit()


# ==================== 认证依赖 ====================

def get_current_user(token: str, db: Session) -> User:
    """根据JWT令牌获取当前用户"""
    username = decode_token(token)
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user
