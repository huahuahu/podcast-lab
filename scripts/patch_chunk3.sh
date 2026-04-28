#!/usr/bin/env bash
# patch_chunk3.sh — 把 DHH 项目缺失的 chunk 3 (600-900s) 补回去
# 单独走 reassign + translate + 合并到 dialog_zh.json
set -euo pipefail

PROJ=/Users/tigerguo/git/podcast-lab/projects/dhh-new-way-of-writing-code
CHUNK_3="$PROJ/transcript/azure_chunks/chunk_003.segs.json"
PATCH_EN="$PROJ/transcript/chunk3_patch_en.json"
PATCH_ZH="$PROJ/transcript/chunk3_patch_zh.json"

unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
export NO_PROXY='*' no_proxy='*'

cp "$CHUNK_3" "$PATCH_EN"
echo "✅ copied $CHUNK_3 -> $PATCH_EN"

cd /Users/tigerguo/git/podcast-lab
echo "--- step 1: reassign speakers ---"
python3 -u scripts/reassign_speakers_llm.py "$PATCH_EN"

echo "--- step 2: translate ---"
python3 -u scripts/translate_dialog_copilot.py "$PATCH_EN" "$PATCH_ZH" --batch-size 8

echo "--- step 3: merge into dialog_zh.json ---"
python3 - "$PROJ/transcript/dialog_zh.json" "$PATCH_ZH" <<'PY'
import json, sys
main_path, patch_path = sys.argv[1], sys.argv[2]
main = json.load(open(main_path))
patch = json.load(open(patch_path))

# 按 start 时间合并
combined = main + patch
combined.sort(key=lambda x: float(x.get("start", 0)))

with open(main_path, "w") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)
print(f"✅ merged: main={len(main)} + patch={len(patch)} -> total={len(combined)}")
PY
