# backend/app/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings, print_config
from ..database import init_db
from ..api.routes import chat, mood, memory, weather, news

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="情绪陪伴与心情日记 Agent",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由（统一加 /api 前缀）
app.include_router(chat.router,    prefix="/api")
app.include_router(mood.router,    prefix="/api")
app.include_router(memory.router,  prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(news.router,    prefix="/api")

@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 60)
    print_config()
    init_db()
    print("\n📚 Swagger 文档: http://localhost:8000/docs")
    print("=" * 60 + "\n")

@app.get("/")
def root():
    return {"name": settings.app_name, "version": settings.app_version, "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": settings.app_name}
