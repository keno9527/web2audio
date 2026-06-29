# web2audio 端到端验收 Case 设计

本文档按 `e2e-test-design` skill 重新整理 web2audio 第一版端到端验收 case。文档只保留影响验收执行的目标、环境、配置、case 矩阵、关键明细、自动化进度、待确认事项和剩余风险。

状态更新时间：2026-06-29 19:43 CST。

## 1. 验收目标和链路摘要

### 验收目标

第一版验收目标是证明用户能在 Chrome 当前文章页主动保存文章，web2audio 能把文章生成音频并登记到 love-song 固定歌单「今日待读」，最终用户能在 love-song iOS 播放器中连续播放文章音频。

当前完成口径分两层：

| 层级 | 完成口径 | 当前状态 |
| --- | --- | --- |
| 本仓库 mock 闭环 | API 提交文章后，经正文处理、fake TTS、fake TOS、fake love-song，同步到 `playable` | 已自动化通过；最新 `./init.sh` 后端 37 passed、4 skipped，插件 2 passed |
| 真实跨工程闭环 | Chrome 插件真实提交，真实豆包/TOS 生成音频，真实 love-song 后端登记资源，iOS「今日待读」连续播放 | 真实 Doubao + TOS audio job 已自动化通过；真实 Doubao + TOS + love-song HTTP 到 `playable` 已自动化通过；iOS 未验收 |

### 链路摘要

```mermaid
flowchart LR
  A["Chrome 当前文章"] --> B["插件提取标题、URL、正文和元信息"]
  B --> C["POST /api/articles"]
  C --> D["web2audio 文章任务"]
  D --> E["正文清洗与分段"]
  E --> F["TTS 生成和 TOS 存储"]
  F --> G["love-song 资源登记"]
  G --> H["追加固定歌单：今日待读"]
  H --> I["love-song iOS 连续播放"]
```

验收中必须区分 fake 自测和真实验收：fake TTS、fake TOS、fake love-song 只能证明 web2audio 本地编排正确，不能证明真实豆包、火山云 TOS、love-song 后端或 iOS 播放体验已经可用。

## 2. 环境准备方式、配置项、账号、测试数据和清理策略

### 本地 mock 环境

| 项目 | 准备方式 |
| --- | --- |
| 目标环境 | 本地仓库 `/Users/bytedance/Codebases/web2audio` |
| 服务地址 | 后端默认 `http://127.0.0.1:8000`；自动化测试使用 FastAPI `TestClient` |
| 数据库 | 当前 MySQL profile；自动化测试按独立 `owner_user_id` 隔离并清理数据 |
| 外部依赖模式 | `TTS_MODE=fake`、`STORAGE_MODE=fake`、`LOVE_SONG_MODE=fake` |
| 账号和权限 | 默认固定 token；测试 token 为 `test-token`，本地开发 token 为 `dev-token` |
| 测试数据 | 公开文章 URL `https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ`；中文正文、站点、作者、发布时间和封面 URL |
| 清理策略 | MySQL 测试数据按 `owner_user_id` 清理；fake TOS object 和 fake love-song 歌单状态随测试进程销毁 |
| 当前验证命令 | `./init.sh`，后端 37 passed、4 skipped，插件 2 passed |

### 线上配置联调环境

| 项目 | 准备方式 |
| --- | --- |
| 目标环境 | 待确认，建议使用独立 staging 或个人联调环境 |
| 配置项 | `TTS_MODE=doubao`、`STORAGE_MODE=tos`、`LOVE_SONG_MODE=http` |
| 配置文件 | `backend/conf/doubao.local.json`、`backend/conf/tos.local.json`、`backend/conf/love_song.local.json` |
| 账号和权限 | 豆包 token、TOS AK/SK 与 bucket 权限、love-song service token |
| 测试数据隔离 | 建议使用测试 owner、测试 playlist 或测试标签；TOS object prefix 使用 `e2e/web2audio/{run_id}/` |
| 清理策略 | 记录 article_id、TOS object key、track_id、asset_id、playlist item；live 自动化按测试 owner 清理 web2audio 数据，默认删除 TOS object 和 love-song playlist item |
| 不进入默认验证 | 线上 case 不应进入 `./init.sh`，避免密钥、成本和外部服务抖动影响本地启动 |
| 当前联调状态 | `doubao.local.json` 可构建真实 Doubao WebSocket client；`tos.local.json` 可写入并校验真实 TOS object；`love_song.local.json` 指向本地 love-song 当前代码服务 `http://127.0.0.1:8001`；W2A-E2E-008 和 W2A-E2E-010 已显式开启 live 自动化通过 |

