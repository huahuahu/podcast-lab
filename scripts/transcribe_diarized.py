#!/usr/bin/env python3
"""
transcribe_diarized.py — 合并 whisper 转录和 pyannote 说话人分段

输入：
    --audio <音频>
    --transcript <whisper 输出的带时间戳 JSON>（如果没有会自动用 whisper-cli 生成）
    --segments <diarize.py 输出的说话人分段 JSON>

输出：
    对齐后的对话 JSON
    [{"speaker": "SPEAKER_00", "start": 0.0, "end": 4.2, "text": "..."}]

用法：
    python3 transcribe_diarized.py --audio in.mp3 --segments seg.json -o dialog.json
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


WHISPER_CLI = os.environ.get("WHISPER_CLI", "/opt/homebrew/bin/whisper-cli")
WHISPER_MODEL = os.environ.get(
    "WHISPER_MODEL",
    os.path.expanduser("~/.openclaw/models/whisper/ggml-large-v3-turbo1.bin"),
)


def run_whisper(audio: str, lang: str = "auto") -> list:
    """Run whisper-cli with word-level timestamps, return list of {start,end,text}."""
    print(f"🎙 transcribing with whisper ({lang})...")

    # Convert to wav first for consistent input
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-i", audio, "-ar", "16000", "-ac", "1", "-y", wav],
                   check=True, capture_output=True)

    # whisper-cli with SRT output for timestamps
    srt_out = tempfile.NamedTemporaryFile(suffix=".srt", delete=False).name
    json_out = srt_out + ".json"
    subprocess.run([
        WHISPER_CLI,
        "-m", WHISPER_MODEL,
        "-f", wav,
        "-l", lang,
        "-oj",   # output JSON
        "-of", srt_out.replace(".srt", ""),
        "-np",
    ], check=True)

    # whisper-cli -oj outputs <base>.json
    with open(json_out) as f:
        data = json.load(f)

    segments = []
    for seg in data.get("transcription", []):
        # offsets in ms
        start_ms = seg["offsets"]["from"]
        end_ms = seg["offsets"]["to"]
        segments.append({
            "start": start_ms / 1000.0,
            "end": end_ms / 1000.0,
            "text": seg["text"].strip(),
        })

    os.unlink(wav)
    os.unlink(json_out)
    print(f"   → {len(segments)} transcript segments")
    return segments


def assign_speakers(transcript_segs: list, diarization_segs: list) -> list:
    """For each transcript segment, assign the speaker with most time overlap."""
    out = []
    for t in transcript_segs:
        best_speaker = None
        best_overlap = 0
        for d in diarization_segs:
            overlap = max(0, min(t["end"], d["end"]) - max(t["start"], d["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d["speaker"]
        out.append({
            "start": round(t["start"], 2),
            "end": round(t["end"], 2),
            "speaker": best_speaker or "UNKNOWN",
            "text": t["text"],
        })
    return out


def merge_adjacent(segs: list) -> list:
    """Merge consecutive segments from the same speaker."""
    if not segs:
        return []
    out = [dict(segs[0])]
    for s in segs[1:]:
        if s["speaker"] == out[-1]["speaker"]:
            out[-1]["end"] = s["end"]
            out[-1]["text"] += " " + s["text"]
        else:
            out.append(dict(s))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--segments", required=True, help="diarize.py output")
    ap.add_argument("--transcript", help="optional: pre-computed whisper JSON")
    ap.add_argument("-o", "--output", default="dialog.json")
    ap.add_argument("--lang", default="auto")
    args = ap.parse_args()

    with open(args.segments) as f:
        diarization = json.load(f)

    if args.transcript:
        with open(args.transcript) as f:
            transcript = json.load(f)
    else:
        transcript = run_whisper(args.audio, lang=args.lang)

    print(f"🔗 aligning {len(transcript)} transcript segs with {len(diarization)} speaker segs...")
    aligned = assign_speakers(transcript, diarization)
    merged = merge_adjacent(aligned)
    print(f"✅ {len(merged)} merged dialog turns")

    with open(args.output, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"💾 saved → {args.output}")

    # Preview
    speakers = {}
    for t in merged:
        speakers.setdefault(t["speaker"], 0)
        speakers[t["speaker"]] += 1
    print(f"📊 speakers: {speakers}")


if __name__ == "__main__":
    main()
