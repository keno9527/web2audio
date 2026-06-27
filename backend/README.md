# web2audio backend

第一版后端使用 FastAPI + SQLAlchemy，当前默认使用本地 SQLite 便于个人 MVP 启动和测试，后续可按 `docs/TECHNICAL_DESIGN.md` 切到 MySQL。

## Run

```bash
cd backend
uvicorn app.asgi:app --reload --host 127.0.0.1 --port 8000
```

默认开发 token 是 `dev-token`。Chrome 插件提交文章时需要发送：

```text
Authorization: Bearer dev-token
```

## Test

从仓库根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests
```