### iOS 人工验收环境

| 项目 | 准备方式 |
| --- | --- |
| 入口 | Chrome unpacked extension、web2audio 后端、love-song 后端、love-song iOS |
| 环境要求 | Chrome 插件和 love-song iOS 指向同一套后端环境 |
| 账号和资源归属 | 个人 MVP 默认用户；真实多用户归属待后续设计 |
| 验收证据 | 插件提交截图、web2audio article 详情、love-song 歌单截图、播放页截图、必要的 track_id 和 article_id |
| 清理策略 | 测试文章、TOS object、love-song track/asset/playlist item 需要可枚举和可清理 |

## 3. E2E Case 矩阵

矩阵只做全量索引和进度跟踪。环境准备见第 2 章；可执行步骤、断言和验收证据放在第 4 章关键 case 明细中。

| Case ID | Case 分类 | 验收目标 | 执行分支 | 核心断言 | 跟进状态 | 优先级 |
| --- | --- | --- | --- | --- | --- | --- |
| W2A-E2E-001 | 文章转音频/主路径/mock | 证明 fake 链路能从文章提交闭环到 `playable` | 自动化 | `./init.sh` 已覆盖 fake full chain 到 `playable`；后端 37 passed、4 skipped，插件 2 passed | 已自动化通过 | P0 |
| W2A-E2E-002 | 文章收集/幂等重复/mock | 证明同一原始 URL 重复提交不重复建文章或重复追加歌单 | 自动化 | 重复提交返回同一 article_id；文章总数不增加；重复同步不重复追加歌单 track | 已自动化通过 | P0 |
| W2A-E2E-003 | 正文处理/数据边界/mock | 证明无有效正文不会消耗音频生成或进入播放链路 | 自动化 | text failed；audio/player failed；无 audio key；无 love-song IDs 和副作用 | 已自动化通过 | P0 |
| W2A-E2E-004 | 音频生成/异步失败/mock | 证明 TTS 或 TOS 异常不会产生错误可播放数据 | 自动化 | TTS 失败后 article failed；无 storage object；无 love-song 登记 | 已自动化通过 | P1 |
| W2A-E2E-005 | 播放器同步/外部依赖失败/mock | 证明 love-song 同步失败时音频产物保留且可重试 | 自动化 | 首次同步失败保留音频 key；恢复 love-song 后可同步到 `playable` | 已自动化通过 | P1 |
| W2A-E2E-006 | 运行时配置/兼容回归 | 证明默认 fake 和真实配置不会混淆 | 自动化 | `test_runtime_config.py` 已通过，覆盖 MySQL 默认 URL、active profile、拒绝本地文件库和真实配置快速失败 | 已自动化通过 | P0 |
| W2A-E2E-007 | Chrome 插件/入口回归 | 证明插件能从当前网页提取可提交文章 payload，并经 API 和正文任务落库 | 自动化 | 提取文章 payload；POST 创建文章；text ready；MySQL 存在清洗正文和 TTS 分段 | 已自动化通过 | P1 |
| W2A-E2E-008 | 真实 TTS/TOS/外部依赖 | 证明真实豆包和火山云 TOS 能生成可同步音频 | 半自动化 | 显式开启 `W2A_RUN_REAL_AUDIO_JOB=1` 后，真实 Doubao 合成、真实 TOS 上传和 object head 校验通过 | 已自动化通过 | P0 |
| W2A-E2E-009 | love-song 后端/跨系统契约 | 证明真实 love-song 可登记 TOS 文章音频并追加「今日待读」 | 半自动化 | love-song 8001 资产登记和歌单追加返回 201；web2audio fake TTS/storage + 真实 love-song HTTP 分支到 `playable` | 已人工通过 | P0 |
| W2A-E2E-010 | 真实后端/主路径/跨系统 | 证明三类真实依赖下 web2audio 能推进到 `playable` | 半自动化 | 显式开启 `W2A_RUN_REAL_FULL_CHAIN=1` 后，同一篇文章到达 `playable`，love-song 歌单回读为 `article_audio` | 已自动化通过 | P0 |
| W2A-E2E-011 | iOS 播放/主路径/人工 | 证明 Chrome 提交后 iOS「今日待读」可看到并播放文章 | 人工 | 插件结果明确；iOS 歌单出现文章；播放页可播放 | 待人工验证 | P0 |
| W2A-E2E-012 | iOS 展示/内容语义/人工 | 证明文章音频不被误展示为普通歌曲 | 人工 | love-song 后端已返回 `content_type=article_audio` 和 `subtitle`；iOS 展示仍待真机或模拟器验证 | 待人工验证 | P0 |
| W2A-E2E-013 | iOS 播放/顺序和历史/人工 | 证明多篇文章按追加顺序连续播放并记录历史 | 人工 | 歌单顺序稳定；下一首符合追加顺序；播放历史记录 article track | 待人工验证 | P1 |
| W2A-E2E-014 | 线上清理/成本安全 | 证明线上联调数据可枚举、可清理、成本可控 | 半自动化 | 测试数据可列出；清理不影响真实数据；调用次数可统计 | 待确认 | P1 |

