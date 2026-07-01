# 会话交接

## 当前目标

- 目标：为 Chrome 提交后到正文处理、TTS/TOS、love-song 同步的后端关键链路补齐日志可观测性，并能通过日志快速判断哪个环节没有执行。
- 当前状态：已完成。新增 `web2audio.pipeline` 结构化日志，覆盖 `article_submission`、`text_processing`、`audio_generation`、`player_sync` 四段。已确认当前 `POST /api/articles` 只负责文章入库，不自动触发后续 worker；若日志只有 `article_task_created` 和 `article_waiting_for_worker`，说明停在等待正文处理 worker。默认 `./init.sh` 通过，后端 39 passed、7 skipped，插件 5 passed。
- 分支与提交：当前分支 `codex/feat-002-submit-entry` 基于 `f55c256 Localize project harness docs`，本次未提交。

## 本次已完成

- 把 `W2A-E2E-011` 到 `W2A-E2E-013` 改为 iOS 接口自动化：
  - 在 `backend/tests/test_live_e2e_external_chain.py` 抽出 `run_full_chain_to_playable` 复用真实 Doubao + TOS + love-song HTTP 全链路，并新增 `love_song_get_playlist`、`love_song_post`、`love_song_patch` 调用 iOS 对应接口。
  - 新增 `test_w2a_e2e_011_ios_today_reading_playable_via_love_song_api`、`test_w2a_e2e_012_ios_article_semantics_via_love_song_api`、`test_w2a_e2e_013_ios_sequential_playback_and_history_via_love_song_api`，均由 `W2A_RUN_REAL_FULL_CHAIN=1` 显式开启，默认 `./init.sh` 跳过。
  - 011 验证歌单详情含文章 track、播放会话定位、`playback-url` 返回 `source_type=tos` 文章音频 URL；012 验证 `content_type=article_audio`、`subtitle=site_name`、`artist=null`、`album=null`；013 验证两篇文章 position 连续、会话顺序一致、逐首播放 URL 与两条播放历史。
  - 2026-06-30 在 8001 启动 love-song 当前代码服务实跑三个 live 用例，`3 passed`，仅有 urllib3 LibreSSL NotOpenSSLWarning。
  - `docs/E2E_ACCEPTANCE_CASES.md`：矩阵、关键 case 明细、已自动化通过表、待确认表、冒烟/回归集状态、剩余风险和第 1、2 章环境说明同步更新。
  - `feature_list.json` `feat-010` 证据、`progress.md` 同步更新。

- 修复 Chrome 插件 popup 提交接收端缺失：
  - `extension/popup.js` 增加页面 URL 支持判断，`chrome://`、扩展管理页等不支持页面不再发送 content script 消息。
  - 对普通 `http/https` 页面，首次 `chrome.tabs.sendMessage` 遇到 `Could not establish connection. Receiving end does not exist.` 时，通过 `chrome.scripting.executeScript` 注入 `content.js` 并重试。
  - popup 的 DOM 绑定只在浏览器环境执行，通信逻辑可通过 node:test 直接验证。
  - 新增 `extension/tests/popup.test.cjs`，覆盖 URL 判断、接收端缺失注入重试、不支持页面短路。
  - `init.sh` 在缺少系统 Node 时会使用 Codex 本地 Node 运行时，并运行 `extension/tests/*.test.cjs`。
  - `extension/README.md` 补充 unpacked 插件刷新、普通网页使用边界和全部插件测试命令。

- 补齐后端 pipeline 日志可观测性：
  - 已定位 Chrome 提交后不继续转语音的直接原因：`POST /api/articles` 创建任务后返回，`process_article_text`、`process_article_audio`、`process_player_sync` 当前需要外部 worker 或测试显式调用。
  - 新增 `backend/app/observability.py`，统一 `web2audio.pipeline` logger 和 key-value 日志格式。
  - `backend/app/main.py` 输出 `article_task_created`、`article_task_duplicate`、`article_waiting_for_worker`；新建文章日志含 `article_id`、`source_url_hash`、三类状态和 `text_char_count`。
  - `backend/app/text_jobs.py` 输出 `text_processing_started`、`text_processing_ready`、`text_processing_failed`；ready 日志含 `segment_count` 和 `next_stage=audio_generation`。
  - `backend/app/audio_jobs.py` 输出 `audio_generation_started`、`audio_segment_started`、`audio_segment_ready`、`audio_generation_ready`、`audio_generation_failed`；失败按 `tts_generation_failed`、`audio_storage_failed`、`segments_missing` 等 `error_code` 区分。
  - `backend/app/player_sync_jobs.py` 输出 `player_sync_started`、`player_sync_ready`、`player_sync_failed`；同步失败保留 `error_code=love_song_sync_failed` 和 `error_detail`。
  - 新增 `backend/tests/test_pipeline_logging.py`，验证提交后等待 worker 日志，以及 text/audio/player 三段用同一个 `article_id` 串联。
  - `backend/README.md` 已补充 Pipeline Logs 排障表：按 `article_id` grep，依据缺失事件判断未执行阶段。

- 更新 `docs/PRODUCT.md`：
  - 产品文档只保留产品目标、系统边界、核心流程、功能范围、验收标准和待确认项。
  - 第一版目标收敛为 love-song iOS 播放器内连续播放文章音频。
  - 「今日待读」定义为系统托管默认歌单，ready 文章追加到末尾，播放顺序复用播放器现有策略。
  - Chrome 插件按原始网页 URL 精确去重。
  - 后台播放、锁屏控制、CarPlay 不纳入第一版验收。
- 新增 `docs/TECHNICAL_DESIGN.md`：
  - 数据库设计使用 `article_audio_items` 和 `article_tts_segments`。
  - 状态字段采用 `TINYINT UNSIGNED`，文档中明确数值映射。
  - API 设计覆盖文章提交、详情、列表和失败重试。
  - love-song 集成契约明确为 HTTP 解耦：先登记可播放资源，再追加到固定歌单「今日待读」。
  - 明确 love-song 仍需补齐幂等 TOS 资源登记 API。
- 更新 `feature_list.json`：
  - feat-004 改为通过 love-song HTTP API 登记可播放资源并追加「今日待读」。
  - feat-005 改为 iOS 文章音频展示与连续播放，不再写车载连续播放。
  - feat-006 改为从 Chrome 到 love-song iOS「今日待读」连续播放的端到端验收。
