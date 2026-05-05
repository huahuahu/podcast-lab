#!/usr/bin/env python3
"""Reassign Host/Guest using the official Dwarkesh Substack transcript.

This script REBUILDS the dialog_en.json segments to align with the official
speaker turns, by:

1. Reading the YouTube VTT (audio.en.vtt) which gives cue-level timestamps
   (~5-7 seconds per cue).
2. Concatenating cue text into one big stream of tokens, each tagged with
   the cue's (start, end) times. This gives us pseudo word-level timestamps
   (interpolated within the cue duration).
3. Concatenating the official transcript into a stream of words tagged with
   speaker. Aligning the two streams using a two-pointer greedy match
   (skip-tolerant) — both streams contain mostly the same words in the same
   order.
4. From the alignment, for each official speaker turn, compute its start
   and end time (min of YouTube timestamps for matched words, max).
5. Output a new dialog_en.json with one segment per official turn:
   speaker (Host/Guest), text (from official, cleaned), start, end.

This guarantees speaker boundaries match the official transcript exactly,
and timestamps are reasonably accurate (within a couple seconds at turn
boundaries).
"""
from __future__ import annotations
import json, re, pathlib, shutil, sys

ROOT = pathlib.Path('projects/dwarkesh-jensen-huang-2026')
OFFICIAL = ROOT / 'transcript' / 'dialog_en.official.json'
VTT = ROOT / 'source' / 'audio.en.vtt'
DIALOG_OUT = ROOT / 'transcript' / 'dialog_en.json'
BACKUP = ROOT / 'transcript' / 'dialog_en.llm_reassigned.bak.json'

NORM_RE = re.compile(r"[^a-z0-9 ]+")
def norm_words(s: str) -> list[str]:
    s = s.replace('\u00a0', ' ').replace('&nbsp;', ' ')
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = s.lower()
    s = NORM_RE.sub(' ', s)
    return s.split()


def parse_vtt(text: str):
    """Return list of (start_sec, end_sec, words[]) for each cue."""
    def t2s(t):
        h, m, s = t.split(':')
        return int(h)*3600 + int(m)*60 + float(s)
    cues = []
    blocks = re.split(r'\n\s*\n', text.strip())
    for b in blocks:
        m = re.search(r'(\d\d:\d\d:\d\d\.\d{3})\s*-->\s*(\d\d:\d\d:\d\d\.\d{3})', b)
        if not m: continue
        start = t2s(m.group(1)); end = t2s(m.group(2))
        # remaining lines after the timing line are the text
        lines = b.split('\n')
        text_lines = []
        seen_timing = False
        for l in lines:
            if not seen_timing:
                if '-->' in l: seen_timing = True
                continue
            text_lines.append(l)
        cue_text = ' '.join(text_lines)
        words = norm_words(cue_text)
        if words:
            cues.append((start, end, words))
    return cues


def build_word_stream(cues):
    """Expand cues into per-word (timestamp_start, timestamp_end, word) by
    linearly interpolating positions inside each cue."""
    stream = []
    for st, en, ws in cues:
        if not ws: continue
        n = len(ws)
        dur = en - st
        for i, w in enumerate(ws):
            t_start = st + (dur * i) / n
            t_end = st + (dur * (i + 1)) / n
            stream.append((t_start, t_end, w))
    return stream


def build_official_stream(official):
    """Return list of (turn_idx, speaker, word) and turns metadata."""
    stream = []
    turns_meta = []
    for i, t in enumerate(official):
        ws = norm_words(t['text'])
        for w in ws:
            stream.append((i, t['speaker'], w))
        turns_meta.append({'idx': i, 'speaker': t['speaker'], 'name': t.get('name'), 'text': t['text'], 'len': len(ws)})
    return stream, turns_meta


