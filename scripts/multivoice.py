#!/usr/bin/env python3
"""
multivoice.py — 把"对话脚本"合成多人配音的 mp3。

输入：一个 JSON 或 YAML 对话文件（见 sample_dialogue.json）
输出：一段拼接好的 mp3 播客音频

用法：
    python3 multivoice.py <dialogue.json> [-o output.mp3]

对话脚本格式（JSON）：
[
  {"speaker": "host",  "text": "主持人：欢迎来到节目。"},
  {"speaker": "guest", "text": "嘉宾：谢谢邀请。"},
  {"speaker": "host",  "text": "今天我们聊聊..."}
]

或带配置 + 台词：
{
  "voices": {
    "host":  "zh-CN-XiaoyiNeural",
    "guest": "zh-CN-YunyangNeural"
  },
  "pause_ms": 400,
  "lines": [
    {"speaker": "host",  "text": "..."},
    {"speaker": "guest", "text": "..."}
  ]
}

依赖：edge-tts, ffmpeg (用于拼接)
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts

DEFAULT_VOICES = {
    "host":   "zh-CN-XiaoxiaoNeural",   # 成熟女声，主持风格
    "guest":  "zh-CN-YunyangNeural",    # 男声，新闻播报风（适合嘉宾）
    "narrator": "zh-CN-YunxiNeural",    # 温和男声（旁白）
    "A":      "zh-CN-XiaoyiNeural",
    "B":      "zh-CN-YunxiNeural",
}
DEFAULT_PAUSE_MS = 400


def load_dialogue(path: str):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        lines = data
        voices = {}
        pause_ms = DEFAULT_PAUSE_MS
    else:
        lines = data["lines"]
        voices = data.get("voices", {})
        pause_ms = data.get("pause_ms", DEFAULT_PAUSE_MS)
    # Fill missing voices from defaults
    for line in lines:
        sp = line["speaker"]
        if sp not in voices:
            voices[sp] = DEFAULT_VOICES.get(sp, "zh-CN-XiaoxiaoNeural")
    return lines, voices, pause_ms


async def synth_line(text: str, voice: str, out_path: Path, rate: str = "+0%"):
    c = edge_tts.Communicate(text, voice, rate=rate)
    await c.save(str(out_path))


def make_silence(duration_ms: int, out_path: Path):
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i",
        f"anullsrc=channel_layout=mono:sample_rate=24000",
        "-t", f"{duration_ms/1000}",
        "-q:a", "9", "-acodec", "libmp3lame",
        "-y", str(out_path)
    ], check=True, capture_output=True)


def concat_mp3s(parts: list[Path], out_path: Path):
    # Build a concat list file for ffmpeg
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        for p in parts:
            f.write(f"file '{p.absolute()}'\n")
        list_file = f.name
    try:
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy",
            "-y", str(out_path)
        ], check=True, capture_output=True)
    finally:
        os.unlink(list_file)


async def main(dialogue_path: str, output_path: str):
    lines, voices, pause_ms = load_dialogue(dialogue_path)
    print(f"📖 {len(lines)} lines, voices: {voices}, pause={pause_ms}ms")

    tmpdir = Path(tempfile.mkdtemp(prefix="multivoice_"))
    print(f"🗂  tmp: {tmpdir}")

    silence_path = tmpdir / "silence.mp3"
    make_silence(pause_ms, silence_path)

    parts = []
    for i, line in enumerate(lines):
        speaker = line["speaker"]
        text = line["text"]
        voice = voices[speaker]
        rate = line.get("rate", "+0%")
        out = tmpdir / f"{i:03d}_{speaker}.mp3"
        print(f"  [{i+1:02d}/{len(lines)}] {speaker:10s} ({voice}) → {text[:40]}...")
        await synth_line(text, voice, out, rate=rate)
        parts.append(out)
        if i < len(lines) - 1:
            parts.append(silence_path)

    print(f"🔗 Concatenating {len(parts)} segments → {output_path}")
    concat_mp3s(parts, Path(output_path))
    size = os.path.getsize(output_path) / 1024
    print(f"✅ Done: {output_path} ({size:.1f} KB)")

    # Duration
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", output_path],
            capture_output=True, text=True, check=True
        )
        dur = float(r.stdout.strip())
        print(f"🎧 Duration: {int(dur//60)}m {int(dur%60)}s")
    except Exception:
        pass


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("dialogue", help="Path to dialogue JSON file")
    p.add_argument("-o", "--output", default="output.mp3")
    args = p.parse_args()
    asyncio.run(main(args.dialogue, args.output))
