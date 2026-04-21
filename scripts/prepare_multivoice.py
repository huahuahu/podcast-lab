#!/usr/bin/env python3
"""把 dialog_zh.json 转成 multivoice_robust.py 能吃的格式，并指定中文音色"""
import json, sys

src = json.load(open(sys.argv[1]))
out_path = sys.argv[2]

# Ethan（嘉宾，前 Amazon VP，老练男声）→ 云扬（沉稳播报）
# Ryan（主持人，活泼提问女声）→ 晓晓
dialogue = {
    "voices": {
        "Ethan": "zh-CN-YunyangNeural",
        "Ryan":  "zh-CN-XiaoxiaoNeural",
    },
    "pause_ms": 350,
    "lines": [
        {"speaker": t["speaker"], "text": t["text"]}
        for t in src if t.get("text")
    ],
}
json.dump(dialogue, open(out_path, "w"), ensure_ascii=False, indent=2)
print(f"✅ {len(dialogue['lines'])} lines → {out_path}")
