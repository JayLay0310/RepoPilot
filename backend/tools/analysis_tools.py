from backend.tools.code_search import keyword_search


def trace_call_chain(repo_path: str, symbol: str, max_depth: int = 2) -> dict:
    chain = {symbol: []}
    current = [symbol]
    for _ in range(max_depth):
        nxt = []
        for item in current:
            refs = keyword_search(repo_path, item, top_k=20)
            children = [r["path"] for r in refs]
            chain[item] = children
            nxt.extend(children)
        current = nxt
    return chain


def analyze_impact(repo_path: str, symbol: str) -> dict:
    refs = keyword_search(repo_path, symbol, top_k=200)
    files = sorted({r["path"] for r in refs})
    risk = "low" if len(files) < 3 else "medium" if len(files) < 10 else "high"
    return {"symbol": symbol, "files": files, "reference_count": len(refs), "risk": risk}
