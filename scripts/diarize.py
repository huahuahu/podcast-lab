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

# 在 stdout 被重定向到文件时，Python 默认全缓冲，导致 print 内容长时间看不到。
# 这里直接关掉缓冲，日志即时落盘，方便 tail -f 调试。
os.environ.setdefault("PYTHONUNBUFFERED", "1")
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

import json
import argparse
import subprocess
import tempfile
from pathlib import Path

from pyannote.audio import Pipeline


def to_wav16k_mono(src: str) -> str:
    """Convert to WAV 16kHz mono (pyannote expects this)."""
    # 说话人分离模型通常要求固定采样率和单声道输入，
    # 这样可以避免不同音频格式带来的兼容性问题。
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
        # pyannote 的官方 pipeline 通过 Hugging Face 分发；首次下载和后续鉴权都依赖 token。
        print("ERROR: set HF_TOKEN env var (source ~/.openclaw/secrets/env.sh)")
        sys.exit(1)

    print("📥 loading pipeline (first run downloads ~100MB)...")
    # 这里加载的不是一个单独的 .bin 文件，而是一整套 diarization pipeline：
    # 包括语音活动检测、分段、embedding/聚类等组件。
    # 第一次运行会从 Hugging Face 下载到本机缓存目录，后面通常直接复用缓存。
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

    # Apple Silicon 上优先用 MPS/Metal 加速；不可用时 pyannote 会继续走 CPU。
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
    # 这些参数用于给聚类阶段提供先验。
    # 像采访场景如果明确知道就是 2 个人，`--num-speakers 2` 往往比自动检测更稳定。
    if args.num_speakers:
        kwargs["num_speakers"] = args.num_speakers
    if args.min_speakers:
        kwargs["min_speakers"] = args.min_speakers
    if args.max_speakers:
        kwargs["max_speakers"] = args.max_speakers

    print(f"🔊 running diarization... ({kwargs or 'auto detect'})")
    # 返回的是一个带时间轴的标注结果，而不是转录文本。
    # 这里的 speaker 标签只是聚类 ID，例如 SPEAKER_00 / SPEAKER_01，
    # 表示“同一个人说的话被归到一组”，不代表脚本知道这个人真实身份。
    # pyannote 4.x: pipeline() 返回 DiarizeOutput（dataclass），
    # 真正的 Annotation 对象在 .speaker_diarization 字段上；
    # pyannote 3.x: 直接返回 Annotation，有 .itertracks 方法。
    # 做个兼容兜底。
    result = pipeline(wav_path, **kwargs)
    if hasattr(result, "speaker_diarization"):
        annotation = result.speaker_diarization       # pyannote 4.x
    else:
        annotation = result                            # pyannote 3.x

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        # turn.start / turn.end 是秒级时间戳；round(2) 主要为了让输出更易读。
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
        })

    speaker_count = len({s["speaker"] for s in segments})
    # 这里统计的是所有分段时长之和；如果存在重叠说话，它可能大于音频总时长。
    total_dur = sum(s["end"] - s["start"] for s in segments)
    print(f"✅ {len(segments)} segments, {speaker_count} speakers, {total_dur:.0f}s total")

    with open(args.output, "w") as f:
        json.dump(segments, f, indent=2, ensure_ascii=False)
    print(f"💾 saved → {args.output}")

    # 临时 wav 只用于喂给 pyannote，写完结果后删除即可。
    os.unlink(wav_path)


if __name__ == "__main__":
    main()
