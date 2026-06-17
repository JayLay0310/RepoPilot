"""LLM 驱动的报告生成工具"""

from typing import Dict, Any
import json

from backend.llm.llm_client import get_llm_client
from backend.llm.prompts import PROMPT_REPORT_GENERATION


def generate_report_llm(
    requirement: str,
    entry_point: str,
    call_chain: Dict[str, Any],
    impact_analysis: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    title: str = "RepoPilot 代码分析报告",
) -> str:
    """使用 LLM 生成结构化的分析报告
    
    Args:
        requirement: 用户需求
        entry_point: 功能入口
        call_chain: 调用链信息
        impact_analysis: 影响分析结果
        risk_assessment: 风险评估结果
        title: 报告标题
    
    Returns:
        Markdown 格式的报告
    """
    client = get_llm_client()
    
    # 构建分析内容摘要
    system_prompt = """你是一个专业的技术文档写手。
你需要基于代码分析结果，生成一份清晰、专业的技术报告。
报告应该包含以下部分：功能概览、核心流程、代码架构、影响范围、风险评估、修改建议和测试计划。
"""
    
    analysis_summary = f"""
## 分析输入

**用户需求:** {requirement}
**功能入口:** {entry_point}

### 调用链信息
{json.dumps(call_chain, ensure_ascii=False, indent=2)}

### 影响范围分析
{json.dumps(impact_analysis, ensure_ascii=False, indent=2)}

### 风险评估
{json.dumps(risk_assessment, ensure_ascii=False, indent=2)}
    """
    
    user_message = f"""
请基于以下分析信息，生成一份专业的技术分析报告。

{analysis_summary}

生成的报告应该包括:
1. **功能概览** - 简要描述涉及的功能和系统架构
2. **核心流程** - 详细的执行流程和数据流动
3. **代码架构** - 主要的类、方法和它们之间的关系
4. **影响范围分析** - 修改可能影响的其他模块和功能
5. **风险评估** - 关键风险点和级别（高/中/低）
6. **修改建议** - 具体的修改步骤和注意事项
7. **测试计划** - 需要进行的测试类型和重点

请使用 Markdown 格式，清晰的标题和列表结构，并包含具体的代码示例（如有）。
    """
    
    result = client.call(
        system_prompt,
        user_message,
        temperature=0.7,
        max_tokens=4000,
    )
    
    if result["success"]:
        report = f"# {title}\n\n{result['content']}"
        return report
    else:
        # 降级：生成基础结构化报告
        return generate_basic_report(
            title, requirement, entry_point, call_chain, impact_analysis, risk_assessment
        )


def generate_basic_report(
    title: str,
    requirement: str,
    entry_point: str,
    call_chain: Dict[str, Any],
    impact_analysis: Dict[str, Any],
    risk_assessment: Dict[str, Any],
) -> str:
    """生成基础的结构化报告（当 LLM 不可用时）"""
    report = f"""# {title}

## 需求分析

**用户需求:** {requirement}
**功能入口:** {entry_point}

## 调用链分析

### 调用路径
"""
    
    if isinstance(call_chain, dict) and "call_chain" in call_chain:
        for i, call in enumerate(call_chain["call_chain"], 1):
            if isinstance(call, dict):
                report += f"{i}. {call.get('name', '未知')} (文件: {call.get('file', '未知')}:\\{call.get('line', '?')})\n"
    
    report += "\n## 影响范围分析\n\n"
    
    if isinstance(impact_analysis, dict):
        if "affected_modules" in impact_analysis:
            report += "### 影响的模块\n\n"
            for module in impact_analysis["affected_modules"]:
                report += f"- {module}\n"
        
        if "risk_level" in impact_analysis:
            report += f"\n### 风险等级\n\n**{impact_analysis['risk_level'].upper()}**\n"
    
    report += "\n## 风险评估\n\n"
    
    if isinstance(risk_assessment, dict) and "risk_points" in risk_assessment:
        for point in risk_assessment["risk_points"]:
            if isinstance(point, dict):
                severity = point.get("severity", "unknown").upper()
                report += f"- [{severity}] {point.get('risk', '未知风险')}\n"
                report += f"  - 缓解方案: {point.get('mitigation', '无')}\n\n"
    
    report += "\n## 建议\n\n"
    
    if isinstance(risk_assessment, dict) and "recommendations" in risk_assessment:
        for i, rec in enumerate(risk_assessment["recommendations"], 1):
            report += f"{i}. {rec}\n"
    
    return report
