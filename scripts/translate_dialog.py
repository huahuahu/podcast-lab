#!/usr/bin/env python3
"""
translate_dialog.py — 把 dialog_en.json 分段翻译成中文

策略：
  - 分 batch（每 batch 12 轮），避免 LLM 输出超长失败
  - 通过 SiliconFlow 的 chat completions 调一个便宜的中文强模型（Qwen3 系列）
  - 每 batch 输入 JSON, 要求 LLM 原样返回同结构 JSON 但 text 换中文
  - 校验：返回条数必须和输入一致；不一致 → 重试；3 次失败 → 退出
  - 断点续传：以 batch 为单位写盘，已完成的 batch 跳过

用法：
    python3 translate_dialog.py <input.json> <output.json> [--batch-size 12]
"""
import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path


def load_api_key() -> str:
    secrets = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
    return secrets["providers"]["siliconflow"]["apiKey"]


# 用 Qwen3 系列，中文强 & 便宜
# SiliconFlow 的可选：Qwen/Qwen2.5-72B-Instruct、deepseek-ai/DeepSeek-V2.5 等
MODEL = os.environ.get("TRANSLATE_MODEL", "Qwen/Qwen2.5-72B-Instruct")
ENDPOINT = "https://api.siliconflow.cn/v1/chat/completions"

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


def call_llm(api_key: str, user_content: str, retries: int = 3) -> str:
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": 8000,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")[:400]
            last_err = f"HTTP {e.code}: {body_err}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        print(f"  ⚠️ attempt {attempt} failed: {last_err}", flush=True)
        time.sleep(3 * attempt)
    raise RuntimeError(f"LLM 调用失败 3 次: {last_err}")


def parse_json_out(text: str):
    """兼容 LLM 偶尔吐 markdown 代码块和 text 里夹裸换行的情况"""
    t = text.strip()
    if t.startswith("```"):
        # 剥掉 ```json ... ```
        lines = t.splitlines()
        lines = [l for l in lines if not l.startswith("```")]
        t = "\n".join(lines).strip()
    # strict=False 允许字符串内的裸换行/制表符等控制字符
    return json.loads(t, strict=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--batch-size", type=int, default=12)
    args = ap.parse_args()

    api_key = load_api_key()
    dialog = json.load(open(args.input))
    print(f"📚 {len(dialog)} turns → translate in batches of {args.batch_size}", flush=True)
    print(f"🤖 model: {MODEL}", flush=True)

    # 断点续传：读已有输出
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

        out_text = call_llm(api_key, user)
        try:
            zh = parse_json_out(out_text)
        except Exception as e:
            print(f"  ❌ 解析失败: {e}\n  原文前 200 字: {out_text[:200]}", flush=True)
            raise

        if not isinstance(zh, list) or len(zh) != len(chunk):
            got = len(zh) if isinstance(zh, list) else "?"
            print(f"  ⚠️ 返回条数不一致：输入 {len(chunk)}，输出 {got}，回折到单条模式", flush=True)
            zh = []
            for one in chunk:
                one_text = call_llm(api_key, json.dumps([one], ensure_ascii=False))
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
                # 最后保底：失败就留空中文，保持英文，后续手动补
                print(f"  ❌ 单条仍失败。保留空译文，turn start={one['start']}", flush=True)
                zh.append({"text": ""})
            if len(zh) != len(chunk):
                raise RuntimeError(f"单条回折后仍不匹配: {len(zh)} vs {len(chunk)}")
        # 保留时间戳/speaker，只用 LLM 返回的 text 
        for src, dst in zip(chunk, zh):
            translated.append({
                "start": src["start"],
                "end": src["end"],
                "speaker": src["speaker"],
                "text_en": src["text"],
                "text": dst.get("text", "").strip(),
            })

        # 每个 batch 落盘（断点续传）
        json.dump(translated, open(out_path, "w"), ensure_ascii=False, indent=2)
        print(f"  ✅ saved ({len(translated)}/{len(dialog)})", flush=True)
        i += args.batch_size

    print(f"🎉 done → {out_path}", flush=True)


if __name__ == "__main__":
    main()
