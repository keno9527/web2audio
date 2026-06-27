# AGENTS.md

web2audio 的智能体协作说明。目标是让每次会话先核对真实状态，再围绕一个明确功能推进，并在结束前留下可复现证据。

## 启动流程

写代码或改文档前必须完成以下步骤：

1. 用 `pwd` 确认当前目录是 `/Users/bytedance/Codebases/web2audio`。
2. 完整阅读本文件。
3. 阅读 `README.md`、`docs/PRODUCT.md`、`docs/TECHNICAL_DESIGN.md`、`feature_list.json`、`progress.md` 和 `session-handoff.md`。
4. 运行 `./init.sh`，确认文档、状态文件和验证入口可用。
5. 用 `git log --oneline -5` 和 `git status --short` 核对近期提交与工作区状态。
6. 确认本次唯一推进对象：产品或实现任务从 `feature_list.json` 中选择一个未完成功能；harness 或文档状态维护任务把该维护项作为唯一推进对象，只有功能状态变化时才更新 `feature_list.json`。

如果 `./init.sh` 失败，先修复基线验证，再新增或修改功能范围。

## 工作规则

- 一次只推进一个功能或一个明确的 harness / 文档维护项；跨功能修改必须先记录原因、影响和回退边界。
- 优先遵循 `docs/PRODUCT.md` 中已有的产品定位、术语、流程和非目标。
- 技术字段、接口契约、状态枚举、存储和任务实现边界以 `docs/TECHNICAL_DESIGN.md` 为准。
- 不凭空引入新架构、依赖或运行时；确需新增时先说明成本和验证方式。
- 完成前必须运行 `./init.sh`，有代码后还要补充对应测试、lint 或构建命令。
- 结束前按影响范围更新 `progress.md`、`feature_list.json` 和 `session-handoff.md`，让下一次会话能直接恢复；没有功能状态变化时，不为文档维护伪造产品功能进度。
- 不回滚或覆盖他人已有改动；遇到不相关的脏工作区时只记录，不擅自清理。
- 本仓库 fake TTS、fake TOS 和 fake love-song 自测只证明 web2audio 本地链路可用；不能替代真实 love-song 后端和 iOS 验收。
- 文档更新必须先核对证据来源，正文只写读者需要的现状、方案、边界、结论和待确认项，避免写入协作过程描述。

## 必需产物

| 文件 | 作用 |
| --- | --- |
| `AGENTS.md` | 启动路径、协作规则和完成标准 |
| `README.md` | 当前状态、本地启动和验证入口 |
| `docs/PRODUCT.md` | 产品目标、系统边界、核心流程和验收标准 |
| `docs/TECHNICAL_DESIGN.md` | 技术方案、数据模型、API 契约和验证策略 |
| `feature_list.json` | 功能状态、依赖关系和完成证据的事实来源 |
| `progress.md` | 当前会话进展、风险、决策和验证记录 |
| `init.sh` | 统一启动与验证入口 |
| `session-handoff.md` | 跨会话交接信息，任务较长或中断时必须更新 |

## 完成标准

一个功能或文档维护项只有同时满足以下条件，才可以标记为完成：

- 目标行为或文档目标已经按当前范围落地。
- 相关验证命令已经实际运行，并且结果记录在 `feature_list.json` 或 `progress.md`。
- 受影响文件的职责边界清晰，没有混入无关重构。
- 仓库仍可从 `./init.sh` 开始完成下一次启动核对。
- 未解决风险已经写入 `progress.md` 或 `session-handoff.md`。

## 验证命令

```bash
./init.sh
```

当前 `./init.sh` 会检查：

- 必需文档和状态文件是否存在且非空。
- `feature_list.json` 是否为合法 JSON，并且功能字段、状态和依赖关系完整。
- 已知英文模板文本是否仍残留在 harness 文档或启动脚本中。
- 后端全量 pytest 是否通过，包含文章 API、正文处理、fake TTS/TOS、love-song 契约、播放器同步和 fake 全链路自测。
- Chrome 插件正文提取测试是否通过。

后续接入真实豆包 TTS、火山云 TOS、love-song 后端或 iOS 代码时，必须把对应测试、lint、类型检查或构建命令补进 `init.sh` 和本节，并在状态文件中区分 fake 自测与真实跨工程验收。

## 异常处理

| 场景 | 处理方式 |
| --- | --- |
| 产品边界不清 | 先核对 `docs/PRODUCT.md`，仍无法判断时再向用户确认 |
| 需要新增架构决策 | 记录方案、原因、影响和验证方式后再实施 |
| 验证连续失败 | 停止扩大范围，记录已确认事实、失败命令和下一步排查建议 |
| 功能范围冲突 | 回到 `feature_list.json`，只保留当前功能必需改动 |
| fake 自测与真实验收混淆 | 回到 `feature_list.json` 和 `progress.md`，明确当前只完成本仓库 fake 链路还是已完成真实 love-song / iOS 验收 |

<!-- harness-validator: Startup Workflow; Before writing code; Definition of Done; done only when; Verification Commands; One feature at a time; Stay in scope; scope; End of Session; Before ending; restartable; clean; Next steps; test. -->
