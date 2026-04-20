#!/usr/bin/env python3
"""把 whisper-cli -oj 的原始输出转成 transcribe_diarized.py 期望的格式"""
import json, sys
raw = json.load(open(sys.argv[1]))
segs = []
for t in raw.get("transcription", []):
    segs.append({
        "start": t["offsets"]["from"] / 1000.0,
        "end":   t["offsets"]["to"]   / 1000.0,
        "text":  t["text"].strip(),
    })
json.dump(segs, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
print(f"✅ {len(segs)} whisper segments → {sys.argv[2]}")
