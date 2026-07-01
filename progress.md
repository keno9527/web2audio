# 会话进度记录

## 当前状态

**最后更新：** 2026-06-30 17:04 CST
**当前功能：** 后端文章转音频链路日志可观测性
**阶段：** 已新增 `web2audio.pipeline` 结构化日志，覆盖文章提交、正文处理、音频生成和播放器同步关键阶段；日志可通过同一个 `article_id` 判断停在提交、正文、TTS/TOS 或 love-song 同步哪个环节。当前确认 Chrome 提交接口只负责入库，不会自动触发后续 worker；默认 `./init.sh` 后端 39 passed、7 skipped，插件 5 passed。

## 已完成

- 已确认当前目录是 `/Users/bytedance/Codebases/web2audio`。
- 已阅读 `AGENTS.md`、`README.md`、`docs/PRODUCT.md`、`docs/TECHNICAL_DESIGN.md`、`feature_list.json`、`progress.md` 和 `session-handoff.md`。
- 已运行 `./init.sh`，确认当前文档和 harness 基线可用。
- 已定位 Chrome 插件弹窗裸露 `Could not establish connection. Receiving end does not exist.` 的原因：`popup.js` 对当前标签页直接 `chrome.tabs.sendMessage`，缺少 content script 接收端缺失时的注入重试和页面协议提示。
- 已新增 `extension/tests/popup.test.cjs`，覆盖普通文章页 URL 判断、接收端缺失后自动注入 `content.js` 并重试、`chrome://` 等不支持页面不发送消息。
- 已重构 `extension/popup.js` 的可测试通信逻辑：DOM 绑定只在浏览器 popup 环境执行，`extractArticleFromTab` 可在 node:test 中验证；正常页先发消息，接收端缺失时通过 `chrome.scripting.executeScript` 注入 `content.js` 后重试。
- 已更新 `init.sh`：找不到系统 `node` 时使用 Codex 本地 Node 运行时，并将 Chrome 插件验证扩展为 `extension/tests/*.test.cjs`。
- 已更新 `extension/README.md`：补充插件重新加载、普通网页使用边界和全部插件测试命令。
- 已确认 Chrome 提交后 DB 可见但没有转语音的直接原因：`POST /api/articles` 仅创建文章任务并返回，后续 `process_article_text`、`process_article_audio`、`process_player_sync` 目前由测试或外部 worker 手动调用，服务端没有在提交接口内自动触发。
- 已新增 `backend/app/observability.py`，提供 `configure_logging()` 和 `log_pipeline_event()`，统一输出 `web2audio.pipeline` key-value 日志。
- 已在 `backend/app/main.py` 为新建、重复提交和等待 worker 增加日志：`article_task_created`、`article_task_duplicate`、`article_waiting_for_worker`。
- 已在 `backend/app/text_jobs.py`、`backend/app/audio_jobs.py` 和 `backend/app/player_sync_jobs.py` 增加阶段日志：`*_started`、`*_ready`、`*_failed`，失败日志包含 `error_code`，外部依赖异常包含 `error_detail`。
- 已新增 `backend/tests/test_pipeline_logging.py`，覆盖提交后只出现等待正文 worker 日志，以及 text/audio/player 三段用同一个 `article_id` 串起完整日志。
- 已更新 `backend/README.md` 的 Pipeline Logs 章节，给出按 `article_id` grep 和根据缺失事件定位未执行阶段的规则。
- 已将 `docs/PRODUCT.md` 收敛为产品方案文档，只保留产品目标、系统边界、核心流程、功能范围、验收标准和待确认项。
- 已移除产品文档中直接描述数据表、接口路径、字段枚举和车载/后台能力的实现细节。
- 已新增 `docs/TECHNICAL_DESIGN.md`，基于产品方案沉淀技术设计，覆盖总体架构、数据库表设计、状态流转、web2audio API、love-song 集成契约、mock 数据约束验证和契约测试。
- 已按最新产品边界更新 `feature_list.json` 中 feat-004、feat-005、feat-006 的描述。
- 已按浏览器评论更新 `docs/TECHNICAL_DESIGN.md`：补充 ER 表级 COMMENT 备注，解释 `article_tts_segments` 和 `snake_case`。
- 已从技术方案中移除 `failure_reason`、`audio_mime_type`、`retry_count`、`tts_provider`、`voice_id` 等不必要持久化字段。
- 已移除公开 `POST /api/articles/{article_id}/retry` 设计，失败详情改为通过任务日志和请求 ID 排查。
- 已将 mock URL 改为公开文章 URL `https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ`。
- 已确认第一版 TTS 使用豆包 lite 模型，音频对象存储使用火山云 TOS。
- 已补充 love-song 资源登记 API 的跨工程落地方式，并将「今日待读」改为固定 `playlist_id` 配置依赖。
- 已创建 `codex/feat-002-submit-entry` 分支推进实现，避免在 `main` 上直接开发。
- 已新增 FastAPI 后端第一版文章任务 API：
  - `GET /api/health`
  - `POST /api/articles`
  - `GET /api/articles/{article_id}`
  - `GET /api/articles`
