from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import analysis, repos, tasks
from backend.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router, prefix="/api/repos", tags=["repos"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