- 更新 `progress.md`，记录本次决策、风险和验证结果。
- 处理浏览器评论后的补充更新：
  - 为 ER 关系图增加表级 COMMENT 备注，并解释 `article_tts_segments` 是内部 TTS 分段表。
  - 从 `article_audio_items` 和 `article_tts_segments` 删除 `failure_reason`、`audio_mime_type`、`retry_count`、`tts_provider`、`voice_id` 等不必要字段。
  - 删除公开 `POST /api/articles/{article_id}/retry` 设计，失败详情改为通过日志按业务 ID 和请求 ID 排查。
  - 将示例测试 URL 改为 `https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ`。
  - 明确 TTS 使用豆包 lite 模型，音频对象存储使用火山云 TOS。
  - 补充 love-song `POST /api/assets/tos` 的跨工程落地方式。
  - 将「今日待读」定位改为固定 `playlist_id` 配置依赖，避免同步 worker 自动创建同名歌单。
  - 更新 `feature_list.json` 中 feat-003 和 feat-004 的描述。
- 完成阶段 1 后端提交入口：
  - 新增 FastAPI 应用，提供健康检查、文章提交、文章详情和文章列表查询。
  - 使用 Bearer token 鉴权，默认开发 token 为 `dev-token`。
  - 使用原始 `source_url` 的 SHA-256 精确去重，同一 owner 下重复提交返回已有任务。
  - 建立第一版 `article_audio_items` SQLAlchemy 模型。
  - 请求校验采用 Pydantic，错误响应统一为 `{error:{code,message,details}}`。
- 完成阶段 2 Chrome 插件提交入口：
  - 新增 Manifest V3 插件。
  - `content.js` 从当前页面提取 `source_url`、标题、正文、站点、作者、发布时间、封面和语言提示。
  - `popup.js` 支持配置 API 地址和 token，并将当前文章提交到 `POST /api/articles`。
  - 弹窗展示首次提交和重复提交的结果状态。
- 验证入口更新：
  - `./init.sh` 已接入后端 pytest 和插件 node:test。
  - `README.md`、`backend/README.md`、`extension/README.md` 已记录本地启动与验证方式。
  - `.gitignore` 已忽略 Python 缓存和本地密钥配置。
  - `feature_list.json` 中 `feat-002` 已标记为 `done`。
- 完成并行任务拆分：
  - `feature_list.json` 已拆为 9 个功能，并增加 `workstream`、`parallel_group` 和 `parallel_notes`。
  - 明确 `feat-003` 与 `feat-005` 可在 wave-1 并行。
  - 明确 `feat-004`、`feat-006`、`feat-007` 可在对应依赖满足后并行推进。
- 完成 `feat-003` 文章正文清洗与分段基础链路：
  - 新增 `backend/app/text_processing.py`，支持正文清洗、语言归一或检测、最小长度校验和按字符上限分段。
  - 新增 `backend/app/text_jobs.py`，提供 `process_article_text` service。
  - 新增 `article_tts_segments` SQLAlchemy 模型，使用 `segment_id` 业务 ID 和 `(article_id, segment_index)` 组合唯一约束。
  - `process_article_text` 会清洗正文、回写 `text_content`、`text_char_count`、`language`，并将 `text_status` 推进到 `ready` 或 `failed`。
  - `./init.sh` 后端测试范围已扩展为整个 `backend/tests`。
  - `feature_list.json` 中 `feat-003` 已标记为 `done`。
- 完成 `feat-004` 豆包 lite TTS 与火山云 TOS 音频产物：
  - 新增 `backend/app/audio_jobs.py`。
  - 提供 fake 豆包 lite TTS client 和 fake 火山云 TOS storage。
  - `process_article_audio` 基于 TTS 分段生成分段音频、合成最终音频、写入 fake TOS object，并回写 `audio_status=ready`。
  - `feature_list.json` 中 `feat-004` 已标记为 `done`。
- 完成 `feat-005` love-song 文章音频集成契约冻结：
  - 新增 `backend/app/love_song_contract.py`。
  - 冻结 TOS 资源登记请求/响应、`content_type=article_audio`、`subtitle`、`source_type=tos`、`external_source + external_id` 幂等和歌单追加幂等语义。
  - `feature_list.json` 中 `feat-005` 已标记为 `done`。
- 完成 `feat-008` web2audio 播放器同步 worker：
  - 新增 `backend/app/player_sync_jobs.py`。
  - 支持 audio ready 文章登记 fake love-song TOS 资源、追加固定歌单、重复同步幂等和失败状态回写。
  - `feature_list.json` 中 `feat-008` 已标记为 `done`。
- 完成 `feat-009` 本仓库 fake 全链路自测：
  - 新增 `backend/app/self_test.py`。
  - `run_fake_full_chain` 串起 API 提交、正文处理、fake TTS/TOS、fake love-song 同步和文章详情 playable 校验。
  - 新增 `feat-010` 保留真实跨工程端到端验收，避免 fake 自测与真实 love-song/iOS 完成状态混淆。
  - `feature_list.json` 中 `feat-009` 已标记为 `done`。
- 完成 web2audio runtime 边界拆分：
  - 新增 `backend/conf/` 配置示例，默认 fake 模式，真实豆包、火山云 TOS 和 love-song HTTP 模式通过 `.env` 显式切换。
  - 新增 `backend/app/core/config.py` 和 `backend/app/db/session.py`，对齐 love-song 后端的配置与 DB session 管理方式。
  - 新增 `backend/app/clients/`，拆分 `FakeTtsClient`、`FakeTosStorage`、`FakeLoveSongClient`、`DoubaoTtsClient`、`TosStorage` 和 `HttpLoveSongClient`。
  - `audio_jobs` 和 `player_sync_jobs` 已改为依赖协议，不直接绑定 fake 实现。
  - 新增 runtime 工厂，真实模式缺配置时快速失败，不静默回退 fake。
- 完成端到端测试 case 文档设计：
  - 新增 `docs/END_TO_END_TEST_CASES.md`。
  - 按文章收集、正文处理、音频生成、播放器同步、播放体验和运行时配置六个领域划分测试。
  - 设计 L1 mock 自动化、L2 线上配置联调、L3 iOS 验收三类分支。
  - 明确 `E2E-MOCK-*`、`E2E-ONLINE-*`、`E2E-IOS-*` case 的业务目标、前置条件、步骤、断言和优先级。
  - 已以用户身份导入飞书文档：`https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b`；旧 bot 文档仍受应用后台 scope 限制，不作为交付链接。
- 完成端到端测试 case 状态标注：
  - `E2E-MOCK-001` 标为已自动化通过。
  - `E2E-MOCK-002`、`E2E-MOCK-003`、`E2E-MOCK-006` 标为部分自动化通过。
  - `E2E-MOCK-004`、`E2E-MOCK-005` 标为待自动化。
  - 所有 `E2E-ONLINE-*` 和 `E2E-IOS-*` 标为待确认。
  - 飞书文档已覆盖同步，并通过关键词读取验证 `Case 状态总览`。
