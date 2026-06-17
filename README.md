# RepoPilot

企业级代码理解与任务执行的智能 Agent 系统

## 项目描述

RepoPilot 是一个基于大模型和 RAG 技术的代码仓库智能分析系统，旨在帮助企业在以下场景中提高效率：

- 📚 **老项目维护** - 快速理解复杂项目的代码结构和功能
- 🔄 **需求变更评估** - 分析功能变更对系统的影响范围
- 📝 **研发知识沉淀** - 自动生成代码文档和调用链分析报告
- 👨‍💼 **新人快速上手** - 帮助新团队成员快速定位功能入口和核心逻辑

## 核心特性

✨ **智能代码理解**
- 支持 Java（Spring Boot）和 Python 项目
- 自动识别功能入口、核心类、调用链路
- 生成结构化的代码分析报告

🔍 **RAG 检索增强**
- 基于 FAISS 的语义代码检索
- 支持中文和英文的代码查询
- 精准定位相关代码片段

🤖 **Agent 工作流**
- LangGraph 驱动的多步骤工作流
- 需求解析 → 代码检索 → 分析 → 报告生成
- 支持动态工具调用和上下文管理

⚙️ **生产就绪**
- FastAPI 服务化部署
- 异步任务处理
- 结构化 API 接口

## 技术栈

- **Agent 框架**: LangGraph + LangChain
- **向量数据库**: FAISS
- **LLM**: OpenAI API (gpt-4-turbo)
- **向量模型**: sentence-transformers
- **后端框架**: FastAPI
- **代码解析**: AST, javalang, tree-sitter
- **数据库**: SQLite / PostgreSQL

## 快速开始

敬请期待...

## 项目结构

```
RepoPilot/
├── backend/                  # 后端服务
├── frontend/                 # 前端应用（可选）
├── docs/                     # 项目文档
└── README.md
```

## 许可证

MIT

## 联系方式

JayLay0310@github.com
