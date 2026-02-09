# СравнениеДок Платформа - Бэкенд

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

from config import settings
from database import engine, Base
from routers import auth, documents, compare, merge, extract

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="СравнениеДок Платформа",
    description="Платформа сравнения и слияния документов с AI. Поддерживает 2 режима сравнения (построчно и семантический), многостороннее слияние документов с разрешением конфликтов.",
    version="2.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
        port=5060,
        reload=True
    )

