#!/usr/bin/env python3
"""通用 speaker 二次校验：让 Copilot GPT-5.4 校对 dialog_zh.json 的 Host/Guest 标注。

用法：
    audit_speakers_llm.py <project_dir> [--apply] [--batch 20]

默认 --apply，会把 FLIP 直接写回 dialog_zh.json（原版备份成 dialog_zh.pre-audit.bak.json）。
传 --no-apply 则只生成 audit_report.json，不动原文件。

可选 <project_dir>/meta.json 提供节目背景，结构示例：
{
  "show": "Soft Skills Engineering #511",
  "host": "Dave Smith — 开场白、念赞助、读问题信件多由他主导",
  "guest": "Jameson Dance — 常笑场、抛回应、做总结"
}
没有就用通用提示词（仅靠对话节奏判断）。

输出：
- <project_dir>/transcript/audit_report.json
- <project_dir>/transcript/.speakers-audited      （sentinel，pipeline 跳过用）
"""
import argparse, json, os, shutil, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config

ENDPOINT = "https://api.githubcopilot.com/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot-chat/0.20.0",
    "Copilot-Integration-Id": "vscode-chat",
    "User-Agent": "GitHubCopilotChat/0.20.0",
}

def token():
    p = os.path.expanduser("~/.openclaw/credentials/github-copilot.token.json")
    return json.load(open(p))["token"]

def build_sys(meta):
    show = meta.get("show", "一档双人播客")
    host = meta.get("host", "HOST — 通常主导话题、提问、念广告/赞助")
    guest = meta.get("guest", "GUEST — 通常做回应、补充、总结")
    return f"""你是一个播客对话分析师。这是 {show}，两位说话人：
- HOST：{host}
- GUEST：{guest}

我会一次给你一个批次（约 20 段）的中文对话，每段带 idx 和当前 speaker 标注（HOST/GUEST）。
你逐段判断当前 speaker 标注是否合理，根据**与前后段的衔接、问答关系、笑点节奏**判断。

输出 JSON 数组，每段一个对象：
  {{"idx": 整数, "current": "HOST"或"GUEST", "verdict": "OK" / "FLIP" / "UNSURE", "reason": "一句话"}}

- OK = 当前标注合理
- FLIP = 当前标注大概率错了，应该是另一个人
- UNSURE = 凭文本无法判断（比如 "嗯" / "对" 这种短回应）

只输出 JSON 数组，不要解释。"""

def call(tok, sys_p, usr):
    body = json.dumps({
        "model": "gpt-5.4",
        "messages": [{"role":"system","content":sys_p},{"role":"user","content":usr}],
        "temperature": 0.1,
    }, ensure_ascii=False).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                ENDPOINT, data=body,
                headers={**HEADERS, "Authorization": f"Bearer {tok}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  retry {attempt+1}: {e}", file=sys.stderr)
    raise RuntimeError("call failed after 3 retries")

def parse_json_array(s):
    s = s.strip().strip("`")
    if s.startswith("json"):
        s = s[4:].strip()
    lo, hi = s.find("["), s.rfind("]")
    return json.loads(s[lo:hi+1])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", help="project dir, e.g. projects/sse-511-temp-management")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--apply", dest="apply", action="store_true", default=True,
                    help="apply FLIPs back to dialog_zh.json (default on)")
    ap.add_argument("--no-apply", dest="apply", action="store_false")
    args = ap.parse_args()

    proj = os.path.abspath(args.project)
    src = os.path.join(proj, "transcript", "dialog_zh.json")
    out = os.path.join(proj, "transcript", "audit_report.json")
    sentinel = os.path.join(proj, "transcript", ".speakers-audited")
    bak = os.path.join(proj, "transcript", "dialog_zh.pre-audit.bak.json")

    if not os.path.exists(src):
        print(f"❌ 缺少 {src}", file=sys.stderr)
        sys.exit(1)

    meta = _config.resolve(proj)
    if meta.get("_series"):
        print(f"📋 series cfg: {meta['_series']}")
    sys_p = build_sys(meta)

    d = json.load(open(src))
    tok = token()

    suspicious, all_verdicts = [], []
    BATCH = args.batch
    for i in range(0, len(d), BATCH):
        chunk = d[i:i+BATCH]
        payload = [{
            "idx": i+j,
            "speaker": ("HOST" if x.get("speaker")=="Host" else "GUEST"),
            "text": x.get("text",""),
        } for j,x in enumerate(chunk)]
        print(f"📤 batch {i//BATCH+1}/{(len(d)+BATCH-1)//BATCH}  idx {i}-{i+len(chunk)-1}", flush=True)
        raw = call(tok, sys_p, json.dumps(payload, ensure_ascii=False))
        try:
            verds = parse_json_array(raw)
        except Exception as e:
            print(f"  parse fail: {e}\n  raw: {raw[:200]}", file=sys.stderr)
            continue
        for v in verds:
            all_verdicts.append(v)
            if v.get("verdict") == "FLIP":
                idx = v["idx"]
                suspicious.append({
                    "idx": idx, "current": v.get("current"),
                    "reason": v.get("reason",""),
                    "text": d[idx]["text"],
                    "prev": d[idx-1]["text"] if idx > 0 else "",
                    "next": d[idx+1]["text"] if idx+1 < len(d) else "",
                })

    n_ok = sum(1 for v in all_verdicts if v.get("verdict")=="OK")
    n_flip = sum(1 for v in all_verdicts if v.get("verdict")=="FLIP")
    n_unsure = sum(1 for v in all_verdicts if v.get("verdict")=="UNSURE")
    print(f"\n📊 OK={n_ok} FLIP={n_flip} UNSURE={n_unsure}")

    json.dump({
        "summary": {"OK":n_ok,"FLIP":n_flip,"UNSURE":n_unsure},
        "suspicious": suspicious,
        "all": all_verdicts,
    }, open(out,"w"), ensure_ascii=False, indent=2)
    print(f"✅ report → {out}")

    if args.apply and suspicious:
        if not os.path.exists(bak):
            shutil.copy(src, bak)
            print(f"💾 backup → {bak}")
        for s in suspicious:
            i = s["idx"]
            d[i]["speaker"] = "Guest" if d[i].get("speaker")=="Host" else "Host"
        json.dump(d, open(src,"w"), ensure_ascii=False, indent=2)
        print(f"✏️  applied {len(suspicious)} FLIPs → {src}")
    elif args.apply:
        print("✓ 没有 FLIP，dialog_zh.json 未改动")

    open(sentinel, "w").close()

if __name__ == "__main__":
    main()