## 4. 关键 Case 明细

### W2A-E2E-001：普通文章提交到可播放

- 验收目标：证明本仓库可在不依赖真实外部服务时，将普通文章从提交推进到 `playable`。
- Case 分类：文章转音频 / 主路径 / mock。
- 环境准备方式：当前 MySQL profile；fake TTS、fake TOS、fake love-song；测试按独立 `owner_user_id` 隔离并清理 MySQL 数据。
- 配置项：默认 fake runtime；测试 token `test-token`；固定 playlist_id `pl_today_reading`。
- 账号和权限：固定 Bearer token。
- 测试数据：公开文章 URL、标题、正文、站点、作者、发布时间、封面和语言提示。
- 操作路径：调用文章提交入口；执行正文处理；执行音频生成；执行播放器同步；查询文章详情。
- 预期结果：文章进入 `playable`，且最终音频和 love-song 承接结果均存在。
- 断言点：
  - 用户可见：文章详情派生状态为 `playable`。
  - API：`GET /api/articles/{article_id}` 返回 `status=playable`，三个阶段状态均为 `ready`。
  - 数据：写入 `audio_storage_key`、`love_song_track_id`、`love_song_asset_id`、`love_song_playlist_id`。
  - 任务/文件/外部系统：fake TOS 包含最终音频 key；fake love-song 歌单包含该 track。
  - 日志/审计：当前未设计独立审计日志，失败定位依赖测试结果和 article_id。
- 验收证据：`backend/tests/test_fake_full_chain.py::test_fake_full_chain_reaches_playable_article_state`；最新 `./init.sh` 通过。
- 执行方式：自动化。
- 跟进状态：已自动化通过。
- 自动化入口：`./init.sh`。
- 待确认事项：真实 Chrome 点击、真实豆包/TOS、真实 love-song、iOS 不在此 case 覆盖范围。
- 优先级：P0。
- 风险说明：该 case 是 mock 主干，不可替代真实跨工程验收。

### W2A-E2E-002：重复提交同一文章不产生重复副作用

- 验收目标：证明同一原始 `source_url` 重复保存时，只保留一个 article，并且不会重复追加 love-song 歌单。
- Case 分类：文章收集 / 幂等重复 / mock。
- 环境准备方式：本地 mock；同一测试数据库和同一个 fake love-song client 状态。
- 配置项：默认 fake runtime；固定 playlist_id。
- 账号和权限：固定 Bearer token。
- 测试数据：先构造一篇已 `playable` 文章，再使用完全相同 `source_url` 重复提交。
- 操作路径：首次跑通 W2A-E2E-001；重复 `POST /api/articles`；再次触发正文、音频、同步入口；查询文章列表和 fake 歌单。
- 预期结果：重复提交返回已有 article，播放器副作用只发生一次。
- 断言点：
  - 用户可见：重复提交返回已有任务和当前状态。
  - API：`created=false`；`article_id` 与首次提交一致。
  - 数据：文章总数不增加。
  - 任务/文件/外部系统：fake love-song 歌单只包含一个 track；重复同步返回相同 track_id 和 asset_id。
  - 日志/审计：可用 article_id 定位重复提交和同步行为。
- 验收证据：`backend/tests/test_fake_full_chain.py::test_duplicate_submission_after_playable_keeps_single_article_and_playlist_track`；最新 `./init.sh` 通过。
- 执行方式：自动化。
- 跟进状态：已自动化通过。
- 自动化入口：`./init.sh`。
- 待确认事项：重复发生在 `submitted`、`audio ready`、`playable` 三个状态时是否都需要进入同一个 E2E case；建议主 E2E 只覆盖 `playable` 后重复，其他状态下沉到 service/API 测试。
- 优先级：P0。
- 风险说明：重复副作用会直接污染「今日待读」，发布前应进入冒烟。

