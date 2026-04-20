#!/usr/bin/env python3
"""
translate_dialog_copilot.py — 用 GitHub Copilot 代理的 GPT-5.4 翻译对话

复用 translate_dialog.py 的大部分逻辑，只是换 provider。
Copilot 走公司 license，不花钱。
"""
import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path


def load_token() -> str:
    p = os.path.expanduser("~/.openclaw/credentials/github-copilot.token.json")
    return json.load(open(p))["token"]


MODEL = os.environ.get("TRANSLATE_MODEL", "gpt-5.4")
ENDPOINT = "https://api.githubcopilot.com/chat/completions"

# Copilot 请求需要这些头假装自己是 VSCode 插件
COPILOT_HEADERS = {
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot-chat/0.20.0",
    "Copilot-Integration-Id": "vscode-chat",
    "User-Agent": "GitHubCopilotChat/0.20.0",
}

SYSTEM_PROMPT = """你是一个专业的播客字幕翻译。

输入：一段 JSON 数组，每个元素形如 {"start":..., "end":..., "speaker":"...", "text":"英文原文"}

任务：把每个元素的 text 翻译成地道、自然的简体中文，保持：
- start / end / speaker 字段原样不动
- 数组元素顺序和数量完全一致
- 不要合并、不要拆分、不要省略
- 口语化但不失准确，人名/品牌保持英文（如 Ethan, Amazon, VP, AWS）
- 专业术语给准确译法（promotion = 晋升，manager = 经理，headcount = 人头数/编制）

输出：只输出翻译后的 JSON 数组，不要 markdown 代码块，不要解释。
注意：text 字段里不允许出现裸换行符和制表符（如需换行写为 \\n）。
"""


def call_llm(token: str, user_content: str, retries: int = 3) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
    }, ensure_ascii=False).encode("utf-8")

    headers = dict(COPILOT_HEADERS)
    headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(ENDPOINT, data=body, headers=headers)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")[:400]
            last_err = f"HTTP {e.code}: {body_err}"
            # 401 → token 过期，重新加载
            if e.code == 401:
                try:
                    token = load_token()
                    headers["Authorization"] = f"Bearer {token}"
                    req = urllib.request.Request(ENDPOINT, data=body, headers=headers)
                    print("  🔄 token 过期，已重载", flush=True)
                except Exception:
                    pass
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        print(f"  ⚠️ attempt {attempt} failed: {last_err}", flush=True)
        time.sleep(3 * attempt)
    raise RuntimeError(f"LLM 调用失败 {retries} 次: {last_err}")


def parse_json_out(text: str):
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = [l for l in lines if not l.startswith("```")]
        t = "\n".join(lines).strip()
    return json.loads(t, strict=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--batch-size", type=int, default=8)
    args = ap.parse_args()

    token = load_token()
    dialog = json.load(open(args.input))
    print(f"📚 {len(dialog)} turns → translate in batches of {args.batch_size}", flush=True)
    print(f"🤖 model: {MODEL} (via GitHub Copilot)", flush=True)

    out_path = Path(args.output)
    translated = []
    if out_path.exists():
        try:
            translated = json.load(open(out_path))
            print(f"♻️  resume: {len(translated)} turns already translated", flush=True)
        except Exception:
            translated = []

    start_idx = len(translated)
    total_batches = (len(dialog) - start_idx + args.batch_size - 1) // args.batch_size

    batch_no = 0
    i = start_idx
    while i < len(dialog):
        batch_no += 1
        chunk = dialog[i : i + args.batch_size]
        user = json.dumps(chunk, ensure_ascii=False)
        print(f"📤 batch {batch_no}/{total_batches}  turns {i}-{i+len(chunk)-1}", flush=True)

        out_text = call_llm(token, user)
        try:
            zh = parse_json_out(out_text)
        except Exception as e:
            print(f"  ❌ 解析失败: {e}\n  原文前 200 字: {out_text[:200]}", flush=True)
            raise

        if not isinstance(zh, list) or len(zh) != len(chunk):
            got = len(zh) if isinstance(zh, list) else "?"
            print(f"  ⚠️ 条数不一致: 输入 {len(chunk)} 输出 {got}，回折单条模式", flush=True)
            zh = []
            for one in chunk:
                one_text = call_llm(token, json.dumps([one], ensure_ascii=False))
                try:
                    one_zh = parse_json_out(one_text)
                    if isinstance(one_zh, list) and len(one_zh) == 1:
                        zh.append(one_zh[0])
                        continue
                    if isinstance(one_zh, dict) and "text" in one_zh:
                        zh.append(one_zh)
                        continue
                except Exception:
                    pass
                print(f"  ❌ 单条仍失败，留空 turn start={one['start']}", flush=True)
                zh.append({"text": ""})

        for src, dst in zip(chunk, zh):
            translated.append({
                "start": src["start"],
                "end": src["end"],
                "speaker": src["speaker"],
                "text_en": src["text"],
                "text": dst.get("text", "").strip(),
            })

        json.dump(translated, open(out_path, "w"), ensure_ascii=False, indent=2)
        print(f"  ✅ saved ({len(translated)}/{len(dialog)})", flush=True)
        i += args.batch_size

    print(f"🎉 done → {out_path}", flush=True)


if __name__ == "__main__":
    main()
