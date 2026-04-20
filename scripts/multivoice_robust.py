#!/usr/bin/env python3
"""
multivoice_robust.py — multivoice.py 的强化版

改进点：
- 每句 edge-tts 有 45s 超时
- 失败自动重试 3 次
- 断点续传：指定 --cache-dir 后，同名 mp3 存在且 >0 字节就跳过
- 进度写进 log 时 flush=True，实时可见
- 最终用 ffmpeg concat 拼接
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
    "host": "zh-CN-XiaoxiaoNeural",
    "guest": "zh-CN-YunyangNeural",
    "Ethan": "zh-CN-YunyangNeural",
    "Ryan": "zh-CN-XiaoxiaoNeural",
}
DEFAULT_PAUSE_MS = 350


def load_dialogue(path: str):
    data = json.load(open(path))
    if isinstance(data, list):
        lines, voices, pause_ms = data, {}, DEFAULT_PAUSE_MS
    else:
        lines = data["lines"]
        voices = data.get("voices", {})
        pause_ms = data.get("pause_ms", DEFAULT_PAUSE_MS)
    for line in lines:
        sp = line["speaker"]
        if sp not in voices:
            voices[sp] = DEFAULT_VOICES.get(sp, "zh-CN-XiaoxiaoNeural")
    return lines, voices, pause_ms


async def synth_one(text: str, voice: str, out_path: Path, timeout: float = 45.0):
    """带超时的单句合成"""
    comm = edge_tts.Communicate(text, voice)
    await asyncio.wait_for(comm.save(str(out_path)), timeout=timeout)


async def synth_with_retry(text: str, voice: str, out_path: Path, retries: int = 3):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            # 确保干净
            if out_path.exists():
                out_path.unlink()
            await synth_one(text, voice, out_path)
            if out_path.exists() and out_path.stat().st_size > 0:
                return True
            last_err = "empty file"
        except asyncio.TimeoutError:
            last_err = "timeout 45s"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        print(f"    ⚠️ attempt {attempt}/{retries} failed: {last_err}", flush=True)
        await asyncio.sleep(2 * attempt)
    # 最后一招：把句子切短（取前 200 字符重试）
    if len(text) > 200:
        try:
            print(f"    🔪 尝试截短至 200 字符后重试", flush=True)
            await synth_one(text[:200] + "。", voice, out_path, timeout=45)
            if out_path.exists() and out_path.stat().st_size > 0:
                return True
        except Exception as e:
            last_err = f"short-retry failed: {e}"
    raise RuntimeError(f"合成失败: {last_err}")


def make_silence(duration_ms: int, out_path: Path):
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i",
        "anullsrc=channel_layout=mono:sample_rate=24000",
        "-t", f"{duration_ms/1000}",
        "-q:a", "9", "-acodec", "libmp3lame",
        "-y", str(out_path),
    ], check=True, capture_output=True)


def concat_mp3s(parts, out_path: Path):
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        for p in parts:
            f.write(f"file '{Path(p).absolute()}'\n")
        list_file = f.name
    try:
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy",
            "-y", str(out_path),
        ], check=True, capture_output=True)
    finally:
        os.unlink(list_file)


async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("dialogue")
    ap.add_argument("-o", "--output", default="output.mp3")
    ap.add_argument("--cache-dir", default=None,
                    help="把每句 mp3 存在这里，支持断点续传")
    args = ap.parse_args()

    lines, voices, pause_ms = load_dialogue(args.dialogue)
    print(f"📖 {len(lines)} lines, voices: {voices}, pause={pause_ms}ms", flush=True)

    if args.cache_dir:
        cache = Path(args.cache_dir)
        cache.mkdir(parents=True, exist_ok=True)
    else:
        cache = Path(tempfile.mkdtemp(prefix="multivoice_"))
    print(f"🗂  cache: {cache}", flush=True)

    silence_path = cache / f"_silence_{pause_ms}.mp3"
    if not silence_path.exists():
        make_silence(pause_ms, silence_path)

    parts = []
    for i, line in enumerate(lines):
        speaker = line["speaker"]
        text = line["text"]
        voice = voices[speaker]
        out = cache / f"{i:03d}_{speaker}.mp3"

        if out.exists() and out.stat().st_size > 0:
            print(f"  [{i+1:03d}/{len(lines)}] {speaker:6s} ♻️  cached", flush=True)
        else:
            preview = text[:40].replace("\n", " ")
            print(f"  [{i+1:03d}/{len(lines)}] {speaker:6s} ({voice}) → {preview}...", flush=True)
            await synth_with_retry(text, voice, out)

        parts.append(out)
        if i < len(lines) - 1:
            parts.append(silence_path)

    print(f"🔗 concat {len(parts)} segments → {args.output}", flush=True)
    concat_mp3s(parts, Path(args.output))
    size_mb = os.path.getsize(args.output) / 1024 / 1024
    print(f"✅ done: {args.output} ({size_mb:.1f} MB)", flush=True)

    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", args.output],
            capture_output=True, text=True, check=True,
        )
        dur = float(r.stdout.strip())
        print(f"🎧 duration: {int(dur//60)}m {int(dur%60)}s", flush=True)
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