### W2A-E2E-003：正文不可用时不生成音频

- 验收目标：证明无效正文不会消耗 TTS/TOS，也不会进入播放链路。
- Case 分类：正文处理 / 数据边界 / mock。
- 环境准备方式：本地 mock；fake client 支持调用记录检查。
- 配置项：默认 fake runtime。
- 账号和权限：固定 Bearer token。
- 测试数据：正文过短、空正文、只有导航噪音的正文。
- 操作路径：提交无效正文；执行正文处理；尝试音频生成和播放器同步；查询文章详情。
- 预期结果：文章停在失败状态，且没有任何音频或 love-song 副作用。
- 断言点：
  - 用户可见：文章状态为 `failed` 或提交阶段返回校验失败。
  - API：失败状态和错误结构符合当前 API 契约。
  - 数据：`audio_storage_key` 为空；`love_song_track_id`、`love_song_asset_id`、`love_song_playlist_id` 为空。
  - 任务/文件/外部系统：fake TTS/TOS/love-song 没有产生成功副作用。
  - 日志/审计：能通过 article_id 或请求结果定位正文失败阶段。
- 验收证据：`backend/tests/test_fake_full_chain.py::test_invalid_article_text_does_not_generate_audio_or_player_side_effects`；最新 `./init.sh` 通过。
- 执行方式：自动化。
- 跟进状态：已自动化通过。
- 自动化入口：`./init.sh`。
- 待确认事项：导航噪音识别规则仍需根据真实页面质量迭代。
- 优先级：P0。
- 风险说明：该 case 控制成本和脏数据风险。

### W2A-E2E-006：运行时配置边界不混淆

- 验收目标：证明默认本地自测稳定使用 fake，真实模式缺配置时快速失败，避免线上误用 fake 或半配置状态。
- Case 分类：运行时配置 / 兼容回归。
- 环境准备方式：本地配置测试，无真实密钥。
- 配置项：默认 settings；`TTS_MODE=doubao`、`STORAGE_MODE=tos`、`LOVE_SONG_MODE=http` 但配置文件缺失。
- 账号和权限：不需要真实外部账号。
- 测试数据：临时缺失配置路径。
- 操作路径：构建 TTS、storage、love-song client。
- 预期结果：默认返回 fake client；真实模式缺配置时抛配置错误。
- 断言点：
  - 用户可见：不涉及 UI。
  - API：不涉及 HTTP API。
  - 数据：不写业务数据。
  - 任务/文件/外部系统：不会发起真实外部调用，也不会静默 fallback fake。
  - 日志/审计：配置错误信息能定位缺失配置类型。
- 验收证据：`backend/tests/test_runtime_config.py`；最新 `./init.sh` 通过。
- 执行方式：自动化。
- 跟进状态：已自动化通过。
- 自动化入口：`./init.sh`。
- 待确认事项：真实配置文件存在但字段缺失或格式错误的分支仍可继续补充。
- 优先级：P0。
- 风险说明：这是线上联调前的安全边界 case。

### W2A-E2E-007：网页提取 payload 后写入正文数据库

- 验收目标：证明插件提取器产生的网页文章 payload 可以被后端接收，并在正文处理后写入 MySQL 主表和分段表。
- Case 分类：Chrome 插件 / 入口回归 / 正文处理 / 数据落库。
- 环境准备方式：本地自动化；Node 调用 `extension/content.js`；后端使用当前 MySQL profile；测试按独立 `owner_user_id` 隔离并清理。
- 配置项：默认 API token；当前 MySQL profile；不依赖真实 TTS、TOS 或 love-song。
- 账号和权限：测试 owner，由 `mysql_app_factory` 自动生成。
- 测试数据：带 `article` 正文、标题、站点、作者、发布时间、封面和 `lang=zh-CN` 的模拟网页 document。
- 操作路径：Node 调用插件 extractor；将 payload 提交 `POST /api/articles`；执行 `process_article_text`；查询 `article_audio_items` 和 `article_tts_segments`。
- 预期结果：后端创建文章任务，清洗后的正文和语言写入主表，TTS 分段写入分段表。
- 断言点：
  - 用户可见：不覆盖真实浏览器点击和 popup UI。
  - API：`POST /api/articles` 返回 `201` 和 article_id。
  - 数据：`article_audio_items` 中 title、source_url、site_name、author、language、text_content、text_char_count 和 `text_status=ready` 正确；`article_tts_segments` 中分段顺序和文本正确。
  - 任务/文件/外部系统：不触发 TTS/TOS/love-song 副作用。
  - 日志/审计：失败时可由 article_id 定位提交或正文处理阶段。
