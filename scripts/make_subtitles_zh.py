#!/usr/bin/env python3
"""make_subtitles_zh.py — 给中文 mp3 (TTS 合成结果) 生成精准字幕。

时间戳从 tts_cache/{idx}_{speaker}.mp3 的真实时长计算（含 _silence_{ms}.mp3 间隔），
而不是用 dialog_zh.json 里的英文 STT 时间戳（那个对中文 mp3 没意义）。

输出：
  transcript/subtitles/zh.srt          中文 SRT，时间戳与 podcast_zh.mp3 对齐
  transcript/subtitles/zh.vtt          WebVTT 同上
  transcript/subtitles/bilingual.srt   双语（中文上+英文下），时间戳与 podcast_zh.mp3 对齐

用法：
  python3 make_subtitles_zh.py <project_dir>
"""
import json
import os
import re
import subprocess
import sys


def fmt_srt_time(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def fmt_vtt_time(s: float) -> str:
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
        for c in cues:
            f.write(f"{fmt_vtt_time(c['start'])} --> {fmt_vtt_time(c['end'])}\n")
            f.write(f"{c['text']}\n\n")


def probe_duration(mp3: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", mp3],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    proj = sys.argv[1].rstrip("/")
    en_path = os.path.join(proj, "transcript", "dialog_en.json")
    zh_path = os.path.join(proj, "transcript", "dialog_zh.json")
    cache_dir = os.path.join(proj, "audio", "tts_cache")
    out_dir = os.path.join(proj, "transcript", "subtitles")
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(zh_path):
        print(f"❌ 缺少 {zh_path}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isdir(cache_dir):
        print(f"❌ 缺少 tts_cache 目录 {cache_dir}", file=sys.stderr)
        sys.exit(2)

    zh_dialog = json.load(open(zh_path))
    en_dialog = json.load(open(en_path)) if os.path.exists(en_path) else None

    # 用了 prepare_multivoice.py 重新格式化过 — 找 dialog_zh_mv.json
    mv_path = os.path.join(proj, "transcript", "dialog_zh_mv.json")
    if os.path.exists(mv_path):
        mv_data = json.load(open(mv_path))
        mv_lines = mv_data.get("lines", mv_data) if isinstance(mv_data, dict) else mv_data
        # 跟 zh_dialog 长度应该一致（prepare 只是转格式 + 配音色映射）
        if len(mv_lines) != len(zh_dialog):
            print(f"⚠️  zh_dialog={len(zh_dialog)} mv={len(mv_lines)}, 用 mv 顺序对齐 cache", file=sys.stderr)
            zh_dialog = [{"text": L["text"], "speaker": L["speaker"]} for L in mv_lines]

    # 间隔 mp3（pause）
    pause_files = [f for f in os.listdir(cache_dir) if f.startswith("_silence_")]
    pause_dur = 0.0
    if pause_files:
        pause_path = os.path.join(cache_dir, pause_files[0])
        pause_dur = probe_duration(pause_path)
        # 提取 ms 名字也行
        m = re.match(r"_silence_(\d+)\.mp3", pause_files[0])
        if m:
            pause_dur = int(m.group(1)) / 1000.0
        print(f"💤 silence: {pause_files[0]} = {pause_dur:.3f}s")

    # 算每行 mp3 的时长，按 multivoice 拼接顺序累计时间戳
    # 顺序：000_speaker.mp3, silence, 001_speaker.mp3, silence, ..., last 不带 silence
    cues_zh = []
    cues_bi = []
    cur = 0.0
    n = len(zh_dialog)
    for i, turn in enumerate(zh_dialog):
        speaker = turn.get("speaker", "")
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        # 找 cache 文件 (与 multivoice 命名一致 {i:03d}_{speaker}.mp3)
        candidate = os.path.join(cache_dir, f"{i:03d}_{speaker}.mp3")
        if not os.path.exists(candidate):
            # 兼容：可能 speaker 字段编码不同（中文 → 英文等），fall back
            matches = [f for f in os.listdir(cache_dir)
                       if f.startswith(f"{i:03d}_") and f.endswith(".mp3")]
            if matches:
                candidate = os.path.join(cache_dir, matches[0])
            else:
                print(f"⚠️ 找不到 cache for line {i}", file=sys.stderr)
                continue
        dur = probe_duration(candidate)
        start = cur
        end = cur + dur
        cur = end + (pause_dur if i < n - 1 else 0)

        prefix = f"[{speaker}] " if speaker and speaker not in ("?", "") else ""
        cues_zh.append({"start": start, "end": end, "text": f"{prefix}{text}"})

        # bilingual: 中文 + 英文
        if en_dialog and i < len(en_dialog):
            en_text = (en_dialog[i].get("text") or "").strip()
            cues_bi.append({"start": start, "end": end,
                            "text": f"{prefix}{text}\n{en_text}"})
        else:
            cues_bi.append({"start": start, "end": end, "text": f"{prefix}{text}"})

    # 输出
    write_srt(os.path.join(out_dir, "zh.srt"), cues_zh)
    write_vtt(os.path.join(out_dir, "zh.vtt"), cues_zh)
    write_srt(os.path.join(out_dir, "bilingual.srt"), cues_bi)
    write_vtt(os.path.join(out_dir, "bilingual.vtt"), cues_bi)
    print(f"✅ {len(cues_zh)} cues  → zh.srt + zh.vtt + bilingual.srt + bilingual.vtt")
    print(f"   total duration ≈ {cur/60:.1f} min")
    print(f"📁 {out_dir}/")


if __name__ == "__main__":
    main()
