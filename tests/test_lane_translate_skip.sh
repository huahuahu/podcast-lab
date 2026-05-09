#!/usr/bin/env bash
# test_lane_translate_skip.sh — lane_translate 应当在产物齐全时全部 skip
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V4="$SCRIPT_DIR/../scripts/v4"
source "$V4/lib/meta.sh"

PROJ=$(mktemp -d); trap 'rm -rf "$PROJ"' EXIT
meta_init "$PROJ" "fake" "https://x" "youtube"
meta_set "$PROJ" lang "en"; meta_set "$PROJ" lane "translate"

# 造空 audio + 全部产物
mkdir -p "$PROJ/source" "$PROJ/transcript" "$PROJ/audio"
ffmpeg -loglevel error -f lavfi -i anullsrc=r=8000:cl=mono -t 1 -q:a 9 "$PROJ/source/audio.mp3"
echo '[{"speaker":"Host","text":"hi","start":0,"end":1}]' > "$PROJ/transcript/dialog_en.json"
echo '[{"speaker":"Host","text":"你好","start":0,"end":1}]' > "$PROJ/transcript/dialog_zh.json"
touch "$PROJ/transcript/.smart-merged" "$PROJ/transcript/.speakers-reassigned" "$PROJ/transcript/.speakers-audited"
ffmpeg -loglevel error -f lavfi -i anullsrc=r=8000:cl=mono -t 1 -q:a 9 "$PROJ/audio/podcast_zh.mp3"

# 跑 lane_translate，不应该调任何外部 API（产物都齐了）
out=$("$V4/process/lane_translate.sh" "$PROJ" 2>&1)
echo "$out" | grep -q 'TTS 合成' && { echo "✗ TTS 不应执行"; exit 1; }
echo "$out" | grep -q 'translate via Copilot' && { echo "✗ 翻译不应执行"; exit 1; }
echo "$out" | grep -q 'Azure STT' && { echo "✗ STT 不应执行"; exit 1; }
echo "  ✓ 产物齐全时全部 skip"
echo "✅ test_lane_translate_skip: passed"