- 验收证据：`backend/tests/test_webpage_text_db_chain.py`；最新 `./init.sh` 通过。
- 执行方式：自动化。
- 跟进状态：已自动化通过。
- 自动化入口：`./init.sh`。
- 待确认事项：真实 Chrome 点击、浏览器权限和复杂站点正文质量仍需单独验收。
- 优先级：P1。
- 风险说明：该 case 证明跨语言提取结果可被后端持久化，但不证明所有真实网页都能高质量提取正文。

### W2A-E2E-008：真实 Doubao TTS 与真实 TOS 音频产物

- 验收目标：证明真实豆包语音合成和真实火山云 TOS 能在同一篇文章 audio job 中连续完成，并产出可供下游同步的 TOS object key。
- Case 分类：真实 TTS/TOS / 外部依赖 / 成本风险。
- 环境准备方式：web2audio 本地 MySQL profile；真实 `TTS_MODE=doubao`；真实 `STORAGE_MODE=tos`；不触发 love-song。
- 配置项：`backend/conf/doubao.local.json`、`backend/conf/tos.local.json`。
- 账号和权限：豆包 API key、TOS AK/SK、目标 bucket 写入和 head 权限。
- 测试数据：短中文文章正文，独立 `owner_user_id` 和唯一 `source_url`。
- 操作路径：提交文章；执行正文处理；执行 `process_article_audio`；校验分段音频和最终音频 TOS object。
- 预期结果：文章 `text_status=ready`、`audio_status=ready`，分段和最终音频 object 均存在且可 `head_object`。
- 断言点：
  - 用户可见：文章详情 `audio_status=ready`。
  - API：`POST /api/articles` 返回 `201`；`GET /api/articles/{article_id}` 返回音频 ready。
  - 数据：`audio_storage_key`、`duration_seconds`、分段 `audio_storage_key` 写入。
  - 任务/文件/外部系统：真实 Doubao 返回音频；真实 TOS `does_object_exist` 和 `head_object` 成功。
  - 日志/审计：失败时可由 article_id 和 provider 请求元数据定位 TTS 或 TOS 阶段。
- 验收证据：`W2A_RUN_REAL_AUDIO_JOB=1 ... pytest backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_008_real_doubao_tts_and_tos_audio_job -s` 通过。
- 执行方式：半自动化。
- 跟进状态：已自动化通过。
- 自动化入口：显式开启 `W2A_RUN_REAL_AUDIO_JOB=1`；默认 `./init.sh` 中跳过。
- 待确认事项：真实音频时长仍按当前估算逻辑写入；精确时长探测不属于该 case。
- 优先级：P0。
- 风险说明：该 case 会产生真实外部调用和临时 TOS object；测试默认清理 TOS object，设置 `W2A_E2E_KEEP_OBJECTS=1` 时保留。

### W2A-E2E-009：真实 love-song HTTP 资源登记与歌单追加

- 验收目标：证明 web2audio 生成的 TOS object 能在真实 love-song 后端登记为文章音频，并追加到「今日待读」。
- Case 分类：love-song 后端 / 跨系统契约 / 外部依赖。
- 环境准备方式：真实 love-song 后端环境；web2audio `LOVE_SONG_MODE=http`；固定 playlist_id。
- 配置项：`backend/conf/love_song.local.json` 指向 `http://127.0.0.1:8001`。
- 账号和权限：love-song service token 具备资源登记和歌单追加权限。
- 测试数据：一条已 audio ready 的文章，包含 `content_type=article_audio`、`subtitle=site_name` 和 TOS object key。
- 操作路径：调用 `POST /api/assets/tos`；调用 `POST /api/playlists/{playlist_id}/tracks`；查询 love-song 歌单或资源。
- 预期结果：love-song 返回稳定 track_id 和 asset_id，重复登记和重复追加幂等。
- 断言点：
  - 用户可见：iOS 不在该 case 范围内。
  - API：love-song 8001 上 `POST /api/assets/tos` 返回 201，`POST /api/playlists/demo_playlist_focus/tracks` 返回 201。
  - 数据：love-song 返回 `track_1b8f330840b24282b53f`、`asset_e919410075c440fc8e7c`。
  - 任务/文件/外部系统：web2audio fake TTS + fake storage + 真实 love-song HTTP 分支返回 `playable`；love-song 歌单 position 7 包含 `content_type=article_audio`、`subtitle=Example`。
  - 日志/审计：web2audio 和 love-song 日志可用 article_id、track_id 关联。
