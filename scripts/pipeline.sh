#!/usr/bin/env bash
# pipeline.sh — YouTube → 双人中文播客 的一键 pipeline (v2)
#
# 默认方案：
#   STT  = SiliconFlow SenseVoiceSmall（云端，快）
#   Diar = pyannote/speaker-diarization-3.1（本地）
#   MT   = GitHub Copilot gpt-5.4（免费，公司 license）
#   TTS  = edge-tts（免费，Microsoft）
#
# 用法：
#   ./pipeline.sh <slug> <youtube_url> [num_speakers]
#
# 环境变量（可选）：
#   STT_PROVIDER=siliconflow|whisper          # 默认 siliconflow
#   TRANSLATE_PROVIDER=copilot|siliconflow    # 默认 copilot
#   OPENCLAW_SECRETS=~/.openclaw/secrets/env.sh
#
# 输出到 projects/<slug>/：
#   source/audio.mp3             — 原音频
#   transcript/siliconflow.txt   — SF 整段转录（或 whisper.json）
#   transcript/whisper.json      — 本地 whisper 转录（始终跑，用来做时间戳对齐）
#   diarization/segments.json    — 说话人分段
#   transcript/dialog_en.json    — 合并后的英文对话（带 speaker）
#   transcript/dialog_zh.json    — 中文翻译
#   audio/podcast_zh.mp3         — 最终双人中文播客

set -euo pipefail

SLUG="${1:?usage: pipeline.sh <slug> <youtube_url> [num_speakers]}"
URL="${2:?usage: pipeline.sh <slug> <youtube_url> [num_speakers]}"
NUM_SPEAKERS="${3:-2}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="$REPO/projects/$SLUG"

STT_PROVIDER="${STT_PROVIDER:-siliconflow}"
TRANSLATE_PROVIDER="${TRANSLATE_PROVIDER:-copilot}"

# 可选：加载本地 secrets（HF_TOKEN、API key 路径等）
[ -f "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}" ] && \
  source "${OPENCLAW_SECRETS:-$HOME/.openclaw/secrets/env.sh}"

mkdir -p "$PROJ"/{source,transcript,audio,diarization}

echo "═══ [$SLUG] Pipeline start ═══"
echo "  STT       : $STT_PROVIDER"
echo "  Translate : $TRANSLATE_PROVIDER"
echo "  Speakers  : $NUM_SPEAKERS"
echo ""

# ─── 1. Download ───────────────────────────────────────────
if [ ! -f "$PROJ/source/audio.mp3" ]; then
  echo "🎬 1/7 Downloading audio..."
  yt-dlp -x --audio-format mp3 --audio-quality 0 \
    -o "$PROJ/source/audio.%(ext)s" "$URL"
else
  echo "✓ 1/7 audio.mp3 exists, skipping"
fi

# ─── 2. 准备 16kHz mono wav（pyannote & whisper 都用）────────
if [ ! -f "$PROJ/source/audio_16k.wav" ]; then
  echo "🔊 2/7 Preparing 16kHz mono wav..."
  ffmpeg -loglevel error -i "$PROJ/source/audio.mp3" \
    -ar 16000 -ac 1 -y "$PROJ/source/audio_16k.wav"
else
  echo "✓ 2/7 audio_16k.wav exists, skipping"
fi

# ─── 3. STT（云端 SF 或本地 whisper）─────────────────────────
# 我们始终用本地 whisper.cpp 的带时间戳输出做后续对齐，因为 SF 不返回时间戳。
# 如果 STT_PROVIDER=siliconflow 就额外跑一份 SF 整段转录存档。
if [ ! -f "$PROJ/transcript/whisper.json" ]; then
  echo "📝 3a/7 Running whisper.cpp for timestamped transcript..."
  : "${WHISPER_CLI:=/opt/homebrew/bin/whisper-cli}"
  : "${WHISPER_MODEL:=$HOME/.openclaw/models/whisper/ggml-large-v3-turbo.bin}"
  "$WHISPER_CLI" -m "$WHISPER_MODEL" \
    -f "$PROJ/source/audio_16k.wav" \
    -l en -oj -np \
    -of "$PROJ/transcript/whisper"
else
  echo "✓ 3a/7 whisper.json exists, skipping"
fi

