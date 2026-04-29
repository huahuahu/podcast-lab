#!/usr/bin/env python3
"""make_subtitles.py — 从 dialog_en.json + dialog_zh.json 生成字幕文件。

输出：
  transcript/subtitles/en.srt              纯英文 SRT
  transcript/subtitles/zh.srt              纯中文 SRT
  transcript/subtitles/bilingual.srt       双语 SRT（中文上、英文下）
  transcript/subtitles/en.vtt              纯英文 WebVTT
  transcript/subtitles/zh.vtt              纯中文 WebVTT
  transcript/subtitles/bilingual.vtt       双语 WebVTT

时间戳来源：dialog_en.json 的 start/end（对应原英文音频）。

用法：
  python3 make_subtitles.py <project_dir>
  例：python3 make_subtitles.py projects/mearsheimer-trump-lost-war
"""
import json
import os
import sys
import re


def fmt_srt_time(s: float) -> str:
    """秒 → SRT 时间格式 HH:MM:SS,mmm"""
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def fmt_vtt_time(s: float) -> str:
    """秒 → WebVTT 时间格式 HH:MM:SS.mmm"""
    return fmt_srt_time(s).replace(",", ".")


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
            f.write(f"{i}\n")
            f.write(f"{fmt_vtt_time(c['start'])} --> {fmt_vtt_time(c['end'])}\n")
            f.write(f"{c['text']}\n\n")


def split_long_text(text: str, max_chars: int = 80) -> list:
    """按句子边界把过长的文本切成多段（字幕单行不能太长）。"""
    if len(text) <= max_chars:
        return [text]
    # 优先按句号/问号/感叹号切
    parts = re.split(r"([。！？.!?]+)", text)
    sentences = []
    cur = ""
    for p in parts:
        cur += p
        if re.search(r"[。！？.!?]+$", cur):
            sentences.append(cur.strip())
            cur = ""
    if cur.strip():
        sentences.append(cur.strip())
    if not sentences:
        sentences = [text]

    # 把过短句子合并起来
    merged = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) <= max_chars:
            cur = (cur + " " + s).strip() if cur else s
        else:
            if cur:
                merged.append(cur)
            cur = s
    if cur:
        merged.append(cur)
    return merged


def make_cues(dialog: list, label_speaker: bool = True) -> list:
    """从 dialog 列表生成 SRT cue 列表。
    
    长文本会自动切成多段，时间戳按字数比例分配。
    """
    cues = []
    for turn in dialog:
        text = turn.get("text", "").strip()
        if not text:
            continue
        speaker = turn.get("speaker", "")
        start = float(turn.get("start", 0))
        end = float(turn.get("end", start + 1))

        # 如果带 speaker label
        if label_speaker and speaker and speaker not in ("?", ""):
            text = f"[{speaker}] {text}"

        chunks = split_long_text(text, max_chars=80)
        if len(chunks) == 1:
            cues.append({"start": start, "end": end, "text": text})
        else:
            total_chars = sum(len(c) for c in chunks) or 1
            duration = end - start
            cur = start
            for ch in chunks:
                d = duration * (len(ch) / total_chars)
                cues.append({"start": cur, "end": cur + d, "text": ch})
                cur += d
    return cues


def make_bilingual_cues(en_dialog: list, zh_dialog: list) -> list:
    """生成双语 cue：每条字幕 = 中文(第一行) + 英文(第二行)。
    
    假设两个 dialog 长度一致、对应 turn 一一对应（reassign 之后是的）。
    """
    if len(en_dialog) != len(zh_dialog):
        print(f"⚠️  en={len(en_dialog)} zh={len(zh_dialog)}, sizes differ. Aligning by min.", file=sys.stderr)
    n = min(len(en_dialog), len(zh_dialog))
    cues = []
    for i in range(n):
        en = en_dialog[i]
        zh = zh_dialog[i]
        en_text = en.get("text", "").strip()
        zh_text = zh.get("text", "").strip()
        speaker = zh.get("speaker") or en.get("speaker") or ""
        start = float(en.get("start", 0))
        end = float(en.get("end", start + 1))
        if not en_text and not zh_text:
            continue

        # 两行：中文（带 speaker label）+ 英文
        prefix = f"[{speaker}] " if speaker and speaker not in ("?", "") else ""
        text = f"{prefix}{zh_text}\n{en_text}"
        cues.append({"start": start, "end": end, "text": text})
    return cues


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    proj = sys.argv[1].rstrip("/")
    en_path = os.path.join(proj, "transcript", "dialog_en.json")
    zh_path = os.path.join(proj, "transcript", "dialog_zh.json")
    out_dir = os.path.join(proj, "transcript", "subtitles")
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(en_path) or not os.path.exists(zh_path):
        print(f"❌ 缺少 {en_path} 或 {zh_path}", file=sys.stderr)
        sys.exit(2)

    en_dialog = json.load(open(en_path))
    zh_dialog = json.load(open(zh_path))
    print(f"📚 en={len(en_dialog)} zh={len(zh_dialog)}")

    # English-only
    en_cues = make_cues(en_dialog, label_speaker=True)
    write_srt(os.path.join(out_dir, "en.srt"), en_cues)
    write_vtt(os.path.join(out_dir, "en.vtt"), en_cues)
    print(f"✅ en.srt / en.vtt: {len(en_cues)} cues")

    # Chinese-only
    zh_cues = make_cues(zh_dialog, label_speaker=True)
    write_srt(os.path.join(out_dir, "zh.srt"), zh_cues)
    write_vtt(os.path.join(out_dir, "zh.vtt"), zh_cues)
    print(f"✅ zh.srt / zh.vtt: {len(zh_cues)} cues")

    # Bilingual
    bi_cues = make_bilingual_cues(en_dialog, zh_dialog)
    write_srt(os.path.join(out_dir, "bilingual.srt"), bi_cues)
    write_vtt(os.path.join(out_dir, "bilingual.vtt"), bi_cues)
    print(f"✅ bilingual.srt / bilingual.vtt: {len(bi_cues)} cues")

    print(f"\n📁 全部输出到 {out_dir}/")


if __name__ == "__main__":
    main()