- 已实现文章提交鉴权、请求校验、原始 `source_url` 精确去重、状态映射和统一错误结构。
- 已新增 Chrome Manifest V3 插件提交入口，从当前页面提取标题、来源 URL、正文和常见元信息，并提交到后端。
- 已将后端 pytest 和插件 node:test 接入 `./init.sh`。
- 已更新 `README.md`、`backend/README.md` 和 `extension/README.md`，记录本地启动与验证方式。
- 已将 `feature_list.json` 中 `feat-002` 标记为 `done`，并写入验证证据。
- 已按可并行工作流重拆 `feature_list.json`：保留 `feat-001`、`feat-002` 完成态，将后续任务拆为正文清洗、TTS/TOS 产物、跨工程契约、love-song 后端、love-song iOS、web2audio 同步 worker 和端到端验收。
- 已在 `feature_list.json` 中新增 `workstream`、`parallel_group` 和 `parallel_notes` 字段，用于标识可并行开发批次和依赖边界。
- 已选择 `feat-003` 作为本次唯一推进对象。
- 已先新增正文处理测试并确认 RED：缺少 `app.text_processing` 和 `ArticleTtsSegment`。
- 已新增 `app.text_processing`，支持正文清洗、语言归一或检测、最小长度校验和按字符上限分段。
- 已新增 `article_tts_segments` SQLAlchemy 模型，使用 `segment_id` 业务 ID 和 `(article_id, segment_index)` 组合唯一约束。
- 已新增 `app.text_jobs.process_article_text`，将文章从 `text_status=queued/processing` 推进到 `ready` 或 `failed`，并写入清洗正文和 TTS 分段。
- 已将 `./init.sh` 后端测试范围扩展到整个 `backend/tests`。
- 已将 `feature_list.json` 中 `feat-003` 标记为 `done`，并写入验证证据。
- 已选择 `feat-004` 作为继续推进对象。
- 已先新增 audio job 测试并确认 RED：缺少 `app.audio_jobs`。
- 已新增 `app.audio_jobs`，提供 fake 豆包 lite TTS client、fake 火山云 TOS storage 和 `process_article_audio`。
- 已实现分段 TTS 生成、分段音频对象写入、最终音频合成、最终 TOS object 写入和 `audio_status=ready/failed` 回写。
- 已将 `feature_list.json` 中 `feat-004` 标记为 `done`，并写入验证证据。
- 已选择 `feat-005` 作为继续推进对象。
- 已先新增 love-song contract 测试并确认 RED：缺少 `app.love_song_contract`。
- 已新增 `app.love_song_contract`，冻结 TOS 资源登记、`content_type=article_audio`、`subtitle`、`source_type=tos`、`external_source + external_id` 幂等和歌单追加幂等语义。
- 已将 `feature_list.json` 中 `feat-005` 标记为 `done`，并写入验证证据。
- 已选择 `feat-008` 作为继续推进对象。
- 已先新增播放器同步 worker 测试并确认 RED：缺少 `app.player_sync_jobs`。
- 已新增 `app.player_sync_jobs`，支持 audio ready 文章登记 fake love-song TOS 资源、追加固定歌单、重复同步幂等和失败状态回写。
- 已将 `feature_list.json` 中 `feat-008` 标记为 `done`，并写入验证证据。
- 已新增 `feat-009` 本仓库 fake 全链路自测，避免把 fake 自测与真实 love-song/iOS 验收混淆。
- 已先新增 fake 全链路测试并确认 RED：缺少 `app.self_test`。
- 已新增 `app.self_test.run_fake_full_chain`，串起 API 提交、正文处理、音频产物、fake love-song 同步和文章详情 playable 校验。
- 已将 `feature_list.json` 中 `feat-009` 标记为 `done`，并保留 `feat-006`、`feat-007`、`feat-010` 表示真实跨工程落地仍未完成。
- 已更新 `AGENTS.md`：启动流程补充 `docs/TECHNICAL_DESIGN.md` 和 `session-handoff.md`，工作规则区分产品功能推进与 harness 文档维护，验证说明覆盖后端全量 pytest、插件测试和 fake 全链路边界。
- 已将 `docs/TECHNICAL_DESIGN.md` 纳入 `init.sh` 必需文件检查。
- 已更新 `feature_list.json` 中 `feat-001` 的 harness 维护证据。
- 已对照 `/Users/bytedance/Codebases/love-song/backend` 的配置目录、`app/core/config.py`、`app/db/session.py` 和 TOS/Doubao 配置示例，确认 web2audio 需要拆分运行时配置、DB session 和外部依赖 client。
- 已新增 `backend/conf/` 配置示例与说明，默认 fake 模式，真实豆包、TOS 和 love-song HTTP 模式通过 `.env` 显式切换。
- 已新增 `backend/app/core/config.py`、`backend/app/db/session.py`、`backend/app/clients/*` 和 `backend/app/runtime.py`，把 fake client、真实 client 和业务 job 协议边界拆开。
- 已将 `process_article_audio` 和 `process_player_sync` 改为依赖 `TtsClient`、`AudioStorage` 和 `LoveSongClient` 协议，不再直接绑定 fake 实现。
- 已新增 love-song HTTP client，按契约调用 `POST /api/assets/tos` 和 `POST /api/playlists/{playlist_id}/tracks`，并将 `track_already_in_playlist` 视为幂等成功。
- 已保留本仓库 fake 全链路自测入口，确保不依赖真实外部服务也能验证到 `playable`。
- 已新增 `docs/END_TO_END_TEST_CASES.md`，按文章收集、正文处理、音频生成、播放器同步、播放体验和运行时配置六个领域设计端到端测试 case。
- 已在端到端测试设计中区分 L1 mock 自动化、L2 线上配置联调和 L3 iOS 验收，保留 `./init.sh` 只运行本地稳定测试的边界。
- 已设计 mock 分支、真实豆包/TOS 分支、真实 love-song HTTP 分支、完整线上分支和 iOS 手工验收分支，并标注优先级、前置条件和断言。
- 已将端到端测试 case 文档以用户身份导入飞书：`https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b`；旧 bot 文档仍受应用后台 scope 限制，不作为交付链接。
- 已在 `docs/END_TO_END_TEST_CASES.md` 和飞书文档中补充 case 状态标注：`E2E-MOCK-001` 已自动化通过，`E2E-MOCK-002`、`E2E-MOCK-003`、`E2E-MOCK-006` 部分自动化通过，`E2E-MOCK-004`、`E2E-MOCK-005` 待自动化，所有 `E2E-ONLINE-*` 和 `E2E-IOS-*` 待确认。
- 已按 `e2e-test-design` skill 新增 `docs/E2E_ACCEPTANCE_CASES.md`，围绕验收目标、环境准备、Case 矩阵、关键 case 明细、已自动化通过、待确认、P0/P1/P2 和剩余风险组织内容。
- 已在 `docs/E2E_ACCEPTANCE_CASES.md` 中设计 14 个端到端验收 case，覆盖本仓库 mock 闭环、运行时配置、Chrome 插件入口、真实豆包/TOS/love-song 分支和 iOS 人工验收分支。
- 已将 `W2A-E2E-001`、`W2A-E2E-006`、`W2A-E2E-007` 标注为已自动化通过；将真实 TTS/TOS、真实 love-song、完整线上链路、iOS 播放和清理策略相关 case 标注为待确认或阻塞。
- 已以用户身份创建新的飞书文档：`https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb`，并通过 outline 与 `W2A-E2E-001` 关键词读取校验内容可见。
- 已简化 `docs/E2E_ACCEPTANCE_CASES.md` 的 E2E Case 矩阵：从 11 列收敛为 `Case ID`、`Case 分类`、`验收目标`、`执行分支`、`核心断言`、`跟进状态`、`优先级` 7 列；环境、前置数据、操作路径和验收证据保留在环境准备和关键 case 明细中。
- 已将简化后的 `docs/E2E_ACCEPTANCE_CASES.md` 覆盖同步到飞书文档 `https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb`，并通过关键词读取验证矩阵表头和 `W2A-E2E-014` 行可读。
- 已按当前 `backend/conf/*.local.json` 做端到端调试：默认 fake 基线通过；真实 Doubao + 真实 TOS + fake love-song 分支失败于 Doubao TTS，错误为 `POST https://ark.cn-beijing.volces.com/api/v3/audio/speech` 返回 404；fake TTS + 真实 TOS 分支失败于 TOS `NoSuchBucket`。
- 已确认当前 `backend/conf/` 存在 `db.local.json`、`doubao.local.json` 和 `tos.local.json`，但不存在 `love_song.local.json`；完整真实 love-song HTTP 分支无法在本仓库闭环。
- 已修复 settings 未读取 `db.local.json` active profile 的问题：`Settings.resolve_database_url()` 会在 `DATABASE_URL` 保持默认值时读取 `DATABASE_CONFIG_PATH` 和 `DATABASE_PROFILE`。
- 已修复 `process_article_audio` 将 TOS 上传失败误归类为 `tts_generation_failed` 的问题：TTS 合成失败返回 `tts_generation_failed`，分段或最终音频上传失败返回 `audio_storage_failed`，并在内部结果中保留 `error_detail`。
- 已补齐 `backend/conf/love_song.example.json`，并在 `.env.example` 与 `backend/conf/README.md` 中补充 DB profile 和 love-song local 配置说明。
- 已确认 love-song 8000 旧进程未加载新增 `/api/assets/tos`，返回 404；已在 8001 启动当前代码新进程用于本次联调。
- 已定位并修复 love-song live MySQL 下 `POST /api/assets/tos` 的 FK flush 问题：创建 track 后先 `flush()`，再创建 audio asset，避免 MySQL 先插入 `audio_assets` 导致 `fk_audio_assets_track_id` 失败。
- 已验证 love-song 8001：`POST /api/assets/tos` 返回 201，`POST /api/playlists/demo_playlist_focus/tracks` 返回 201。
- 已跑 web2audio 真实 Doubao + 真实 TOS + 真实 love-song HTTP 完整链路：提交和正文处理成功，音频阶段仍失败于 Doubao `/api/v3/audio/speech` 404，未进入 TOS 上传和 love-song 同步。
- 已隔离验证真实 TOS 上传仍失败：`tos.local.json` 指向的 bucket 返回 `NoSuchBucket`。
- 已跑 web2audio fake TTS + fake storage + 真实 love-song HTTP 分支：文章任务最终返回 `playable`，love-song 返回 `track_1b8f330840b24282b53f`、`asset_e919410075c440fc8e7c`，并追加到 `demo_playlist_focus`。
- 已读取 love-song 歌单详情确认新文章音频位于 position 7，`content_type=article_audio`，`subtitle=Example`。
- 已参考火山文档 `https://www.volcengine.com/docs/6561/2532486?lang=zh`，通过文档中心接口确认页面标题为「双向流式语音合成WebSocket」，WSS 地址为 `wss://openspeech.bytedance.com/api/v3/tts/bidirection`，请求头为 `X-Api-Key`、`X-Api-Resource-Id`、`X-Api-Connect-Id`，客户端事件包括 `StartConnection`、`StartSession`、`TaskRequest`、`FinishSession`、`FinishConnection`。
- 已下载官方附件 `TTS Websocket Bidirection protocols.zip` 并核对二进制消息封装：`FullClientRequest + WithEvent` 携带事件号、会话 ID 和 JSON payload，服务端音频可通过 `AudioOnlyServer` 或 `TTSResponse` 返回。
- 已将 `DoubaoTtsClient` 从 HTTP `POST /audio/speech` 改为火山双向 WebSocket：建连、创建会话、发送文本、结束会话、收集音频 chunk、结束连接，并保留现有同步 `TtsClient.synthesize()` 协议。
- 已新增 Doubao WebSocket client 测试，覆盖配置默认值、请求头、事件顺序、`StartSession` / `TaskRequest` payload、音频 chunk 汇总和 `SessionFailed` 错误传播。
- 已更新 `doubao.example.json`、`backend/conf/README.md`、`backend/README.md`、`docs/TECHNICAL_DESIGN.md` 和 `feature_list.json`，将旧 Ark REST / lite 表述收敛为火山双向流式 TTS WebSocket 配置。
- 已将 `websockets` 写入 `backend/requirements.txt`，避免真实运行依赖隐式全局环境。
- 已用当前 `doubao.local.json` 做构建诊断：快速失败信息为 `missing required fields: speaker; base_url must be a WebSocket URL; resource_id must be one of: seed-icl-2.0, seed-tts-2.0`，不会再继续请求错误的 `/audio/speech`。
- 已根据火山「接入语音模型」示例修正 `TaskRequest` payload：文本放入 `req_params.text`，并携带 `speaker`、`audio_params`、语速、音量和显式语言；真实服务不再返回空文本 `TTSSentenceStart`。
- 已扩展 `AudioSynthesisResult.metadata`，Doubao 结果会返回 `provider`、`connect_id`、`session_id` 和 `SessionFinished` 中的 `usage`，便于调试请求与计费字符数。
- 已新增 `backend/tests/test_doubao_live_tts.py` 真实 TTS 调试用例：默认跳过，设置 `W2A_RUN_REAL_DOUBAO_TTS=1` 后读取 `backend/conf/doubao.local.json` 真连火山。
- 已用当前 `backend/conf/doubao.local.json` 跑通真实 Doubao TTS 调试：生成 `/tmp/web2audio-doubao-debug.mp3`，文件大小 54K，`file` 识别为 128 kbps、24 kHz、单声道 MP3。
- 已确认当前 `backend/conf/db.local.json` 的 active profile 是 `mysql`，目标数据库为 SQLAlchemy 兼容的 MySQL URL。
- 已新增 `app.db.schema.ensure_database_schema()`，按当前配置创建或补齐数据库表。
- 已将 `article_audio_items` 和 `article_tts_segments` 的索引、CHECK 约束补进 SQLAlchemy schema，并通过 MySQL 外键约束校验分段引用。
- 已在当前 active MySQL 中创建或补齐 web2audio 数据库表；inspect 结果确认两张表、`idx_article_audio_items_owner_status`、`idx_article_audio_items_love_song_track_id`、`idx_article_tts_segments_article_status` 和状态 CHECK 约束存在。
- 已新增 `backend/tests/test_db_schema.py`，覆盖 schema 创建、索引、CHECK 约束和 MySQL 外键约束。
- 已更新 `docs/E2E_ACCEPTANCE_CASES.md` 当前端到端 case 状态：`W2A-E2E-001` 到 `W2A-E2E-007` 按 2026-06-30 `./init.sh` 结果标为已自动化通过；`W2A-E2E-008` 和 `W2A-E2E-010` 保留显式 live 自动化通过记录；`W2A-E2E-009` 保持已人工通过；`W2A-E2E-011`、`W2A-E2E-012`、`W2A-E2E-013` 已改为 iOS 对应接口自动化并通过。
- 已将端到端 case 状态覆盖同步到飞书文档 `https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb`，最新飞书 revision_id 为 54，并通过 `W2A-E2E-011`、`live 批量 3 passed`、`37 passed` 和 `W2A_RUN_REAL_FULL_CHAIN=1` 关键词读取验证。
- 已用当前 `backend/conf/tos.local.json` 复现本地 MP3 直传远端 TOS，`/tmp/web2audio-doubao-debug.mp3` 上传成功，`head_object` 返回 55341 bytes。
- 已新增 `backend/tests/test_tos_live_upload.py`，默认跳过；设置 `W2A_RUN_REAL_TOS_UPLOAD=1` 后读取本地 MP3、上传到真实 TOS、校验 object 存在和 content length，并支持 `W2A_TOS_KEEP_OBJECT=1` 保留远端 object。
- 已在 `backend/conf/README.md` 补充真实 TOS 上传自测命令和保留 object 开关。
- 已按 E2E Case 矩阵补齐 `backend/tests/test_fake_full_chain.py` 自动化：覆盖重复提交幂等、正文不可用不生成音频、TTS 失败无可播放副作用、love-song 同步失败后保留音频并可恢复。
- 已更新 `docs/E2E_ACCEPTANCE_CASES.md`：`W2A-E2E-002`、`W2A-E2E-003`、`W2A-E2E-004`、`W2A-E2E-005` 从待自动化改为已自动化通过；默认自动化通过集扩展为 `W2A-E2E-001` 到 `W2A-E2E-007`。
- 已新增 `backend/tests/test_webpage_text_db_chain.py`，用 Node 调用真实 `extension/content.js` 提取网页 payload，再经 `POST /api/articles`、`process_article_text` 验证 MySQL `article_audio_items` 主表和 `article_tts_segments` 分段表落库。
- 已更新 `docs/E2E_ACCEPTANCE_CASES.md` 中 `W2A-E2E-007`：验收目标收敛为插件提取 payload 后写入正文数据库，自动化证据包含 `backend/tests/test_webpage_text_db_chain.py`，最新默认验证结果为后端 37 passed、7 skipped，插件 2 passed。
- 已新增 `backend/tests/test_live_e2e_external_chain.py`，默认跳过；显式开启后覆盖 `W2A-E2E-008` 真实 Doubao + TOS audio job，以及 `W2A-E2E-010` 真实 Doubao + TOS + love-song HTTP 后端完整链路。
- 已补齐本地忽略配置 `backend/conf/love_song.local.json`，指向 love-song 当前代码服务 `http://127.0.0.1:8001`。
- 已验证 love-song 8001 当前代码服务可用，`GET /api/playlists` 返回 200，目标歌单 `demo_playlist_focus` 存在。
- 已运行 `W2A_RUN_REAL_AUDIO_JOB=1 ... test_w2a_e2e_008_real_doubao_tts_and_tos_audio_job -s`，通过；真实 Doubao 合成、真实 TOS 上传和 object head 校验通过。
- 已运行 `W2A_RUN_REAL_FULL_CHAIN=1 ... test_w2a_e2e_010_real_doubao_tos_and_love_song_full_chain -s`，通过；同一篇文章到 `playable`，love-song 歌单回读 `content_type=article_audio`、`subtitle=site_name`。
- 已更新 `docs/E2E_ACCEPTANCE_CASES.md`：`W2A-E2E-008` 和 `W2A-E2E-010` 从待确认改为已自动化通过；`W2A-E2E-011` 到 `W2A-E2E-013` 已改为 iOS 对应接口自动化并标为已自动化通过。
- 已在 `backend/conf/README.md` 记录 `love_song.local.json` 格式，以及 `W2A_RUN_REAL_AUDIO_JOB=1`、`W2A_RUN_REAL_FULL_CHAIN=1` 两个 live E2E 复跑命令。
- 已将 `feature_list.json` 中 `feat-010` 更新为 `in-progress`，证据记录后端真实依赖 live 已通过、iOS 对应接口自动化已通过，真机体验只保留可选抽查。
- 已把 `W2A-E2E-011` 到 `W2A-E2E-013` 从 iOS 人工端测试改为通过 love-song iOS 对应 HTTP 接口做接口自动化：
  - 在 `backend/tests/test_live_e2e_external_chain.py` 抽出 `run_full_chain_to_playable` 复用真实 Doubao + TOS + love-song HTTP 全链路，并新增 `love_song_get_playlist`、`love_song_post`、`love_song_patch` 调用 iOS 对应接口。
  - `W2A-E2E-011`：歌单详情含文章 track，`POST /api/playback-sessions` 定位该 track 和 asset，`POST /api/playback-url` 返回 `source_type=tos`、`mime_type=audio/mpeg`，`url` 等于文章 `audio_storage_key`。
  - `W2A-E2E-012`：歌单详情 track `content_type=article_audio`、`title=文章标题`、`subtitle=site_name`、`artist=null`、`album=null`、`duration_seconds` 与 web2audio 一致。
  - `W2A-E2E-013`：两篇文章 position 连续，播放会话 `ordered_track_ids` 顺序一致，逐首 `playback-url` 返回各自音频 URL，`PATCH /api/playback-sessions/{id}` 切到第二篇后 `current_asset_id` 匹配，`POST /api/play-history` 写入两条 article track。
  - 三个用例由 `W2A_RUN_REAL_FULL_CHAIN=1` 显式开启，默认 `./init.sh` 跳过。
