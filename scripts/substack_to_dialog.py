#!/usr/bin/env python3
"""substack_to_dialog.py — Convert Substack transcription.json → dialog_en.json + dialog_en.unmerged.json

Reads transcript/substack_transcription.json (with SPEAKER_00/01/02... labels)
Writes:
  transcript/dialog_en.unmerged.json  — segments, speaker mapped to real names
  transcript/dialog_en.json           — consecutive same-speaker turns merged

Usage:
  python3 scripts/substack_to_dialog.py <project_dir> \
      --map SPEAKER_00=Gergely SPEAKER_01=Gergely SPEAKER_02=Dax
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--map", nargs="+", required=True,
                    help="SPEAKER_XX=Name pairs (e.g. SPEAKER_00=Gergely SPEAKER_01=Dax)")
    ap.add_argument("--max-merge-gap", type=float, default=2.0,
                    help="If consecutive same-speaker turns have gap > this (s), keep them as separate turns")
    args = ap.parse_args()

    proj = Path(args.project)
    src = proj / "transcript" / "substack_transcription.json"
    if not src.exists():
        sys.exit(f"❌ missing {src}")

    speaker_map = {}
    for pair in args.map:
        k, v = pair.split("=", 1)
        speaker_map[k] = v

    with src.open() as f:
        segments = json.load(f)

    # Step 1: map raw SPEAKER_XX labels to real names. Drop segments with empty text.
    unmerged = []
    unknown = set()
    for seg in segments:
        raw_spk = seg.get("speaker")
        if raw_spk not in speaker_map:
            unknown.add(raw_spk)
            continue
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        unmerged.append({
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "speaker": speaker_map[raw_spk],
            "text": text,
        })

    if unknown:
        print(f"⚠️  unmapped speakers (skipped): {sorted(unknown)}", file=sys.stderr)

    print(f"✓ {len(segments)} substack segments → {len(unmerged)} mapped turns", file=sys.stderr)

    # Step 2: merge consecutive same-speaker turns
    merged = []
    for seg in unmerged:
        if merged and merged[-1]["speaker"] == seg["speaker"] \
                and seg["start"] - merged[-1]["end"] <= args.max_merge_gap:
            merged[-1]["end"] = seg["end"]
            merged[-1]["text"] = merged[-1]["text"].rstrip() + " " + seg["text"].lstrip()
        else:
            merged.append(dict(seg))

    print(f"✓ merged → {len(merged)} turns", file=sys.stderr)

    out_unmerged = proj / "transcript" / "dialog_en.unmerged.json"
    out_merged = proj / "transcript" / "dialog_en.json"
    with out_unmerged.open("w") as f:
        json.dump(unmerged, f, ensure_ascii=False, indent=2)
    with out_merged.open("w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✓ wrote {out_unmerged.name} and {out_merged.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
