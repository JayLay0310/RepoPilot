from fastapi import APIRouter

from backend.parser.code_analyzer import CodeAnalyzer
from backend.tools.analysis_tools import trace_call_chain
from backend.tools.code_search import keyword_search
from backend.models.schemas import AnalyzeRequest, ChainTraceRequest, SearchRequest

router = APIRouter()
analyzer = CodeAnalyzer()


@router.post("/search")
def search_code(payload: SearchRequest) -> dict:
    return {"results": keyword_search(payload.repo_path, payload.keyword, top_k=payload.top_k)}


@router.post("/analyze")
def analyze_code(payload: AnalyzeRequest) -> dict:
    return analyzer.analyze(payload.code, payload.language)


@router.post("/chain-trace")
def chain_trace(payload: ChainTraceRequest) -> dict:
    return {"chain": trace_call_chain(payload.repo_path, payload.symbol)}
