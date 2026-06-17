from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    repo_path: str
    requirement: str
    parsed_requirement: dict[str, Any]
    repo_scan: dict[str, Any]
    retrieval_results: list[dict[str, Any]]
    file_context: dict[str, str]
    analysis: dict[str, Any]
    report_markdown: str
