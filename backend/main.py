# СравнениеДок Платформа - Бэкенд

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import asyncio
import logging

# Configure logging - ensure auth_service messages are visible
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

from config import settings
from database import engine, Base
from routers import auth, documents, compare, merge, extract, anonymizer, docanalysis
from services.cleanup_service import cleanup_old_files

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Scheduler task for cleanup
async def cleanup_scheduler():
    """Запускает очистку старых файлов каждый час"""
    while True:
        try:
            logger.info("Running scheduled file cleanup...")
            deleted = cleanup_old_files()
            if deleted > 0:
                logger.info(f"Cleanup scheduler: deleted {deleted} old files")
        except Exception as e:
            logger.error(f"Cleanup scheduler error: {e}")
        # Запуск каждый час
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup: запуск планировщика очистки
    logger.info(f"Starting cleanup scheduler (retention: {settings.FILE_RETENTION_DAYS} days)")
    # Запускаем очистку при старте
    cleanup_old_files()
    # Очистка файлов anonymizer
    from anonymizer_utils.file_utils import cleanup_old_files as anon_cleanup
    anon_cleanup()
    # Создаём фоновую задачу
    cleanup_task = asyncio.create_task(cleanup_scheduler())
    yield
    # Shutdown: останавливаем планировщик
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Cleanup scheduler stopped")

app = FastAPI(
    title="Документы Про",
    description="Платформа сравнения и слияния документов с AI. Поддерживает 2 режима сравнения (построчно и семантический), многостороннее слияние документов с разрешением конфликтов.",
    version="2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Аутентификация"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Документы"])
app.include_router(compare.router, prefix="/api/v1/compare", tags=["Сравнение"])
app.include_router(merge.router, prefix="/api/v1/merge", tags=["Слияние"])
app.include_router(extract.router, prefix="/api/v1/extract", tags=["Извлечение"])
app.include_router(anonymizer.router, prefix="/api/v1/anonymizer", tags=["Обезличивание"])
app.include_router(docanalysis.router, prefix="/api/v1/docanalysis", tags=["Анализ документа"])

# Frontend path
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.get("/")
async def root():
    """Serve frontend index.html"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "DocumentCompare Platform API", "docs": "/docs"}

@app.get("/styles.css")
async def get_styles():
    """Serve CSS file - no cache for dev"""
    css_path = os.path.join(frontend_path, "styles.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"error": "CSS not found"}

@app.get("/app.js")
async def get_js():
    """Serve JS file - no cache for dev"""
    js_path = os.path.join(frontend_path, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"error": "JS not found"}

@app.get("/favicon.ico")
async def get_favicon():
    """Serve favicon"""
    return FileResponse(os.path.join(frontend_path, "favicon.ico")) if os.path.exists(os.path.join(frontend_path, "favicon.ico")) else {"status": "no favicon"}

@app.get("/api/v1/health")
async def health_check():
    """Проверка состояния системы"""
    return {
        "status": "ok",
        "version": "2.0",
        "message": "СравнениеДок Платформа работает",
        "ml_config": {
            "gpt_host": settings.ML_HOST_GPT,
            "vision_host": settings.ML_HOST_VISION
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5055,
        reload=True
    )
