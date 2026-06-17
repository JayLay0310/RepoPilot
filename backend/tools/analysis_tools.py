from backend.tools.code_search import keyword_search
from backend.tools.static_call_graph import build_static_call_graph, trace_static_call_chain


def trace_call_chain(repo_path: str, symbol: str, max_depth: int = 3) -> dict:
    return trace_static_call_chain(repo_path, symbol, max_depth=max_depth)


def analyze_impact(repo_path: str, symbol: str) -> dict:
    graph = build_static_call_graph(repo_path)
    chain = trace_static_call_chain(repo_path, symbol, max_depth=3)
    impacted_node_ids = {edge["to"] for edge in chain["chain"]} | set(chain["resolved_symbols"])
    reverse_refs = [
        {"from": source, "to": target}
        for target in chain["resolved_symbols"]
        for source in graph.get("reverse_adjacency", {}).get(target, [])
    ]
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    files = sorted({node_by_id[node_id]["path"] for node_id in impacted_node_ids if node_id in node_by_id})

    if not files:
        refs = keyword_search(repo_path, symbol, top_k=200)
        files = sorted({item["path"] for item in refs})
        reference_count = len(refs)
    else:
        reference_count = len(chain["chain"]) + len(reverse_refs)

    risk = "low" if len(files) < 3 else "medium" if len(files) < 10 else "high"
    return {
        "symbol": symbol,
        "files": files,
        "reference_count": reference_count,
        "risk": risk,
        "resolved_symbols": chain["resolved_symbols"],
        "forward_edges": chain["chain"],
        "reverse_edges": reverse_refs,
        "graph_stats": graph["stats"],
    }