def align_two_streams(yt_words, off_words):
    """Align two word lists. Returns list of (yt_idx, off_idx) for matches.

    Strategy: greedy two-pointer with broad skip tolerance. We look for a
    n-gram (n>=3 preferred, fall back to 2 then 1) that anchors both
    streams, with windows large enough to cross sponsor breaks, missing
    paragraphs etc.
    """
    matches = []
    i = j = 0
    n = len(yt_words); m = len(off_words)
    while i < n and j < m:
        if yt_words[i] == off_words[j]:
            matches.append((i, j)); i += 1; j += 1
            continue
        # Try anchors of decreasing strength.
        anchor = None
        for ngram in (4, 3, 2, 1):
            for win_off, win_yt in ((400, 80), (1500, 200), (3000, 600)):
                if anchor: break
                best = None
                for di in range(win_yt):
                    if i + di + ngram > n: break
                    if yt_words[i+di] != yt_words[i+di]: pass  # noop
                    # Try to find this ngram starting at j..j+win_off
                    needle = yt_words[i+di:i+di+ngram]
                    if any(w == '' for w in needle): continue
                    for dj in range(win_off):
                        if j + dj + ngram > m: break
                        if off_words[j+dj:j+dj+ngram] == needle:
                            cost = di * 2 + dj  # bias toward small yt skip
                            if best is None or cost < best[0]:
                                best = (cost, di, dj)
                            break
                if best:
                    anchor = best
            if anchor: break
        if not anchor:
            # Could not find any anchor — advance off side (more likely to have extra words like link anchors)
            j += 1
            # Safety stop
            if j - matches[-1][1] > 5000 if matches else j > 5000:
                break
            continue
        _, di, dj = anchor
        i += di; j += dj
        # loop will emit the match next iteration
    return matches


def main():
    official = json.loads(OFFICIAL.read_text())
    cues = parse_vtt(VTT.read_text())
    print(f'VTT cues: {len(cues)}')
    yt_stream = build_word_stream(cues)
    off_stream, turns_meta = build_official_stream(official)
    print(f'YT words: {len(yt_stream)}, Official words: {len(off_stream)}')

    yt_words = [w for _,_,w in yt_stream]
    off_words = [w for _,_,w in off_stream]

    matches = align_two_streams(yt_words, off_words)
    print(f'Matched word pairs: {len(matches)}  (coverage YT={len(matches)/len(yt_words):.1%}, Off={len(matches)/len(off_words):.1%})')

    # For each official turn, gather YT timestamps of matched words
    turn_times = [[] for _ in turns_meta]
    for yi, oi in matches:
        ti = off_stream[oi][0]
        turn_times[ti].append(yt_stream[yi][0])  # use start time

    # Build new dialog segments: one per official turn
    new_dialog = []
    audio_max_end = max(t[1] for t in cues)
    prev_end = 0.0
    for i, meta in enumerate(turns_meta):
        ts = turn_times[i]
        if ts:
            start = min(ts)
            # end = max of times for THIS turn or start of next non-empty turn
            end = max(ts)
        else:
            # no matches — interpolate between prev and next
            start = prev_end
            end = prev_end
        new_dialog.append({
            'start': round(start, 3),
            'end': round(end, 3),
            'speaker': meta['speaker'],
            'text': meta['text'],
        })

    # Post-process: ensure monotonic non-decreasing start times and reasonable ends.
    # If a turn's start < prev turn's end, push it. Then set end = next.start (or audio_max_end for last).
    for i in range(len(new_dialog)):
        if i > 0 and new_dialog[i]['start'] < new_dialog[i-1]['start']:
            new_dialog[i]['start'] = new_dialog[i-1]['start']
    # Set end = next turn's start (or current end if larger). For last turn, use audio_max_end.
    for i in range(len(new_dialog)):
        if i + 1 < len(new_dialog):
            ns = new_dialog[i+1]['start']
            if new_dialog[i]['end'] < ns:
                new_dialog[i]['end'] = ns
            # If start >= end, fix
            if new_dialog[i]['end'] <= new_dialog[i]['start']:
                new_dialog[i]['end'] = max(new_dialog[i]['start'] + 1.0, ns)
        else:
            if new_dialog[i]['end'] < audio_max_end:
                new_dialog[i]['end'] = audio_max_end

    counts = {'Host':0,'Guest':0}
    for s in new_dialog:
        counts[s['speaker']] = counts.get(s['speaker'],0)+1
    print(f'\nNew distribution: {counts}')
    print(f'Total turns: {len(new_dialog)}')

    print('\nFirst 8 turns:')
    for s in new_dialog[:8]:
        print(f'  [{s["speaker"]:5s}] {s["start"]:7.2f}-{s["end"]:7.2f}  {s["text"][:90]}')
    print('\nLast 4 turns:')
    for s in new_dialog[-4:]:
        print(f'  [{s["speaker"]:5s}] {s["start"]:7.2f}-{s["end"]:7.2f}  {s["text"][:90]}')

    # Backup OLD dialog_en.json (LLM reassigned) — only once
    if not BACKUP.exists():
        shutil.copy(DIALOG_OUT, BACKUP)
        print(f'\nBackup created: {BACKUP}')
    else:
        print(f'\nBackup already exists at {BACKUP} (kept as is)')

    DIALOG_OUT.write_text(json.dumps(new_dialog, ensure_ascii=False, indent=2))
    print(f'Wrote {DIALOG_OUT} ({len(new_dialog)} turns)')


if __name__ == '__main__':
    main()
