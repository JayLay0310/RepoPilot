# RepoPilot

企业级代码理解与任务执行的智能 Agent 系统。

## 已实现内容

- FastAPI 主应用与 `/health` 健康检查
- Agent 6 节点工作流（需求解析 → 仓库扫描 → 代码检索 → 文件读取 → 分析生成 → 报告输出）
- 工具集合：repo_tools / code_search / file_tools / analysis_tools / report_tools
- RAG 检索模块：embeddings / vector_store / indexer / retriever
- 代码解析模块：Java + Python + 统一 code_analyzer
- API 路由：`/api/repos`、`/api/tasks`、`/api/analysis`
- 配置与文档：`backend/config.py`、`backend/requirements.txt`、`docs/*`

## 项目结构

```
RepoPilot/
├── backend/
├── frontend/
└── docs/
```

## 快速开始

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```
