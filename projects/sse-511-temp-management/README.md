# Soft Skills Engineering #511 · 临时顶上去当 manager / 怎么用指标算绩效奖金？

| 项目 | 值 |
| --- | --- |
| 标题 | Soft Skills Engineering #511 — Temporary management role & performance bonus metrics |
| 来源 | [Episode 511](https://softskills.audio/episodes/511) — Soft Skills Engineering Podcast |
| 主持 | Dave Smith & Jameson Dance |
| 录制日期 | 2026-05 |
| 时长 | 中文 TTS 41:30 |
| slug | sse-511-temp-management |
| Status | 英文 STT ✅ · LLM speaker reassign ✅（再次 LLM 校验 16 处） · 中文翻译 ✅ · 中文 TTS 双音色 ✅ · 字幕 ✅ |
| Release | [`v0.15.0-sse-511-temp-management`](https://github.com/huahuahu/podcast-lab/releases/tag/v0.15.0-sse-511-temp-management) |

## 简介

SSE 第 511 期，两个问题：

1. 一位听众的同事因为健康原因要请 1–2 个月病假，他被领导临时指派接手对方在团队里的 manager 职责，自己之前从来没做过管理。这是一次"临时但又可能转正"的机会——他要怎么开始？两个 host 的核心建议是：**当作以后会一直做下去那样去做**，但**不要在 1–2 个月内做大动作**（除非真起火）。
2. 一位 team lead 想问：**怎么用指标衡量软件团队的绩效，再据此发奖金？**——尤其是在 HR 把"加薪"这条路堵死、只留下"奖金"这条路、而且 team lead 自己对谁拿多少根本没决定权的情况下。Dave 和 Jameson 都偏悲观：再漂亮的指标都会被钻空子，团队层面的还能用，个人层面的基本不行；最佳策略反而是回到"被人看见 + 找一个真懂工程的人当你的影响力代理"。

## 文件清单

- `source/audio.mp3` — 原始录音（不入 git）
- `audio/podcast_zh.mp3` — 中文双人 TTS（不入 git，GitHub Release 下载）
- `transcript/dialog_en.json` — 英文 diarized STT（Host/Guest 已经 LLM 校正）
- `transcript/dialog_zh.json` — 中文翻译（speaker 二次校验后版本）
- `transcript/dialog_zh.llm_v1.bak.json` — 第一次 LLM 翻译/重判后的备份（speaker 校验前）
- `transcript/dialog_zh_mv.json` — multivoice TTS 输入（198 行）
- `transcript/subtitles/zh.srt` / `zh.vtt` — 中文字幕（按中文 mp3 时长对齐）
- `transcript/subtitles/bilingual.srt` / `bilingual.vtt` — 双语字幕
- `transcript/azure_chunks/` — STT 切片中间产物（不入 git）

## 制作管线（pipeline v3.1）

1. **STT + Diarize** — Azure `gpt-4o-transcribe-diarize`，5 分钟切片，全程 `unset HTTPS_PROXY/HTTP_PROXY/ALL_PROXY` 走直连
2. **Speaker reassign** — Copilot GPT-5.4 校正成 Host / Guest
3. **翻译** — Copilot GPT-5.4 批量翻译
4. **Speaker 二次校验** — 翻译后再次用 LLM 复核 Host/Guest 边界，对比 v1 备份共 **修正 16 处**（详见下方"Speaker 校验"）
5. **TTS** — Edge TTS 双音色（晓晓 = Host，云扬 = Guest）
6. **字幕** — 按 `tts_cache` 真实音频时长累加（scheme B），与中文 mp3 严格对齐

## 数据

- TTS 句子（= 中文段落）：**198** lines
- LLM 终判分布：**Host 106** 段 / **Guest 92** 段
- 字幕条数：**198**
- 中文 mp3 时长：**41:30**

## Speaker 校验

翻译之后做了一次额外的 speaker 二次校验。对比 `dialog_zh.llm_v1.bak.json`（v1：第一次 LLM 重判后）与 `dialog_zh.json`（v2：二次校验后）：

- 共发现 **16 处** speaker 标签可疑、并被改判
- 主要集中在两段：
  - **idx 40–45**（节目中段过渡到第一个问题）：v1 把 Dave/Jameson 之间的衔接对话连续判反，二次校验改成正确的 Host/Guest 交替
  - **idx 146–193**（第二个问题后半段，Joe 那段管理层会议的回忆 + 收尾）：v1 把 Jameson（Guest）几段长论述误判成 Host，二次校验改回 Guest
- 其余零散修正：idx 165、175、176

如果不做这一步，TTS 出来的中文版会出现"Dave 突然说出 Jameson 视角的话"这种听感断裂；二次校验直接消除了这些问题。
