from backend.agent.nodes import (
    analysis_node,
    build_or_load_index_node,
    parse_requirement_node,
    read_files_node,
    report_node,
    retrieve_code_node,
    scan_repo_node,
)
from backend.agent.state import AgentState

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover
    StateGraph = None
    START = "START"
    END = "END"


NODE_SEQUENCE = [
    parse_requirement_node,
    scan_repo_node,
    build_or_load_index_node,
    retrieve_code_node,
    read_files_node,
    analysis_node,
    report_node,
]

NODE_PROGRESS = {
    "parse_requirement_node": (15, "parsing requirement"),
    "scan_repo_node": (25, "scanning repository"),
    "build_or_load_index_node": (45, "building or loading vector index"),
    "retrieve_code_node": (60, "retrieving code and call graph context"),
    "read_files_node": (72, "reading file context"),
    "analysis_node": (88, "running static graph and LLM analysis"),
    "report_node": (96, "generating report"),
}


def build_workflow():
    if StateGraph is None:
        return None

    graph = StateGraph(AgentState)
    graph.add_node("parse_requirement", parse_requirement_node)
    graph.add_node("scan_repo", scan_repo_node)
    graph.add_node("build_or_load_index", build_or_load_index_node)
    graph.add_node("semantic_retrieve", retrieve_code_node)
    graph.add_node("read_files", read_files_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "parse_requirement")
    graph.add_edge("parse_requirement", "scan_repo")
    graph.add_edge("scan_repo", "build_or_load_index")
    graph.add_edge("build_or_load_index", "semantic_retrieve")
    graph.add_edge("semantic_retrieve", "read_files")
    graph.add_edge("read_files", "analysis")
    graph.add_edge("analysis", "report")
    graph.add_edge("report", END)

    return graph.compile()


def run_workflow(state: dict, progress_callback=None) -> dict:
    if progress_callback is not None:
        result = dict(state)
        for node in NODE_SEQUENCE:
            progress, message = NODE_PROGRESS.get(node.__name__, (0, node.__name__))
            progress_callback(progress, message)
            result.update(node(result))
        progress_callback(100, "completed")
        return result

    app = build_workflow()
    if app is not None:
        return app.invoke(state)

    result = dict(state)
    for node in NODE_SEQUENCE:
        result.update(node(result))
    return result
