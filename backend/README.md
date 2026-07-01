# web2audio backend

第一版后端使用 FastAPI + SQLAlchemy，数据库统一连接 MySQL。运行时通过 `DATABASE_URL` 或 `conf/db.local.json` 提供 SQLAlchemy 兼容的 `mysql+pymysql://` URL。

默认运行时全部使用 fake client，确保本仓库自测不依赖真实豆包、火山云 TOS 或 love-song 服务。真实服务通过 `backend/conf/.env` 切换模式，并从对应 `*.local.json` 读取密钥和服务地址。

## Run

后端服务从仓库的 `backend/` 目录启动。默认配置会读取 `conf/.env`，未提供时使用 fake TTS、fake TOS、fake love-song client 和默认 MySQL URL。

首次启动或切换数据库后，先按当前配置创建或补齐数据库表：

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
from app.db.schema import ensure_database_schema

engine = ensure_database_schema()
print(engine.url.render_as_string(hide_password=True))
engine.dispose()
PY
```

启动 FastAPI 开发服务：

```bash
cd backend
uvicorn app.asgi:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

默认开发 token 是 `dev-token`。Chrome 插件提交文章时需要发送：

```text
Authorization: Bearer dev-token
```

真实豆包、TOS 或 love-song HTTP 联调前，先在 `conf/.env` 中显式切换 `TTS_MODE`、`STORAGE_MODE` 或 `LOVE_SONG_MODE`，并准备对应 `*.local.json`。`LOVE_SONG_MODE=http` 还需要先启动 love-song 当前代码服务，推荐本地端口为 `127.0.0.1:8001`；具体配置和命令见 `conf/README.md`。

## Pipeline Logs

后端关键链路使用 `web2audio.pipeline` logger 输出结构化 key-value 日志。默认日志级别是 `INFO`，可通过 `LOG_LEVEL` 调整。

按 `article_id` 定位单篇文章：

```bash
grep 'article_id=art_xxx' backend.log
```

关键事件：

| event | stage | 含义 |
| --- | --- | --- |
| `article_task_created` | `article_submission` | Chrome/API 提交已入库 |
| `article_waiting_for_worker` | `article_submission` | 文章等待正文处理 worker；如果只有这条，说明后续 worker 没有执行 |
| `text_processing_started` / `text_processing_ready` | `text_processing` | 正文清洗和分段开始 / 完成 |
| `audio_generation_started` / `audio_generation_ready` | `audio_generation` | TTS 生成和音频上传开始 / 完成 |
| `player_sync_started` / `player_sync_ready` | `player_sync` | love-song 资源登记和歌单追加开始 / 完成 |
| `*_failed` | 对应 stage | 对应阶段执行失败，日志包含 `error_code`，外部依赖错误会包含 `error_detail` |

排障判断：

- 只有 `article_task_created` 和 `article_waiting_for_worker`：文章已经入库，但正文处理 worker 没执行。
- 有 `text_processing_ready`，没有 `audio_generation_started`：正文处理完成，但 TTS worker 没执行。
- 有 `audio_generation_failed`：TTS 或 TOS 阶段已执行但失败，按 `error_code` 区分 `tts_generation_failed`、`audio_storage_failed`、`segments_missing`。
- 有 `audio_generation_ready`，没有 `player_sync_started`：音频已生成，但播放器同步 worker 没执行。
- 有 `player_sync_failed`：love-song 资源登记或歌单追加失败。

## Config

配置示例在 `conf/`：

- `.env.example`：环境变量示例，默认 `TTS_MODE=fake`、`STORAGE_MODE=fake`、`LOVE_SONG_MODE=fake`。
- `doubao.example.json`：豆包双向流式 TTS WebSocket 配置示例。
- `tos.example.json`：火山云 TOS 配置示例。
- `love_song.example.json`：love-song HTTP API 配置示例。
- `db.example.json`：MySQL URL 示例。

本地密钥文件使用 `conf/.env` 和 `conf/*.local.json`，不会提交。真实模式缺少配置文件或必填字段时会快速失败，不会静默回退到 fake。

## Database Schema

`Run` 中的建表命令会调用 `app.db.schema.ensure_database_schema()`，按当前运行时配置创建或补齐数据库表。

默认 `db.local.json` 的 active profile 是 `mysql`，会在当前 MySQL 数据库创建或补齐 `article_audio_items` 和 `article_tts_segments`。切换数据库或 profile 后，需要重新执行建表命令。

## Test

从仓库根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests
```
