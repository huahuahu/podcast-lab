#!/usr/bin/env python3
"""make_subtitles_simple.py — 从 [{start,end,text}] JSON 生成 srt + vtt。

适用于 STT 已经给出真实音频时间戳的场景（如 azure_transcribe_mini.sh 输出的
dialog_en.json，但内容其实是中文）。

长文本按句子标点切，时间戳按字数比例分配。

用法:
  python3 make_subtitles_simple.py <input.json> <out_dir> [--lang zh]
"""
import json
import os
import re
import sys


def fmt_srt_time(s: float) -> str:
    s = max(0.0, float(s))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int(round((s - int(s)) * 1000))
    if ms == 1000:
        ms = 0
        sec += 1
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def fmt_vtt_time(s: float) -> str:
    return fmt_srt_time(s).replace(",", ".")


def split_long(text: str, max_chars: int = 40) -> list:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    # 先按强标点切（句号/问号/感叹号/分号）
    parts = re.split(r"([。！？!?；;])", text)
    sentences = []
    cur = ""
    for p in parts:
        cur += p
        if re.search(r"[。！？!?；;]$", cur):
            sentences.append(cur.strip())
            cur = ""
    if cur.strip():
        sentences.append(cur.strip())

    # 二次切：仍然太长的按逗号/顿号切
    refined = []
    for s in sentences:
        if len(s) <= max_chars:
            refined.append(s)
            continue
        sub = re.split(r"([，、,])", s)
        buf = ""
        for x in sub:
            buf += x
            if re.search(r"[，、,]$", buf) and len(buf) >= max_chars * 0.6:
                refined.append(buf.strip())
                buf = ""
        if buf.strip():
            refined.append(buf.strip())

    # 再合并过短的
    merged = []
    cur = ""
    for s in refined:
        if not s:
            continue
        if len(cur) + len(s) <= max_chars:
            cur = (cur + s) if cur else s
        else:
            if cur:
                merged.append(cur)
            cur = s
    if cur:
        merged.append(cur)

    # 兜底：仍然超长的硬切
    final = []
    for m in merged:
        if len(m) <= max_chars * 1.5:
            final.append(m)
        else:
            for i in range(0, len(m), max_chars):
                final.append(m[i : i + max_chars])
    return [x for x in final if x.strip()]


def make_cues(items: list, max_chars: int = 40) -> list:
    cues = []
    for it in items:
        text = (it.get("text") or "").strip()
        if not text:
            continue
        start = float(it.get("start", 0))
        end = float(it.get("end", start + 1))
        if end <= start:
            end = start + 1.0
        chunks = split_long(text, max_chars=max_chars)
        if len(chunks) == 1:
            cues.append({"start": start, "end": end, "text": chunks[0]})
            continue
        total = sum(len(c) for c in chunks) or 1
        dur = end - start
        cur = start
        for i, ch in enumerate(chunks):
            d = dur * (len(ch) / total)
            cend = cur + d if i < len(chunks) - 1 else end
            cues.append({"start": cur, "end": cend, "text": ch})
            cur = cend
    return cues


def write_srt(path: str, cues: list):
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n")
            f.write(f"{fmt_srt_time(c['start'])} --> {fmt_srt_time(c['end'])}\n")
            f.write(f"{c['text']}\n\n")


def write_vtt(path: str, cues: list):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, c in enumerate(cues, 1):
            f.write(f"{fmt_vtt_time(c['start'])} --> {fmt_vtt_time(c['end'])}\n")
            f.write(f"{c['text']}\n\n")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    in_path = sys.argv[1]
    out_dir = sys.argv[2]
    lang = "zh"
    if "--lang" in sys.argv:
        lang = sys.argv[sys.argv.index("--lang") + 1]
    os.makedirs(out_dir, exist_ok=True)
    with open(in_path, encoding="utf-8") as f:
        items = json.load(f)
    cues = make_cues(items)
    srt_path = os.path.join(out_dir, f"{lang}.srt")
    vtt_path = os.path.join(out_dir, f"{lang}.vtt")
    write_srt(srt_path, cues)
    write_vtt(vtt_path, cues)
    print(f"✅ {len(cues)} cues → {srt_path}")
    print(f"✅ {len(cues)} cues → {vtt_path}")


if __name__ == "__main__":
    main()
