"""LLM 驱动的代码分析工具"""

from typing import Dict, Any, List
import json

from backend.llm.llm_client import get_llm_client
from backend.llm.prompts import (
    PROMPT_CALL_CHAIN_ANALYSIS,
    PROMPT_IMPACT_ANALYSIS,
    PROMPT_RISK_ASSESSMENT,
)
from backend.tools.code_search import keyword_search
from backend.tools.file_tools import read_file


def trace_call_chain_llm(repo_path: str, function_name: str, max_depth: int = 2) -> Dict[str, Any]:
    """使用 LLM 追踪调用链
    
    Args:
        repo_path: 仓库路径
        function_name: 要追踪的函数名
        max_depth: 追踪深度
    
    Returns:
        包含调用链信息的字典
    """
    # 搜索相关代码
    search_results = keyword_search(repo_path, function_name, top_k=30)
    
    if not search_results:
        return {
            "success": False,
            "error": f"Function {function_name} not found",
            "call_chain": [],
        }
    
    # 收集代码上下文
    code_context = ""
    for result in search_results[:5]:
        try:
            content = read_file(result["path"])
            code_context += f"\n\n--- File: {result['path']} ---\n{content[:1000]}"
        except Exception:
            pass
    
    # 调用 LLM 进行分析
    client = get_llm_client()
    system_prompt = "你是代码流分析专家，擅长追踪函数调用链。"
    user_message = PROMPT_CALL_CHAIN_ANALYSIS.format(
        function_name=function_name,
        code_context=code_context,
    )
    
    result = client.call_with_json(system_prompt, user_message)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"],
            "tokens_used": result.get("tokens_used", 0),
        }
    else:
        return {
            "success": False,
            "error": result["error"],
            "call_chain": [],
        }


def analyze_impact_llm(
    repo_path: str,
    code_to_change: str,
    related_files: List[str],
) -> Dict[str, Any]:
    """使用 LLM 分析代码变更的影响范围
    
    Args:
        repo_path: 仓库路径
        code_to_change: 待修改的代码
        related_files: 相关文件列表
    
    Returns:
        包含影响分析的字典
    """
    # 收集相关文件的信息
    files_summary = ""
    for file_path in related_files[:10]:
        try:
            content = read_file(file_path)
            files_summary += f"\n--- {file_path} ---\n{content[:500]}"
        except Exception:
            pass
    
    # 调用 LLM 进行分析
    client = get_llm_client()
    system_prompt = "你是资深代码审查专家，擅长评估代码变更的影响范围。"
    user_message = PROMPT_IMPACT_ANALYSIS.format(
        code_to_change=code_to_change,
        related_files_summary=files_summary,
        call_chain_info="",
    )
    
    result = client.call_with_json(system_prompt, user_message)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"],
            "tokens_used": result.get("tokens_used", 0),
        }
    else:
        return {
            "success": False,
            "error": result["error"],
            "data": {},
        }


def identify_risks_llm(
    modification_details: str,
    involved_files: List[str],
    risk_factors: List[str] = None,
) -> Dict[str, Any]:
    """使用 LLM 识别风险点
    
    Args:
        modification_details: 修改的详细描述
        involved_files: 涉及的文件
        risk_factors: 已知的风险因素
    
    Returns:
        包含风险评估的字典
    """
    risk_factors = risk_factors or []
    
    # 调用 LLM 进行风险评估
    client = get_llm_client()
    system_prompt = "你是代码风险评估专家，擅长识别代码修改的潜在风险。"
    user_message = PROMPT_RISK_ASSESSMENT.format(
        modification_details=modification_details,
        involved_files=", ".join(involved_files),
        risk_factors=", ".join(risk_factors) if risk_factors else "无已知风险因素",
    )
    
    result = client.call_with_json(system_prompt, user_message)
    
    if result["success"]:
        return {
            "success": True,
            "data": result["data"],
            "tokens_used": result.get("tokens_used", 0),
        }
    else:
        return {
            "success": False,
            "error": result["error"],
            "data": {},
        }


def generate_suggestions_llm(
    current_code: str,
    requirement: str,
    analysis_results: Dict[str, Any],
) -> Dict[str, str]:
    """使用 LLM 生成修改建议
    
    Args:
        current_code: 当前代码
        requirement: 需求描述
        analysis_results: 分析结果
    
    Returns:
        包含修改建议的字典
    """
    client = get_llm_client()
    system_prompt = "你是资深的代码架构师，擅长提供具体的修改建议。"
    
    analysis_str = json.dumps(analysis_results, ensure_ascii=False, indent=2)
    user_message = f"""
当前代码:
```
{current_code}
```

需求: {requirement}

分析结果:
{analysis_str}

请提供:
1. 具体的修改步骤
2. 代码修改示例
3. 需要注意的事项
4. 测试验证方案

以 Markdown 格式输出。
    """
    
    result = client.call(system_prompt, user_message, max_tokens=2000)
    
    if result["success"]:
        return {
            "success": True,
            "suggestions": result["content"],
            "tokens_used": result.get("tokens_used", 0),
        }
    else:
        return {
            "success": False,
            "error": result["error"],
            "suggestions": "",
        }