- 完成 e2e-test-design 版端到端验收 case 文档：
  - 新增 `docs/E2E_ACCEPTANCE_CASES.md`，按验收目标、环境准备、Case 矩阵、关键 case、已自动化通过、待确认、P0/P1/P2 和剩余风险组织。
  - 设计 `W2A-E2E-001` 到 `W2A-E2E-014` 共 14 个 case，覆盖 mock 主干、幂等重复、正文边界、任务失败、外部依赖失败、运行时配置、Chrome 插件入口、真实豆包/TOS、真实 love-song、完整线上链路和 iOS 人工验收。
  - `W2A-E2E-001`、`W2A-E2E-006`、`W2A-E2E-007` 已标为已自动化通过；真实跨工程和 iOS 相关 case 仍为待确认或阻塞。
  - 已以用户身份创建新的飞书文档：`https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb`，并通过 outline 与 `W2A-E2E-001` 关键词读取验证。
- 完成 E2E Case 矩阵简化：
  - `docs/E2E_ACCEPTANCE_CASES.md` 的矩阵已从 11 列收敛为 7 列，只保留索引和进度跟踪字段。
  - 环境、前置数据、操作路径、断言细节和验收证据仍保留在第 2 章环境准备和第 4 章关键 case 明细中。
  - 飞书文档 `https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb` 已覆盖同步，并通过 `W2A-E2E-014` 关键词读取验证。
- 完成当前 conf 端到端调试与本仓库修复：
  - `./init.sh` 基线通过，后端 23 个 pytest 用例和插件 2 个 node:test 用例通过。
  - 当时 `backend/conf/` 存在 `db.local.json`、`doubao.local.json` 和 `tos.local.json`，缺少 `love_song.local.json`；当前已补本地忽略配置指向 8001。
  - 真实 Doubao + 真实 TOS + fake love-song 最小分支中，文章提交和正文处理成功，音频阶段失败为 Doubao `/api/v3/audio/speech` 404，最终文章状态为 `failed`。
  - fake TTS + 真实 TOS 隔离分支失败为 `audio_storage_failed`，TOS 返回 `NoSuchBucket`。
  - 新增 `Settings.resolve_database_url()`，在 `DATABASE_URL` 保持默认值时读取 `db.local.json` 的 active profile；`create_app` 和默认 `SessionLocal` 已切换到解析后的数据库 URL。
  - `process_article_audio` 已区分 `tts_generation_failed` 与 `audio_storage_failed`，内部结果保留 `error_detail`，便于定位 provider HTTP 错误或 TOS 请求错误。
  - 新增 `backend/conf/love_song.example.json`，并补充 `.env.example`、`backend/conf/README.md` 的 DB profile 和 love-song local 配置说明。
  - 本次修复后 `./init.sh` 通过，后端 25 个 pytest 用例和插件 2 个 node:test 用例通过。
- 完成 love-song HTTP 分支联调：
  - love-song 8000 是旧进程，`POST /api/assets/tos` 返回 404；本次在 8001 启动当前代码新进程进行联调。
  - love-song live MySQL 首次 `POST /api/assets/tos` 返回 500，根因为同一事务内缺少 ORM relationship/flush 顺序，MySQL 先插入 `audio_assets` 时触发 `fk_audio_assets_track_id`。
  - 已在 love-song `backend/app/services/assets.py` 中创建 track 后先 `db.flush()`，再创建 audio asset；重新启动 8001 后资产登记返回 201，追加 `demo_playlist_focus` 返回 201。
  - web2audio 真实 Doubao + 真实 TOS + 真实 love-song HTTP 完整链路仍失败于 Doubao `/api/v3/audio/speech` 404。
  - web2audio fake TTS + fake storage + 真实 love-song HTTP 分支成功：文章详情返回 `playable`，love-song 返回 `track_1b8f330840b24282b53f` 和 `asset_e919410075c440fc8e7c`，歌单详情显示 position 7、`content_type=article_audio`、`subtitle=Example`。
- 完成真实 TTS 请求协议优化：
  - 参考火山文档 `https://www.volcengine.com/docs/6561/2532486?lang=zh`，通过文档中心 `getDocDetail?DocumentID=2532486&LibraryID=6561` 确认文档标题为「双向流式语音合成WebSocket」。
  - 确认 WSS 地址为 `wss://openspeech.bytedance.com/api/v3/tts/bidirection`，请求头为 `X-Api-Key`、`X-Api-Resource-Id`、`X-Api-Connect-Id`，客户端事件为 `StartConnection`、`StartSession`、`TaskRequest`、`FinishSession`、`FinishConnection`。
  - 下载并核对官方附件 `TTS Websocket Bidirection protocols.zip`，确认二进制消息封装使用 `FullClientRequest + WithEvent` 携带事件号、会话 ID 和 payload。
  - `backend/app/clients/doubao.py` 已从 httpx REST client 改为 `websockets` 双向流式 client，保留同步 `TtsClient.synthesize()` 接口。
  - 新增 `backend/tests/test_doubao_tts_client.py`，覆盖配置默认值、请求头、事件顺序、`StartSession` / `TaskRequest` payload、音频 chunk 汇总和 provider 失败事件。
  - 更新 `backend/conf/doubao.example.json` 和 `backend/conf/README.md`，真实 TTS 配置改为 `base_url` WSS、`resource_id`、`speaker`、`audio_format`、`sample_rate`、`bit_rate`。
  - 已根据火山「接入语音模型」示例修正 `TaskRequest` payload：文本放入 `req_params.text`，并携带 `speaker`、`audio_params`、语速、音量和显式语言；真实服务不再返回空文本 `TTSSentenceStart`。
  - `AudioSynthesisResult` 新增 `metadata`，Doubao 结果会返回 `provider`、`connect_id`、`session_id` 和 `usage`，便于调试请求与计费字符数。
  - 新增 `backend/tests/test_doubao_live_tts.py` 真实 TTS 调试用例；默认跳过，设置 `W2A_RUN_REAL_DOUBAO_TTS=1` 后读取 `backend/conf/doubao.local.json` 真连火山。
  - 当前 `backend/conf/doubao.local.json` 可构建真实 `DoubaoTtsClient`，endpoint 为 `wss://openspeech.bytedance.com/api/v3/tts/bidirection`，`resource_id=seed-tts-2.0`，`speaker=zh_female_vv_uranus_bigtts`。
  - 真实 TTS 调试已通过，生成 `/tmp/web2audio-doubao-debug.mp3`，文件大小 54K，`file` 识别为 128 kbps、24 kHz、单声道 MP3。
- 完成当前端到端 case 状态更新：
  - `docs/E2E_ACCEPTANCE_CASES.md` 已更新状态更新时间为 2026-06-30 11:06 CST。
  - `W2A-E2E-001` 到 `W2A-E2E-007` 按 2026-06-30 `./init.sh` 结果标为已自动化通过。
  - `W2A-E2E-008` 和 `W2A-E2E-010` 标为已自动化通过；真实 Doubao/TOS/love-song 后端链路已有显式 live 自动化证据，但默认 `./init.sh` 中跳过。
  - `W2A-E2E-009` 标为已人工通过，证据为 love-song 8001 HTTP 探针、web2audio fake TTS + fake storage + 真实 love-song HTTP 分支到 `playable`、love-song 歌单查询。
  - `W2A-E2E-011`、`W2A-E2E-012`、`W2A-E2E-013` 已按当前验收口径改为 iOS 对应接口自动化并通过；真机或模拟器只保留体验层抽查。
  - 飞书文档 `https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb` 已覆盖同步本次最新状态，revision_id 为 54。
