from datetime import datetime
from pydantic import BaseModel, Field


class RepoRegisterRequest(BaseModel):
    name: str
    path: str


class RepoResponse(BaseModel):
    id: str
    name: str
    path: str
    created_at: datetime


class TaskCreateRequest(BaseModel):
    repo_id: str
    query: str = Field(min_length=1)


class TaskResponse(BaseModel):
    id: str
    repo_id: str
    query: str
    status: str
    progress: int
    stage: str = "pending"


class SearchRequest(BaseModel):
    repo_id: str
    keyword: str
    top_k: int = 10


class AnalyzeRequest(BaseModel):
    code: str
    language: str


class ChainTraceRequest(BaseModel):
    repo_id: str
    symbol: str


class CallGraphRequest(BaseModel):
    repo_id: str
