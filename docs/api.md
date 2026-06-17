# API 文档

## 仓库管理 `/api/repos`
- `POST /register`
- `GET /list`
- `GET /{repo_id}`
- `DELETE /{repo_id}`

## 任务管理 `/api/tasks`
- `POST /`
- `GET /{task_id}`
- `GET /{task_id}/progress`
- `GET /{task_id}/report`
- `GET /{task_id}/report/download`

## 分析接口 `/api/analysis`
- `POST /search`
- `POST /analyze`
- `POST /chain-trace`
