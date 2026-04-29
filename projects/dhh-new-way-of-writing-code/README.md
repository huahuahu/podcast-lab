# DHH × Pragmatic Engineer：用 AI 写代码的新方式

| 项目 | 值 |
| --- | --- |
| 标题 | DHH × Pragmatic Engineer：用 AI 写代码的新方式 |
| 来源 | [DHH's new way of writing code](https://www.pragmaticengineer.com/dhh-new-way-of-writing-code) — The Pragmatic Engineer Podcast |
| 嘉宾 | David Heinemeier Hansson (DHH)，主持 Gergely Orosz |
| 录制日期 | 2026-04 |
| 时长 | 01:46:14（源音频，ffprobe 实测 6374s）/ 中文 TTS 02:14:51（8091s） |
| slug | dhh-new-way-of-writing-code |
| Status | 英文 STT ✅ · LLM speaker reassign ✅ · 中文翻译 ✅ · 中文 TTS 双音色 ✅ · 字幕 ✅ |
| Release | [`v0.9.0-dhh-new-way-of-writing-code`](https://github.com/huahuahu/podcast-lab/releases/tag/v0.9.0-dhh-new-way-of-writing-code)（**v2 重制版**） |

## 简介

DHH 半年前还狠批 AI 编程，冬休期间 180 度大转弯——他和 37signals 的团队现在 AI-first，每个工程师/设计师都能用 agent 大幅提升雄心，重做了 Hey、Linux 发行版 Omarchy、Basecamp 等。访谈聊：AI tooling 的演化、传统 IDE 为什么让位给终端 agent、招聘标准的变化、Smalltalk 与 Kent Beck 的影响、以及 software engineer 数量是否已经见顶。

## v2 重制版（v0.9.0）说明

旧版 `v0.6.0` 因为：
- LLM speaker reassignment **之前**已经手工打过多个补丁，speaker 标签不一致；
- chunk 3 单独走过修补流程；
- 结尾几个 chunk speaker 切换不稳。

听感"乱"。这一版**整集从头重跑**，没有任何手工修补，干净一致：

1. 备份旧产物到 `_archive_v0.6/`（本地保留，不入 git）
2. 全程 `unset HTTPS_PROXY HTTP_PROXY ALL_PROXY` 跑 Azure，避免 SSE 中途断流
3. 一次性重新生成 `dialog_en.json` → reassign → `dialog_zh.json` → TTS → 字幕

## 文件清单

- `source/audio.mp3` — 原始录音（不入 git）
- `audio/podcast_zh.mp3` — 中文双人 TTS（不入 git，GitHub Release 下载）
- `transcript/dialog_en.json` — 英文 diarized STT（HOST/GUEST 已经 LLM 校正）
- `transcript/dialog_zh.json` — 中文翻译
- `transcript/dialog_zh_mv.json` — multivoice TTS 输入
- `transcript/subtitles/zh.srt` / `zh.vtt` — 中文字幕（按中文 mp3 时长对齐）
- `transcript/subtitles/bilingual.srt` / `bilingual.vtt` — 双语字幕
- `transcript/azure_chunks/` — STT 切片中间产物（不入 git）

## 制作管线（pipeline v3.1，干净版）

1. **STT + Diarize** — `scripts/azure_transcribe_diarize.sh` 调 Azure `gpt-4o-transcribe-diarize`，5 分钟切片
2. **Speaker reassign** — `scripts/reassign_speakers_llm.py` 用 Copilot GPT-5.4 把 `SPEAKER_00/01/02/03` 校正成 HOST/GUEST
3. **翻译** — `scripts/translate_dialog_copilot.py` 用 Copilot GPT-5.4 批量翻译
4. **TTS** — `scripts/prepare_multivoice.py` + `scripts/multivoice_robust.py`，Edge TTS 双音色（晓晓 = HOST，云扬 = GUEST）
5. **字幕** — `scripts/make_subtitles_zh.py` 按 `tts_cache` 的真实音频时长累加（scheme B），与中文 mp3 严格对齐

## 数据

- 英文段落：**724** utterances
- LLM 重判分布：**HOST 247** 段 / **GUEST 477** 段
- TTS 句子：**722** lines
- 字幕条数：**722**
