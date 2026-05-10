#!/usr/bin/env bash
# azure_transcribe_mini.sh — 用 Azure gpt-4o-mini-transcribe（非流式）分段转录
#
# 不带 diarization。speaker 由后续 reassign_speakers_llm.py 用 LLM 推断。
# 优点：HTTP 短连接 + 非流式 → 对不稳定网络友好，比 diarize 模型快得多。
#
# 用法:
#   ./azure_transcribe_mini.sh <audio> <out_dir> [chunk_sec]
#
# 产物:
#   <out_dir>/azure_chunks/chunk_NNN.mp3       切片
#   <out_dir>/azure_chunks/chunk_NNN.json      原始 verbose_json
#   <out_dir>/azure_chunks/chunk_NNN.segs.json 解析后的 segments (含全局时间)
#   <out_dir>/dialog_en.json                   合并后的 dialog（schema 同 diarize 版）
set -euo pipefail

# Azure endpoint 在国内需要直连；脚本内部 unset proxy，不影响调用者环境。
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy NO_PROXY no_proxy 2>/dev/null || true

AUDIO="${1:?usage: $0 <audio> <out_dir> [chunk_sec]}"
OUT_DIR="${2:?usage: $0 <audio> <out_dir> [chunk_sec]}"
CHUNK_SEC="${3:-${CHUNK_SEC:-300}}"

CRED="${AZURE_OPENAI_CRED_FILE:-$HOME/.openclaw/credentials/azure-openai.json}"
[ -r "$CRED" ] || { echo "missing $CRED" >&2; exit 2; }

EP=$(jq -r '.endpoint' "$CRED")
KEY=$(jq -r '.apiKey' "$CRED")
VER=$(jq -r '.apiVersion // "2025-03-01-preview"' "$CRED")
DEP=$(jq -r '.deployments.mini.name // "gpt-4o-mini-transcribe"' "$CRED")
URL="${EP%/}/openai/deployments/${DEP}/audio/transcriptions?api-version=${VER}"

CHUNK_DIR="$OUT_DIR/azure_chunks"
mkdir -p "$CHUNK_DIR"

TOTAL=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$AUDIO" \
        | awk '{printf "%d", $1}')
N_CHUNKS=$(( (TOTAL + CHUNK_SEC - 1) / CHUNK_SEC ))
echo "🎬 total=${TOTAL}s chunk=${CHUNK_SEC}s → ${N_CHUNKS} 片 (mini-transcribe)"

idx=0
start=0
while [ "$start" -lt "$TOTAL" ]; do
  idx=$((idx + 1))
  padded=$(printf "%03d" "$idx")
  mp3="$CHUNK_DIR/chunk_${padded}.mp3"
  raw="$CHUNK_DIR/chunk_${padded}.json"
  segs="$CHUNK_DIR/chunk_${padded}.segs.json"

  if [ ! -f "$mp3" ]; then
    echo "✂️  chunk $idx @ ${start}s"
    ffmpeg -loglevel error -ss "$start" -t "$CHUNK_SEC" -i "$AUDIO" \
      -map_metadata -1 \
      -acodec libmp3lame -b:a 64k -ac 1 -ar 16000 -y "$mp3"
  fi

  if [ -f "$segs" ] && jq -e '. | type == "array" and length > 0' "$segs" >/dev/null 2>&1; then
    echo "⏭  chunk $idx 已有 segs，跳过"
  else
    echo "📤  uploading chunk $idx to Azure mini-transcribe..."
    attempt=0
    ok=0
    while [ $attempt -lt 12 ]; do
      if curl -sS --fail-with-body \
          --connect-timeout 20 --max-time 60 \
          -X POST "$URL" \
          -H "api-key: $KEY" \
          -F "file=@${mp3}" \
          -F "response_format=json" \
          -o "$raw"; then
        ok=1
        break
      fi
      attempt=$((attempt + 1))
      echo "⚠️  chunk $idx 第 $attempt 次失败，3s 后重试..." >&2
      sleep 3
    done

    if [ "$ok" != "1" ]; then
      echo "❌ chunk $idx 6 次全失败，跳过" >&2
      rm -f "$raw"
      start=$((start + CHUNK_SEC))
      continue
    fi

    # mini-transcribe 只返回纯文本，使用 Python 按句切分
    python3 - "$raw" "$start" "$CHUNK_SEC" > "$segs" <<'PY'
import json, re, sys
raw_path, offset, chunk_sec = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
data = json.load(open(raw_path))
text = (data.get("text") or "").strip()

# 按句号/问号/感叹号 + 空格 切句（保留标点）
sentences = re.findall(r"[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$", text)
sentences = [s.strip() for s in sentences if s.strip()]

# 没有时间戳，只能估计：按字数按比例平均分配 chunk_sec
total_chars = sum(len(s) for s in sentences) or 1
out = []
cur = 0.0
for s in sentences:
    dur = chunk_sec * (len(s) / total_chars)
    out.append({
        "start": round(offset + cur, 3),
        "end":   round(offset + cur + dur, 3),
        "speaker": "?",
        "text": s,
    })
    cur += dur
json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
PY
    echo "   ✓ $(jq length "$segs") sentences"
  fi

  start=$((start + CHUNK_SEC))
done

# 合并所有 chunk（无 speaker，全部标 "?"，只按长度合并相邻片段以减少碎片）
echo "🔗 合并 ${idx} 个 chunk → dialog_en.json"
python3 - "$CHUNK_DIR" "$OUT_DIR/dialog_en.json" <<'PY'
import json, os, sys, glob
chunk_dir, out = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(os.path.join(chunk_dir, "chunk_*.segs.json")))
all_segs = []
for fp in files:
    with open(fp) as f:
        all_segs.extend(json.load(f))

# 合并连续句子到 ~250 字符上限（让 TTS 单句不太长）
MAX_CHARS = 250
merged = []
for s in all_segs:
    if (merged
        and s["start"] - merged[-1]["end"] < 1.0
        and len(merged[-1]["text"]) + len(s["text"]) + 1 <= MAX_CHARS):
        merged[-1]["end"] = s["end"]
        merged[-1]["text"] = (merged[-1]["text"] + " " + s["text"]).strip()
    else:
        merged.append(dict(s))

# 没有 speaker 信息，全标 "?" 让后续 LLM 处理
for s in merged:
    s["speaker"] = "?"

with open(out, "w") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f"✅ {len(merged)} utterances → {out}")
print("⚠️  speaker 字段全部是 '?'，请运行 reassign_speakers_llm.py 用 LLM 推断")
PY

echo ""
echo "✅ STT 完成: $OUT_DIR/dialog_en.json"
echo "💡 下一步：python3 scripts/reassign_speakers_llm.py $OUT_DIR/dialog_en.json"