- 验收证据：love-song 8001 HTTP 探针通过；web2audio fake TTS + fake storage + 真实 love-song HTTP 分支通过；love-song 歌单详情确认新增文章音频位于 position 7。
- 执行方式：半自动化。
- 跟进状态：已人工通过。
- 自动化入口：当前通过一次性联调命令和 HTTP 探针验证；默认 `./init.sh` 只覆盖 `backend/tests/test_love_song_http_client.py` 的 HTTP mock 契约。
- 待确认事项：love-song 8000 旧进程仍返回 404；当前本地联调固定使用 8001。
- 优先级：P0。
- 风险说明：该 case 证明真实 love-song API 能承接文章音频，但本次未证明真实 TOS object 可读，也未覆盖 iOS 播放。

### W2A-E2E-010：真实 Doubao、TOS 和 love-song 完整后端链路

- 验收目标：证明同一篇文章在真实 Doubao、真实 TOS 和真实 love-song HTTP 后端下能推进到 `playable`。
- Case 分类：真实后端 / 主路径 / 跨系统。
- 环境准备方式：web2audio 本地 MySQL profile；love-song 当前代码服务运行在 `http://127.0.0.1:8001`；固定 playlist_id `demo_playlist_focus`。
- 配置项：`backend/conf/doubao.local.json`、`backend/conf/tos.local.json`、`backend/conf/love_song.local.json`。
- 账号和权限：豆包 API key、TOS AK/SK、love-song 资源登记和歌单追加权限。
- 测试数据：短中文文章正文，独立 `owner_user_id` 和唯一 `source_url`。
- 操作路径：提交文章；执行正文处理；执行真实 audio job；执行 `process_player_sync`；查询 web2audio article 详情和 love-song 歌单详情。
- 预期结果：web2audio article 为 `playable`；love-song 返回 track/asset；固定歌单包含文章音频 track。
- 断言点：
  - 用户可见：iOS 不在该 case 范围内。
  - API：`GET /api/articles/{article_id}` 返回 `status=playable`；love-song `GET /api/playlists/{playlist_id}` 能回读新增 track。
  - 数据：web2audio 写入 `audio_storage_key`、`love_song_track_id`、`love_song_asset_id` 和 `love_song_playlist_id`。
  - 任务/文件/外部系统：真实 TOS object 存在；love-song 歌单 track 的 `content_type=article_audio`、`subtitle=site_name`。
  - 日志/审计：article_id、track_id、asset_id 可串联排障。
- 验收证据：`W2A_RUN_REAL_FULL_CHAIN=1 ... pytest backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_010_real_doubao_tos_and_love_song_full_chain -s` 通过。
- 执行方式：半自动化。
- 跟进状态：已自动化通过。
- 自动化入口：显式开启 `W2A_RUN_REAL_FULL_CHAIN=1`；默认 `./init.sh` 中跳过。
- 待确认事项：Chrome 真实点击和 iOS 播放不在该 case 范围内；love-song 8000 旧进程仍需重启或下线。
- 优先级：P0。
- 风险说明：该 case 证明真实后端链路到 `playable`，但不替代 W2A-E2E-011 到 W2A-E2E-013 的 iOS 人工验收。

### W2A-E2E-011：Chrome 提交后 iOS「今日待读」可播放

- 验收目标：证明用户从 Chrome 保存文章后，最终能在 love-song iOS「今日待读」看到并播放文章。
- Case 分类：iOS 播放 / 主路径 / 人工验收。
- 环境准备方式：Chrome 加载 unpacked extension；web2audio、love-song 后端、love-song iOS 指向同一环境。
- 配置项：Chrome 插件 API 地址和 token；web2audio 真实 TTS/TOS/love-song 配置；love-song iOS 环境配置。
- 账号和权限：个人 MVP 默认用户；后续多用户归属待确认。
- 测试数据：普通公开文章，正文长度可控，带标题和来源站点。
- 操作路径：打开文章；点击插件提交；等待 web2audio `playable`；打开 iOS「今日待读」；播放文章音频。
- 预期结果：iOS 歌单出现文章，播放页能播放，播放控制复用 love-song 既有能力。
- 断言点：
  - 用户可见：插件提交结果明确；iOS 歌单显示文章；播放页可播放。
  - API：web2audio article 详情为 `playable`。
  - 数据：web2audio 有 love_song IDs；love-song 有对应 track/asset/playlist item。
  - 任务/文件/外部系统：TOS object 存在；love-song 播放 URL 可用。
  - 日志/审计：article_id、track_id、asset_id 可串联排障。