- 已在 8001 启动 love-song 当前代码服务并实跑三个 live 用例，`3 passed`。
- 已更新 `docs/E2E_ACCEPTANCE_CASES.md`：`W2A-E2E-011`、`W2A-E2E-012`、`W2A-E2E-013` 矩阵分类改为接口自动化、跟进状态改为已自动化通过；关键 case 明细重写为 iOS 接口操作路径与断言；已自动化通过表、待确认表、冒烟/回归集状态、剩余风险和第 1、2 章环境说明同步更新。
- 已将 `feature_list.json` 中 `feat-010` 证据更新为 iOS 接口自动化通过记录。

## 正在处理

- 无。

## 下一步

1. 如需真机或模拟器体验抽查，覆盖 `W2A-E2E-011` 到 `W2A-E2E-013` 的实际播放流畅度和文案渲染。
2. 如需要重新确认外部依赖漂移，再显式开启 `W2A_RUN_REAL_AUDIO_JOB=1` 或 `W2A_RUN_REAL_FULL_CHAIN=1` 复跑 live 自动化。
3. 如目标是其它远端 MySQL，需要替换 `backend/conf/db.local.json` 或 `DATABASE_URL` 后执行 schema 初始化或迁移；当前更新的是 active MySQL profile。

## 风险与阻塞

