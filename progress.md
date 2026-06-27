# 会话进度记录

## 当前状态

**最后更新：** 2026-06-27 11:01 CST
**当前功能：** AGENTS.md harness 文档维护
**阶段：** 已更新启动范围、验证范围和 fake / 真实验收边界

## 已完成

- 已确认当前目录是 `/Users/bytedance/Codebases/web2audio`。
- 已阅读 `AGENTS.md`、`README.md`、`docs/PRODUCT.md`、`docs/TECHNICAL_DESIGN.md`、`feature_list.json`、`progress.md` 和 `session-handoff.md`。
- 已运行 `./init.sh`，确认当前文档和 harness 基线可用。
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

## 正在处理

- 无。

## 下一步

1. 本仓库 fake 全链路自测已满足。
2. 真实跨工程仍需推进 `feat-006` love-song TOS 资源登记 API 和 `feat-007` love-song iOS 文章音频展示语义。
3. `feat-006`、`feat-007` 完成后，再执行 `feat-010` 真实端到端验收与风险收敛。

## 风险与阻塞

- 当前后端仍使用本地 SQLite 作为个人 MVP 默认存储；技术方案中的 MySQL 表结构属于后续部署形态。
- 当前插件正文提取为第一版启发式规则，复杂站点正文质量仍需通过后续清洗链路兜底。
- 当前后端已完成文章任务提交、查询、正文清洗、分段、fake TTS/TOS 音频产物和 fake love-song 同步。
- 本仓库 fake 自测已到 `playable`；真实 love-song 后端和 iOS 尚未完成，不能视为真实跨工程验收完成。
- `docs/TECHNICAL_DESIGN.md` 记录的 love-song `POST /api/assets/tos` 资源登记能力当前仍是依赖契约，love-song 侧尚未实现对应路由。
- iOS 避免「未知艺术家」「首歌」等音乐化文案需要 love-song API/iOS 识别 `content_type=article_audio`，当前属于后续实现范围。

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
| 第一版使用豆包 lite 模型 | 收敛 TTS 选型 | 模型 ID、音色和凭据进入运行时配置，不进入业务表 |
| 第一版使用火山云 TOS | 收敛对象存储选型 | web2audio 与 love-song 传递 object key，不传云凭据 |
| 后续任务按工作流并行拆分 | 原串行依赖把 web2audio、love-song 后端和 iOS 强行排成单链路 | `feature_list.json` 现在用 `parallel_group` 表达可并行批次，用真实依赖控制最终集成 |

## 本次修改文件

- `docs/PRODUCT.md`：更新为产品方案文档，收敛 MVP 范围和 love-song 产品边界。
- `docs/TECHNICAL_DESIGN.md`：新增技术方案，覆盖数据库设计、API 设计和 love-song 集成契约。
- `feature_list.json`：同步更新 TTS 和播放器接入功能描述。
- `progress.md`：记录本次文档更新、决策和验证。
- `session-handoff.md`：更新跨会话交接信息。
- `README.md`：更新当前状态、本地启动和验证说明。
- `.gitignore`：忽略 Python 测试缓存、字节码和本地 SQLite 数据库。
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

## 验证记录

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

## 给下一次会话

先运行 `./init.sh`。如果通过，本仓库 fake 自测链路已经满足；真实跨工程下一步推进 `feat-006` 或 `feat-007`。

<!-- harness-validator: Current State; What's Done; What's Next; Evidence; Last Updated; Recommended Next Step. -->