if [ "$STT_PROVIDER" = "siliconflow" ] && [ ! -f "$PROJ/transcript/siliconflow.txt" ]; then
  echo "☁️  3b/7 Running SiliconFlow SenseVoice for reference transcript..."
  bash "$REPO/scripts/sf_transcribe_all.sh" \
    "$PROJ/source/audio.mp3" \
    "$PROJ/transcript"
elif [ "$STT_PROVIDER" = "siliconflow" ]; then
  echo "✓ 3b/7 siliconflow.txt exists, skipping"
fi

# ─── 4. Diarize（pyannote 本地）─────────────────────────────
if [ ! -f "$PROJ/diarization/segments.json" ]; then
  echo "👥 4/7 Speaker diarization (pyannote)..."
  python3 -u "$REPO/scripts/diarize.py" \
    "$PROJ/source/audio_16k.wav" \
    --num-speakers "$NUM_SPEAKERS" \
    -o "$PROJ/diarization/segments.json"
else
  echo "✓ 4/7 segments.json exists, skipping"
fi

# ─── 5. 合并对齐 ───────────────────────────────────────────
if [ ! -f "$PROJ/transcript/whisper_segs.json" ]; then
  python3 "$REPO/scripts/whisper_to_segs.py" \
    "$PROJ/transcript/whisper.json" \
    "$PROJ/transcript/whisper_segs.json"
fi

if [ ! -f "$PROJ/transcript/dialog_en.json" ]; then
  echo "🔗 5/7 Aligning transcript with speakers..."
  python3 "$REPO/scripts/transcribe_diarized.py" \
    --audio       "$PROJ/source/audio_16k.wav" \
    --transcript  "$PROJ/transcript/whisper_segs.json" \
    --segments    "$PROJ/diarization/segments.json" \
    -o            "$PROJ/transcript/dialog_en.json"
else
  echo "✓ 5/7 dialog_en.json exists, skipping"
fi

# ─── 6. 翻译（默认 Copilot GPT-5.4）──────────────────────────
if [ ! -f "$PROJ/transcript/dialog_zh.json" ] \
  || [ "$(python3 -c "import json; print(len(json.load(open('$PROJ/transcript/dialog_zh.json'))))" 2>/dev/null || echo 0)" -lt \
       "$(python3 -c "import json; print(len(json.load(open('$PROJ/transcript/dialog_en.json'))))")" ]; then
  echo "🌐 6/7 Translating via $TRANSLATE_PROVIDER..."
  if [ "$TRANSLATE_PROVIDER" = "copilot" ]; then
    python3 -u "$REPO/scripts/translate_dialog_copilot.py" \
      "$PROJ/transcript/dialog_en.json" \
      "$PROJ/transcript/dialog_zh.json" \
      --batch-size 8
  else
    python3 -u "$REPO/scripts/translate_dialog.py" \
      "$PROJ/transcript/dialog_en.json" \
      "$PROJ/transcript/dialog_zh.json" \
      --batch-size 8
  fi
else
  echo "✓ 6/7 dialog_zh.json complete, skipping"
fi

# ─── 7. TTS 合成 ───────────────────────────────────────────
if [ ! -f "$PROJ/audio/podcast_zh.mp3" ]; then
  echo "🎙 7/7 Synthesizing Chinese podcast audio..."
  python3 "$REPO/scripts/prepare_multivoice.py" \
    "$PROJ/transcript/dialog_zh.json" \
    "$PROJ/transcript/dialog_zh_mv.json"
  python3 -u "$REPO/scripts/multivoice_robust.py" \
    "$PROJ/transcript/dialog_zh_mv.json" \
    -o "$PROJ/audio/podcast_zh.mp3" \
    --cache-dir "$PROJ/audio/tts_cache"
else
  echo "✓ 7/7 podcast_zh.mp3 exists, skipping"
fi

echo ""
echo "✅ Done! Final podcast:"
echo "   $PROJ/audio/podcast_zh.mp3"
echo ""
echo "👉 发布到 GitHub Release（mp3 >50MB 时推荐）:"
echo "   gh release create v0.1.0-$SLUG --repo huahuahu/podcast-lab \\"
echo "     --title '...' --notes '...' \\"
echo "     $PROJ/audio/podcast_zh.mp3"
