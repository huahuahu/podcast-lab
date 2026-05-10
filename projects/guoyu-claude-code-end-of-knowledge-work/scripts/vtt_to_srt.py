#!/usr/bin/env python3
"""把 YouTube zh.vtt 转成干净的 zh.srt + zh.vtt + 繁→简。"""
import re, sys, json
from pathlib import Path

try:
    from opencc import OpenCC
    cc = OpenCC('t2s')
    convert = cc.convert
except ImportError:
    convert = lambda x: x  # 没装 opencc 就保留繁体

src = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

raw = src.read_text(encoding='utf-8')
lines = raw.splitlines()

cues = []
i = 0
while i < len(lines):
    l = lines[i].strip()
    if '-->' in l:
        m = re.match(r'(\d+:\d+:\d+\.\d+)\s*-->\s*(\d+:\d+:\d+\.\d+)', l)
        if m:
            start, end = m.group(1), m.group(2)
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                t = re.sub(r'<[^>]+>', '', lines[i]).strip()
                if t:
                    text_lines.append(t)
                i += 1
            text = ' '.join(text_lines).strip()
            if text:
                cues.append((start, end, convert(text)))
    i += 1

# 去重连续重复
dedup = []
for c in cues:
    if dedup and dedup[-1][2] == c[2]:
        # 合并：扩展上一条 end
        dedup[-1] = (dedup[-1][0], c[1], c[2])
    else:
        dedup.append(c)

# SRT
def vtt_to_srt_time(t):  # 00:00:03.720 -> 00:00:03,720
    return t.replace('.', ',')

srt_lines = []
for idx, (s, e, t) in enumerate(dedup, 1):
    srt_lines.append(str(idx))
    srt_lines.append(f"{vtt_to_srt_time(s)} --> {vtt_to_srt_time(e)}")
    srt_lines.append(t)
    srt_lines.append('')
(out_dir / 'zh.srt').write_text('\n'.join(srt_lines), encoding='utf-8')

# 干净 VTT
vtt_lines = ['WEBVTT', '']
for s, e, t in dedup:
    vtt_lines.append(f"{s} --> {e}")
    vtt_lines.append(t)
    vtt_lines.append('')
(out_dir / 'zh.vtt').write_text('\n'.join(vtt_lines), encoding='utf-8')

# JSON dialog（无 speaker，单 channel）
def to_sec(t):
    h, m, rest = t.split(':')
    s, ms = rest.split('.')
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

dialog = [{'start': to_sec(s), 'end': to_sec(e), 'text': t} for s, e, t in dedup]
Path(out_dir.parent / 'dialog_zh.json').write_text(
    json.dumps(dialog, ensure_ascii=False, indent=2), encoding='utf-8'
)

print(f"✓ {len(dedup)} cues → {out_dir}/zh.srt zh.vtt + dialog_zh.json")