- 当前 active 数据库已更新为 MySQL；目标环境切换时仍需在对应 MySQL 实例执行 schema 初始化或迁移。
- 当前插件正文提取为第一版启发式规则，复杂站点正文质量仍需通过后续清洗链路兜底。
- 当前网页到 DB 自动化覆盖的是 Node 直接调用 extractor、后端 API 和正文处理链路，不覆盖真实 Chrome 点击、popup UI 权限或任意复杂网页的正文质量。
- Chrome 内部页面、Chrome Web Store 和扩展管理页仍不支持正文提取；插件会在这些页面返回中文提示，不能绕过浏览器限制。
- 本地未通过自动化控制 Chrome 内部扩展页安装插件；更新 unpacked 插件代码后仍需在 `chrome://extensions` 手动点击该扩展卡片的刷新图标。
- Chrome 提交接口当前只入库并记录 `article_waiting_for_worker`，不自动执行正文处理、TTS/TOS 或 love-song 同步；如果日志中只有提交阶段事件，需要启动或手动调用后续 worker。
- 当前后端已完成文章任务提交、查询、正文清洗、分段、fake TTS/TOS 音频产物、fake love-song 同步，以及显式开启的真实 Doubao/TOS/love-song HTTP 后端链路验证。
- 本仓库 fake 自测已到 `playable`；真实后端链路也已到 `playable`；iOS 对应接口层已自动化通过，真机或模拟器播放体验仍可作为可选抽查。
- love-song 当前代码服务 8001 已提供 `POST /api/assets/tos` 并通过 W2A-E2E-010；8000 旧进程仍返回 404，需要环境固化。
- iOS 避免「未知艺术家」「首歌」等音乐化文案的接口语义已由 `W2A-E2E-012` 覆盖；模拟器或真机仍可抽查最终视觉渲染。
- 豆包 TTS client 当前已按双向 WebSocket 协议真实生成音频，但时长仍按字符数估算；真实音频时长精确计算仍需后续接入音频探测或 provider 元数据。
- `W2A-E2E-008` 和 `W2A-E2E-010` 的 live 自动化默认跳过；外部配置或远端服务变更后，需要显式开启环境变量复跑确认。
- 当前 `backend/conf/love_song.local.json` 已指向 `http://127.0.0.1:8001`；该文件属于本地忽略配置，不应提交密钥。
- love-song 8000 仍是旧进程，`POST /api/assets/tos` 返回 404；当前验证通过 8001 当前代码服务完成。
- love-song iOS 文章音频展示语义已通过 iOS 对应接口自动化验证；真实模拟器或真机只保留体验层抽查。

## 已做决策

