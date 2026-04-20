#!/usr/bin/env python3
"""
diarize.py — 说话人分离（pyannote-audio）

输入：音频文件（任意格式，内部用 ffmpeg 转 wav 16kHz mono）
输出：JSON 格式的说话人分段
    [{"start": 0.0, "end": 4.2, "speaker": "SPEAKER_00"}, ...]

用法：
    python3 diarize.py <audio> -o segments.json [--num-speakers 2]
"""
import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path

from pyannote.audio import Pipeline


def to_wav16k_mono(src: str) -> str:
    """Convert to WAV 16kHz mono (pyannote expects this)."""
    dst = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run([
        "ffmpeg", "-i", src,
        "-ar", "16000", "-ac", "1",
        "-y", dst
    ], check=True, capture_output=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("-o", "--output", default="segments.json")
    ap.add_argument("--num-speakers", type=int, default=None,
                    help="Force number of speakers (e.g. 2 for interview)")
    ap.add_argument("--min-speakers", type=int, default=None)
    ap.add_argument("--max-speakers", type=int, default=None)
    args = ap.parse_args()

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        print("ERROR: set HF_TOKEN env var (source ~/.openclaw/secrets/env.sh)")
        sys.exit(1)

    print("📥 loading pipeline (first run downloads ~100MB)...")
    # pyannote >= 3.3 uses `token=`; older uses `use_auth_token=`
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        )
    except TypeError:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )

    # Prefer Apple MPS on M-series; fallback CPU
    try:
        import torch
        if torch.backends.mps.is_available():
            pipeline.to(torch.device("mps"))
            print("🍎 using Apple MPS (Metal)")
    except Exception:
        pass

    print(f"🎬 preparing audio: {args.audio}")
    wav_path = to_wav16k_mono(args.audio)

    kwargs = {}
    if args.num_speakers:
        kwargs["num_speakers"] = args.num_speakers
    if args.min_speakers:
        kwargs["min_speakers"] = args.min_speakers
    if args.max_speakers:
        kwargs["max_speakers"] = args.max_speakers

    print(f"🔊 running diarization... ({kwargs or 'auto detect'})")
    diarization = pipeline(wav_path, **kwargs)

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
        })

    speaker_count = len({s["speaker"] for s in segments})
    total_dur = sum(s["end"] - s["start"] for s in segments)
    print(f"✅ {len(segments)} segments, {speaker_count} speakers, {total_dur:.0f}s total")

    with open(args.output, "w") as f:
        json.dump(segments, f, indent=2, ensure_ascii=False)
    print(f"💾 saved → {args.output}")

    # cleanup
    os.unlink(wav_path)


if __name__ == "__main__":
    main()
