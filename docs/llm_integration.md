# RepoPilot LLM 集成文档

## 概述

RepoPilot 通过集成 OpenAI 的大模型（GPT-4-Turbo）实现深度的代码理解和分析能力。

## 核心模块

### 1. LLM 客户端 (`backend/llm/llm_client.py`)

封装了 OpenAI API 的调用，提供统一的接口：

```python
from backend.llm.llm_client import get_llm_client

client = get_llm_client()

# 调用 LLM
result = client.call(
    system_prompt="你是代码分析专家",
    user_message="分析这段代码",
    temperature=0.7,
    max_tokens=2000,
)

if result["success"]:
    print(result["content"])
else:
    print(f"Error: {result['error']}")
```

### 2. 向量化模块 (`backend/retrieval/llm_embeddings.py`)

使用 sentence-transformers 将代码片段转换为向量：

```python
from backend.retrieval.llm_embeddings import get_embeddings

embeddings = get_embeddings()

# 单个向量化
vec = embeddings.embed("def hello(): pass")

# 批量向量化
vecs = embeddings.embed_batch(["code1", "code2", "code3"])

# 计算相似度
similarity = embeddings.cosine_similarity(vec1, vec2)
```

### 3. 混合检索 (`backend/retrieval/hybrid_retriever.py`)

结合 BM25 关键词搜索和向量语义相似度的混合检索：

```python
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.retrieval.llm_embeddings import get_embeddings

embeddings = get_embeddings()
retriever = HybridRetriever(embeddings, repo_path="/path/to/repo")

# 构建索引
documents = [
    {"id": "1", "content": "def login()", "path": "auth.py", "line": 10},
    # ...
]
retriever.build_index(documents)

# 检索
results = retriever.search("用户登录", top_k=5, alpha=0.5)
```

### 4. LLM 驱动的分析工具 (`backend/tools/analysis_tools_llm.py`)

使用 LLM 进行深度的代码分析：

#### 调用链追踪

```python
from backend.tools.analysis_tools_llm import trace_call_chain_llm

result = trace_call_chain_llm(
    repo_path="/path/to/repo",
    function_name="authenticate",
    max_depth=3,
)

if result["success"]:
    print(result["data"]["call_chain"])
```

#### 影响范围分析

```python
from backend.tools.analysis_tools_llm import analyze_impact_llm

result = analyze_impact_llm(
    repo_path="/path/to/repo",
    code_to_change="修改的代码片段",
    related_files=["file1.py", "file2.py"],
)

if result["success"]:
    print(result["data"]["affected_modules"])
```

#### 风险识别

```python
from backend.tools.analysis_tools_llm import identify_risks_llm

result = identify_risks_llm(
    modification_details="修改详情",
    involved_files=["file1.py", "file2.py"],
    risk_factors=["API 变更", "数据库迁移"],
)

if result["success"]:
    print(result["data"]["risk_points"])
```

### 5. LLM 报告生成 (`backend/tools/report_tools_llm.py`)

生成高质量的 Markdown 分析报告：

```python
from backend.tools.report_tools_llm import generate_report_llm

report = generate_report_llm(
    requirement="分析登录功能的修改影响",
    entry_point="UserController.login()",
    call_chain={"entry_point": "login", "call_chain": [...]},
    impact_analysis={"affected_modules": ["auth", "user"]},
    risk_assessment={"risk_points": [...]},
    title="登录功能变更分析报告",
)

print(report)
```

## 配置

### 环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# OpenAI 配置
REPOPILOT_OPENAI_API_KEY=sk-xxx
REPOPILOT_OPENAI_MODEL=gpt-4-turbo

# 向量模型配置
REPOPILOT_EMBEDDING_MODEL=sentence-transformers/multilingual-e5-large

# 检索配置
REPOPILOT_RETRIEVAL_TOP_K=10
REPOPILOT_RETRIEVAL_ALPHA=0.5
```

### Python 配置

在 `backend/config.py` 中修改默认值：

```python
class Settings(BaseSettings):
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4-turbo")
    embedding_model: str = Field(default="sentence-transformers/multilingual-e5-large")
    retrieval_top_k: int = Field(default=10)
    retrieval_alpha: float = Field(default=0.5)
```

## 使用流程

### 1. 安装依赖

```bash
pip install -r backend/requirements.txt
```

### 2. 配置 OpenAI API Key

```bash
export REPOPILOT_OPENAI_API_KEY=sk-xxx
```

### 3. 运行 API

```bash
cd backend
uvicorn main:app --reload
```

### 4. 创建分析任务

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "repo1",
    "query": "分析登录功能的修改影响"
  }'
```

### 5. 查看报告

```bash
curl http://localhost:8000/api/tasks/{task_id}/report
```

## 成本优化

### Token 缓存

RepoPilot 实现了多层缓存以减少 API 调用：

1. **向量缓存** - 避免重复向量化相同的文本
2. **检索缓存** - 缓存相同查询的检索结果
3. **LLM 缓存** - 缓存相同提示词的 LLM 响应（可选）

### 批量处理

对于大量代码的分析，使用批量接口提高效率：

```python
# 批量向量化
embeddings = get_embeddings()
vectors = embeddings.embed_batch(code_list)
```

## 故障排查

### OpenAI API 不可用

if OpenAI 不可用，RepoPilot 会自动降级到基础的关键词搜索和启发式分析。

```python
# LLMClient 会返回 success=False
result = client.call(...)
if not result["success"]:
    # 使用备选方案
    pass
```

### 向量模型加载失败

如果 sentence-transformers 加载失败，系统会使用关键词搜索作为备选。

## 最佳实践

1. **使用混合检索** - 结合关键词和语义搜索获得最佳结果
2. **调整 Alpha 参数** - 根据需求调整 BM25 权重（0-1）
3. **监控 Token 使用** - 跟踪 API 调用成本
4. **缓存策略** - 对频繁查询的代码使用缓存
5. **错误处理** - 始终检查 LLM 调用的 success 字段
