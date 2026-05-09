#!/usr/bin/env bash
# test_lane_decision.sh — 中文/英文 lang_hint → 正确 lane
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V4="$SCRIPT_DIR/../scripts/v4"
source "$V4/lib/meta.sh"

PROJ=$(mktemp -d)
trap 'rm -rf "$PROJ"' EXIT

meta_init "$PROJ" "fake-slug" "https://x" "youtube"

# zh → passthrough
meta_set "$PROJ" lang "zh"
got=$("$V4/process/decide_lane.sh" "$PROJ")
[ "$got" = "passthrough" ] || { echo "✗ zh expected passthrough got $got"; exit 1; }
echo "  ✓ zh → passthrough"

# en → translate
meta_set "$PROJ" lang "en"
got=$("$V4/process/decide_lane.sh" "$PROJ")
[ "$got" = "translate" ] || { echo "✗ en expected translate got $got"; exit 1; }
echo "  ✓ en → translate"

# missing lang → 失败
jq 'del(.lang)' "$PROJ/source/meta.json" > "$PROJ/source/meta.json.tmp" && mv "$PROJ/source/meta.json.tmp" "$PROJ/source/meta.json"
if "$V4/process/decide_lane.sh" "$PROJ" 2>/dev/null; then
  echo "✗ missing lang should fail"; exit 1
fi
echo "  ✓ missing lang → fails as expected"

echo "✅ test_lane_decision: all passed"