- 完成 E2E Case 矩阵自动化补充：
  - `backend/tests/test_fake_full_chain.py` 新增重复提交幂等、正文不可用、TTS 失败、love-song 同步失败后恢复 4 个端到端用例。
  - `W2A-E2E-002` 验证重复提交返回同一 article_id、文章总数不增加、重复同步不重复追加歌单 track。
  - `W2A-E2E-003` 验证正文不可用时 text/audio/player 失败，无 audio key、love-song IDs 和 fake 外部副作用。
  - `W2A-E2E-004` 验证 TTS 失败后 article failed，无 storage object 和 love-song 登记。
  - `W2A-E2E-005` 验证 love-song 同步失败保留音频 key，恢复后可同步到 `playable`。
- 完成数据库 schema 落库：
  - 当前 `backend/conf/db.local.json` 的 active profile 为 `mysql`，解析出的数据库为 SQLAlchemy 兼容的 MySQL URL。
  - 新增 `app.db.schema.ensure_database_schema()`，按当前配置创建或补齐数据库表。
  - `article_audio_items` 和 `article_tts_segments` 的索引、CHECK 约束已补进 SQLAlchemy schema。
  - MySQL 外键约束会阻止分段表引用不存在的 `article_id`。
  - 已在当前 active MySQL 中创建或补齐 web2audio 表；inspect 结果确认表、索引和 CHECK 约束存在。
  - 新增 `backend/tests/test_db_schema.py`，覆盖 schema 创建、索引、CHECK 约束和 MySQL 外键约束。
- 完成真实 TOS 本地 MP3 上传自测：
  - 当前 `backend/conf/tos.local.json` 指向 `cn-shanghai` 的 `tos-web2audio` bucket。
  - `/tmp/web2audio-doubao-debug.mp3` 已通过 `TosStorage.put_object()` 上传到远端 TOS，并通过 `head_object` 校验大小为 55341 bytes。
  - 新增 `backend/tests/test_tos_live_upload.py`，默认跳过；设置 `W2A_RUN_REAL_TOS_UPLOAD=1` 后执行真实上传。
  - live 自测支持 `W2A_TOS_UPLOAD_INPUT` 指定本地 MP3，支持 `W2A_TOS_KEEP_OBJECT=1` 保留远端 object 供后续 love-song 联调。
  - 本次保留的远端 object key 为 `web2audio/debug/live-upload/c752d4cf2f9e/web2audio-doubao-debug.mp3`。
- 完成网页正文提取到 DB 落库链路自测：
  - 新增 `backend/tests/test_webpage_text_db_chain.py`。
  - 测试用 Node 调用真实 `extension/content.js` 的 `extractArticleFromDocument`，从模拟网页 document 提取标题、URL、站点、作者、语言和正文 payload。
  - 测试将 payload 提交到 `POST /api/articles`，再执行 `process_article_text`，最后查询 MySQL。
  - 断言覆盖 `article_audio_items` 的来源 URL、标题、站点、作者、语言、清洗正文、字符数和状态，以及 `article_tts_segments` 的分段顺序、分段文本和 `audio_status=pending`。
  - `docs/E2E_ACCEPTANCE_CASES.md` 已把 `W2A-E2E-007` 更新为“插件提取 payload 后写入正文数据库”，并记录最新 `./init.sh` 后端 37 passed、7 skipped，插件 2 passed。
- 完成 `W2A-E2E-008` / `W2A-E2E-010` live 自动化验证：
  - 新增 `backend/tests/test_live_e2e_external_chain.py`，默认跳过；显式开启 env 后才调用真实 Doubao、TOS 和 love-song。
  - 新增本地忽略配置 `backend/conf/love_song.local.json`，指向 `http://127.0.0.1:8001`。
  - `W2A-E2E-008` 验证同一篇文章完成真实 Doubao 合成、真实 TOS 上传和 object head 校验。
  - `W2A-E2E-010` 验证同一篇文章完成真实 Doubao、真实 TOS、真实 love-song HTTP 同步，web2audio article 到 `playable`，love-song 歌单回读 `content_type=article_audio` 和 `subtitle=site_name`。
  - `backend/conf/README.md` 已补充 `love_song.local.json` 格式和两个 live E2E 复跑命令。
  - `feature_list.json` 中 `feat-010` 已更新为 `in-progress`，证据记录后端真实依赖 live 已通过、iOS 对应接口自动化已通过，真机体验只保留可选抽查。

## 验证证据

