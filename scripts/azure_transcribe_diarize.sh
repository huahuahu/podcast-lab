#!/usr/bin/env bash
# azure_transcribe_diarize.sh — 用 Azure gpt-4o-transcribe-diarize 一步搞定
# STT + speaker diarization（替代 SF SenseVoice + pyannote）。
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
    python3 - "$sse" "$start" > "$segs" <<'PY'
import json, re, sys
sse_path, offset = sys.argv[1], float(sys.argv[2])
segs = []
with open(sse_path) as f:
    for line in f:
        line = line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        try:
            evt = json.loads(payload)
        except Exception:
            continue
        if evt.get("type") != "transcript.text.segment":
            continue
        segs.append({
            "start": round(float(evt["start"]) + offset, 3),
            "end":   round(float(evt["end"])   + offset, 3),
            "speaker": evt.get("speaker") or "?",
            "text": (evt.get("text") or "").strip(),
        })
json.dump(segs, sys.stdout, ensure_ascii=False, indent=2)
PY
    echo "   ✓ $(jq length "$segs") segments"
  fi

  start=$((start + CHUNK_SEC))
done

# 合并所有 chunk 的 segs → dialog_en.json
echo "🔗 合并 ${idx} 个 chunk → dialog_en.json"
python3 - "$CHUNK_DIR" "$OUT_DIR/dialog_en.json" <<'PY'
import json, os, sys, glob, re
chunk_dir, out = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(os.path.join(chunk_dir, "chunk_*.segs.json")))
all_segs = []
for fp in files:
    with open(fp) as f:
        all_segs.extend(json.load(f))

# Azure 返回的 speaker 是 'A' / 'B' / 'C' ...
# 每个 chunk 内部是独立 diarize 的，不同 chunk 里的 'A' 不一定是同一个人。
# 后续可用 rename_speakers.py 手工重映射到 Host/Guest。
#
# 合并策略：
#   1) 相邻同 speaker + 间隔 <1s → 合并
#   2) 但合并后的段落长度不超过 MAX_CHARS（默认 250），超了就开新段
#   3) 这样避免独白视频被合成一大段导致 TTS 超时
MAX_CHARS = 250  # 大致 15-25 秒语音
merged = []
for s in all_segs:
    if (merged
        and merged[-1]["speaker"] == s["speaker"]
        and s["start"] - merged[-1]["end"] < 1.0
        and len(merged[-1]["text"]) + len(s["text"]) + 1 <= MAX_CHARS):
        merged[-1]["end"] = s["end"]
        merged[-1]["text"] = (merged[-1]["text"] + " " + s["text"]).strip()
    else:
        merged.append(dict(s))

# speaker 规范化 A→SPEAKER_00, B→SPEAKER_01, ...（和 pyannote 对齐）
def norm(sp):
    if re.fullmatch(r"[A-Z]", sp or ""):
        return f"SPEAKER_{ord(sp) - ord('A'):02d}"
    return sp
for s in merged:
    s["speaker"] = norm(s["speaker"])

with open(out, "w") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f"✅ {len(merged)} utterances → {out}")
PY

echo ""
echo "✅ 完成: $OUT_DIR/dialog_en.json"
echo "💡 下一步：python3 scripts/rename_speakers.py $OUT_DIR/dialog_en.json SPEAKER_00=Host SPEAKER_01=Guest"
