#!/usr/bin/env python3
"""预览 dialog_en.json 前 N 轮"""
import json, sys
d = json.load(open(sys.argv[1]))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
print(f"总 {len(d)} 轮对话")
for t in d[:n]:
    txt = t["text"][:120] + ("..." if len(t["text"]) > 120 else "")
    print(f"[{t['start']:>7.1f}-{t['end']:>7.1f}] {t['speaker']}: {txt}")
