#!/usr/bin/env python3
"""Parse Azure diarize SSE stream into segments JSON, applying global time offset.

Usage: _parse_segs.py <sse_path> <offset_seconds>
Writes JSON to stdout.
"""
import json, sys

sse_path, offset = sys.argv[1], float(sys.argv[2])
segs = []
with open(sse_path) as f:
    for line in f:
        line = line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        try:
            evt = json.loads(payload)
        except Exception:
            continue
        if evt.get("type") != "transcript.text.segment":
            continue
        segs.append({
            "start": round(float(evt["start"]) + offset, 3),
            "end":   round(float(evt["end"])   + offset, 3),
            "speaker": evt.get("speaker") or "?",
            "text": (evt.get("text") or "").strip(),
        })
json.dump(segs, sys.stdout, ensure_ascii=False, indent=2)
