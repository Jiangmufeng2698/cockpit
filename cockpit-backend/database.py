"""
数据库连接与ORM模型
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """FastAPI依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    """用户表 - 密码使用bcrypt哈希存储"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="登录账号(拼音)")
    name = Column(String(50), nullable=False, comment="真实姓名")
    dept = Column(String(100), nullable=False, comment="部门")
    scope = Column(String(50), nullable=False, default="全市", comment="权限范围: 全市或区县名")
    password_hash = Column(String(255), nullable=False, comment="bcrypt哈希密码")
    is_first_login = Column(Boolean, nullable=False, default=True, comment="是否首次登录(需改密)")
    is_active = Column(Boolean, nullable=False, default=True, comment="账号是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class LoginAttempt(Base):
    """登录尝试记录表 - 用于暴力破解防护"""
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, index=True, comment="尝试登录的账号")
    ip_address = Column(String(45), nullable=False, index=True, comment="客户端IP")
    success = Column(Boolean, nullable=False, comment="是否登录成功")
    attempted_at = Column(DateTime, server_default=func.now(), index=True, comment="尝试时间")


class ReportData(Base):
    """营销数据存储表 - 替代前端report_data.js"""
    __tablename__ = "report_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_date = Column(String(8), nullable=False, index=True, comment="数据日期YYYYMMDD")
    content = Column(Text, nullable=False, comment="JSON格式业务数据")
    created_at = Column(DateTime, server_default=func.now(), comment="上传时间")


class OperationLog(Base):
    """操作日志表 - 审计追踪"""
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, index=True, comment="操作人")
    action = Column(String(50), nullable=False, comment="操作类型: login/logout/change_pwd/upload_data")
    ip_address = Column(String(45), nullable=True, comment="客户端IP")
    detail = Column(Text, nullable=True, comment="操作详情")
    created_at = Column(DateTime, server_default=func.now(), comment="操作时间")
