#!/usr/bin/env python3
"""
align_speakers_multi.py — 多人播客 (>2 speakers) 跨 chunk speaker 对齐。

背景：Azure gpt-4o-transcribe-diarize 每个 chunk 独立 diarize，返回 A/B/C/...
跨 chunk 标签不连贯（chunk 1 的 A 不一定是 chunk 2 的 A）。

策略：读 series 配置里的 personas（人物画像），让 GPT 看每个 chunk 里每个
speaker 标签的代表性发言，把 A/B/C... 映射到全局人名（如 Chamath/Sacks/
Jason/Freeberg/Unknown），原地改写每个 chunk 的 segs.json，再让上游
_merge_chunks.py 合并。

用法：
    python3 align_speakers_multi.py <project_dir>

前提：
- <project_dir>/transcript/azure_chunks/chunk_*.segs.json 已生成
- configs/series.json 里匹配到的系列配置 personas: {Name: 描述, ...}
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import _config  # noqa: E402


MODEL = os.environ.get("ALIGN_MODEL", "gpt-5.4")
ENDPOINT = "https://api.githubcopilot.com/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot-chat/0.20.0",
    "Copilot-Integration-Id": "vscode-chat",
    "User-Agent": "GitHubCopilotChat/0.20.0",
}

# 每个 speaker 在一个 chunk 里抽几段代表性发言喂给 LLM
SAMPLES_PER_SPEAKER = 6
SAMPLE_MIN_CHARS = 60
SAMPLE_MAX_CHARS = 400


def load_token() -> str:
    p = os.path.expanduser("~/.openclaw/credentials/github-copilot.token.json")
    return json.load(open(p))["token"]


def call_llm(token: str, system_prompt: str, user_content: str, retries: int = 4) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
    }, ensure_ascii=False).encode("utf-8")

    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                ENDPOINT, data=body,
                headers={**HEADERS, "Authorization": f"Bearer {token}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            print(f"  ⚠️  attempt {attempt+1} failed: {e}", file=sys.stderr)
    raise last_err


def parse_json_obj(s: str):
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\n", "", s)
        s = re.sub(r"\n```$", "", s)
    lo, hi = s.find("{"), s.rfind("}")
    if lo >= 0 and hi > lo:
        s = s[lo:hi+1]
    return json.loads(s)


def pick_samples(segs):
    """从一个 chunk 的 segs 里，按 speaker 分组，抽代表性发言。"""
    by_sp = defaultdict(list)
    for s in segs:
        text = (s.get("text") or "").strip()
        if SAMPLE_MIN_CHARS <= len(text) <= SAMPLE_MAX_CHARS:
            by_sp[s["speaker"]].append(text)

    # 没长发言的 speaker 放短的兜底
    for s in segs:
        sp = s["speaker"]
        if not by_sp[sp]:
            t = (s.get("text") or "").strip()
            if t:
                by_sp[sp].append(t[:SAMPLE_MAX_CHARS])

    samples = {}
    for sp, lst in by_sp.items():
        # 取从头到尾均匀分布的 SAMPLES_PER_SPEAKER 条
        if len(lst) <= SAMPLES_PER_SPEAKER:
            samples[sp] = lst
        else:
            step = len(lst) / SAMPLES_PER_SPEAKER
            samples[sp] = [lst[int(i * step)] for i in range(SAMPLES_PER_SPEAKER)]
    return samples


def build_prompt(personas: dict, chunk_idx: int, samples: dict) -> tuple[str, str]:
    persona_block = "\n".join(f"- {name}: {desc}" for name, desc in personas.items())
    names_csv = ", ".join(personas.keys())

    sys_prompt = f"""你是一个播客对话分析师。

人物档案：
{persona_block}

任务：下面给你一个 chunk 里若干 speaker（用 A/B/C/... 标记，仅在本 chunk
内有效）的代表性英文发言，请根据他们的话题、用词、立场把每个标签映射到上面
的人名（{names_csv}）。无法判断时填 "Unknown"。

输出：只输出一个 JSON 对象 {{"A": "Sacks", "B": "Jason", ...}}。不要解释，
不要 markdown。每个标签必须出现一次，值必须是上面列出的人名之一或 "Unknown"。
"""
    parts = [f"# chunk {chunk_idx}\n"]
    for sp in sorted(samples.keys()):
        parts.append(f"\n## Speaker {sp}\n")
        for t in samples[sp]:
            parts.append(f"- {t}\n")
    return sys_prompt, "".join(parts)


def align_chunk(token: str, personas: dict, chunk_idx: int, segs_path: str):
    segs = json.load(open(segs_path))
    samples = pick_samples(segs)
    if not samples:
        print(f"  ⏭  chunk {chunk_idx}: 无可用样本，跳过")
        return None

    sys_p, user_p = build_prompt(personas, chunk_idx, samples)
    raw = call_llm(token, sys_p, user_p)
    try:
        mapping = parse_json_obj(raw)
    except Exception as e:
        print(f"  ❌ chunk {chunk_idx} 解析失败: {e}\n  原始: {raw[:200]}", file=sys.stderr)
        return None

    valid = set(personas.keys()) | {"Unknown"}
    fixed = {}
    for sp in samples.keys():
        v = mapping.get(sp, "Unknown")
        if v not in valid:
            v = "Unknown"
        fixed[sp] = v
    print(f"  🔗 chunk {chunk_idx}: {fixed}")
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印映射，不改写 segs.json")
    args = ap.parse_args()

    proj = os.path.abspath(args.project_dir)
    cfg = _config.resolve(proj)
    personas = cfg.get("personas") or {}
    if not personas:
        print("❌ 没有 personas 配置（configs/series.json）。退出。", file=sys.stderr)
        sys.exit(2)

    chunk_dir = os.path.join(proj, "transcript", "azure_chunks")
    files = sorted(f for f in os.listdir(chunk_dir) if f.endswith(".segs.json"))
    if not files:
        print(f"❌ 没找到 segs.json: {chunk_dir}", file=sys.stderr)
        sys.exit(2)

    print(f"📚 personas: {list(personas.keys())}")
    print(f"📦 {len(files)} 个 chunk 待对齐")

    token = load_token()
    state_path = os.path.join(proj, "transcript", ".speakers-aligned.json")
    state = {}
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path))
        except Exception:
            state = {}

    for fname in files:
        m = re.search(r"chunk_(\d+)\.segs\.json", fname)
        if not m:
            continue
        idx = int(m.group(1))
        segs_path = os.path.join(chunk_dir, fname)

        if fname in state:
            print(f"  ✓ chunk {idx}: 已对齐 → {state[fname]}")
            mapping = state[fname]
        else:
            mapping = align_chunk(token, personas, idx, segs_path)
            if mapping is None:
                continue
            state[fname] = mapping
            with open(state_path, "w") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

        if args.dry_run:
            continue

        # 改写 segs.json：把 A/B/C 替换为人名
        segs = json.load(open(segs_path))
        backup = segs_path + ".pre-align.json"
        if not os.path.exists(backup):
            with open(backup, "w") as f:
                json.dump(segs, f, ensure_ascii=False, indent=2)
        for s in segs:
            sp = s.get("speaker")
            if sp in mapping:
                s["speaker"] = mapping[sp]
        with open(segs_path, "w") as f:
            json.dump(segs, f, ensure_ascii=False, indent=2)

    print("\n✅ 对齐完成。下一步重跑 _merge_chunks.py 生成 dialog_en.json。")


if __name__ == "__main__":
    main()
