#!/bin/bash
# sf_transcribe_all.sh — 用硅基流动 SenseVoiceSmall 把一个长音频切片后整段转录
# 用法：./sf_transcribe_all.sh <audio> <out_dir>
#
# 产物：
#   <out_dir>/sf_chunks/chunk_NNN.mp3     切片音频（10 分钟一段）
#   <out_dir>/sf_chunks/chunk_NNN.json    每段的原始 API 返回
#   <out_dir>/siliconflow.txt             拼接后的纯文本（带 [HH:MM:SS] 起始时间戳标记）
set -euo pipefail

AUDIO="${1:?audio file required}"
OUT_DIR="${2:?output dir required}"
CHUNK_SEC="${CHUNK_SEC:-600}"   # 10 分钟一段
PROMPT="${PROMPT:-The following is an English podcast interview about corporate politics at Amazon. Please transcribe in English.}"

API_KEY="$(jq -r '.providers.siliconflow.apiKey' "$HOME/.openclaw/secrets.json")"
if [ -z "$API_KEY" ] || [ "$API_KEY" = "null" ]; then
  echo "ERROR: siliconflow apiKey missing" >&2
  exit 2
fi

CHUNK_DIR="$OUT_DIR/sf_chunks"
mkdir -p "$CHUNK_DIR"
OUT_TXT="$OUT_DIR/siliconflow.txt"
: > "$OUT_TXT"

# 获取总时长（秒）
TOTAL=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$AUDIO" | awk '{printf "%d", $1}')
echo "🎬 total duration: ${TOTAL}s, chunk size: ${CHUNK_SEC}s"

idx=0
start=0
while [ "$start" -lt "$TOTAL" ]; do
  idx=$((idx + 1))
  padded=$(printf "%03d" "$idx")
  mp3="$CHUNK_DIR/chunk_${padded}.mp3"
  json="$CHUNK_DIR/chunk_${padded}.json"

  # 时间戳标记（hh:mm:ss）
  hh=$((start / 3600)); mm=$(((start % 3600) / 60)); ss=$((start % 60))
  ts=$(printf "%02d:%02d:%02d" "$hh" "$mm" "$ss")

  if [ -f "$json" ] && jq -e '.text' "$json" >/dev/null 2>&1; then
    echo "⏭  chunk $idx @ $ts 已存在，跳过"
  else
    echo "✂️  chunk $idx @ $ts → $mp3"
    ffmpeg -loglevel error -ss "$start" -t "$CHUNK_SEC" -i "$AUDIO" -c copy -y "$mp3"

    echo "📤  uploading chunk $idx..."
    # --fail-with-body 确保错误能被看到；重试 2 次
    attempt=0
    while [ $attempt -lt 3 ]; do
      if curl -sS --fail-with-body -X POST \
          "https://api.siliconflow.cn/v1/audio/transcriptions" \
          -H "Authorization: Bearer ${API_KEY}" \
          -F "file=@${mp3}" \
          -F "model=FunAudioLLM/SenseVoiceSmall" \
          -F "prompt=${PROMPT}" \
          -o "$json"; then
        break
      fi
      attempt=$((attempt + 1))
      echo "⚠️  chunk $idx attempt $attempt 失败，等 5s 重试..."
      sleep 5
    done
  fi

  # 拼接到总文本
  {
    echo ""
    echo "[$ts] ===== chunk $idx ====="
    jq -r '.text // .error.message // "(empty)"' "$json"
  } >> "$OUT_TXT"

  start=$((start + CHUNK_SEC))
done

echo ""
echo "✅ done. transcript → $OUT_TXT"
wc -c "$OUT_TXT"
