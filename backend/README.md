# web2audio backend

第一版后端使用 FastAPI + SQLAlchemy，数据库统一连接 MySQL。运行时通过 `DATABASE_URL` 或 `conf/db.local.json` 提供 SQLAlchemy 兼容的 `mysql+pymysql://` URL。

默认运行时全部使用 fake client，确保本仓库自测不依赖真实豆包、火山云 TOS 或 love-song 服务。真实服务通过 `backend/conf/.env` 切换模式，并从对应 `*.local.json` 读取密钥和服务地址。

## Run

```bash
cd backend
uvicorn app.asgi:app --reload --host 127.0.0.1 --port 8000
```

默认开发 token 是 `dev-token`。Chrome 插件提交文章时需要发送：

```text
Authorization: Bearer dev-token
```

## Config

配置示例在 `conf/`：

- `.env.example`：环境变量示例，默认 `TTS_MODE=fake`、`STORAGE_MODE=fake`、`LOVE_SONG_MODE=fake`。
- `doubao.example.json`：豆包双向流式 TTS WebSocket 配置示例。
- `tos.example.json`：火山云 TOS 配置示例。
- `love_song.example.json`：love-song HTTP API 配置示例。
- `db.example.json`：MySQL URL 示例。

本地密钥文件使用 `conf/.env` 和 `conf/*.local.json`，不会提交。真实模式缺少配置文件或必填字段时会快速失败，不会静默回退到 fake。

## Database Schema

按当前配置创建或补齐数据库表：

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
from app.db.schema import ensure_database_schema

engine = ensure_database_schema()
print(engine.url.render_as_string(hide_password=True))
engine.dispose()
PY
```

默认 `db.local.json` 的 active profile 是 `mysql`，会在当前 MySQL 数据库创建或补齐 `article_audio_items` 和 `article_tts_segments`。

## Test

从仓库根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests
```