| 决策 | 原因 | 影响 |
| --- | --- | --- |
| 产品文档不承载技术方案 | 降低产品评审阅读成本 | 表结构、API、枚举和测试策略转入 `docs/TECHNICAL_DESIGN.md` |
| 第一版只要求 iOS 播放器内连续播放文章音频 | MVP 收敛 | 后台播放、锁屏控制、CarPlay 不纳入第一版验收 |
| `source_url` 精确去重 | 简化重复提交规则 | 不做 canonical URL 或正文 hash 合并 |
| web2audio 与 love-song 通过 HTTP API 解耦 | 避免跨系统直接写库 | love-song 需要提供幂等资源登记能力 |
| 「今日待读」为固定系统托管歌单 | 复用播放器现有歌单顺序 | web2audio 只追加，不维护独立播放排序 |
| 失败详情不进入业务表 | 错误原因类型不稳定，且容易泄漏内部细节 | 失败排障通过日志按业务 ID 和请求 ID 查询 |
| 不暴露公开重跑 API | 当前技术方案先收敛提交和查询契约 | 失败任务重跑由后端任务系统或运维动作触发 |
| 第一版使用豆包语音合成 WebSocket | 收敛 TTS 选型并对齐火山真实协议 | `resource_id`、音色和凭据进入运行时配置，不进入业务表 |
| 第一版使用火山云 TOS | 收敛对象存储选型 | web2audio 与 love-song 传递 object key，不传云凭据 |
| 后续任务按工作流并行拆分 | 原串行依赖把 web2audio、love-song 后端和 iOS 强行排成单链路 | `feature_list.json` 现在用 `parallel_group` 表达可并行批次，用真实依赖控制最终集成 |
| 默认 runtime 使用 fake client | 保持本仓库自测稳定，不依赖外部服务和密钥 | 真实豆包/TOS/love-song 必须通过 `.env` 显式切换 |
| 真实 runtime 配置缺失时快速失败 | 避免线上误用 fake 或半配置状态 | `build_tts_client`、`build_audio_storage`、`build_love_song_client` 会抛出配置错误 |

## 本次修改文件

- `docs/PRODUCT.md`：更新为产品方案文档，收敛 MVP 范围和 love-song 产品边界。
- `docs/TECHNICAL_DESIGN.md`：新增技术方案，覆盖数据库设计、API 设计和 love-song 集成契约。
- `feature_list.json`：同步更新 TTS 和播放器接入功能描述。
- `progress.md`：记录本次文档更新、决策和验证。
- `session-handoff.md`：更新跨会话交接信息。
- `README.md`：更新当前状态、本地启动和验证说明。
- `.gitignore`：忽略 Python 测试缓存、字节码和本地密钥配置。
- `backend/`：新增 FastAPI 后端、文章任务 API、测试和运行说明。
- `extension/`：新增 Chrome Manifest V3 插件、弹窗提交入口、正文提取测试和使用说明。
- `init.sh`：接入后端 pytest 和插件 node:test 验证。
- `feature_list.json`：按并行工作流重拆未完成任务，新增并行批次和工作流标记。
- `backend/app/text_processing.py`：新增正文清洗、语言识别和分段纯函数。
- `backend/app/text_jobs.py`：新增文章正文处理 service。
- `backend/app/main.py`：新增 `article_tts_segments` 模型，并暴露测试可用的 session factory。
- `backend/tests/test_text_processing.py`：新增正文清洗和过短正文测试。
- `backend/tests/test_text_jobs.py`：新增文章处理后写入分段和 ready 状态的集成测试。
- `AGENTS.md`：更新启动阅读范围、工作规则、完成标准、验证范围和 fake / 真实验收边界。
- `backend/app/audio_jobs.py`：新增 fake TTS/TOS audio job。
- `backend/tests/test_audio_jobs.py`：新增音频产物生成和 text not ready 失败测试。
- `backend/app/love_song_contract.py`：新增 love-song TOS 资源登记和歌单追加契约对象及 fake client。
- `backend/tests/test_love_song_contract.py`：新增资源登记和歌单追加幂等测试。
- `backend/app/player_sync_jobs.py`：新增播放器同步 worker。
- `backend/tests/test_player_sync_jobs.py`：新增播放器同步和 audio not ready 失败测试。
- `backend/app/self_test.py`：新增 fake 全链路自测入口。
- `backend/tests/test_fake_full_chain.py`：新增本仓库 fake 全链路自测。
- `backend/conf/`：新增 `.env`、DB、豆包、TOS 和 love-song 配置示例。
- `backend/app/core/config.py`：新增运行时配置入口。
- `backend/app/db/session.py`：新增 DB engine 与 session factory 边界。
- `backend/app/clients/`：新增 fake client、豆包 TTS、TOS storage 和 love-song HTTP client。
- `backend/app/runtime.py`：新增按配置构建外部依赖 client 的工厂。
- `backend/tests/test_runtime_config.py`：新增 runtime 配置和 client 选择测试。
- `backend/tests/test_love_song_http_client.py`：新增 love-song HTTP client 契约测试。
- `backend/tests/test_db_session.py`：新增 DB session 工厂和 `create_app(settings=...)` 测试。
- `docs/END_TO_END_TEST_CASES.md`：新增端到端测试 case 设计，覆盖 mock、线上配置和 iOS 验收分支。
- `docs/END_TO_END_TEST_CASES.md`：补充 case 状态口径、状态总览，以及每个 case 的自动化状态、通过证据和待确认项。
- `docs/E2E_ACCEPTANCE_CASES.md`：新增 e2e-test-design 版端到端验收 case 文档，覆盖 Case 矩阵、关键 case、自动化通过状态、待确认状态和 P0/P1/P2 回归集。
- `backend/app/core/config.py`：新增 `db.local.json` active profile 解析。
- `backend/app/db/session.py`：默认 session factory 使用解析后的数据库 URL。
- `backend/app/main.py`：应用工厂使用解析后的数据库 URL。
- `backend/app/audio_jobs.py`：区分 TTS 生成失败和音频存储失败，并返回内部错误详情。
- `backend/conf/.env.example`：补充 DB config/profile 环境变量入口。
- `backend/conf/README.md`：补充 DB profile、真实 love-song local 配置和完整真实端到端边界。
- `backend/conf/love_song.example.json`：新增 love-song HTTP 配置示例。
- `backend/tests/test_runtime_config.py`：新增 DB active profile 解析测试。
- `backend/tests/test_audio_jobs.py`：新增存储失败分类测试。
- `backend/app/clients/doubao.py`：改为火山双向流式 TTS WebSocket client。
- `backend/tests/test_doubao_tts_client.py`：新增 Doubao WebSocket 请求与交互测试。
- `backend/tests/test_doubao_live_tts.py`：新增真实 Doubao TTS 手动调试用例，默认跳过。
- `backend/app/clients/tts.py`：为 TTS 结果新增 provider metadata。
- `backend/conf/doubao.example.json`：更新真实 TTS 配置示例为 WSS endpoint、`resource_id`、`speaker` 和音频参数。
- `backend/conf/README.md`：补充真实豆包 TTS WebSocket 配置说明。
- `backend/app/db/schema.py`：新增数据库 schema 初始化入口。
- `backend/tests/test_db_schema.py`：新增数据库表、索引、CHECK 约束和 MySQL 外键约束测试。
- `backend/app/db/session.py`：默认 session factory 使用 MySQL 连接。
- `backend/app/main.py`：补齐数据库索引和状态 CHECK 约束。
- `backend/README.md`：补充按当前配置创建或补齐数据库表的命令。
- `backend/tests/test_tos_live_upload.py`：新增真实 TOS 本地 MP3 上传自测，默认跳过。
- `backend/conf/README.md`：补充真实 TOS 上传自测命令和 object 保留开关。
- `backend/tests/test_webpage_text_db_chain.py`：新增网页提取 payload 到正文主表和分段表的自动化链路测试。
- `docs/E2E_ACCEPTANCE_CASES.md`：更新 `W2A-E2E-007` 的链路目标、断言、自动化证据和最新验证计数。

## 验证记录

