import json
from pathlib import Path
from typing import Any

from backend.llm.llm_client import get_llm_client
from backend.rag.indexer import build_or_load_index
from backend.rag.retriever import hybrid_retrieve, semantic_retrieve
from backend.tools.analysis_tools import analyze_impact, trace_call_chain
from backend.tools.file_tools import read_file
from backend.tools.repo_tools import scan_repo
from backend.tools.report_tools import build_markdown_report
from backend.tools.static_call_graph import build_static_call_graph

MAX_FILE_CONTEXT_CHARS = 3000
REQUIREMENT_STOPWORDS = {"分析", "查看", "定位", "生成", "调用链", "影响", "范围", "修改", "代码", "功能"}


def parse_requirement_node(state: dict) -> dict:
    requirement = state.get("requirement", "")
    normalized = requirement.replace("，", " ").replace(",", " ")
    keywords = [
        token
        for token in normalized.split()
        if len(token) > 1 and token not in REQUIREMENT_STOPWORDS
    ]
    return {"parsed_requirement": {"raw": requirement, "keywords": keywords}}


def scan_repo_node(state: dict) -> dict:
    return {"repo_scan": scan_repo(state["repo_path"])}


def build_or_load_index_node(state: dict) -> dict:
    return {"index_stats": build_or_load_index(state["repo_path"])}


def retrieve_code_node(state: dict) -> dict:
    query = state.get("requirement", "")
    try:
        results = hybrid_retrieve(state["repo_path"], query, top_k=10, keyword_top_k=20)
    except Exception:
        results = semantic_retrieve(state["repo_path"], query, top_k=10)

    graph_context = _call_graph_context_for_results(state["repo_path"], results)
    return {"retrieval_results": results, "call_graph_context": graph_context}


def read_files_node(state: dict) -> dict:
    contexts = {}
    candidate_paths = [hit["path"] for hit in state.get("retrieval_results", [])[:8]]
    candidate_paths.extend(item["path"] for item in state.get("call_graph_context", {}).get("related_nodes", [])[:8])

    for path in candidate_paths:
        if path and path not in contexts:
            contexts[path] = read_file(path)[:MAX_FILE_CONTEXT_CHARS]
    return {"file_context": contexts}


def analysis_node(state: dict) -> dict:
    requirement = state.get("requirement", "")
    focus = _pick_focus(state)
    impact = analyze_impact(state["repo_path"], focus) if focus else {}
    call_chain = trace_call_chain(state["repo_path"], focus, max_depth=3) if focus else {}
    llm_result = _llm_structured_analysis(state, focus, impact, call_chain)

    return {
        "analysis": {
            "focus": focus,
            "impact": impact,
            "static_call_chain": call_chain,
            "llm": llm_result,
            "requirement": requirement,
        }
    }


def report_node(state: dict) -> dict:
    analysis = state.get("analysis", {})
    llm_data = analysis.get("llm", {}).get("data", {})
    call_chain = analysis.get("static_call_chain", {})
    impact = analysis.get("impact", {})
    sections = {
        "需求解析": _format_json(state.get("parsed_requirement", {})),
        "仓库扫描": _format_json(state.get("repo_scan", {})),
        "索引状态": _format_json(state.get("index_stats", {})),
        "入口定位": _format_entrypoints(call_chain.get("entrypoints", []), llm_data),
        "调用链图": _format_mermaid_call_chain(call_chain.get("chain", [])),
        "代码检索": _format_retrieval_results(state.get("retrieval_results", [])),
        "调用图上下文": _format_call_graph_context(state.get("call_graph_context", {})),
        "文件上下文": "\n".join(f"- {Path(path).name}: {path}" for path in state.get("file_context", {})),
        "LLM 结构化分析": _format_structured_analysis(llm_data),
        "静态调用图影响分析": _format_json(
            {
                "focus": analysis.get("focus"),
                "files": impact.get("files", []),
                "risk": impact.get("risk"),
                "reference_count": impact.get("reference_count"),
                "graph_stats": impact.get("graph_stats"),
                "static_call_chain": call_chain,
            }
        ),
    }
    report = build_markdown_report(sections, title="RepoPilot 结构化代码分析报告")
    return {"report_markdown": report}


