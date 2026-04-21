#!/usr/bin/env python3
"""把 dialog_zh.json 转成 multivoice_robust.py 能吃的格式，并指定中文音色。

支持多种 speaker 命名，自动按性别分配男女声。未知 speaker 走 default。
"""
import json, sys

src = json.load(open(sys.argv[1]))
out_path = sys.argv[2]

# 主持人 → 晓晓（女声，活泼）  嘉宾/叙述者 → 云扬（男声，沉稳）
VOICE_MAP = {
    # 英文命名
    "Host":       "zh-CN-XiaoxiaoNeural",
    "Guest":      "zh-CN-YunyangNeural",
    "Ryan":       "zh-CN-XiaoxiaoNeural",
    "Ethan":      "zh-CN-YunyangNeural",
    "narrator":   "zh-CN-YunxiNeural",
    # pyannote / Azure fallback
    "SPEAKER_00": "zh-CN-XiaoxiaoNeural",
    "SPEAKER_01": "zh-CN-YunyangNeural",
    "SPEAKER_02": "zh-CN-YunxiNeural",
    "SPEAKER_03": "zh-CN-XiaoyiNeural",
}
DEFAULT_VOICE = "zh-CN-XiaoyiNeural"  # 晓伊（女声），未知 speaker 兜底

# 实际用到的音色（只塞实际出现的 speaker，保持输出精简）
speakers_seen = {t["speaker"] for t in src if t.get("text")}
voices = {sp: VOICE_MAP.get(sp, DEFAULT_VOICE) for sp in speakers_seen}

dialogue = {
    "voices": voices,
    "pause_ms": 350,
    "lines": [
        {"speaker": t["speaker"], "text": t["text"]}
        for t in src if t.get("text")
    ],
}
json.dump(dialogue, open(out_path, "w"), ensure_ascii=False, indent=2)
print(f"✅ {len(dialogue['lines'])} lines → {out_path}")
print(f"   voices: {voices}")
