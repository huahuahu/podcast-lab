#!/usr/bin/env python3
"""给 podcast_zh.mp3 写 ID3 chapters。

用法：
    add_chapters.py <project_dir> [--rules sse|generic|...]

读取：
- <proj>/audio/podcast_zh.mp3
- <proj>/transcript/timings.json   （multivoice_robust.py --timings 输出）
- <proj>/transcript/dialog_zh.json （speaker + 文本）
- <proj>/meta.json                 （可选，里面 chapters.rules 指定规则集）

规则集：
- sse  : Soft Skills Engineering 专用，按"读问题/下一个问题/Question N"分章
- generic: 简单按 5 分钟切（兜底）

输出：
- 原 mp3 备份成 podcast_zh.nochapters.bak.mp3
- 重写带 chapters 的 mp3（ffmpeg ffmetadata）
- <proj>/transcript/chapters.json （审阅用）
"""
import argparse, json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config

def detect_sse(timings, dialog):
    """SSE 专用：找 Q1/Q2 信件正文起点。

    节目里主持人常玩双关调侃（比如 “你应该读下一个问题”），所以：
    1. 以 LEAD（“读...问题/要我来读”等）为入口
    2. 从 LEAD 后一段开始，跳过所有“继续玩棗/双关”的段（仍含 LEAD 关键词或太短）
    3. 落在第一段不含 LEAD、且长度 ≥ 60 的“信件正文”上
    """
    LEAD = re.compile(r"(读.*?(下一个|第一个|另一个).*?问题|来读.*问题|要不要.*读|我希望由你来读|我希望你来读|想让你读|要我来读)")
    LETTER = re.compile(r"(亲爱的\s*(SSE|Soft Skills|主持人|Dave|Jameson|两位)|Dear\s+SSE)")
    n = len(timings)

    raw_starts = []  # 信件正文 idx
    i = 0
    while i < n:
        text = timings[i]["text"]
        if LEAD.search(text):
            # 从 i+1 开始找“信件正文”
            j = i + 1
            while j < n:
                tj = timings[j]["text"]
                if not LEAD.search(tj) and len(tj) >= 60:
                    raw_starts.append(j)
                    i = j  # 从正文位置继续扫，避免重复处理头的调侃
                    break
                j += 1
            else:
                i += 1
                continue
        elif LETTER.search(text) and len(text) >= 40:
            raw_starts.append(i)
        i += 1

    full = [{"title": "开场 / 广告", "start_ms": 0}]
    last_ms = -10_000
    for idx in raw_starts:
        ms = timings[idx]["start_ms"]
        if ms - last_ms < 30_000:  # 30s 去重
            continue
        full.append({"title": f"问题 {len(full)}", "start_ms": ms})
        last_ms = ms
    return full


def detect_generic(timings, total_ms, step_ms=5*60_000):
    """每 step_ms 一个章节。"""
    chapters = [{"title": "开场", "start_ms": 0}]
    t = step_ms
    n = 1
    while t < total_ms - 30_000:
        chapters.append({"title": f"第 {n+1} 段", "start_ms": t})
        n += 1
        t += step_ms
    return chapters


def build_ffmetadata(chapters, total_ms):
    out = [";FFMETADATA1"]
    for i, c in enumerate(chapters):
        start = c["start_ms"]
        end = chapters[i+1]["start_ms"] - 1 if i+1 < len(chapters) else total_ms
        out.append("[CHAPTER]")
        out.append("TIMEBASE=1/1000")
        out.append(f"START={start}")
        out.append(f"END={end}")
        out.append(f"title={c['title']}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--rules", default=None, help="sse | generic（默认从 meta.json 读，否则 sse 自动判定，否则 generic）")
    args = ap.parse_args()

    proj = os.path.abspath(args.project)
    mp3 = os.path.join(proj, "audio", "podcast_zh.mp3")
    timings_path = os.path.join(proj, "transcript", "timings.json")
    chapters_path = os.path.join(proj, "transcript", "chapters.json")
    bak = os.path.join(proj, "audio", "podcast_zh.nochapters.bak.mp3")

    if not os.path.exists(mp3) or not os.path.exists(timings_path):
        print(f"❌ 缺少 {mp3} 或 {timings_path}", file=sys.stderr)
        sys.exit(1)

    timings = json.load(open(timings_path))
    cfg = _config.resolve(proj)
    rules = args.rules or (cfg.get("chapters") or {}).get("rules")
    if cfg.get("_series") and not args.rules:
        print(f"📋 series cfg: {cfg['_series']}, rules={rules}")

    # 自动判定：slug 含 sse → sse 规则
    if rules is None:
        slug = os.path.basename(proj).lower()
        rules = "sse" if "sse-" in slug or slug.startswith("sse") else "generic"

    total_ms = timings[-1]["end_ms"] if timings else 0

    if rules == "sse":
        chapters = detect_sse(timings, None)
        if len(chapters) <= 1:
            print("⚠️  SSE 规则没找到问题标记，回退 generic")
            chapters = detect_generic(timings, total_ms)
    else:
        chapters = detect_generic(timings, total_ms)

    json.dump(chapters, open(chapters_path, "w"), ensure_ascii=False, indent=2)
    print(f"📑 {len(chapters)} chapters → {chapters_path}")
    for c in chapters:
        s = c["start_ms"] // 1000
        print(f"   [{s//60:02d}:{s%60:02d}] {c['title']}")

    ffmeta_text = build_ffmetadata(chapters, total_ms)
    ffmeta_path = os.path.join(proj, "transcript", "ffmetadata.txt")
    open(ffmeta_path, "w").write(ffmeta_text)

    if not os.path.exists(bak):
        shutil.copy(mp3, bak)
        print(f"💾 backup → {bak}")

    tmp_out = mp3 + ".chapters.mp3"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", bak,
        "-i", ffmeta_path,
        "-map_metadata", "1",
        "-codec", "copy",
        "-id3v2_version", "3",
        tmp_out,
    ], check=True, capture_output=True)
    shutil.move(tmp_out, mp3)
    size_mb = os.path.getsize(mp3) / 1024 / 1024
    print(f"✅ {mp3} ({size_mb:.1f} MB) with {len(chapters)} chapters")


if __name__ == "__main__":
    main()
