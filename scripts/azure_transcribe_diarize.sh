#!/usr/bin/env bash
# azure_transcribe_diarize.sh — 用 Azure gpt-4o-transcribe-diarize 一步搞定
# STT + speaker diarization（替代 SF SenseVoice + pyannote）。
#
# 注意：访问 Azure endpoint 要走直连，不要走 VPN/proxy。
#   试过走 VPN 握手在 chunked SSE 中间易断流。如果 shell 有
#   HTTPS_PROXY / HTTP_PROXY / ALL_PROXY / https_proxy / http_proxy / all_proxy
#   请先 unset 后再跑：
#     unset HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy
#
# 备选：可改用 OpenAI 直连（api.openai.com）的 gpt-4o-transcribe。
#   把 URL 换成 https://api.openai.com/v1/audio/transcriptions，
#   把 api-key 头换成 Authorization: Bearer $OPENAI_API_KEY，
#   model 字段填 gpt-4o-transcribe。其他切片/SSE 解析逻辑不变。
#
# 用法:
#   ./azure_transcribe_diarize.sh <audio> <out_dir> [chunk_sec]
#
# 产物:
#   <out_dir>/azure_chunks/chunk_NNN.mp3       切片
#   <out_dir>/azure_chunks/chunk_NNN.sse       每片的原始 SSE 流
#   <out_dir>/azure_chunks/chunk_NNN.segs.json 每片解析后的 segments (带全局时间)
#   <out_dir>/dialog_en.json                    合并后的 dialog（schema 同 pipeline.sh）
#
# 环境变量:
#   AZURE_OPENAI_CRED_FILE  (默认 ~/.openclaw/credentials/azure-openai.json)
#   CHUNK_SEC               (默认 300，5 分钟一段。越小越稳，diarize 模型处理大文件慢且易断)
#   MAX_BYTES               (默认 24000000，~24MB 低于 Azure 25MB 上限)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Azure endpoint 在国内需要直连（走 VPN/proxy 在长 SSE 中间易断流、握手失败）。
# 在脚本内部 unset proxy，这样调用者不需要预处理环境；
# 其它需要 proxy 的工具（gh/git/copilot 等）不受影响，因为只在本脚本进程生效。
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy NO_PROXY no_proxy 2>/dev/null || true

AUDIO="${1:?usage: azure_transcribe_diarize.sh <audio> <out_dir> [chunk_sec]}"
OUT_DIR="${2:?usage: azure_transcribe_diarize.sh <audio> <out_dir> [chunk_sec]}"
CHUNK_SEC="${3:-${CHUNK_SEC:-300}}"

CRED="${AZURE_OPENAI_CRED_FILE:-$HOME/.openclaw/credentials/azure-openai.json}"
[ -r "$CRED" ] || { echo "missing $CRED" >&2; exit 2; }

EP=$(jq -r '.endpoint' "$CRED")
KEY=$(jq -r '.apiKey' "$CRED")
VER=$(jq -r '.apiVersion // "2025-03-01-preview"' "$CRED")
DEP=$(jq -r '.deployments.diarize.name // "gpt-4o-transcribe-diarize"' "$CRED")
URL="${EP%/}/openai/deployments/${DEP}/audio/transcriptions?api-version=${VER}"

CHUNK_DIR="$OUT_DIR/azure_chunks"
mkdir -p "$CHUNK_DIR"

TOTAL=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$AUDIO" \
        | awk '{printf "%d", $1}')
echo "🎬 total=${TOTAL}s chunk=${CHUNK_SEC}s → $(( (TOTAL + CHUNK_SEC - 1) / CHUNK_SEC )) 片"

idx=0
start=0
while [ "$start" -lt "$TOTAL" ]; do
  idx=$((idx + 1))
  padded=$(printf "%03d" "$idx")
  mp3="$CHUNK_DIR/chunk_${padded}.mp3"
  sse="$CHUNK_DIR/chunk_${padded}.sse"
  segs="$CHUNK_DIR/chunk_${padded}.segs.json"

  # 切片（用 re-encode 保证大小可控；c copy 对 mp3 也 ok，但某些源会不准）
  if [ ! -f "$mp3" ]; then
    echo "✂️  chunk $idx @ ${start}s → $mp3"
    ffmpeg -loglevel error -ss "$start" -t "$CHUNK_SEC" -i "$AUDIO" \
      -map_metadata -1 \
      -acodec libmp3lame -b:a 64k -ac 1 -ar 16000 -y "$mp3"
  fi

  if [ -f "$segs" ] && jq -e '. | type == "array" and length > 0' "$segs" >/dev/null 2>&1; then
    echo "⏭  chunk $idx 已有 segs，跳过"
  else
    echo "📤  uploading chunk $idx to Azure diarize..."
    attempt=0
    ok=0
    while [ $attempt -lt 6 ]; do
      if curl -sS --fail-with-body \
          --connect-timeout 30 --max-time 360 \
          -X POST "$URL" \
          -H "api-key: $KEY" \
          -F "file=@${mp3}" \
          -F "response_format=json" \
          -F "chunking_strategy=auto" \
          -F "stream=true" \
          -o "$sse"; then
        ok=1
        break
      fi
      attempt=$((attempt + 1))
      echo "⚠️  chunk $idx 第 $attempt 次失败，15s 后重试..." >&2
      sleep 15
    done

    if [ "$ok" != "1" ]; then
      echo "❌ chunk $idx 6 次全失败，先跳过，后面手动重跑" >&2
      rm -f "$sse"
      start=$((start + CHUNK_SEC))
      continue
    fi

    # 从 SSE 抽出 segment 事件，加上全局偏移
    python3 "$SCRIPT_DIR/_parse_segs.py" "$sse" "$start" > "$segs"
    echo "   ✓ $(jq length "$segs") segments"
  fi

  start=$((start + CHUNK_SEC))
done

# 合并所有 chunk 的 segs → dialog_en.json
echo "🔗 合并 ${idx} 个 chunk → dialog_en.json"
python3 "$SCRIPT_DIR/_merge_chunks.py" "$CHUNK_DIR" "$OUT_DIR/dialog_en.json"

echo ""
echo "✅ 完成: $OUT_DIR/dialog_en.json"
echo "💡 下一步：python3 scripts/rename_speakers.py $OUT_DIR/dialog_en.json SPEAKER_00=Host SPEAKER_01=Guest"
