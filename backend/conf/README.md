# web2audio backend config

后端配置统一放在 `backend/conf/`，避免真实服务凭据散落在代码或测试里。

## 文件约定

- `.env.example`：环境变量示例，可以提交。
- `.env`：本地运行环境变量，不提交。
- `*.example.json`：外部服务配置示例，可以提交。
- `*.local.json`：本地密钥或线上环境配置，不提交。

## 运行模式

默认模式全部使用 fake client，适合本仓库自测：

- `TTS_MODE=fake`
- `STORAGE_MODE=fake`
- `LOVE_SONG_MODE=fake`
- 默认数据库使用 `DATABASE_URL=mysql+pymysql://...` 或 `db.local.json` 的 `mysql` profile。

接入真实服务时显式切换：

- `TTS_MODE=doubao`
- `STORAGE_MODE=tos`
- `LOVE_SONG_MODE=http`
- 如需使用 `db.local.json` 中的数据库 profile，保持 `DATABASE_URL` 为默认 MySQL URL，并设置 `DATABASE_PROFILE`；未设置时使用文件内 `active` profile。

真实模式会读取对应 `*.local.json`。配置文件缺失或必填字段为空时，服务会快速失败，不会静默回退到 fake。完整真实端到端还需要 `love_song.local.json`，并依赖 love-song 后端已实现 TOS 资源登记接口。

## 豆包 TTS 配置

真实豆包 TTS 使用火山「双向流式语音合成 WebSocket」协议，不再调用 Ark 文本模型的 REST `/audio/speech`。

`doubao.local.json` 最小字段：

```json
{
  "api_key": "控制台 API Key",
  "base_url": "wss://openspeech.bytedance.com/api/v3/tts/bidirection",
  "resource_id": "seed-tts-2.0",
  "speaker": "控制台音色 ID",
  "audio_format": "mp3",
  "sample_rate": 24000,
  "bit_rate": 128000
}
```

`resource_id` 当前支持 `seed-tts-2.0` 和 `seed-icl-2.0`。`speaker` 必须使用控制台音色库中的音色 ID；`voice` 仍作为兼容别名读取，但建议使用 `speaker`。

真实 TTS 调试用例默认跳过，手动启用命令：

```bash
W2A_RUN_REAL_DOUBAO_TTS=1 \
W2A_DOUBAO_TTS_OUTPUT=/tmp/web2audio-doubao-debug.mp3 \
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_live_tts.py -s
```

该命令会读取 `backend/conf/doubao.local.json`，真实调用火山接口并生成一段调试音频；不应放入默认 `./init.sh`。

## 火山云 TOS 配置

真实 TOS 上传使用 `backend/conf/tos.local.json`，最小字段：

```json
{
  "access_key_id": "控制台 AK",
  "access_key_secret": "控制台 SK",
  "endpoint": "tos-cn-shanghai.volces.com",
  "region": "cn-shanghai",
  "bucket": "bucket 名称",
  "object_prefix": "web2audio"
}
```

本地 MP3 到真实 TOS 的上传自测默认跳过，手动启用命令：

```bash
W2A_RUN_REAL_TOS_UPLOAD=1 \
W2A_TOS_UPLOAD_INPUT=/tmp/web2audio-doubao-debug.mp3 \
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python3 -m pytest -p no:cacheprovider backend/tests/test_tos_live_upload.py -s
```

默认会在上传和 `head_object` 校验后删除测试 object。需要保留远端 object 作为跨系统联调输入时，额外设置 `W2A_TOS_KEEP_OBJECT=1`。

## love-song HTTP 配置

真实 love-song 后端使用 `backend/conf/love_song.local.json`，最小字段：

```json
{
  "base_url": "http://127.0.0.1:8001",
  "service_token": "",
  "timeout": 20
}
```

当前本地联调使用 8001 上的 love-song 当前代码服务；8000 旧进程未加载 `/api/assets/tos` 时会返回 404。

启动 love-song 8001 的本地命令：

```bash
cd /Users/bytedance/Codebases/love-song/backend
UV_CACHE_DIR=/tmp/love-song-uv-cache \
UV_PYTHON_INSTALL_DIR=/tmp/love-song-uv-python-managed \
UV_PROJECT_ENVIRONMENT=/tmp/love-song-backend-venv \
uv run --project . --python 3.12 --extra dev \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## live E2E 验证

真实 Doubao + 真实 TOS 的 audio job 验证默认跳过，手动启用命令：

```bash
W2A_RUN_REAL_AUDIO_JOB=1 \
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python3 -m pytest -p no:cacheprovider \
  backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_008_real_doubao_tts_and_tos_audio_job -s
```

真实 Doubao + 真实 TOS + 真实 love-song HTTP 后端链路验证默认跳过，手动启用命令：

```bash
W2A_RUN_REAL_FULL_CHAIN=1 \
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python3 -m pytest -p no:cacheprovider \
  backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_010_real_doubao_tos_and_love_song_full_chain -s
```

live E2E 会产生真实外部调用。默认会清理 web2audio 测试数据、TOS object 和 love-song playlist item；需要保留远端对象时设置 `W2A_E2E_KEEP_OBJECTS=1`，需要保留歌单项时设置 `W2A_E2E_KEEP_LOVE_SONG_TRACK=1`。