| 检查 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| Pipeline logging RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_pipeline_logging.py` | 失败符合预期 | 旧代码没有 `web2audio.pipeline` 日志 |
| Pipeline logging GREEN | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_pipeline_logging.py` | 通过 | 2 个用例覆盖提交等待 worker 和完整阶段日志 |
| Pipeline logging 定向回归 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_articles_api.py backend/tests/test_text_jobs.py backend/tests/test_audio_jobs.py backend/tests/test_player_sync_jobs.py` | 通过 | 12 passed |
| Pipeline logging 最终启动验证 | `./init.sh` | 通过 | 后端 39 passed、7 skipped，插件 5 passed |
| Chrome popup RED | `PATH="/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" node --test extension/tests/popup.test.cjs` | 失败符合预期 | 旧 `popup.js` 在 Node 下直接引用 `document`，无法测试通信逻辑 |
| Chrome popup 定向 GREEN | `PATH="/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" node --test extension/tests/popup.test.cjs` | 通过 | 3 个用例覆盖 URL 判断、注入重试和不支持页面短路 |
| Chrome 插件正文提取回归 | `PATH="/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH" node --test extension/tests/article_extractor.test.cjs` | 通过 | 2 个用例通过 |
| Chrome popup 修复最终启动验证 | `./init.sh` | 通过 | 后端 37 passed、7 skipped，插件 5 passed |
| 当前 conf 基线 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| 当前 conf 构建诊断 | `PYTHONPATH=backend python3 - <<'PY' ... build_tts_client/build_audio_storage/build_love_song_client ... PY` | 部分通过 | Doubao client 和 TOS storage 可构建；love-song HTTP 因缺少 `backend/conf/love_song.local.json` 快速失败 |
| 当前 conf 最小真实分支 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... real Doubao + real TOS + fake love-song ... PY` | 失败可定位 | 提交和正文处理成功；音频阶段为 `tts_generation_failed`，Doubao `/api/v3/audio/speech` 返回 404 |
| 当前 TOS 隔离分支 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... fake TTS + real TOS ... PY` | 失败可定位 | 音频阶段为 `audio_storage_failed`，TOS 返回 `NoSuchBucket` |
| 本次 RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_audio_jobs.py` | 失败 | 缺少 `Settings.resolve_database_url()`；存储失败被误归类为 `tts_generation_failed` |
| 本次 GREEN | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_audio_jobs.py` | 通过 | 7 个用例通过 |
| 修复后启动验证 | `./init.sh` | 通过 | 后端 25 个 pytest 用例和插件 2 个 node:test 用例通过 |
| love-song 当前代码验证 | `bash ./init.sh` | 通过 | 后端 23 个 pytest 用例通过 |
| love-song 资产 API 定向验证 | `UV_CACHE_DIR=/tmp/love-song-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/love-song-uv-python-managed UV_PROJECT_ENVIRONMENT=/tmp/love-song-backend-venv uv run --project . --python 3.12 --extra dev pytest app/api/routes/assets_api_test.py app/models/entities_test.py` | 通过 | 7 个用例通过 |
| love-song 8001 HTTP 探针 | `POST /api/assets/tos`、`POST /api/playlists/demo_playlist_focus/tracks` | 通过 | 资产登记 201，歌单追加 201 |
| web2audio 真实完整链路 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... real Doubao + real TOS + real love-song HTTP ... PY` | 失败可定位 | 提交和正文处理成功；音频阶段为 Doubao `/api/v3/audio/speech` 404 |
| web2audio TOS 隔离验证 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... real TOS put_object ... PY` | 失败可定位 | TOS 返回 `NoSuchBucket` |
| web2audio 真实 love-song 分支 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... fake TTS + fake storage + real love-song HTTP ... PY` | 通过 | 文章详情为 `playable`，`player_sync_status=ready` |
| love-song 歌单确认 | `curl -sS http://127.0.0.1:8001/api/playlists/demo_playlist_focus | python3 -c ...` | 通过 | 新文章音频 position 7，`content_type=article_audio`，`subtitle=Example` |
| Doubao WebSocket RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py` | 失败 | 缺少 `_DoubaoEvent` 等 WebSocket 协议封装，确认测试先于实现 |
| Doubao WebSocket GREEN | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py` | 通过 | 4 个用例通过 |
| Doubao/runtime 定向回归 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_doubao_tts_client.py` | 通过 | 9 个用例通过 |
| 当前 Doubao conf 构建诊断 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... build_tts_client(Settings(tts_mode='doubao')) ... PY` | 失败可定位 | 旧配置缺少 `speaker`，`base_url` 非 WebSocket，`resource_id` 非 `seed-tts-2.0` / `seed-icl-2.0` |
| 最终启动验证 | `./init.sh` | 通过 | 后端 30 个 pytest 用例和插件 2 个 node:test 用例通过 |
| Doubao metadata RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py` | 失败 | `AudioSynthesisResult` 缺少 `metadata` |
| Doubao TaskRequest RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py` | 失败 | 当前 `TaskRequest` 发送顶层 `text`，真实服务返回空文本 |
| Doubao 调整后 GREEN | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py` | 通过 | 4 个用例通过 |
| 真实 Doubao 首轮调试 | `W2A_RUN_REAL_DOUBAO_TTS=1 W2A_DOUBAO_TTS_OUTPUT=/tmp/web2audio-doubao-debug.mp3 ... pytest backend/tests/test_doubao_live_tts.py -s` | 失败可定位 | 连接和会话成功，`TTSSentenceStart` 文本为空，未返回音频；根因是 `TaskRequest` payload 结构错误 |
| 真实 Doubao 复跑 | `W2A_RUN_REAL_DOUBAO_TTS=1 W2A_DOUBAO_TTS_OUTPUT=/tmp/web2audio-doubao-debug.mp3 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_live_tts.py -s` | 通过 | 生成 `/tmp/web2audio-doubao-debug.mp3` |
| 调试音频确认 | `file /tmp/web2audio-doubao-debug.mp3` | 通过 | MP3，128 kbps，24 kHz，Monaural |
| 当前 Doubao conf 构建诊断 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... build_tts_client(Settings(tts_mode='doubao')) ... PY` | 通过 | 构建 `DoubaoTtsClient`，`resource_id=seed-tts-2.0`，`speaker=zh_female_vv_uranus_bigtts` |
| 定向回归 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_doubao_tts_client.py backend/tests/test_doubao_live_tts.py backend/tests/test_runtime_config.py` | 通过 | 9 个用例通过，1 个真实调试用例默认跳过 |
| 数据库 schema RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_db_schema.py` | 失败 | 缺少 `app.db.schema`，确认测试先于实现 |
| 数据库 schema GREEN | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_db_schema.py backend/tests/test_db_session.py` | 通过 | 3 个用例通过 |
| 当前 active 数据库落库检查 | `cd backend && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... ensure_database_schema + inspect ... PY` | 通过 | 当前 MySQL profile 包含 `article_audio_items` 和 `article_tts_segments`，索引和 CHECK 约束均存在 |
| 数据库 schema 最终启动验证 | `./init.sh` | 通过 | 后端 32 个 pytest 用例通过，1 个真实 Doubao 调试用例默认跳过，插件 2 个 node:test 用例通过 |
| 最终启动验证 | `./init.sh` | 通过 | 后端 30 个 pytest 用例通过，1 个真实 Doubao 调试用例默认跳过，插件 2 个 node:test 用例通过 |
| 端到端 case 状态更新最终启动验证 | `./init.sh` | 通过 | 后端 32 个 pytest 用例通过，1 个真实 Doubao 调试用例默认跳过，插件 2 个 node:test 用例通过 |
| 端到端 case 状态更新本地格式检查 | `git diff --check -- docs/E2E_ACCEPTANCE_CASES.md` | 通过 | 无尾随空格或补丁格式问题 |
| 端到端 case 状态更新飞书同步 | `lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json` | 通过 | revision_id 为 41 |
| 端到端 case 状态更新飞书读取验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-009' --context-before 1 --context-after 1 --format json` | 通过 | 矩阵和关键 case 明细可读取 |
| 端到端 case 状态更新飞书最终验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword '36 passed' --context-before 2 --context-after 2 --format json` | 通过 | 自动化通过列表可读取 |
| 端到端 case 状态更新飞书新增自动化验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-005' --context-before 1 --context-after 1 --format json` | 通过 | 新增 W2A-E2E-005 自动化状态可读取 |
| 端到端 case 状态更新飞书 live 边界验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'live 自动化默认跳过' --context-before 1 --context-after 1 --format json` | 通过 | live 分支默认跳过边界可读取 |
| TOS 本地 MP3 直传探针 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend python3 - <<'PY' ... TosStorage.put_object('/tmp/web2audio-doubao-debug.mp3') ... PY` | 通过 | object key 为 `web2audio/debug/manual-1782732549-web2audio-doubao-debug.mp3` |
| TOS live 自测默认模式 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_tos_live_upload.py` | 通过 | 1 个用例默认跳过，不触发远端上传 |
| TOS live 自测真实上传 | `W2A_RUN_REAL_TOS_UPLOAD=1 W2A_TOS_KEEP_OBJECT=1 W2A_TOS_UPLOAD_INPUT=/tmp/web2audio-doubao-debug.mp3 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_tos_live_upload.py -s` | 通过 | object key 为 `web2audio/debug/live-upload/c752d4cf2f9e/web2audio-doubao-debug.mp3`，content length 为 55341 |
| E2E Case 矩阵自动化定向验证 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_fake_full_chain.py` | 通过 | 5 个用例通过，覆盖 W2A-E2E-001 到 W2A-E2E-005 |
| E2E Case 矩阵自动化最终启动验证 | `./init.sh` | 通过 | 后端 36 个 pytest 用例通过，2 个真实调试用例默认跳过，插件 2 个 node:test 用例通过 |
| 网页正文到 DB 链路定向验证 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_webpage_text_db_chain.py` | 通过 | 1 个用例通过，覆盖 extractor payload、API 提交、正文处理和 MySQL 落库 |
| 网页正文到 DB 与正文任务回归 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_webpage_text_db_chain.py backend/tests/test_text_jobs.py` | 通过 | 2 个用例通过 |
| W2A-E2E-008 默认跳过验证 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py` | 通过 | 2 个 live 用例默认跳过，不触发真实外部依赖 |
| W2A-E2E-008 live 验证 | `W2A_RUN_REAL_AUDIO_JOB=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_008_real_doubao_tts_and_tos_audio_job -s` | 通过 | 1 个用例通过；真实 Doubao 合成、真实 TOS 上传和 object head 校验成功 |
| W2A-E2E-010 live 验证 | `W2A_RUN_REAL_FULL_CHAIN=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_010_real_doubao_tos_and_love_song_full_chain -s` | 通过 | 1 个用例通过；同一篇文章到 `playable`，love-song 歌单回读文章语义 |
| W2A-E2E-011/012/013 默认跳过验证 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py` | 通过 | 5 个 live 用例默认跳过，不触发真实外部依赖 |
| W2A-E2E-011/012/013 live 复跑 | `W2A_RUN_REAL_FULL_CHAIN=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_011_ios_today_reading_playable_via_love_song_api backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_012_ios_article_semantics_via_love_song_api backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_013_ios_sequential_playback_and_history_via_love_song_api -s` | 通过 | 2026-06-30 live 批量 3 passed，1 warning（urllib3 LibreSSL NotOpenSSLWarning） |
| E2E 验收文档飞书同步 | `lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json` | 通过 | revision_id 为 54 |
| E2E 验收文档飞书读取验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-011|live 批量 3 passed|37 passed|W2A_RUN_REAL_FULL_CHAIN=1' ...` | 通过 | 011/012/013 已自动化通过、live 批量 3 passed、`37 passed、7 skipped` 和 live 命令可读取 |
| E2E case 状态更新最终启动验证 | `./init.sh` | 通过 | 后端 37 passed、7 skipped，插件 2 passed |
| E2E case 状态更新 JSON 校验 | `python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok` | 通过 | `feature_list.json` 结构合法 |
| E2E case 状态更新差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| Chrome 插件正文提取回归 | `node --test extension/tests/article_extractor.test.cjs` | 通过 | 2 个 node:test 用例通过 |
| 网页正文到 DB 链路最终启动验证 | `./init.sh` | 通过 | 后端 37 个 pytest 用例通过，4 个默认跳过用例，插件 2 个 node:test 用例通过 |
| 网页正文到 DB 链路 JSON 校验 | `python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok` | 通过 | `feature_list.json` 结构合法 |
| 网页正文到 DB 链路差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| W2A-E2E-008/010 飞书同步 | `lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json` | 通过 | 历史 revision_id 50 |
| W2A-E2E-008/010 飞书读取验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-008|W2A-E2E-010|37 passed|W2A_RUN_REAL_FULL_CHAIN=1' ...` | 通过 | 008/010 已自动化通过；当前最新读取验证见 revision_id 54 记录 |
| TOS 相关定向回归 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_tos_live_upload.py backend/tests/test_runtime_config.py backend/tests/test_audio_jobs.py` | 通过 | 9 个用例通过，1 个真实 TOS 上传用例默认跳过 |
| TOS 上传自测最终启动验证 | `./init.sh` | 通过 | 后端 32 个 pytest 用例通过，2 个真实调试用例默认跳过，插件 2 个 node:test 用例通过 |
| JSON 校验 | `python3 -m json.tool feature_list.json >/tmp/web2audio_feature_list.json && echo ok` | 通过 | `feature_list.json` 结构合法 |
| 产品文档技术残留检查 | `rg -n "tracks|audio_assets|playback-url|playback-sessions|play-history|TINYINT|VARCHAR|HTTP|/api|接口路径|数据表|枚举" docs/PRODUCT.md` | 通过 | 仅命中文档分工说明，无具体技术方案残留 |
| MVP 范围残留检查 | `rg -n "车载|CarPlay|锁屏|后台播放|未听完优先|playback-url表|audio_assets表" docs/PRODUCT.md feature_list.json docs/TECHNICAL_DESIGN.md` | 通过 | 后台、锁屏、CarPlay 仅出现在非目标语境 |
| 启动验证 | `./init.sh` | 通过 | 必需文件存在，6 个功能条目结构合法，未发现模板文本残留 |
| 差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| 浏览器评论残留检查 | `rg -n "failure_reason|audio_mime_type|retry_count|voice_id|/retry|article_not_retryable" docs/TECHNICAL_DESIGN.md` | 通过 | 无命中，确认被删除字段和接口不再残留 |
| 评论改动确认检查 | `rg -n "豆包 lite|火山云 TOS|https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ|article_tts_segments|snake_case|跨工程落地方式" docs/TECHNICAL_DESIGN.md feature_list.json` | 通过 | 命中预期内容 |
| 最终启动验证 | `./init.sh` | 通过 | 必需文件存在，6 个功能条目结构合法，未发现模板文本残留 |
| 最终差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| 临时 HTML 预览 | `curl -I http://127.0.0.1:4173/index.html` | 通过 | 返回 `200 OK` |
| 后端测试首轮 RED | `python3 -m pytest backend/tests/test_articles_api.py` | 失败 | 缺少 `app` 模块，确认测试先于实现 |
| 插件测试首轮 RED | `node --test extension/tests/article_extractor.test.cjs` | 失败 | 缺少 `extension/content.js`，确认测试先于实现 |
| 后端文章 API 测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_articles_api.py` | 通过 | 6 个 pytest 用例通过 |
| Chrome 插件正文提取测试 | `node --test extension/tests/article_extractor.test.cjs` | 通过 | 2 个 node:test 用例通过 |
| `feat-004` RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_audio_jobs.py` | 失败 | 缺少 `app.audio_jobs`，确认测试先于实现 |
| 音频产物测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_audio_jobs.py` | 通过 | 2 个 pytest 用例通过 |
| `feat-005` RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_love_song_contract.py` | 失败 | 缺少 `app.love_song_contract`，确认测试先于实现 |
| love-song 契约测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_love_song_contract.py` | 通过 | 2 个 pytest 用例通过 |
| `feat-008` RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_player_sync_jobs.py` | 失败 | 缺少 `app.player_sync_jobs`，确认测试先于实现 |
| 播放器同步测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_player_sync_jobs.py` | 通过 | 2 个 pytest 用例通过 |
| `feat-009` RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_fake_full_chain.py` | 失败 | 缺少 `app.self_test`，确认测试先于实现 |
| fake 全链路自测 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_fake_full_chain.py` | 通过 | 1 个 pytest 用例通过 |
| 最终统一启动验证 | `./init.sh` | 通过 | 10 个功能条目结构合法，后端 16 个 pytest 用例和插件 2 个 node:test 用例通过 |
| 最终差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| 阶段 1/2 启动验证 | `./init.sh` | 通过 | harness、后端测试和插件测试均通过 |
| 阶段 1/2 差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| `feat-003` RED 文本处理 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_text_processing.py` | 失败 | 缺少 `app.text_processing`，确认测试先于实现 |
| `feat-003` RED 文章处理 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_text_jobs.py` | 失败 | 缺少 `ArticleTtsSegment`，确认测试先于实现 |
| `feat-003` 新增测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_text_processing.py backend/tests/test_text_jobs.py` | 通过 | 3 个新增 pytest 用例通过 |
| 后端全量测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests` | 通过 | 9 个 pytest 用例通过 |
| Chrome 插件正文提取测试 | `node --test extension/tests/article_extractor.test.cjs` | 通过 | 2 个 node:test 用例通过 |
| runtime 边界 RED | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_love_song_http_client.py backend/tests/test_db_session.py` | 失败 | 缺少 `app.clients` 和 `app.core`，确认测试先于实现 |
| runtime 边界新增测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests/test_runtime_config.py backend/tests/test_love_song_http_client.py backend/tests/test_db_session.py` | 通过 | 7 个新增 pytest 用例通过 |
| runtime 边界后端全量测试 | `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests` | 通过 | 23 个 pytest 用例通过 |
| runtime 边界最终启动验证 | `./init.sh` | 通过 | 10 个功能条目结构合法，后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| runtime 边界差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| 端到端测试文档启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| 端到端测试文档差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| 端到端测试文档飞书导入 | `lark-cli docs +create --api-version v2 --doc-format markdown --content @docs/END_TO_END_TEST_CASES.md --format json` | 通过 | 旧 bot 文档创建成功；自动授权失败，缺少应用后台 `docs:permission.member:create` 等 scope |
| 端到端测试文档最终启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| 端到端测试文档最终差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| lark-cli 升级 | `lark-cli update --json` | 通过 | 版本从 `1.0.46` 升级到 `1.0.59`，官方 skills 已同步 |
| lark-cli 用户授权 | `lark-cli auth login --device-code ...` | 通过 | 用户 `刘浩` 已授予 docx 创建/读写和 `docs:permission.member:create` |
| 端到端测试文档用户身份导入 | `lark-cli docs +create --api-version v2 --as user --doc-format markdown --content @docs/END_TO_END_TEST_CASES.md --title 'web2audio 端到端测试 Case 设计' --format json` | 通过 | 新文档 URL 为 `https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b` |
| 端到端测试文档用户身份读取验证 | `lark-cli docs +fetch --api-version v2 --as user --doc 'https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b' --doc-format markdown --scope outline --format json` | 通过 | outline 能正常读取 |
| 飞书链接更新后最终启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| 飞书链接更新后最终差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| 端到端 case 状态标注启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| 端到端 case 状态标注飞书同步 | `lark-cli docs +update --doc 'https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b' --as user --command overwrite --doc-format markdown --content @docs/END_TO_END_TEST_CASES.md --format json` | 通过 | 飞书文档覆盖更新成功 |
| 端到端 case 状态标注飞书读取验证 | `lark-cli docs +fetch --doc 'https://bytedance.larkoffice.com/docx/D9REdC0KxofH0fxZ8bjcJOFKn9b' --as user --doc-format markdown --scope keyword --keyword 'Case 状态总览' --context-after 2 --format json` | 通过 | 状态总览可读取 |
| 端到端 case 状态标注最终启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| 端到端 case 状态标注最终差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| e2e-test-design 版文档结构检查 | `rg -n "证据表|领域划分|Case 矩阵|已自动化通过的 Case|待确认的 Case|P0 冒烟集|未覆盖风险" docs/E2E_ACCEPTANCE_CASES.md` | 通过 | 只命中预期章节，无独立证据表或独立领域划分章节 |
| e2e-test-design 版文档差异格式检查 | `git diff --check -- docs/E2E_ACCEPTANCE_CASES.md` | 通过 | 无尾随空格或补丁格式问题 |
| e2e-test-design 版文档飞书创建 | `lark-cli docs +create --as user --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --title 'web2audio 端到端验收 Case 设计（e2e-test-design）' --format json` | 通过 | 新文档 URL 为 `https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb` |
| e2e-test-design 版文档飞书目录读取验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope outline --format json` | 通过 | outline 能正常读取 |
| e2e-test-design 版文档飞书关键词读取验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-001' --context-after 1 --format json` | 通过 | `W2A-E2E-001` 矩阵与明细可读取 |
| e2e-test-design 版文档最终启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| e2e-test-design 版文档最终差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |
| E2E Case 矩阵简化前启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| E2E Case 矩阵简化本地格式检查 | `git diff --check -- docs/E2E_ACCEPTANCE_CASES.md` | 通过 | 无尾随空格或补丁格式问题 |
| E2E Case 矩阵简化飞书同步 | `lark-cli docs +update --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --command overwrite --doc-format markdown --content @docs/E2E_ACCEPTANCE_CASES.md --format json` | 通过 | revision_id 为 13 |
| E2E Case 矩阵简化飞书读取验证 | `lark-cli docs +fetch --as user --doc 'https://bytedance.larkoffice.com/docx/OFG1dKwKWoaRUwxXJ83cbbuanRb' --doc-format markdown --scope keyword --keyword 'W2A-E2E-014' --context-before 1 --context-after 1 --format json` | 通过 | 简化矩阵行可读取 |
| E2E Case 矩阵简化最终启动验证 | `./init.sh` | 通过 | 后端 23 个 pytest 用例和插件 2 个 node:test 用例通过 |
| E2E Case 矩阵简化最终差异格式检查 | `git diff --check` | 通过 | 无尾随空格或补丁格式问题 |

