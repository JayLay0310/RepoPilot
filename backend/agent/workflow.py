from backend.agent.nodes import (
    analysis_node,
    parse_requirement_node,
    read_files_node,
    report_node,
    retrieve_code_node,
    scan_repo_node,
)

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover
    StateGraph = None
    START = "START"
    END = "END"


NODE_SEQUENCE = [
    parse_requirement_node,
    scan_repo_node,
    retrieve_code_node,
    read_files_node,
    analysis_node,
    report_node,
]


def build_workflow():
    if StateGraph is None:
        return None

    graph = StateGraph(dict)
    graph.add_node("parse_requirement", parse_requirement_node)
    graph.add_node("scan_repo", scan_repo_node)
    graph.add_node("retrieve_code", retrieve_code_node)
    graph.add_node("read_files", read_files_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "parse_requirement")
    graph.add_edge("parse_requirement", "scan_repo")
    graph.add_edge("scan_repo", "retrieve_code")
    graph.add_edge("retrieve_code", "read_files")
    graph.add_edge("read_files", "analysis")
    graph.add_edge("analysis", "report")
    graph.add_edge("report", END)

    return graph.compile()


def run_workflow(state: dict) -> dict:
    app = build_workflow()
    if app is not None:
        return app.invoke(state)

    result = dict(state)
    for node in NODE_SEQUENCE:
        result.update(node(result))
    return result
