# 部署说明

## 本地启动

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## 环境变量

通过 `.env` 配置，前缀为 `REPOPILOT_`。
