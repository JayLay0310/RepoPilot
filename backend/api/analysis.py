from fastapi import APIRouter, HTTPException

from backend.parser.code_analyzer import CodeAnalyzer
from backend.tools.analysis_tools import trace_call_chain
from backend.tools.code_search import keyword_search
from backend.models.schemas import AnalyzeRequest, ChainTraceRequest, SearchRequest

router = APIRouter()
analyzer = CodeAnalyzer()


@router.post("/search")
def search_code(payload: SearchRequest) -> dict:
    try:
        return {"results": keyword_search(payload.repo_path, payload.keyword, top_k=payload.top_k)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analyze")
def analyze_code(payload: AnalyzeRequest) -> dict:
    return analyzer.analyze(payload.code, payload.language)


@router.post("/chain-trace")
def chain_trace(payload: ChainTraceRequest) -> dict:
    try:
        return {"chain": trace_call_chain(payload.repo_path, payload.symbol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
