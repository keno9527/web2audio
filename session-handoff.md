# 会话交接

## 当前目标

- 目标：持续推进到本仓库 fake 全链路自测满足。
- 当前状态：`feat-009` 已实现并通过统一自测；真实跨工程仍需推进 `feat-006`、`feat-007` 和 `feat-010`。
- 分支与提交：当前分支 `codex/feat-002-submit-entry` 基于 `f55c256 Localize project harness docs`，本次未提交。

## 本次已完成

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
  - 建立第一版 `article_audio_items` SQLAlchemy 模型，默认使用本地 SQLite 便于 MVP 验证。
  - 请求校验采用 Pydantic，错误响应统一为 `{error:{code,message,details}}`。
- 完成阶段 2 Chrome 插件提交入口：
  - 新增 Manifest V3 插件。
  - `content.js` 从当前页面提取 `source_url`、标题、正文、站点、作者、发布时间、封面和语言提示。
  - `popup.js` 支持配置 API 地址和 token，并将当前文章提交到 `POST /api/articles`。
  - 弹窗展示首次提交和重复提交的结果状态。
- 验证入口更新：
  - `./init.sh` 已接入后端 pytest 和插件 node:test。
  - `README.md`、`backend/README.md`、`extension/README.md` 已记录本地启动与验证方式。
  - `.gitignore` 已忽略 Python 缓存和本地 SQLite 数据库。
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

## 验证证据

| 检查 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
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

## 本次修改文件

- `docs/PRODUCT.md`
- `docs/TECHNICAL_DESIGN.md`
- `feature_list.json`
- `progress.md`
- `session-handoff.md`
- `README.md`
- `AGENTS.md`
- `.gitignore`
- `backend/README.md`
- `backend/app/__init__.py`
- `backend/app/asgi.py`
- `backend/app/main.py`
- `backend/app/audio_jobs.py`
- `backend/app/love_song_contract.py`
- `backend/app/player_sync_jobs.py`
- `backend/app/self_test.py`
- `backend/app/text_jobs.py`
- `backend/app/text_processing.py`
- `backend/requirements.txt`
- `backend/tests/test_articles_api.py`
- `backend/tests/test_audio_jobs.py`
- `backend/tests/test_fake_full_chain.py`
- `backend/tests/test_love_song_contract.py`
- `backend/tests/test_player_sync_jobs.py`
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
| 使用豆包 lite 模型 | 收敛 TTS 选型 | 模型和音色作为运行时配置 |
| 使用火山云 TOS | 收敛对象存储选型 | web2audio 与 love-song 传递 object key |

## 风险与阻塞

- love-song 当前已有歌单和播放 API，但 `POST /api/assets/tos` 资源登记路由尚未实现；需要在 love-song 仓库补齐契约和测试。
- iOS 文案去音乐化依赖 love-song API/iOS 支持 `content_type=article_audio` 或等价展示语义。
- 当前后端默认 SQLite 只用于个人 MVP 本地验证；生产部署仍需按技术方案迁移到目标数据库。
- 当前插件正文提取为启发式规则，复杂页面的正文质量仍需继续通过后续处理策略观察和补充。
- 当前本仓库 fake 自测链路已经到 `playable`。
- fake TTS、fake TOS 和 fake love-song client 只用于本仓库自测，不代表真实豆包、火山云 TOS 或 love-song 后端已完成。
- 真实 love-song `POST /api/assets/tos` 和 iOS 文章音频展示语义仍未实现。

## 下一次启动

1. 阅读 `AGENTS.md`。
2. 阅读 `docs/PRODUCT.md`、`docs/TECHNICAL_DESIGN.md`、`feature_list.json`、`progress.md` 和本文件。
3. 运行 `./init.sh`。
4. 本仓库 fake 自测链路已满足；真实跨工程下一步推进 `feat-006` 或 `feat-007`。

## 建议下一步

- 真实跨工程下一步优先补 love-song `POST /api/assets/tos` 路由、service、schema 和测试，或推进 iOS 对 `content_type=article_audio` 的展示语义。

<!-- harness-validator: Current Objective; Blockers; Files; Next Session; Recommended Next Step; Verification Evidence. -->
