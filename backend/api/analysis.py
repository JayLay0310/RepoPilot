from fastapi import APIRouter, HTTPException

from backend.parser.code_analyzer import CodeAnalyzer
from backend.tools.analysis_tools import trace_call_chain
from backend.tools.static_call_graph import build_static_call_graph
from backend.tools.code_search import keyword_search
from backend.api.repos import _REPOS
from backend.models.schemas import AnalyzeRequest, CallGraphRequest, ChainTraceRequest, SearchRequest

router = APIRouter()
analyzer = CodeAnalyzer()


@router.post("/search")
def search_code(payload: SearchRequest) -> dict:
    repo = _REPOS.get(payload.repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        return {"results": keyword_search(repo.path, payload.keyword, top_k=payload.top_k)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analyze")
def analyze_code(payload: AnalyzeRequest) -> dict:
    return analyzer.analyze(payload.code, payload.language)


@router.post("/chain-trace")
def chain_trace(payload: ChainTraceRequest) -> dict:
    repo = _REPOS.get(payload.repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        return {"chain": trace_call_chain(repo.path, payload.symbol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/call-graph")
def call_graph(payload: CallGraphRequest) -> dict:
    repo = _REPOS.get(payload.repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        graph = build_static_call_graph(repo.path)
        graph.pop("file_units", None)
        return {"call_graph": graph}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
