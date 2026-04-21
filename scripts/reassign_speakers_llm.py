#!/usr/bin/env python3
"""
reassign_speakers_llm.py — 用 LLM 根据对话内容重新分配说话人。

Azure diarize 模型每个 chunk 内部独立判断 A/B/C，跨 chunk 映射朴素地按字母
合并，导致主持人和嘉宾在不同 chunk 里可能被错标。

这个脚本读 dialog_en.json，让 Copilot GPT-5.4 根据英文内容判断每一段属于
主持人（HOST）还是嘉宾（GUEST），覆盖原来的 speaker 字段。

用法:
    python3 reassign_speakers_llm.py <dialog_en.json> [-o <out.json>]
                                     [--host-hint "Chris Hedges"]
                                     [--guest-hint "John Mearsheimer"]

策略:
  - 分段喂给 LLM（每次 30 轮左右，留上下文）
  - 第一次让 LLM 先确认谁是主持人谁是嘉宾（给前几段看）
  - 然后逐批标注，返回每轮的 HOST/GUEST
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def load_token() -> str:
    p = os.path.expanduser("~/.openclaw/credentials/github-copilot.token.json")
    return json.load(open(p))["token"]


MODEL = os.environ.get("REASSIGN_MODEL", "gpt-5.4")
ENDPOINT = "https://api.githubcopilot.com/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot-chat/0.20.0",
    "Copilot-Integration-Id": "vscode-chat",
    "User-Agent": "GitHubCopilotChat/0.20.0",
}


SYSTEM_PROMPT_TMPL = """你是一个播客对话分析师。

语境：这是一档播客访谈节目，{host_desc} 是主持人，{guest_desc} 是嘉宾。

任务：给你一段英文对话（每轮带 idx 编号和英文文本），你要判断每一轮是主持人（HOST）说的还是嘉宾（GUEST）说的。

判断线索：
- HOST 通常：提问、承接对方话、介绍话题、做总结、欢迎观众、打广告
- GUEST 通常：长段分析、回答问题、阐述观点、引经据典
- 问句（以 Do you / What / Why / How 开头）多是 HOST
- 第一人称长段独白多是 GUEST

输出：只输出 JSON 数组，每个元素 {{"idx": 整数, "who": "HOST" 或 "GUEST"}}。不要解释，不要 markdown。数组长度必须和输入一致。
"""


def call_llm(token: str, system_prompt: str, user_content: str, retries: int = 3) -> str:
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
        except urllib.error.HTTPError as e:
            last_err = e
            msg = e.read().decode("utf-8", errors="ignore")[:300]
            print(f"  ⚠️  HTTP {e.code} attempt {attempt+1}: {msg}", file=sys.stderr)
        except Exception as e:
            last_err = e
            print(f"  ⚠️  err attempt {attempt+1}: {e}", file=sys.stderr)
    raise last_err


def parse_json_out(s: str):
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`").lstrip("json").strip()
    # 找第一个 [ 到最后一个 ]
    lo, hi = s.find("["), s.rfind("]")
    if lo >= 0 and hi > lo:
        s = s[lo:hi+1]
    return json.loads(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="dialog_en.json")
    ap.add_argument("-o", "--output", help="默认覆写输入文件")
    ap.add_argument("--host-hint", default="主持人", help="主持人描述（可选），如 'Chris Hedges'")
    ap.add_argument("--guest-hint", default="嘉宾", help="嘉宾描述（可选），如 'John Mearsheimer'")
    ap.add_argument("--batch-size", type=int, default=30)
    ap.add_argument("--host-speaker", default="Host", help="输出中主持人的 speaker 名")
    ap.add_argument("--guest-speaker", default="Guest", help="输出中嘉宾的 speaker 名")
    args = ap.parse_args()

    in_path = args.input
    out_path = args.output or in_path
    token = load_token()

    dialog = json.load(open(in_path))
    n = len(dialog)
    print(f"📚 {n} 轮对话，batch_size={args.batch_size}", flush=True)

    system_prompt = SYSTEM_PROMPT_TMPL.format(
        host_desc=args.host_hint, guest_desc=args.guest_hint,
    )

    assignments = {}  # idx -> "HOST" / "GUEST"
    i = 0
    batch_num = 0
    total_batches = (n + args.batch_size - 1) // args.batch_size
    while i < n:
        batch_num += 1
        chunk = dialog[i:i + args.batch_size]
        payload = [{"idx": i + j, "text": t["text"]} for j, t in enumerate(chunk)]
        user = json.dumps(payload, ensure_ascii=False)
        print(f"📤 batch {batch_num}/{total_batches} idx {i}-{i+len(chunk)-1}", flush=True)

        raw = call_llm(token, system_prompt, user)
        try:
            out = parse_json_out(raw)
        except Exception as e:
            print(f"  ❌ parse failed: {e}\n   raw: {raw[:200]}", file=sys.stderr)
            # 全标 GUEST 兜底
            for item in payload:
                assignments[item["idx"]] = "GUEST"
            i += args.batch_size
            continue

        for item in out:
            idx = int(item.get("idx", -1))
            who = str(item.get("who", "GUEST")).upper()
            if who not in ("HOST", "GUEST"):
                who = "GUEST"
            assignments[idx] = who

        # 缺失的补兜底
        for item in payload:
            if item["idx"] not in assignments:
                assignments[item["idx"]] = "GUEST"

        done = sum(1 for idx in assignments if idx < i + len(chunk))
        print(f"  ✅ {done}/{n} assigned", flush=True)

        i += args.batch_size

    # 统计
    host_n = sum(1 for v in assignments.values() if v == "HOST")
    guest_n = sum(1 for v in assignments.values() if v == "GUEST")
    print(f"\n📊 HOST: {host_n} 轮, GUEST: {guest_n} 轮", flush=True)

    # 重写 dialog
    out = []
    for idx, turn in enumerate(dialog):
        who = assignments.get(idx, "GUEST")
        new = dict(turn)
        new["speaker"] = args.host_speaker if who == "HOST" else args.guest_speaker
        out.append(new)

    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=2)
    print(f"✅ wrote → {out_path}", flush=True)


if __name__ == "__main__":
    main()
