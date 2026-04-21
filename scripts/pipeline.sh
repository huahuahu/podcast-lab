#!/usr/bin/env bash
# pipeline.sh — YouTube → 双人中文播客 的一键 pipeline (v3)
#
# 唯一方案：
#   STT + Diar = Azure gpt-4o-transcribe-diarize（一步搞定）
#   MT         = GitHub Copilot gpt-5.4（免费，公司 license）
#   TTS        = edge-tts（免费，Microsoft）
#
# 用法：
#   ./pipeline.sh <slug> <youtube_url> [num_speakers]
#
# 环境变量（可选）：
#   CHUNK_SEC=600                             # Azure 切片长度，默认 10 分钟
#   AZURE_OPENAI_CRED_FILE=~/.openclaw/credentials/azure-openai.json
#   OPENCLAW_SECRETS=~/.openclaw/secrets/env.sh
#
# 输出到 projects/<slug>/：
#   source/audio.mp3             — 原音频
#   transcript/azure_chunks/     — Azure 切片原始 SSE + 解析后 segs（中间产物，断点续传用）
#   transcript/dialog_en.json    — 合并后的英文对话（带 speaker）
#   transcript/dialog_zh.json    — 中文翻译
#   audio/podcast_zh.mp3         — 最终双人中文播客

set -euo pipefail

SLUG="${1:?usage: pipeline.sh <slug> <youtube_url> [num_speakers]}"
URL="${2:?usage: pipeline.sh <slug> <youtube_url> [num_speakers]}"
NUM_SPEAKERS="${3:-2}"   # 目前仅做提示用，Azure 自动分

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="$REPO/projects/$SLUG"

# 可选：加载本地 secrets
[ -f "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}" ] && \
  source "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}"

mkdir -p "$PROJ"/{source,transcript,audio}

echo "═══ [$SLUG] Pipeline start ═══"
echo "  STT+Diar  : Azure gpt-4o-transcribe-diarize"
echo "  Translate : Copilot GPT-5.4"
echo "  Speakers  : ~$NUM_SPEAKERS (auto-detected)"
echo ""

# ─── 1. Download ───────────────────────────────────────────
if [ ! -f "$PROJ/source/audio.mp3" ]; then
  echo "🎬 1/4 Downloading audio..."
  yt-dlp -x --audio-format mp3 --audio-quality 0 \
    -o "$PROJ/source/audio.%(ext)s" "$URL"
else
  echo "✓ 1/4 audio.mp3 exists, skipping"
fi

# ─── 2. STT + Diarize（Azure 一步）──────────────────────────
if [ ! -f "$PROJ/transcript/dialog_en.json" ]; then
  echo "☁️  2/4 Azure gpt-4o-transcribe-diarize (STT + diarize)..."
  bash "$REPO/scripts/azure_transcribe_diarize.sh" \
    "$PROJ/source/audio.mp3" \
    "$PROJ/transcript"
else
  echo "✓ 2/4 dialog_en.json exists, skipping"
fi

# ─── 3. 翻译（Copilot GPT-5.4）──────────────────────────────
if [ ! -f "$PROJ/transcript/dialog_zh.json" ] \
  || [ "$(python3 -c "import json; print(len(json.load(open('$PROJ/transcript/dialog_zh.json'))))" 2>/dev/null || echo 0)" -lt \
       "$(python3 -c "import json; print(len(json.load(open('$PROJ/transcript/dialog_en.json'))))")" ]; then
  echo "🌐 3/4 Translating via Copilot GPT-5.4..."
  python3 -u "$REPO/scripts/translate_dialog_copilot.py" \
    "$PROJ/transcript/dialog_en.json" \
    "$PROJ/transcript/dialog_zh.json" \
    --batch-size 8
else
  echo "✓ 3/4 dialog_zh.json complete, skipping"
fi

# ─── 4. TTS 合成 ───────────────────────────────────────────
if [ ! -f "$PROJ/audio/podcast_zh.mp3" ]; then
  echo "🎙 4/4 Synthesizing Chinese podcast audio..."
  python3 "$REPO/scripts/prepare_multivoice.py" \
    "$PROJ/transcript/dialog_zh.json" \
    "$PROJ/transcript/dialog_zh_mv.json"
  python3 -u "$REPO/scripts/multivoice_robust.py" \
    "$PROJ/transcript/dialog_zh_mv.json" \
    -o "$PROJ/audio/podcast_zh.mp3" \
    --cache-dir "$PROJ/audio/tts_cache"
else
  echo "✓ 4/4 podcast_zh.mp3 exists, skipping"
fi

echo ""
echo "✅ Done! Final podcast:"
echo "   $PROJ/audio/podcast_zh.mp3"
echo ""
echo "👉 发布到 GitHub Release（mp3 >50MB 时推荐）:"
echo "   gh release create v0.1.0-$SLUG --repo huahuahu/podcast-lab \\"
echo "     --title '...' --notes '...' \\"
echo "     $PROJ/audio/podcast_zh.mp3"
