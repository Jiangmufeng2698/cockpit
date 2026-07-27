"""
数据路由 - 获取营销数据 / 上传数据
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from database import get_db, ReportData, User
from auth import get_current_user, log_operation

router = APIRouter(prefix="/api/data", tags=["数据"])
security = HTTPBearer()


@router.get("/report")
async def get_report_data(
    request: Request,
    token: str = Depends(security),
    db: Session = Depends(get_db),
):
    """
    获取最新营销数据（替代前端report_data.js）
    返回最新一条数据的JSON
    """
    user = get_current_user(token.credentials, db)
    
    # 获取最新数据
    latest = db.query(ReportData).order_by(ReportData.data_date.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="暂无数据")
    
    try:
        data = json.loads(latest.content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="数据格式错误")
    
    # 区县权限过滤
    if user.scope != "全市":
        # 递归过滤数据，只保留该区县相关数据
        data = filter_by_scope(data, user.scope)
    
    return {
        "date": latest.data_date,
        "data": data,
    }


@router.post("/upload")
async def upload_report_data(
    request: Request,
    file: UploadFile = File(...),
    token: str = Depends(security),
    db: Session = Depends(get_db),
):
    """
    上传营销数据JSON文件（仅全市权限用户可用）
    Agent通过此接口推送每日更新数据
    """
    user = get_current_user(token.credentials, db)
    
    if user.scope != "全市":
        raise HTTPException(status_code=403, detail="无权限上传数据")
    
    client_ip = request.client.host if request.client else "unknown"
    
    # 读取文件内容
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="文件格式错误，请上传JSON文件")
    
    # 提取数据日期
    data_date = data.get("date", datetime.now().strftime("%Y%m%d"))
    
    # 存入数据库
    report = ReportData(
        data_date=data_date,
        content=json.dumps(data, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    
    log_operation(db, user.username, "upload_data", client_ip, f"date={data_date}")
    
    return {"message": f"数据上传成功，日期: {data_date}", "date": data_date}


@router.get("/history")
async def get_history_dates(
    token: str = Depends(security),
    db: Session = Depends(get_db),
):
    """获取所有可用数据日期列表"""
    user = get_current_user(token.credentials, db)
    
    dates = db.query(ReportData.data_date).order_by(
        ReportData.data_date.desc()
    ).all()
    
    return {"dates": [d[0] for d in dates]}


def filter_by_scope(data: dict, scope: str) -> dict:
    """
    递归过滤数据，只保留指定区县的数据
    根据实际数据结构调整过滤逻辑
    """
    # 如果数据中有区县字段，进行过滤
    # 这里需要根据实际的REPORT_DATA结构来实现
    # 基本思路：遍历所有包含区县名称的数据节点，只保留匹配scope的
    filtered = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # 检查是否有区县相关的key
            if "区县" in value or "区县名" in value or "scope" in value:
                county = value.get("区县") or value.get("区县名") or value.get("scope", "")
                if county == scope:
                    filtered[key] = value
            else:
                filtered[key] = filter_by_scope(value, scope)
        elif isinstance(value, list):
            filtered_list = []
            for item in value:
                if isinstance(item, dict):
                    county = item.get("区县") or item.get("区县名") or item.get("scope", "")
                    if county == scope or not county:
                        filtered_list.append(item)
                else:
                    filtered_list.append(item)
            filtered[key] = filtered_list
        else:
            filtered[key] = value
    return filtered
