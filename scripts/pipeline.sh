#!/usr/bin/env bash
# pipeline.sh — YouTube → 多人中文播客 的一键 pipeline
#
# 用法：
#   ./pipeline.sh <slug> <youtube_url>
#
# 输出到 projects/<slug>/ 下：
#   source/audio.mp3         — 原音频
#   diarization/segments.json — 说话人分段
#   transcript/en-dialog.json — 带说话人的英文对话
#   transcript/cn-dialog.json — 翻译后的中文对话（需要人工/LLM 干预）
#   audio/cn-podcast.mp3     — 最终中文双人配音播客

set -euo pipefail

SLUG="${1:?usage: pipeline.sh <slug> <youtube_url> [num_speakers]}"
URL="${2:?usage: pipeline.sh <slug> <youtube_url> [num_speakers]}"
NUM_SPEAKERS="${3:-2}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="$REPO/projects/$SLUG"

# 可选：加载本地 secrets（如 HF_TOKEN 等）。文件不存在就跳过。
[ -f "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}" ] && source "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}"

mkdir -p "$PROJ"/{source,transcript,audio,diarization}

echo "═══ [$SLUG] Pipeline start ═══"

# 1. Download
if [ ! -f "$PROJ/source/audio.mp3" ]; then
  echo "🎬 1/5 Downloading audio..."
  yt-dlp -x --audio-format mp3 --audio-quality 0 \
    -o "$PROJ/source/audio.%(ext)s" "$URL"
else
  echo "✓ 1/5 audio.mp3 exists, skipping"
fi

# 2. Diarize
if [ ! -f "$PROJ/diarization/segments.json" ]; then
  echo "👥 2/5 Running speaker diarization..."
  python3 "$REPO/scripts/diarize.py" \
    "$PROJ/source/audio.mp3" \
    --num-speakers "$NUM_SPEAKERS" \
    -o "$PROJ/diarization/segments.json"
else
  echo "✓ 2/5 segments.json exists, skipping"
fi

# 3. Transcribe + align speakers
if [ ! -f "$PROJ/transcript/en-dialog.json" ]; then
  echo "📝 3/5 Transcribing + aligning speakers..."
  python3 "$REPO/scripts/transcribe_diarized.py" \
    --audio "$PROJ/source/audio.mp3" \
    --segments "$PROJ/diarization/segments.json" \
    --lang en \
    -o "$PROJ/transcript/en-dialog.json"
else
  echo "✓ 3/5 en-dialog.json exists, skipping"
fi

# 4. Translate (manual or LLM)
if [ ! -f "$PROJ/transcript/cn-dialog.json" ]; then
  echo ""
  echo "⏸  4/5 PAUSED: translate en-dialog.json to cn-dialog.json"
  echo "   input:  $PROJ/transcript/en-dialog.json"
  echo "   output: $PROJ/transcript/cn-dialog.json"
  echo ""
  echo "   Format should be compatible with multivoice.py:"
  echo "   {"
  echo "     \"voices\": {\"SPEAKER_00\": \"zh-CN-XiaoxiaoNeural\", \"SPEAKER_01\": \"zh-CN-YunyangNeural\"},"
  echo "     \"lines\": [{\"speaker\": \"SPEAKER_00\", \"text\": \"...\"}, ...]"
  echo "   }"
  echo ""
  echo "   Run this script again after translating."
  exit 0
else
  echo "✓ 4/5 cn-dialog.json exists"
fi

# 5. TTS
echo "🎙 5/5 Generating Chinese podcast audio..."
python3 "$REPO/scripts/multivoice.py" \
  "$PROJ/transcript/cn-dialog.json" \
  -o "$PROJ/audio/cn-podcast.mp3"

echo ""
echo "✅ Done! Final podcast: $PROJ/audio/cn-podcast.mp3"
