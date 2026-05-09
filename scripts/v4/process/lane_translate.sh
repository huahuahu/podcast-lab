#!/usr/bin/env bash
# lane_translate.sh — 英文源：STT → speaker → translate → TTS
#   薄壳，复用现有 scripts/{azure_transcribe_diarize,reassign_speakers_llm,
#   smart_merge_dialog,translate_dialog_copilot,audit_speakers_llm,
#   prepare_multivoice,multivoice_robust}.{sh,py}
#
# 用法: lane_translate.sh <project_dir>
#
# 前置: <project_dir>/source/audio.mp3 已存在；meta.json 已 ingest
# 产物: transcript/dialog_zh.json + audio/podcast_zh.mp3 + transcript/timings.json
set -euo pipefail

PROJ="${1:?usage: lane_translate.sh <project_dir>}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/meta.sh
source "$SCRIPT_DIR/../lib/meta.sh"

[ -f "$PROJ/source/audio.mp3" ] || { echo "❌ missing $PROJ/source/audio.mp3"; exit 2; }
mkdir -p "$PROJ/transcript" "$PROJ/audio"

# 加载 secrets（Azure / Copilot 等）
[ -f "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}" ] && \
  source "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}"

HAS_OFFICIAL=$(meta_get "$PROJ" has_official_transcript || echo false)

echo "🛤  lane_translate: $(basename "$PROJ") (official_transcript=$HAS_OFFICIAL)"

# 1) 拿 dialog_en.json
if [ -f "$PROJ/transcript/dialog_en.json" ]; then
  echo "✓ dialog_en.json 已存在"
elif [ "$HAS_OFFICIAL" = "true" ] && [ -f "$PROJ/source/transcript.json" ]; then
  echo "📄 使用官方 transcript（跳过 Azure STT）"
  cp "$PROJ/source/transcript.json" "$PROJ/transcript/dialog_en.json"
else
  echo "☁️  Azure STT + diarize..."
  bash "$REPO/scripts/azure_transcribe_diarize.sh" \
    "$PROJ/source/audio.mp3" "$PROJ/transcript"
fi

# 2) Speaker reassign（无官方 transcript 才需要）
if [ "$HAS_OFFICIAL" != "true" ]; then
  REASSIGN_SPEAKERS="${REASSIGN_SPEAKERS:-1}"
  S="$PROJ/transcript/.speakers-reassigned"
  if [ "$REASSIGN_SPEAKERS" = "1" ] && [ ! -f "$S" ]; then
    echo "👥 reassign Host/Guest..."
    [ -f "$PROJ/transcript/dialog_en.orig.json" ] || \
      cp "$PROJ/transcript/dialog_en.json" "$PROJ/transcript/dialog_en.orig.json"
    python3 -u "$REPO/scripts/reassign_speakers_llm.py" "$PROJ/transcript/dialog_en.json"
    touch "$S"
  fi
fi

# 3) Smart merge
SMART="$PROJ/transcript/.smart-merged"
if [ ! -f "$SMART" ]; then
  echo "🔀 smart merge..."
  python3 -u "$REPO/scripts/smart_merge_dialog.py" "$PROJ"
  touch "$SMART"
fi

# 4) 翻译
NEED_TR=1
if [ -f "$PROJ/transcript/dialog_zh.json" ]; then
  EN_N=$(python3 -c "import json; print(len(json.load(open('$PROJ/transcript/dialog_en.json'))))")
  ZH_N=$(python3 -c "import json; print(len(json.load(open('$PROJ/transcript/dialog_zh.json'))))" 2>/dev/null || echo 0)
  [ "$ZH_N" -ge "$EN_N" ] && NEED_TR=0
fi
if [ "$NEED_TR" = 1 ]; then
  echo "🌐 translate via Copilot..."
  python3 -u "$REPO/scripts/translate_dialog_copilot.py" \
    "$PROJ/transcript/dialog_en.json" "$PROJ/transcript/dialog_zh.json" --batch-size 8
fi

# 5) Speaker audit
AUDIT_SPEAKERS="${AUDIT_SPEAKERS:-1}"
A="$PROJ/transcript/.speakers-audited"
if [ "$AUDIT_SPEAKERS" = "1" ] && [ ! -f "$A" ]; then
  echo "🔍 audit speakers..."
  python3 -u "$REPO/scripts/audit_speakers_llm.py" "$PROJ"
fi

# 6) TTS
if [ ! -f "$PROJ/audio/podcast_zh.mp3" ]; then
  echo "🎙 TTS 合成..."
  python3 "$REPO/scripts/prepare_multivoice.py" \
    "$PROJ/transcript/dialog_zh.json" "$PROJ/transcript/dialog_zh_mv.json"
  python3 -u "$REPO/scripts/multivoice_robust.py" \
    "$PROJ/transcript/dialog_zh_mv.json" \
    -o "$PROJ/audio/podcast_zh.mp3" \
    --cache-dir "$PROJ/audio/tts_cache" \
    --timings "$PROJ/transcript/timings.json"
fi

# 7) 章节（仅 SSE 系列）
SERIES=$(meta_get "$PROJ" series 2>/dev/null || echo "")
if [ "$SERIES" = "softskills_engineering" ] && [ -f "$PROJ/transcript/timings.json" ] && [ ! -f "$PROJ/audio/.chapters-added" ]; then
  echo "📑 add chapters (SSE series)..."
  python3 -u "$REPO/scripts/add_chapters.py" "$PROJ" && touch "$PROJ/audio/.chapters-added" || echo "⚠️  add_chapters 失败"
fi

echo "✅ lane_translate done: $PROJ/audio/podcast_zh.mp3"