def _call_graph_context_for_results(repo_path: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    graph = build_static_call_graph(repo_path)
    hit_paths = {str(Path(item.get("path", "")).resolve()) for item in results if item.get("path")}
    nodes = [node for node in graph["nodes"] if str(Path(node["path"]).resolve()) in hit_paths]
    node_ids = {node["id"] for node in nodes}
    related_ids = set(node_ids)

    for node_id in list(node_ids):
        related_ids.update(graph.get("adjacency", {}).get(node_id, []))
        related_ids.update(graph.get("reverse_adjacency", {}).get(node_id, []))

    related_nodes = [node for node in graph["nodes"] if node["id"] in related_ids]
    related_edges = [
        edge for edge in graph["edges"] if edge["from"] in related_ids or edge["to"] in related_ids
    ][:80]
    return {
        "matched_nodes": nodes[:40],
        "related_nodes": related_nodes[:80],
        "related_edges": related_edges,
        "spring": graph.get("spring", {}),
        "fastapi": graph.get("fastapi", {}),
        "stats": graph.get("stats", {}),
    }


def _pick_focus(state: dict) -> str:
    keywords = state.get("parsed_requirement", {}).get("keywords", [])
    code_like = [
        keyword
        for keyword in keywords
        if any(char.isascii() and (char.isalnum() or char == "_") for char in keyword)
    ]
    if code_like:
        return code_like[0]
    if keywords:
        return keywords[0]
    results = state.get("retrieval_results", [])
    if results:
        return Path(results[0].get("path", "")).stem
    return state.get("requirement", "general")


def _llm_structured_analysis(state: dict, focus: str, impact: dict, call_chain: dict) -> dict[str, Any]:
    client = get_llm_client()
    context = _compact_context(state.get("file_context", {}))
    retrieval = state.get("retrieval_results", [])[:10]
    call_graph_context = state.get("call_graph_context", {})
    system_prompt = (
        "你是资深代码理解助手。请基于代码证据、静态调用图和检索上下文谨慎分析；"
        "不知道时明确写“代码证据不足”，并只输出 JSON。"
    )
    user_message = f"""
需求:
{state.get("requirement", "")}

检索结果:
{_format_json(retrieval)}

调用图上下文:
{_format_json(_compact_call_graph_context(call_graph_context))}

文件上下文:
{context}

静态调用链:
{_format_json(call_chain)}

影响分析:
{_format_json(impact)}

请输出 JSON，字段固定为:
{{
  "functional_entry_points": ["功能入口定位"],
  "core_classes": [{{"name": "核心类或函数", "file": "文件", "description": "说明"}}],
  "static_call_chain": ["静态调用链"],
  "suggested_files": ["建议修改文件"],
  "modification_steps": ["修改步骤"],
  "impact_scope": ["影响范围"],
  "risks": ["风险点"],
  "patch_suggestions": ["代码补丁建议"]
}}
"""
    response = client.call_with_json(system_prompt, user_message, temperature=0.2)
    if response.get("success"):
        return response

    return {
        "success": False,
        "error": response.get("error", "LLM unavailable"),
        "data": _fallback_structured_analysis(state, focus, impact, call_chain),
    }


def _fallback_structured_analysis(state: dict, focus: str, impact: dict, call_chain: dict) -> dict[str, Any]:
    files = list(state.get("file_context", {}).keys())
    retrieval = state.get("retrieval_results", [])
    entrypoints = call_chain.get("entrypoints") or []
    fallback_entries = [f"{item.get('path')}:{item.get('line')}" for item in retrieval[:3]]
    return {
        "functional_entry_points": [
            f"{entry.get('method')} {entry.get('path')} -> {entry.get('handler')}" for entry in entrypoints
        ] or fallback_entries or ["代码证据不足"],
        "core_classes": [
            {"name": Path(path).stem, "file": path, "description": "由语义检索和静态调用图命中的候选核心文件"}
            for path in files[:5]
        ],
        "static_call_chain": [
            f"{edge.get('from')} -> {edge.get('to')}" for edge in call_chain.get("chain", [])[:10]
        ] or ["代码证据不足"],
        "suggested_files": files[:5],
        "modification_steps": ["确认入口和业务分支", "补充或调整核心实现", "增加回归测试", "运行相关接口验证"],
        "impact_scope": impact.get("files", [])[:10],
        "risks": [f"引用数量: {impact.get('reference_count', 0)}", f"风险等级: {impact.get('risk', 'unknown')}"],
        "patch_suggestions": ["根据命中的核心文件生成最小改动补丁，避免一次性重构无关模块"],
    }


def _compact_call_graph_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "matched_nodes": context.get("matched_nodes", [])[:10],
        "related_nodes": context.get("related_nodes", [])[:15],
        "related_edges": context.get("related_edges", [])[:20],
        "spring_entrypoints": context.get("spring", {}).get("entrypoints", [])[:20],
        "fastapi_entrypoints": context.get("fastapi", {}).get("entrypoints", [])[:20],
        "bean_dependencies": context.get("spring", {}).get("bean_dependencies", [])[:20],
        "stats": context.get("stats", {}),
    }


