"""
FastAPI 主应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import settings
from database import Base, engine
from routes.auth import router as auth_router
from routes.data import router as data_router


# ==================== 数据库初始化 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表（生产环境建议用Alembic迁移）
    Base.metadata.create_all(bind=engine)
    yield


# ==================== 速率限制 ====================

limiter = Limiter(key_func=get_remote_address)


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="大庆分公司营销驾驶舱 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 速率限制
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


# CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Gzip压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 路由
app.include_router(auth_router)
app.include_router(data_router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"detail": "请求过于频繁，请稍后再试"},
    )


@app.get("/")
async def root():
    return {"name": "大庆分公司营销驾驶舱 API", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
