from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from backend.models.domain import Repository
from backend.models.schemas import RepoRegisterRequest

router = APIRouter()
_REPOS: dict[str, Repository] = {}


@router.post("/register")
def register_repo(payload: RepoRegisterRequest) -> dict:
    path = Path(payload.path)
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail="Repository path must be an existing directory")
    repo = Repository(id=str(uuid4()), name=payload.name, path=payload.path)
    _REPOS[repo.id] = repo
    return asdict(repo)


@router.get("/list")
def list_repos() -> list[dict]:
    return [asdict(repo) for repo in _REPOS.values()]


@router.get("/{repo_id}")
def get_repo(repo_id: str) -> dict:
    repo = _REPOS.get(repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return asdict(repo)


@router.delete("/{repo_id}")
def delete_repo(repo_id: str) -> dict:
    if repo_id not in _REPOS:
        raise HTTPException(status_code=404, detail="Repository not found")
    _REPOS.pop(repo_id)
    return {"deleted": True, "repo_id": repo_id}