- 验收证据：插件截图、article 详情、iOS 歌单截图、播放页截图、关键业务 ID。
- 执行方式：人工。
- 跟进状态：待人工验证。
- 自动化入口：暂不设计；后续可评估设备自动化。
- 待确认事项：Chrome 真实点击、iOS「今日待读」播放和文章语义仍需真机或模拟器验收。
- 优先级：P0。
- 风险说明：这是第一版真实端到端完成标准。

## 5. 已自动化通过的 Case

`W2A-E2E-001` 到 `W2A-E2E-007` 已随最新 `./init.sh` 自动化通过。`W2A-E2E-008` 和 `W2A-E2E-010` 已通过显式开启的 live 自动化；它们默认在 `./init.sh` 中跳过，不计入本地启动基线。

| Case ID | 场景名 | 自动化入口 | 最近通过时间或版本 |
| --- | --- | --- | --- |
| W2A-E2E-001 | 普通文章提交到可播放 | `./init.sh`；`backend/tests/test_fake_full_chain.py` | 2026-06-29，后端 37 passed、4 skipped，插件 2 passed |
| W2A-E2E-002 | 重复提交不重复建文章或追加歌单 | `./init.sh`；`backend/tests/test_fake_full_chain.py` | 2026-06-29，后端 37 passed、4 skipped，插件 2 passed |
| W2A-E2E-003 | 正文不可用时不生成音频 | `./init.sh`；`backend/tests/test_fake_full_chain.py` | 2026-06-29，后端 37 passed、4 skipped，插件 2 passed |
| W2A-E2E-004 | TTS 失败不产生可播放副作用 | `./init.sh`；`backend/tests/test_fake_full_chain.py` | 2026-06-29，后端 37 passed、4 skipped，插件 2 passed |
| W2A-E2E-005 | love-song 同步失败后可恢复 | `./init.sh`；`backend/tests/test_fake_full_chain.py` | 2026-06-29，后端 37 passed、4 skipped，插件 2 passed |
| W2A-E2E-006 | 运行时配置兼容回归 | `./init.sh`；`backend/tests/test_runtime_config.py` | 2026-06-29，后端 37 passed、4 skipped，插件 2 passed |
| W2A-E2E-007 | 插件提取 payload 后写入正文数据库 | `./init.sh`；`node --test extension/tests/article_extractor.test.cjs`；`backend/tests/test_webpage_text_db_chain.py` | 2026-06-29，后端 37 passed、4 skipped，插件 2 passed |
| W2A-E2E-008 | 真实 Doubao TTS 与真实 TOS 音频产物 | `W2A_RUN_REAL_AUDIO_JOB=1 ... pytest backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_008_real_doubao_tts_and_tos_audio_job -s` | 2026-06-29，1 passed，真实 Doubao 合成、真实 TOS 上传和 object head 校验通过 |
| W2A-E2E-010 | 真实 Doubao、TOS 和 love-song 完整后端链路 | `W2A_RUN_REAL_FULL_CHAIN=1 ... pytest backend/tests/test_live_e2e_external_chain.py::test_w2a_e2e_010_real_doubao_tos_and_love_song_full_chain -s` | 2026-06-29，1 passed，article 到 `playable`，love-song 歌单回读 `article_audio` |

### 已人工通过的 Case

| Case ID | 场景名 | 验收入口 | 最近通过时间或版本 |
| --- | --- | --- | --- |
| W2A-E2E-009 | 真实 love-song HTTP 资源登记与歌单追加 | love-song 8001 HTTP 探针；web2audio fake TTS + fake storage + 真实 love-song HTTP 分支；love-song 歌单查询 | 2026-06-29，真实 love-song HTTP 分支通过；TOS 真对象和 iOS 不在此 case 通过范围内 |

## 6. 待确认的 Case

