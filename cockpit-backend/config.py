"""
配置文件 - 生产环境请通过环境变量覆盖敏感配置
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # MySQL数据库配置
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "cockpit")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "change_me_in_production")
    DB_NAME = os.getenv("DB_NAME", "cockpit")
    
    @property
    def DATABASE_URL(self):
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    # JWT配置
    JWT_SECRET = os.getenv("JWT_SECRET", "dpcCockpit_Secret_Key_2026!@#_change_me")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_HOURS = 18  # 与原前端session保持一致
    
    # CORS - 前端域名
    CORS_ORIGINS = [
        "https://jiangmufeng2698.github.io",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    # 登录安全策略
    MAX_LOGIN_ATTEMPTS = 5       # 最大失败次数
    LOCKOUT_MINUTES = 15         # 锁定时长（分钟）
    LOGIN_RATE_LIMIT = "10/minute"  # 频率限制
    
    # 密码策略
    PWD_MIN_LENGTH = 6
    PWD_REQUIRE_LETTER = True
    PWD_REQUIRE_DIGIT = True

settings = Settings()
