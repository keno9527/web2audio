#!/bin/bash
set -e

echo "=== web2audio 启动验证 ==="

echo "=== 检查必需文件 ==="
required_files=(
  "AGENTS.md"
  "README.md"
  "docs/PRODUCT.md"
  "docs/TECHNICAL_DESIGN.md"
  "feature_list.json"
  "progress.md"
  "session-handoff.md"
  "init.sh"
)

for file in "${required_files[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "缺少必需文件或文件为空：$file"
    exit 1
  fi
  echo "通过：$file"
done

echo "=== 检查功能状态 JSON ==="
python3 - <<'PY'
import json
from pathlib import Path

path = Path("feature_list.json")
data = json.loads(path.read_text(encoding="utf-8"))
features = data.get("features")
allowed_statuses = {"not-started", "in-progress", "blocked", "done"}

if not isinstance(features, list) or not features:
    raise SystemExit("feature_list.json 必须包含非空 features 数组")

ids = set()
for index, item in enumerate(features, start=1):
    if not isinstance(item, dict):
        raise SystemExit(f"第 {index} 个功能必须是对象")
    for field in ("id", "name", "description", "dependencies", "status", "evidence"):
        if field not in item:
            raise SystemExit(f"{item.get('id', f'第 {index} 个功能')} 缺少字段：{field}")
    if not isinstance(item["id"], str) or not item["id"].startswith("feat-"):
        raise SystemExit(f"功能 ID 不合法：{item['id']}")
    if item["id"] in ids:
        raise SystemExit(f"功能 ID 重复：{item['id']}")
    ids.add(item["id"])
    if item["status"] not in allowed_statuses:
        raise SystemExit(f"{item['id']} 状态不合法：{item['status']}")
    if not isinstance(item["dependencies"], list):
        raise SystemExit(f"{item['id']} dependencies 必须是数组")

for item in features:
    for dependency in item["dependencies"]:
        if dependency not in ids:
            raise SystemExit(f"{item['id']} 依赖不存在：{dependency}")

print(f"通过：{len(features)} 个功能条目结构合法")
PY

echo "=== 检查已知模板文本残留 ==="
placeholder_pattern='No package manifest detected|replace this line|Replace this placeholder|YYYY-MM-DD|Completed item|Current work item|Next action item|Following action item|Blocker 1|Risk 1|Decision 1|path/to/file|Free-form notes|Feature Name|First User-Facing Feature|Project Setup|Verification Coverage|Documentation Update|Cleanup and Handoff|Session Progress Log'

if grep -R -n -E "$placeholder_pattern" AGENTS.md README.md docs feature_list.json progress.md session-handoff.md; then
  echo "发现已知模板文本残留，请先清理。"
  exit 1
fi

echo "通过：未发现已知模板文本残留"

if [[ -d "backend/tests" ]]; then
  echo "=== 运行后端测试 ==="
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider backend/tests
fi

if [[ -d "extension/tests" ]]; then
  echo "=== 运行 Chrome 插件测试 ==="
  node --test extension/tests/article_extractor.test.cjs
fi

echo "=== 验证完成 ==="
echo ""
echo "下一步："
echo "1. 阅读 feature_list.json 和 progress.md"
echo "2. 选择一个未完成功能作为本次唯一推进对象"
echo "3. 完成后重新运行 ./init.sh 并记录证据"
