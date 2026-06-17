# RepoPilot 架构说明

RepoPilot 采用 backend/frontend/docs 三层结构。

- **backend**：FastAPI 服务、Agent 工作流、RAG 检索、代码解析、API 接口
- **frontend**：预留前端目录
- **docs**：架构/API/部署文档

Agent 工作流包含 6 个节点：需求解析、仓库扫描、代码检索、文件读取、分析生成、报告输出。
