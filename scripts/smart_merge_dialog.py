#!/usr/bin/env python3
"""Smart-merge preprocessor for diarized dialog.

Runs after Host/Guest reassignment and before translation.

Two passes:
  1. Drop pure backchannel utterances (short social-glue tokens that don't
     contribute content), so they don't fragment the dialogue or waste TTS.
  2. Merge adjacent same-speaker short utterances split by Azure diarize.

Usage:
    python3 smart_merge_dialog.py <project_dir>
    python3 smart_merge_dialog.py <dialog_en.json>
    python3 smart_merge_dialog.py --dry-run <project_dir>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from typing import List, Dict, Any

BACKCHANNEL_WORDS = {
    "yeah", "yes", "no", "ok", "okay", "right", "sure",
    "mm-hmm", "mhm", "uh-huh", "oh", "ah", "wow",
    "great", "awesome", "exactly", "totally", "absolutely",
    "true", "nice", "cool", "hmm", "huh", "well", "so",
}

BACKCHANNEL_MAX_DURATION = 2.0    # seconds
BACKCHANNEL_MAX_WORDS = 4
MERGE_MAX_GAP = 2.0               # seconds between segments
MERGE_MAX_CHARS = 400             # char ceiling for merged text


def _normalize_token(tok: str) -> str:
    # strip surrounding punctuation, keep internal hyphens (mm-hmm, uh-huh)
    return re.sub(r"^[^\w-]+|[^\w-]+$", "", tok).lower()


def is_pure_backchannel(seg: Dict[str, Any]) -> bool:
    text = seg.get("text", "").strip()
    if not text:
        return True  # empty → drop
    duration = float(seg.get("end", 0)) - float(seg.get("start", 0))
    if duration >= BACKCHANNEL_MAX_DURATION:
        return False
    # tokenize on whitespace
    raw_tokens = text.split()
    if len(raw_tokens) > BACKCHANNEL_MAX_WORDS:
        return False
    norm_tokens = [_normalize_token(t) for t in raw_tokens]
    norm_tokens = [t for t in norm_tokens if t]  # drop pure-punctuation tokens
    if not norm_tokens:
        return True
    return all(t in BACKCHANNEL_WORDS for t in norm_tokens)


def drop_backchannel(segs: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    kept = []
    dropped = 0
    for s in segs:
        if is_pure_backchannel(s):
            dropped += 1
            continue
        kept.append(s)
    return kept, dropped


def merge_pass(segs: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    """One merging pass. Returns (new_segs, num_merges_done)."""
    if not segs:
        return segs, 0
    out = [dict(segs[0])]
    merges = 0
    for cur in segs[1:]:
        prev = out[-1]
        same_speaker = prev.get("speaker") == cur.get("speaker")
        gap = float(cur.get("start", 0)) - float(prev.get("end", 0))
        merged_text = (prev.get("text", "").rstrip() + " " + cur.get("text", "").lstrip()).strip()
        if (
            same_speaker
            and gap < MERGE_MAX_GAP
            and len(merged_text) <= MERGE_MAX_CHARS
        ):
            prev["text"] = merged_text
            prev["end"] = cur.get("end", prev.get("end"))
            merges += 1
        else:
            out.append(dict(cur))
    return out, merges


def smart_merge(segs: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], dict]:
    original_count = len(segs)
    kept, dropped = drop_backchannel(segs)
    after_drop = len(kept)

    # repeat merge pass until stable
    cur = kept
    total_merges = 0
    for _ in range(20):
        cur, m = merge_pass(cur)
        total_merges += m
        if m == 0:
            break

    stats = {
        "original": original_count,
        "dropped_backchannel": dropped,
        "after_drop": after_drop,
        "final": len(cur),
        "merges": total_merges,
    }
    return cur, stats


def resolve_dialog_path(arg: str) -> str:
    if os.path.isfile(arg):
        return arg
    if os.path.isdir(arg):
        candidate = os.path.join(arg, "transcript", "dialog_en.json")
        if os.path.isfile(candidate):
            return candidate
        candidate2 = os.path.join(arg, "dialog_en.json")
        if os.path.isfile(candidate2):
            return candidate2
    raise SystemExit(f"❌ cannot find dialog_en.json at {arg}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="project dir or dialog_en.json path")
    ap.add_argument("--dry-run", action="store_true",
                    help="don't overwrite; print stats and idx 130-145 diff")
    args = ap.parse_args()

    path = resolve_dialog_path(args.target)
    with open(path, "r", encoding="utf-8") as f:
        original = json.load(f)

    merged, stats = smart_merge(original)

    print(f"原始 utterances: {stats['original']}")
    print(f"丢弃 backchannel: {stats['dropped_backchannel']}")
    print(f"合并相邻同 speaker: {stats['after_drop']} → {stats['final']}")
    saved_pct = (
        100.0 * (stats["original"] - stats["final"]) / stats["original"]
        if stats["original"] else 0.0
    )
    print(f"最终输出: {stats['final']} utterances（节省 {saved_pct:.0f}%）")

    if args.dry_run:
        # show before/after for idx 130-145 region (best effort overlap by time)
        lo, hi = 130, 145
        print()
        print(f"=== BEFORE idx {lo}-{hi} ===")
        for i in range(lo, min(hi + 1, len(original))):
            s = original[i]
            print(f"{i:3d} [{s['start']:7.2f}-{s['end']:7.2f}] {s['speaker']:6s}: {s['text']}")

        if original and merged:
            t_lo = original[lo]["start"] if lo < len(original) else 0
            t_hi = original[min(hi, len(original)-1)]["end"]
            print()
            print(f"=== AFTER (segments overlapping {t_lo:.2f}-{t_hi:.2f}) ===")
            for j, s in enumerate(merged):
                if s["end"] < t_lo or s["start"] > t_hi:
                    continue
                print(f"{j:3d} [{s['start']:7.2f}-{s['end']:7.2f}] {s['speaker']:6s}: {s['text']}")
        return 0

    # backup + overwrite
    backup = path.replace("dialog_en.json", "dialog_en.unmerged.json")
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print(f"📦 backup: {backup}")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    print(f"✅ wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
