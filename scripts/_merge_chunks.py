#!/usr/bin/env python3
"""Merge per-chunk segs.json files into a single dialog_en.json.

Usage: _merge_chunks.py <chunk_dir> <out_path>
"""
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
