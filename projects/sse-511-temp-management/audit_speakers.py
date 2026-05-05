#!/usr/bin/env python3
"""SSE-511 临时脚本：让 Copilot GPT-5.4 二次审查 dialog_zh.json 的 speaker 划分。

策略：
- 给 LLM 一窗口（前后各 2 段 + 当前段），问当前段最可能是 Dave/Host 还是
  Jameson/Guest，让它返回 confidence 和理由。
- 用滑动窗口跑全部，挑出 LLM 判定与现有 speaker 不一致 + confidence 高的段。
- 输出 suspicious 列表到 audit_report.json，供人工审阅 / 直接修正。
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "transcript", "dialog_zh.json")
OUT = os.path.join(ROOT, "audit_report.json")

def token():
    return json.load(open(os.path.expanduser("~/.openclaw/credentials/github-copilot.token.json")))["token"]

ENDPOINT = "https://api.githubcopilot.com/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot-chat/0.20.0",
    "Copilot-Integration-Id": "vscode-chat",
    "User-Agent": "GitHubCopilotChat/0.20.0",
}

SYS = """你是一个播客对话分析师。这是 Soft Skills Engineering 第 511 期，
两位联合主持人：
- Dave Smith（标记为 HOST，开场说 "It takes more than..."、念赞助、读问题信件多由他主导）
- Jameson Dance（标记为 GUEST，常笑场、抛回应、做总结）

我会一次给你一个批次（约 20 段）的中文对话，每段带 idx 和当前 speaker 标注（HOST/GUEST）。
你逐段判断当前 speaker 标注是否合理，根据**与前后段的衔接、问答关系、笑点节奏**判断。

输出 JSON 数组，每段一个对象：
  {"idx": 整数, "current": "HOST"或"GUEST", "verdict": "OK" / "FLIP" / "UNSURE", "reason": "一句话"}

- OK = 当前标注合理
- FLIP = 当前标注大概率错了，应该是另一个人
- UNSURE = 凭文本无法判断（比如 "嗯" / "对" 这种短回应）

只输出 JSON 数组，不要解释。"""

def call(t, sys_p, usr):
    body = json.dumps({
        "model": "gpt-5.4",
        "messages": [{"role":"system","content":sys_p},{"role":"user","content":usr}],
        "temperature": 0.1,
    }, ensure_ascii=False).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(ENDPOINT, data=body,
                headers={**HEADERS, "Authorization": f"Bearer {t}"}, method="POST")
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  retry {attempt+1}: {e}", file=sys.stderr)
    raise RuntimeError("call failed")

def parse(s):
    s = s.strip().strip("`")
    if s.startswith("json"): s = s[4:].strip()
    lo, hi = s.find("["), s.rfind("]")
    return json.loads(s[lo:hi+1])

def main():
    d = json.load(open(SRC))
    t = token()
    BATCH = 20
    suspicious = []
    all_verdicts = []
    for i in range(0, len(d), BATCH):
        chunk = d[i:i+BATCH]
        payload = [{"idx": i+j, "speaker": ("HOST" if x["speaker"]=="Host" else "GUEST"), "text": x["text"]} for j,x in enumerate(chunk)]
        usr = json.dumps(payload, ensure_ascii=False)
        print(f"📤 batch {i//BATCH+1}/{(len(d)+BATCH-1)//BATCH}  idx {i}-{i+len(chunk)-1}", flush=True)
        raw = call(t, SYS, usr)
        try:
            verds = parse(raw)
        except Exception as e:
            print(f"  parse fail: {e}\n  raw: {raw[:200]}", file=sys.stderr)
            continue
        for v in verds:
            all_verdicts.append(v)
            if v.get("verdict") == "FLIP":
                idx = v["idx"]
                suspicious.append({
                    "idx": idx, "current": v["current"],
                    "reason": v.get("reason",""),
                    "text": d[idx]["text"],
                    "prev": d[idx-1]["text"] if idx > 0 else "",
                    "next": d[idx+1]["text"] if idx+1 < len(d) else "",
                })
    n_ok = sum(1 for v in all_verdicts if v.get("verdict")=="OK")
    n_flip = sum(1 for v in all_verdicts if v.get("verdict")=="FLIP")
    n_unsure = sum(1 for v in all_verdicts if v.get("verdict")=="UNSURE")
    print(f"\n📊 OK={n_ok} FLIP={n_flip} UNSURE={n_unsure}")
    json.dump({"summary":{"OK":n_ok,"FLIP":n_flip,"UNSURE":n_unsure},
               "suspicious": suspicious, "all": all_verdicts},
              open(OUT,"w"), ensure_ascii=False, indent=2)
    print(f"✅ → {OUT}")

if __name__ == "__main__":
    main()
