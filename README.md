# web2audio

web2audio 是个人自用的网页转音频 MVP：在 Chrome 中一键提交当前文章，由服务端生成 TTS 音频，并复用 love-song iOS 播放器的队列、播放 URL 和播放历史，在通勤和车载场景连续收听。

## 当前状态

- 产品方案见 `docs/PRODUCT.md`。
- 技术方案见 `docs/TECHNICAL_DESIGN.md`。
- e2e-test-design 版端到端验收 case 见 `docs/E2E_ACCEPTANCE_CASES.md`；旧版领域拆分 case 见 `docs/END_TO_END_TEST_CASES.md`。
- 当前仓库已包含第一版 FastAPI 后端、正文清洗与分段、TTS/TOS/love-song client 边界、fake 全链路自测，以及 Chrome Manifest V3 插件提交入口。
- 本仓库 fake 自测链路可跑到文章 `playable`；真实 love-song 后端和 iOS 集成仍需单独实现。
- 统一启动与验证入口是 `./init.sh`。
- 功能拆解和完成证据以 `feature_list.json` 和 `progress.md` 为准。

## 本地启动

后端开发服务：

```bash
cd backend
uvicorn app.asgi:app --reload --host 127.0.0.1 --port 8000
```

Chrome 插件从 `extension/` 目录以 unpacked extension 方式加载。默认 API 地址是 `http://127.0.0.1:8000`，默认开发 token 是 `dev-token`。

后端默认使用 fake TTS、fake TOS 和 fake love-song client。真实豆包、火山云 TOS 和 love-song HTTP client 配置入口见 `backend/conf/README.md`。

## 验证

```bash
./init.sh
```

当前验证会检查 harness 文档、`feature_list.json` 结构，并运行后端 pytest 和 Chrome 插件正文提取测试。