def _compact_context(file_context: dict[str, str]) -> str:
    parts = []
    for path, content in file_context.items():
        parts.append(f"### {path}\n```text\n{content[:MAX_FILE_CONTEXT_CHARS]}\n```")
    return "\n\n".join(parts)


def _format_entrypoints(entrypoints: list[dict[str, Any]], llm_data: dict[str, Any]) -> str:
    if entrypoints:
        rows = ["| Method | Path | Handler | Evidence |", "| --- | --- | --- | --- |"]
        for item in entrypoints:
            rows.append(
                f"| {item.get('method', '')} | `{item.get('path', '')}` | `{item.get('handler', '')}` | "
                f"{item.get('file', '')}:{item.get('line', 0)} |"
            )
        return "\n".join(rows)
    entries = llm_data.get("functional_entry_points", []) if isinstance(llm_data, dict) else []
    return "\n".join(f"- {entry}" for entry in entries) if entries else "未定位到明确入口。"


def _format_mermaid_call_chain(edges: list[dict[str, Any]]) -> str:
    if not edges:
        return "暂无可视化调用链。"
    lines = ["```mermaid", "graph TD"]
    for edge in edges[:30]:
        source = _mermaid_node(edge["from"])
        target = _mermaid_node(edge["to"])
        lines.append(f'  {source}["{_short_label(edge["from"])}"] --> {target}["{_short_label(edge["to"])}"]')
    lines.append("```")
    return "\n".join(lines)


def _format_retrieval_results(results: list[dict[str, Any]]) -> str:
    lines = []
    for item in results:
        score = item.get("score")
        score_text = f" score={score:.3f}" if isinstance(score, float) else ""
        source = item.get("source", "unknown")
        content = item.get("content", "").strip().replace("\n", " ")[:180]
        lines.append(f"- [{source}{score_text}] {item.get('path')}:{item.get('line', 0)} `{content}`")
    return "\n".join(lines) if lines else "未检索到相关代码。"


def _format_call_graph_context(context: dict[str, Any]) -> str:
    compact = _compact_call_graph_context(context)
    return _format_json(compact)


def _format_structured_analysis(data: dict[str, Any]) -> str:
    if not data:
        return "LLM 未返回结构化结果。"
    return _format_json(data)


def _format_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _mermaid_node(value: str) -> str:
    return "N" + "".join(char if char.isalnum() else "_" for char in value)[-60:]


def _short_label(value: str) -> str:
    return value.rsplit(".", 2)[-1].replace('"', "'")
