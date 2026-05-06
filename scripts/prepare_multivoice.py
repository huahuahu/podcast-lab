#!/usr/bin/env python3
"""把 dialog_zh.json 转成 multivoice_robust.py 能吃的格式，并指定中文音色。

支持多种 speaker 命名，自动按性别分配男女声。未知 speaker 走 default。

可选 projects/<slug>/meta.json 里的 voices 字段覆盖默认（按 speaker 名）：
  {
    "voices": { "Host": "zh-CN-YunxiNeural", "Guest": "zh-CN-YunyangNeural" }
  }
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config

src_path = sys.argv[1]
out_path = sys.argv[2]

src = json.load(open(src_path))

# 主持人 → 晓晓（女声，活泼）  嘉宾/叙述者 → 云扬（男声，沉稳）
VOICE_MAP = {
    "Host":       "zh-CN-XiaoxiaoNeural",
    "Guest":      "zh-CN-YunyangNeural",
    "Ryan":       "zh-CN-XiaoxiaoNeural",
    "Ethan":      "zh-CN-YunyangNeural",
    "narrator":   "zh-CN-YunxiNeural",
    "SPEAKER_00": "zh-CN-XiaoxiaoNeural",
    "SPEAKER_01": "zh-CN-YunyangNeural",
    "SPEAKER_02": "zh-CN-YunxiNeural",
    "SPEAKER_03": "zh-CN-XiaoyiNeural",
}
DEFAULT_VOICE = "zh-CN-XiaoyiNeural"

# 找同级 project 目录: <proj>/transcript/dialog_zh.json -> <proj>/
proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(src_path)))
cfg = _config.resolve(proj_dir)
override = (cfg.get("voices") or {})
if override:
    src_label = cfg.get("_series", "meta.json")
    print(f"📋 voices override [{src_label}]: {override}")

speakers_seen = {t["speaker"] for t in src if t.get("text")}
voices = {sp: override.get(sp, VOICE_MAP.get(sp, DEFAULT_VOICE)) for sp in speakers_seen}

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
