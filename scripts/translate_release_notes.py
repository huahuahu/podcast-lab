#!/usr/bin/env python3
"""给 release notes HTML 片段做中文翻译，保留 HTML 结构。"""
import json
import os
import sys
import urllib.request


def load_token() -> str:
    p = os.path.expanduser("~/.openclaw/credentials/github-copilot.token.json")
    return json.load(open(p))["token"]


SYSTEM = """你是一个播客本地化翻译。

任务：把英文播客 release notes（HTML 片段）翻译成中文。

要求：
1. 保留所有 HTML 标签（<p>, <ol>, <li>, <a>, <strong> 等），只翻译内容
2. 风格自然、口语化，像个懂技术/业务的中文朋友在复述
3. 技术术语保留英文（AI, engineering manager, layoff, PIP 等）或常见中文对应（mentor → 带新人）
4. 人名、公司名、地名保留原文
5. 不加任何多余解释，直接输出翻译后的 HTML
"""


def call(token, system, user):
    body = json.dumps({
        "model": "gpt-5.4",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.githubcopilot.com/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Editor-Version": "vscode/1.95.0",
            "Editor-Plugin-Version": "copilot-chat/0.20.0",
            "Copilot-Integration-Id": "vscode-chat",
            "User-Agent": "GitHubCopilotChat/0.20.0",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def main():
    html = sys.stdin.read() if len(sys.argv) < 2 else open(sys.argv[1]).read()
    token = load_token()
    out = call(token, SYSTEM, html)
    # 去 ``` 包裹
    s = out.strip()
    if s.startswith("```"):
        s = s.strip("`").split("\n", 1)[-1] if s.count("\n") else s
        if s.endswith("```"):
            s = s[:-3].strip()
    print(s)


if __name__ == "__main__":
    main()