## 本次修改文件

- `docs/PRODUCT.md`
- `docs/TECHNICAL_DESIGN.md`
- `docs/E2E_ACCEPTANCE_CASES.md`
- `docs/END_TO_END_TEST_CASES.md`
- `feature_list.json`
- `progress.md`
- `session-handoff.md`
- `README.md`
- `AGENTS.md`
- `.gitignore`
- `backend/README.md`
- `backend/conf/`
- `backend/conf/love_song.example.json`
- `backend/app/__init__.py`
- `backend/app/asgi.py`
- `backend/app/main.py`
- `backend/app/audio_jobs.py`
- `backend/app/clients/`
- `backend/app/clients/doubao.py`
- `backend/app/clients/tts.py`
- `backend/tests/test_doubao_tts_client.py`
- `backend/tests/test_doubao_live_tts.py`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/app/db/schema.py`
- `backend/app/love_song_contract.py`
- `backend/app/player_sync_jobs.py`
- `backend/app/runtime.py`
- `backend/app/self_test.py`
- `backend/app/text_jobs.py`
- `backend/app/text_processing.py`
- `backend/requirements.txt`
- `backend/tests/test_articles_api.py`
- `backend/tests/test_audio_jobs.py`
- `backend/tests/test_db_session.py`
- `backend/tests/test_db_schema.py`
- `backend/tests/test_live_e2e_external_chain.py`
- `backend/tests/test_tos_live_upload.py`
- `backend/tests/test_webpage_text_db_chain.py`
- `backend/tests/test_fake_full_chain.py`
- `backend/tests/test_love_song_contract.py`
- `backend/tests/test_love_song_http_client.py`
- `backend/tests/test_player_sync_jobs.py`
- `backend/tests/test_runtime_config.py`
- `backend/tests/test_text_jobs.py`
- `backend/tests/test_text_processing.py`
- `extension/README.md`
- `extension/content.js`
- `extension/manifest.json`
- `extension/popup.html`
- `extension/popup.js`
- `extension/tests/article_extractor.test.cjs`
- `init.sh`

## 已做决策

| 决策 | 原因 | 影响 |
| --- | --- | --- |
| 产品与技术文档拆分 | 产品评审不应混入表结构和接口细节 | 技术方案进入 `docs/TECHNICAL_DESIGN.md` |
| 第一版播放目标限定在 iOS 播放器内 | 降低 MVP 复杂度 | 车载、后台、锁屏、CarPlay 暂不验收 |
| 按原始 `source_url` 精确去重 | 用户确认并简化实现 | 不做 canonical URL 或内容 hash 合并 |
| web2audio 通过 HTTP 调 love-song | 系统解耦 | love-song 需提供幂等资源登记能力 |
| 「今日待读」采用追加顺序 | 复用播放器歌单策略 | web2audio 不维护独立播放排序 |
| 失败详情不入库 | 错误原因类型不稳定，且日志更适合排障 | 业务表只保存阶段状态，日志负责错误细节 |
| 不设计公开重跑 API | 当前技术方案先收敛提交与查询接口 | 失败任务由任务系统或运维动作重新投递 |
| 使用豆包语音合成 WebSocket | 收敛 TTS 选型并对齐火山真实协议 | `resource_id`、音色和凭据作为运行时配置 |
| 使用火山云 TOS | 收敛对象存储选型 | web2audio 与 love-song 传递 object key |
| fake 与真实 runtime 显式分离 | 避免线上误用 fake，也保持本仓库自测稳定 | 默认 fake；真实豆包/TOS/love-song 通过 `.env` 和 `*.local.json` 显式启用 |

## 风险与阻塞

- love-song 8000 仍是旧进程，`POST /api/assets/tos` 返回 404；当前代码需重启或改用 8001 服务。
- iOS 文案去音乐化的接口语义已由 `W2A-E2E-012` 覆盖；真机或模拟器仍可抽查最终视觉渲染。
- 当前 active 数据库已更新为 MySQL；目标环境切换时仍需在对应 MySQL 实例执行 schema 初始化或迁移。
- 当前插件正文提取为启发式规则，复杂页面的正文质量仍需继续通过后续处理策略观察和补充。
- 当前网页到 DB 自动化覆盖的是 Node 直接调用 extractor、后端 API 和正文处理链路，不覆盖真实 Chrome 点击、popup UI 权限或任意复杂网页的正文质量。
- 当前本仓库 fake 自测链路已经到 `playable`，显式开启的真实 Doubao/TOS/love-song HTTP 后端链路也已经到 `playable`。
- fake TTS、fake TOS 和 fake love-song client 只用于本仓库自测；真实后端验收以 `W2A_RUN_REAL_AUDIO_JOB=1` 和 `W2A_RUN_REAL_FULL_CHAIN=1` 的 live 自动化结果为准。
- love-song iOS 文章音频展示语义已通过 iOS 对应接口（歌单详情、播放会话、播放 URL、播放历史）自动化验证（`W2A-E2E-011` 到 `W2A-E2E-013`）；真机或模拟器播放体验、文案渲染仍可人工抽查。
- 豆包 TTS client 当前已按火山双向 WebSocket 协议真实生成音频，但真实时长仍按字符数估算；真实时长精确计算仍需后续 provider 元数据或音频探测。
- `W2A-E2E-008`、`W2A-E2E-010` 和 `W2A-E2E-011` 到 `W2A-E2E-013` 的 live 自动化默认跳过；外部配置或远端服务变更后，需要显式开启环境变量复跑确认。
- 当前 `backend/conf/love_song.local.json` 已指向 `http://127.0.0.1:8001`；该文件属于本地忽略配置，不应提交密钥。
- love-song 8000 仍是旧进程，`POST /api/assets/tos` 返回 404；需要重启或改用 8001 当前代码服务。复跑 iOS 接口 live 用例前需先在 8001 启动 love-song 当前代码服务。

## 下一次启动

1. 阅读 `AGENTS.md`。
2. 阅读 `docs/PRODUCT.md`、`docs/TECHNICAL_DESIGN.md`、`feature_list.json`、`progress.md` 和本文件。
3. 运行 `./init.sh`。
4. 如需复跑 iOS 接口 live 自动化，先在 8001 启动 love-song 当前代码服务，再显式开启 `W2A_RUN_REAL_FULL_CHAIN=1` 跑 `W2A-E2E-011/012/013`；如怀疑外部配置漂移，也可显式开启 `W2A_RUN_REAL_AUDIO_JOB=1` 复跑 008。

## 建议下一步

- iOS 接口层 `W2A-E2E-011` 到 `W2A-E2E-013` 已自动化通过；下一步可选在真机或模拟器做体验层抽查（播放流畅度、文案渲染），或推进 `W2A-E2E-014` 线上清理与成本安全。

<!-- harness-validator: Current Objective; Blockers; Files; Next Session; Recommended Next Step; Verification Evidence. -->