| Case ID | 待确认事项 | 影响 | 建议确认人或来源 |
| --- | --- | --- | --- |
| W2A-E2E-011 | Chrome、web2audio、love-song 后端、iOS 是否指向同一环境 | 阻塞真实用户路径验收 | web2audio 与 love-song iOS 负责人 |
| W2A-E2E-012 | iOS 对 `content_type=article_audio` 和 `subtitle` 的实际展示规则 | 文章音频去音乐化仍缺真机或模拟器证据 | love-song iOS 负责人；`feat-007` |
| W2A-E2E-014 | 测试 owner、object prefix、测试 playlist 或 tag、清理方式 | 线上联调可能污染真实数据或产生不可控成本 | web2audio 运维/配置负责人 |

## 7. P0 冒烟集、P1 主干回归集、P2 边界回归集

### P0 冒烟集

| Case ID | 执行时机 | 当前状态 |
| --- | --- | --- |
| W2A-E2E-001 | 每次本仓库变更后 | 已自动化通过 |
| W2A-E2E-002 | 每次文章提交或同步幂等改动后 | 已自动化通过 |
| W2A-E2E-003 | 每次正文处理或失败状态改动后 | 已自动化通过 |
| W2A-E2E-006 | 每次 runtime 配置变更后 | 已自动化通过 |
| W2A-E2E-008 | 真实豆包/TOS 接入后 | 已自动化通过：显式 live |
| W2A-E2E-009 | love-song 后端资源登记完成后 | 已人工通过：临时 8001 |
| W2A-E2E-010 | 三类真实依赖联调前后 | 已自动化通过：显式 live |
| W2A-E2E-011 | 第一版真实验收前 | 待人工验证 |
| W2A-E2E-012 | iOS 文章展示语义完成后 | 待人工验证 |

### P1 主干回归集

| Case ID | 执行时机 | 当前状态 |
| --- | --- | --- |
| W2A-E2E-004 | 音频生成任务或 TTS/TOS client 改动后 | 已自动化通过 |
| W2A-E2E-005 | love-song 同步 worker 或 client 改动后 | 已自动化通过 |
| W2A-E2E-007 | Chrome 插件正文提取改动后 | 已自动化通过 |
| W2A-E2E-013 | iOS 播放顺序、歌单或播放历史改动后 | 待人工验证 |
| W2A-E2E-014 | 线上联调环境或清理策略变更后 | 待确认 |

### P2 边界回归集

当前不单独列 P2 E2E。字段校验、非法 JSON、分页过滤、数据库索引、配置字段格式等边界优先下沉到 API、service、database 或 config 测试。只有当它们引入跨系统副作用风险时，再提升为 E2E。

## 8. 未覆盖风险和剩余风险

| 风险 | 当前影响 | 建议下一步 |
| --- | --- | --- |
| MySQL 测试依赖当前 active profile | 默认自动化现在依赖 `backend/conf/db.local.json` 或 `DATABASE_URL` 指向可用 MySQL；目标环境切换时需要先确认连接和清理权限 | 保持测试 owner 隔离策略，切换 MySQL URL 后先跑 DB/session/runtime 目标回归 |
| 真实后端已通过但 iOS 未验收 | W2A-E2E-010 已证明真实后端链路到 `playable`，但无法证明 iOS 歌单展示和播放体验 | 使用模拟器或真机执行 W2A-E2E-011 到 W2A-E2E-013 |
| love-song 运行环境未固化 | 8001 当前代码已通过并已写入 `love_song.local.json`；8000 旧进程仍返回 404 | 重启 8000、下线旧进程，或在联调文档中固定 8001 |
| iOS 文章语义未人工验收 | 后端已返回 `content_type=article_audio` 和 `subtitle`，但无法证明 iOS 不出现音乐化文案 | 使用模拟器或真机执行 W2A-E2E-012 |
| live 自动化默认跳过 | 真实 Doubao、真实 TOS 和真实 love-song 测试会产生外部调用、成本或远端对象，默认不进入 `./init.sh` | 需要真实联调时显式设置 `W2A_RUN_REAL_AUDIO_JOB=1` 或 `W2A_RUN_REAL_FULL_CHAIN=1` |
| Chrome 插件未做真实点击到后端自动化 | 当前只验证正文提取，未验证浏览器权限、popup 配置和提交交互 | 后续可用 Playwright 或手工冒烟覆盖插件点击链路 |
| 数据清理策略未完全落地 | live 自动化默认清理 web2audio 测试 owner、TOS object 和 love-song playlist item；love-song track/asset 本体清理仍缺固定入口 | 继续完善 W2A-E2E-014，定义测试资源标记和清理脚本 |