- W2A-E2E-011/012/013 默认跳过验证：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py`，通过；5 个 live 用例默认跳过。
- Chrome popup RED：`PATH="/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" node --test extension/tests/popup.test.cjs`，按预期失败于 `document is not defined`，确认旧 popup 逻辑无法被测试且没有接收端缺失兜底。
- Pipeline logging RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_pipeline_logging.py`，按预期失败；提交和 worker 阶段没有 `web2audio.pipeline` 日志。
- Pipeline logging GREEN：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_pipeline_logging.py`，通过；2 个用例覆盖提交等待 worker 和 text/audio/player 阶段日志串联。
- Pipeline logging 定向回归：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_articles_api.py backend/tests/test_text_jobs.py backend/tests/test_audio_jobs.py backend/tests/test_player_sync_jobs.py`，通过；12 passed。
- Pipeline logging 最终启动验证：`./init.sh`，通过；后端 39 passed、7 skipped，插件 5 passed。
- Chrome popup 定向 GREEN：`PATH="/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" node --test extension/tests/popup.test.cjs`，通过；3 个用例覆盖 URL 支持判断、接收端缺失注入重试和不支持页面短路。
- Chrome 插件正文提取回归：`PATH="/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" node --test extension/tests/article_extractor.test.cjs`，通过；2 个用例通过。
- Chrome popup 修复最终启动验证：`./init.sh`，通过；后端 37 passed、7 skipped，插件 5 passed。
- W2A-E2E-011/012/013 live 复跑：2026-06-30 在 8001 启动 love-song 当前代码服务后，`W2A_RUN_REAL_FULL_CHAIN=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_011_ios_today_reading_playable_via_love_song_api backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_012_ios_article_semantics_via_love_song_api backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_013_ios_sequential_playback_and_history_via_love_song_api -s`，通过；3 passed，1 warning（urllib3 LibreSSL NotOpenSSLWarning），真实 Doubao + TOS + love-song HTTP 全链路下经 iOS 对应接口验证歌单展示、播放 URL、文章语义、顺序连播和播放历史。
- E2E 验收文档飞书同步：`lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json`，通过；revision_id 为 54。
- E2E 验收文档飞书读取验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-011|live 批量 3 passed|37 passed|W2A_RUN_REAL_FULL_CHAIN=1' ...`，通过；011/012/013 已自动化通过、live 批量 3 passed、`37 passed、7 skipped` 和 live 命令可读取。
- E2E case 状态更新最终启动验证：`./init.sh`，通过；后端 37 passed、7 skipped，插件 2 passed。
- E2E case 状态更新 JSON 校验：`python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok`，通过。
- E2E case 状态更新差异格式检查：`git diff --check`，通过。
- iOS 接口自动化最终启动验证：`./init.sh`，通过；后端 37 passed、7 skipped，插件 2 passed。
- 启动基线：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- 配置构建诊断：`PYTHONPATH=backend python3 - <<'PY' ... build_tts_client/build_audio_storage/build_love_song_client ... PY`，结果为 Doubao client 和 TOS storage 可构建，love-song HTTP 因缺少 `backend/conf/love_song.local.json` 快速失败。
- 当前 conf 最小真实分支：`PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... real Doubao + real TOS + fake love-song ... PY`，提交和正文处理成功，音频阶段失败为 `tts_generation_failed`，错误详情为 Doubao `/api/v3/audio/speech` 404，最终文章状态 `failed`。
- 当前 TOS 分支隔离验证：`PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... fake TTS + real TOS ... PY`，音频阶段失败为 `audio_storage_failed`，TOS 返回 `NoSuchBucket`。
- 本次 RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_audio_jobs.py`，按预期失败于缺少 `Settings.resolve_database_url()` 和存储失败被误归类为 `tts_generation_failed`。
- 本次 GREEN：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_audio_jobs.py`，7 个用例通过。
- 修复后启动验证：`./init.sh`，通过；后端 25 个 pytest 用例和插件 2 个 node:test 用例通过。
- love-song 当前代码验证：`bash ./init.sh`，通过；后端 23 个 pytest 用例通过。
- love-song 资产 API 定向验证：`UV_CACHE_DIR=/tmp/love-song-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/love-song-uv-python-managed UV_PROJECT_ENVIRONMENT=/tmp/love-song-backend-venv uv run --project . --python 3.12 --extra dev pytest app/api/routes/assets_api_test.py app/models/entities_test.py`，7 个用例通过。
- love-song 8001 HTTP 探针：`POST /api/assets/tos` 返回 201，随后 `POST /api/playlists/demo_playlist_focus/tracks` 返回 201。
- web2audio 真实完整链路：`PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... real Doubao + real TOS + real love-song HTTP ... PY`，提交和正文处理成功，音频阶段失败于 Doubao `/api/v3/audio/speech` 404，详情状态为 `failed`。
- web2audio TOS 隔离验证：`PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... real TOS put_object ... PY`，失败为 `NoSuchBucket`。
- web2audio 真实 love-song 分支：`PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... fake TTS + fake storage + real love-song HTTP ... PY`，通过；文章详情返回 `status=playable`、`player_sync_status=ready`。
- love-song 歌单确认：`curl -sS http://127.0.0.1:8001/api/playlists/demo_playlist_focus | python3 -c ...`，确认新增文章音频位于 position 7，`content_type=article_audio`，`subtitle=Example`。
- Doubao WebSocket RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py`，按预期失败于缺少 `_DoubaoEvent` 等 WebSocket 协议封装。
- Doubao WebSocket GREEN：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py`，4 个用例通过。
- Doubao/runtime 定向回归：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_doubao_tts_client.py`，9 个用例通过。
- 当前 Doubao conf 构建诊断：`PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... build_tts_client(Settings(tts_mode='doubao')) ... PY`，快速失败于旧配置：缺少 `speaker`、`base_url` 不是 WebSocket URL、`resource_id` 不是 `seed-tts-2.0` 或 `seed-icl-2.0`。
- 最终启动验证：`./init.sh`，通过；后端 30 个 pytest 用例和插件 2 个 node:test 用例通过。
- Doubao metadata RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py`，按预期失败于 `AudioSynthesisResult` 缺少 `metadata`。
- Doubao TaskRequest RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py`，按预期失败于当前 `TaskRequest` 仍发送顶层 `text`，不是火山示例中的 `req_params.text`。
- Doubao WebSocket 调整后 GREEN：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py`，4 个用例通过。
- 真实 Doubao 调试首轮：`W2A_RUN_REAL_DOUBAO_TTS=1 W2A_DOUBAO_TTS_OUTPUT=/tmp/web2audio-doubao-debug.mp3 ... pytest backend/tests/test_doubao_live_tts.py -s`，失败为 `doubao TTS returned no audio`；抓包事件显示 `TTSSentenceStart` payload 文本为空，定位到 `TaskRequest` payload 结构错误。
- 真实 Doubao 调试复跑：`W2A_RUN_REAL_DOUBAO_TTS=1 W2A_DOUBAO_TTS_OUTPUT=/tmp/web2audio-doubao-debug.mp3 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_live_tts.py -s`，通过；生成 `/tmp/web2audio-doubao-debug.mp3`。
- 调试音频确认：`file /tmp/web2audio-doubao-debug.mp3`，识别为 `Audio file with ID3 version 2.4.0`，MPEG layer III，128 kbps，24 kHz，Monaural。
- 定向回归：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py backend/tests/test_doubao_live_tts.py backend/tests/test_runtime_config.py`，9 个用例通过，1 个真实调试用例默认跳过。
- 当前 Doubao conf 构建诊断：`PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... build_tts_client(Settings(tts_mode='doubao')) ... PY`，通过；构建 `DoubaoTtsClient`，endpoint 为 `wss://openspeech.bytedance.com/api/v3/tts/bidirection`，`resource_id=seed-tts-2.0`，`speaker=zh_female_vv_uranus_bigtts`。
- 数据库 schema RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_db_schema.py`，按预期失败于缺少 `app.db.schema`。
- 数据库 schema GREEN：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_db_schema.py backend/tests/test_db_session.py`，3 个用例通过。
- 当前 active 数据库落库检查：`cd backend && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... ensure_database_schema + inspect ... PY`，通过；当前 MySQL profile 包含 `article_audio_items` 和 `article_tts_segments`，索引和 CHECK 约束均存在。
- 数据库 schema 最终启动验证：`./init.sh`，通过；后端 32 个 pytest 用例通过，1 个真实 Doubao 调试用例默认跳过，插件 2 个 node:test 用例通过。
- 最终启动验证：`./init.sh`，通过；后端 30 个 pytest 用例通过，1 个真实 Doubao 调试用例默认跳过，插件 2 个 node:test 用例通过。
- 端到端 case 状态更新最终启动验证：`./init.sh`，通过；后端 32 个 pytest 用例通过，1 个真实 Doubao 调试用例默认跳过，插件 2 个 node:test 用例通过。
- 端到端 case 状态更新本地格式检查：`git diff --check -- docs/E2E_ACCEPTANCE_CASES.md`，通过。
- 端到端 case 状态更新飞书同步：`lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json`，通过；revision_id 为 41。
- 端到端 case 状态更新飞书读取验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-009' --context-before 1 --context-after 1 --format json`，通过。
- 端到端 case 状态更新飞书最终验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword '36 passed' --context-before 2 --context-after 2 --format json`，通过。
- 端到端 case 状态更新飞书新增自动化验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-005' --context-before 1 --context-after 1 --format json`，通过。
- 端到端 case 状态更新飞书 live 边界验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'live 自动化默认跳过' --context-before 1 --context-after 1 --format json`，通过。
- TOS 本地 MP3 直传探针：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend python3 - <<'PY' ... TosStorage.put_object('/tmp/web2audio-doubao-debug.mp3') ... PY`，通过；远端 object key 为 `web2audio/debug/manual-1782732549-web2audio-doubao-debug.mp3`。
- TOS live 自测默认模式：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_tos_live_upload.py`，通过；1 个用例默认跳过，不触发远端上传。
- TOS live 自测真实上传：`W2A_RUN_REAL_TOS_UPLOAD=1 W2A_TOS_KEEP_OBJECT=1 W2A_TOS_UPLOAD_INPUT=/tmp/web2audio-doubao-debug.mp3 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_tos_live_upload.py -s`，通过；远端 object key 为 `web2audio/debug/live-upload/c752d4cf2f9e/web2audio-doubao-debug.mp3`，content length 为 55341。
- TOS 相关定向回归：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_tos_live_upload.py backend/tests/test_runtime_config.py backend/tests/test_audio_jobs.py`，通过；9 个用例通过，1 个真实 TOS 上传用例默认跳过。
- TOS 上传自测最终启动验证：`./init.sh`，通过；后端 32 个 pytest 用例通过，2 个真实调试用例默认跳过，插件 2 个 node:test 用例通过。
- E2E Case 矩阵自动化定向验证：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_fake_full_chain.py`，通过；5 个用例通过。
- E2E Case 矩阵自动化最终启动验证：`./init.sh`，通过；后端 36 个 pytest 用例通过，2 个真实调试用例默认跳过，插件 2 个 node:test 用例通过。
- 网页正文到 DB 链路定向验证：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_webpage_text_db_chain.py`，通过；1 个用例通过。
- 网页正文到 DB 与正文任务回归：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_webpage_text_db_chain.py backend/tests/test_text_jobs.py`，通过；2 个用例通过。
- W2A-E2E-008 默认跳过验证：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py`，通过；2 个 live 用例默认跳过。
- W2A-E2E-008 live 验证：`W2A_RUN_REAL_AUDIO_JOB=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_008_real_doubao_tts_and_tos_audio_job -s`，通过；1 个用例通过，真实 Doubao 合成、真实 TOS 上传和 object head 校验成功。
- W2A-E2E-010 live 验证：`W2A_RUN_REAL_FULL_CHAIN=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_010_real_doubao_tos_and_love_song_full_chain -s`，通过；1 个用例通过，同一篇文章到 `playable`，love-song 歌单回读 `content_type=article_audio` 和 `subtitle=site_name`。
- W2A-E2E-008/010 飞书同步：`lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json`，通过；历史 revision_id 50。
- W2A-E2E-008/010 飞书读取验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-008|W2A-E2E-010|37 passed|W2A_RUN_REAL_FULL_CHAIN=1' ...`，通过；矩阵、关键 case 明细、自动化通过列表和默认验证结果可读取。
- Chrome 插件正文提取回归：`node --test extension/tests/article_extractor.test.cjs`，通过；2 个 node:test 用例通过。
- 网页正文到 DB 链路最终启动验证：`./init.sh`，通过；后端 37 个 pytest 用例通过，4 个默认跳过用例，插件 2 个 node:test 用例通过。
- 网页正文到 DB 链路 JSON 校验：`python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok`，通过。
- 网页正文到 DB 链路差异格式检查：`git diff --check`，通过。
- E2E 验收文档飞书同步：`lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json`，通过；revision_id 为 46。
- E2E 验收文档飞书读取验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword '37 passed' ...`，通过；当前最新读取验证见 revision_id 54 记录。
- JSON 校验：`python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok`，通过。
- 产品文档技术细节残留检查：`rg -n "tracks|audio_assets|playback-url|playback-sessions|play-history|TINYINT|VARCHAR|HTTP|/api|接口路径|数据表|枚举" docs/PRODUCT.md`，仅命中首段说明“技术数据表、接口契约、存储方案和任务实现细节沉淀在技术方案文档中”，无具体技术方案残留。
- 范围残留检查：`rg -n "车载|CarPlay|锁屏|后台播放|未听完优先|playback-url表|audio_assets表" docs/PRODUCT.md feature_list.json docs/TECHNICAL_DESIGN.md`，仅在非目标/不包含语境中命中后台、锁屏、CarPlay。
- 启动验证：`./init.sh`，通过；必需文件存在，6 个功能条目结构合法，未发现已知模板文本残留。
- 差异格式检查：`git diff --check`，通过。
- 浏览器评论残留检查：`rg -n "failure_reason|audio_mime_type|retry_count|voice_id|/retry|article_not_retryable" docs/TECHNICAL_DESIGN.md`，无命中。
- 评论改动确认检查：`rg -n "豆包 lite|火山云 TOS|https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ|article_tts_segments|snake_case|跨工程落地方式" docs/TECHNICAL_DESIGN.md feature_list.json`，命中预期内容。
- JSON 校验：`python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok`，通过。
- 最终启动验证：`./init.sh`，通过；必需文件存在，6 个功能条目结构合法，未发现已知模板文本残留。
- 最终差异格式检查：`git diff --check`，通过。
- 临时 HTML 预览：`/private/tmp/web2audio-technical-design-preview/index.html` 已重新生成，`curl -I http://127.0.0.1:4173/index.html` 返回 `200 OK`。
- 后端测试首轮 RED：`python3 -m pytest backend/tests/test_articles_api.py`，失败于缺少 `app` 模块，确认测试先于实现。
- 插件测试首轮 RED：`node --test extension/tests/article_extractor.test.cjs`，失败于缺少 `extension/content.js`，确认测试先于实现。
- 后端文章 API 测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_articles_api.py`，6 个用例通过。
- Chrome 插件正文提取测试：`node --test extension/tests/article_extractor.test.cjs`，2 个用例通过。
- 启动验证：`./init.sh`，通过；必需文件存在，6 个功能条目结构合法，未发现已知模板文本残留，后端与插件测试通过。
- 差异格式检查：`git diff --check`，通过。
- 并行任务拆分前启动验证：`./init.sh`，通过；必需文件存在，6 个功能条目结构合法，后端与插件测试通过。
- `feat-003` RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_text_processing.py`，失败于缺少 `app.text_processing`。
- `feat-003` RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_text_jobs.py`，失败于缺少 `ArticleTtsSegment`。
- 新增正文处理测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_text_processing.py backend/tests/test_text_jobs.py`，3 个用例通过。
- 后端全量测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests`，9 个用例通过。
- Chrome 插件测试：`node --test extension/tests/article_extractor.test.cjs`，2 个用例通过。
- `feat-004` RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_audio_jobs.py`，失败于缺少 `app.audio_jobs`。
- 音频产物测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_audio_jobs.py`，2 个用例通过。
- 后端全量测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests`，11 个用例通过。
- Chrome 插件测试：`node --test extension/tests/article_extractor.test.cjs`，2 个用例通过。
- `feat-005` RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_love_song_contract.py`，失败于缺少 `app.love_song_contract`。
- love-song 契约测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_love_song_contract.py`，2 个用例通过。
- 后端全量测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests`，13 个用例通过。
- `feat-008` RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_player_sync_jobs.py`，失败于缺少 `app.player_sync_jobs`。
- 播放器同步测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_player_sync_jobs.py`，2 个用例通过。
- 后端全量测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests`，15 个用例通过。
- `feat-009` RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_fake_full_chain.py`，失败于缺少 `app.self_test`。
- fake 全链路自测：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_fake_full_chain.py`，1 个用例通过。
- 最终统一启动验证：`./init.sh`，通过；10 个功能条目结构合法，后端 16 个 pytest 用例通过，插件 2 个 node:test 用例通过。
- 最终差异格式检查：`git diff --check`，通过。
- harness 结构校验：`node /Users/bytedance/.codex/skills/harness-creator/scripts/validate-harness.mjs --target /Users/bytedance/Codebases/web2audio`，通过；总分 100/100。
- AGENTS.md 文档维护 JSON 校验：`python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok`，通过。
- AGENTS.md 文档维护统一启动验证：`./init.sh`，通过；已检查 `docs/TECHNICAL_DESIGN.md`，后端 16 个 pytest 用例通过，插件 2 个 node:test 用例通过。
- AGENTS.md 文档维护差异格式检查：`git diff --check`，通过。
- runtime 边界 RED：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_love_song_http_client.py backend/tests/test_db_session.py`，失败于缺少 `app.clients` 和 `app.core`，确认测试先于实现。
- runtime 边界新增测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_love_song_http_client.py backend/tests/test_db_session.py`，7 个用例通过。
- runtime 边界后端全量测试：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests`，23 个 pytest 用例通过。
- runtime 边界最终启动验证：`./init.sh`，通过；必需文件检查通过，10 个功能条目结构合法，后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- runtime 边界差异格式检查：`git diff --check`，通过。
- 端到端测试文档启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- 端到端测试文档差异格式检查：`git diff --check`，通过。
- 端到端测试文档飞书导入：`lark-cli docs +create --api-version v2 --doc-format markdown --content @docs/END_TO_END_TEST_CASES.md --format json`，创建成功；旧 bot 文档自动授权失败，缺少应用后台 `docs:permission.member:create` 等 scope。
- 端到端测试文档最终启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- 端到端测试文档最终差异格式检查：`git diff --check`，通过。
- lark-cli 升级：`lark-cli update --json`，通过；版本从 `1.0.46` 升级到 `1.0.59`，官方 skills 已同步。
- lark-cli 用户授权：`lark-cli auth login --device-code ...`，通过；用户 `刘浩` 已授予 `docx:document:create`、`docx:document:write_only`、`docx:document:readonly` 和 `docs:permission.member:create`。
- 端到端测试文档用户身份导入：`lark-cli docs +create --api-version v2 --as user --doc-format markdown --content @docs/END_TO_END_TEST_CASES.md --title 'web2audio 端到端测试 Case 设计' --format json`，通过；新文档 URL 为 `https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b`。
- 端到端测试文档用户身份读取验证：`lark-cli docs +fetch --api-version v2 --as user --doc 'https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b' --doc-format markdown --scope outline --format json`，通过。
- 飞书链接更新后最终启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- 飞书链接更新后最终差异格式检查：`git diff --check`，通过。
- 端到端 case 状态标注启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- 端到端 case 状态标注飞书同步：`lark-cli docs +update --doc 'https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b' --as user --command overwrite --doc-format markdown --content @docs/END_TO_END_TEST_CASES.md --format json`，通过。
- 端到端 case 状态标注飞书读取验证：`lark-cli docs +fetch --doc 'https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b' --as user --doc-format markdown --scope keyword --keyword 'Case 状态总览' --context-after 2 --format json`，通过。
- 端到端 case 状态标注最终启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- 端到端 case 状态标注最终差异格式检查：`git diff --check`，通过。
- e2e-test-design 版文档结构检查：`rg -n "证据表|领域划分|Case 矩阵|已自动化通过的 Case|待确认的 Case|P0 冒烟集|未覆盖风险" docs/E2E_ACCEPTANCE_CASES.md`，通过；只命中预期章节，无独立证据表或独立领域划分章节。
- e2e-test-design 版文档差异格式检查：`git diff --check -- docs/E2E_ACCEPTANCE_CASES.md`，通过。
- e2e-test-design 版文档飞书创建：`lark-cli docs +create --as user --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --title 'web2audio 端到端验收 Case 设计（e2e-test-design）' --format json`，通过；新文档 URL 为 `https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb`。
- e2e-test-design 版文档飞书目录读取验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope outline --format json`，通过。
- e2e-test-design 版文档飞书关键词读取验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-001' --context-after 1 --format json`，通过。
- e2e-test-design 版文档最终启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- e2e-test-design 版文档最终差异格式检查：`git diff --check`，通过。
- E2E Case 矩阵简化前启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- E2E Case 矩阵简化本地格式检查：`git diff --check -- docs/E2E_ACCEPTANCE_CASES.md`，通过。
- E2E Case 矩阵简化飞书同步：`lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json`，通过；revision_id 为 13。
- E2E Case 矩阵简化飞书读取验证：`lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-014' --context-before 1 --context-after 1 --format json`，通过；简化矩阵行可读取。
- E2E Case 矩阵简化最终启动验证：`./init.sh`，通过；后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
- E2E Case 矩阵简化最终差异格式检查：`git diff --check`，通过。

## 给下一次会话

先运行 `./init.sh`。如果通过，本仓库 fake 自测链路、runtime 边界测试和端到端 case 设计文档已经满足；真实跨工程下一步推进 `feat-006` 或 `feat-007`，或按 `docs/E2E_ACCEPTANCE_CASES.md` 补齐 mock 分支自动化。

<!-- harness-validator: Current State; What's Done; What's Next; Evidence; Last Updated; Recommended Next Step. -->
