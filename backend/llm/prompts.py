"""代码分析的 Prompt 模板库"""

PROMPT_REQUIREMENT_PARSING = """
你是一个资深的软件架构师。现在需要理解用户的代码分析需求。

用户需求: {requirement}

请分析用户的需求，提取以下信息，以 JSON 格式返回:
{{
  "task_type": "impact_analysis|feature_location|call_chain_trace|code_review",
  "focus_areas": ["area1", "area2"],
  "key_components": ["component1", "component2"],
  "priority": "high|medium|low",
  "analysis_goals": ["goal1", "goal2"]
}}
"""

PROMPT_CODE_UNDERSTANDING = """
你是一个代码审查专家。现在需要理解以下代码片段的功能。

代码:
```
{code}
```

文件路径: {file_path}
文件类型: {language}

请分析这段代码，以 JSON 格式返回:
{{
  "summary": "该代码的简要功能描述（一句话）",
  "purpose": "代码的目的和业务意义",
  "inputs": ["输入参数1", "输入参数2"],
  "outputs": ["输出或返回值"],
  "side_effects": ["副作用1", "副作用2"],
  "dependencies": ["依赖1", "依赖2"],
  "key_operations": ["关键操作1", "关键操作2"]
}}
"""

PROMPT_CALL_CHAIN_ANALYSIS = """
你是一个代码流分析专家。现在需要分析函数/方法的调用链。

核心函数/方法: {function_name}

已知的相关代码片段:
{code_context}

请分析调用链，以 JSON 格式返回:
{{
  "entry_point": "入口点",
  "call_chain": [
    {{
      "name": "函数名",
      "file": "文件路径",
      "line": "行号",
      "purpose": "该函数的作用"
    }}
  ],
  "data_flow": ["数据流向描述"],
  "external_calls": ["调用的外部服务或API"],
  "depth": 调用链深度
}}
"""

PROMPT_IMPACT_ANALYSIS = """
你是一个资深代码审查专家。现在需要分析代码变更的影响范围。

待修改的代码:
```
{code_to_change}
```

相关的代码文件:
{related_files_summary}

调用链信息:
{call_chain_info}

请分析这个修改的影响，以 JSON 格式返回:
{{
  "affected_modules": ["模块1", "模块2"],
  "directly_affected_files": ["文件1", "文件2"],
  "indirectly_affected_areas": ["间接影响1", "间接影响2"],
  "breaking_changes": ["可能的破坏性变更"],
  "compatibility_issues": ["兼容性问题"],
  "performance_impact": "性能影响描述",
  "required_tests": ["需要进行的测试"],
  "risk_level": "high|medium|low"
}}
"""

PROMPT_RISK_ASSESSMENT = """
你是一个代码风险评估专家。现在需要识别代码修改的风险点。

修改内容:
{modification_details}

涉及的文件:
{involved_files}

已知的风险因素:
{risk_factors}

请识别并评估风险，以 JSON 格式返回:
{{
  "risk_points": [
    {{
      "risk": "风险描述",
      "severity": "critical|high|medium|low",
      "affected_area": "受影响的领域",
      "mitigation": "风险缓解方案"
    }}
  ],
  "overall_risk": "high|medium|low",
  "recommendations": ["建议1", "建议2"],
  "testing_focus": ["测试重点1", "测试重点2"]
}}
"""

PROMPT_REPORT_GENERATION = """
你是一个专业的技术文档写手。现在需要生成一份结构化的代码分析报告。

分析内容:
- 需求: {requirement}
- 功能入口: {entry_point}
- 调用链: {call_chain}
- 影响范围: {impact_analysis}
- 风险评估: {risk_assessment}

请生成一份专业的 Markdown 格式分析报告，包含以下部分:
1. 功能概览
2. 核心流程
3. 代码架构
4. 影响范围分析
5. 风险评估
6. 修改建议
7. 测试计划

报告应该清晰、专业、可操作。
"""

PROMPT_MODIFICATION_SUGGESTION = """
你是一个资深的代码架构师。基于代码分析结果，现在需要提供具体的修改建议。

当前代码:
```
{current_code}
```

需求:
{requirement}

分析结果:
{analysis_results}

请提供:
1. 具体的修改步骤
2. 代码修改示例（伪代码或实际代码）
3. 需要注意的事项
4. 测试验证方案

以 Markdown 格式输出。
"""
