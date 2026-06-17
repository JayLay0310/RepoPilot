from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from backend.agent.workflow import run_workflow
from backend.api.repos import _REPOS
from backend.models.domain import AnalysisTask
from backend.models.schemas import TaskCreateRequest

router = APIRouter()
_TASKS: dict[str, AnalysisTask] = {}


@router.post("/")
def create_task(payload: TaskCreateRequest) -> dict:
    repo = _REPOS.get(payload.repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    task = AnalysisTask(id=str(uuid4()), repo_id=payload.repo_id, query=payload.query, status="running", progress=10)
    _TASKS[task.id] = task

    result = run_workflow({"repo_path": repo.path, "requirement": payload.query})
    task.status = "completed"
    task.progress = 100
    task.report = result.get("report_markdown", "")
    return asdict(task)


@router.get("/{task_id}")
def get_task(task_id: str) -> dict:
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return asdict(task)


@router.get("/{task_id}/progress")
def get_task_progress(task_id: str) -> dict:
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task.id, "status": task.status, "progress": task.progress}


@router.get("/{task_id}/report")
def get_task_report(task_id: str) -> dict:
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task.id, "report": task.report}


@router.get("/{task_id}/report/download")
def download_task_report(task_id: str) -> PlainTextResponse:
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return PlainTextResponse(task.report, media_type="text/markdown")
