# AGENTS.md — podcast-lab agent entry point

> 你是新接手 podcast-lab 仓库的 agent（比如小爪），没记忆。
> **先读这两个文件，再做事**：
>
> 1. [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md) — 当前真实有效的运维流程（活文档，每次踩坑都更新）
> 2. [`docs/PIPELINE_V4.md`](docs/PIPELINE_V4.md) — v4 流水线设计文档（背景知识）
>
> README 是给人类看的高层介绍；MAINTENANCE 才是给你看的操作手册。

## 不要做这些事（容易把仓库搞坏）

- 不要 `rm -rf projects/*/` —— 单集中间产物（azure_chunks、tts_cache）丢了要花钱重跑
- 不要 force push docs/rss.xml —— 历史 EPnn 编号靠 git 历史保命
- 不要在 `configs/series.json` 里凭记忆写音色名 —— 必须 `python3 -m edge_tts --list-voices` 核对
- 不要用 `rm`，用 `trash`

## 出新一集的最快路径

1. 读 `docs/MAINTENANCE.md` 的 "TL;DR" 一节
2. 拿到本集 EP 号：`grep -oE 'EP[0-9]+' docs/rss.xml | sort -u | tail -n 1`，+1
3. 一键起跑：见 MAINTENANCE.md TL;DR
4. 跑完按 MAINTENANCE.md 的发布步骤走

## 维护这份文档

- 每次跑完一集 / 改了脚本默认值 / 踩了新坑 → **更新 `docs/MAINTENANCE.md`**
- 大的设计变更 → 同时更新 `docs/PIPELINE_V4.md`
- 这个 AGENTS.md 本身只是路标，尽量不变；MAINTENANCE.md 才是会长大的那个

## 凭证位置

- Azure: `~/.openclaw/credentials/azure-openai.json`
- GitHub Copilot: `~/.openclaw/credentials/github-copilot.token.json`
- gh CLI: 已 ssh 登录 `huahuahu`
