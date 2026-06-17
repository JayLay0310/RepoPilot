from backend.tools.analysis_tools import analyze_impact
from backend.tools.code_search import keyword_search
from backend.tools.file_tools import read_file
from backend.tools.repo_tools import scan_repo
from backend.tools.report_tools import build_markdown_report


def parse_requirement_node(state: dict) -> dict:
    requirement = state.get("requirement", "")
    keywords = [token for token in requirement.replace("，", " ").replace(",", " " ).split() if len(token) > 1]
    return {"parsed_requirement": {"raw": requirement, "keywords": keywords}}


def scan_repo_node(state: dict) -> dict:
    return {"repo_scan": scan_repo(state["repo_path"])}


def retrieve_code_node(state: dict) -> dict:
    keywords = state.get("parsed_requirement", {}).get("keywords", [])
    query = keywords[0] if keywords else state.get("requirement", "")
    return {"retrieval_results": keyword_search(state["repo_path"], query, top_k=20)}


def read_files_node(state: dict) -> dict:
    contexts = {}
    for hit in state.get("retrieval_results", [])[:5]:
        path = hit["path"]
        if path not in contexts:
            contexts[path] = read_file(path)[:3000]
    return {"file_context": contexts}


def analysis_node(state: dict) -> dict:
    keywords = state.get("parsed_requirement", {}).get("keywords", [])
    focus = keywords[0] if keywords else state.get("requirement", "general")
    impact = analyze_impact(state["repo_path"], focus)
    return {"analysis": {"focus": focus, "impact": impact}}


def report_node(state: dict) -> dict:
    sections = {
        "需求解析": str(state.get("parsed_requirement", {})),
        "仓库扫描": str(state.get("repo_scan", {})),
        "代码检索": str(state.get("retrieval_results", [])),
        "文件上下文": str(list(state.get("file_context", {}).keys())),
        "分析结果": str(state.get("analysis", {})),
    }
    report = build_markdown_report(sections, title="RepoPilot 结构化分析报告")
    return {"report_markdown": report}
