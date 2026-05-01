# Soft Skills Engineering #510 · 又老又落后，怎么撑到退休？

| 项目 | 值 |
| --- | --- |
| 标题 | Soft Skills Engineering #510 — Old and behind and how do I hang on for the last few years until retirement? |
| 来源 | [Episode 510](https://softskills.audio/episodes/510) — Soft Skills Engineering Podcast |
| 主持 | Dave Smith & Jameson Dance |
| 录制日期 | 2026-04 |
| 时长 | 33:58（源音频）/ 中文 TTS 45:46 |
| slug | sse-510-old-and-behind |
| Status | 英文 STT ✅ · LLM speaker reassign ✅ · 中文翻译 ✅ · 中文 TTS 双音色 ✅ · 字幕 ✅ |
| Release | [`v0.10.0-sse-510-old-and-behind`](https://github.com/huahuahu/podcast-lab/releases/tag/v0.10.0-sse-510-old-and-behind) |

## 简介

SSE 第 510 期，两个问题：

1. 一位将近 40 岁的听众，在大型远程办公公司里和一群 20 多岁的同事相处不来，年度线下聚会该怎么社交？是否会被看成"拍马屁"？
2. 一位在科技行业工作 30 年的资深工程师，在保险/金融大厂还有几年退休，但已经厌倦了这个"冷血贪权"的行业。怎么才能"既不留下一地消沉情绪，又不在退休前继续给这头怪兽添柴"？Dave 和 Jameson 给出了相当走心的回应。

## 文件清单

- `source/audio.mp3` — 原始录音（不入 git）
- `audio/podcast_zh.mp3` — 中文双人 TTS（不入 git，GitHub Release 下载）
- `transcript/dialog_en.json` — 英文 diarized STT（Host/Guest 已经 LLM 校正）
- `transcript/dialog_zh.json` — 中文翻译
- `transcript/dialog_zh_mv.json` — multivoice TTS 输入
- `transcript/subtitles/zh.srt` / `zh.vtt` — 中文字幕（按中文 mp3 时长对齐）
- `transcript/subtitles/bilingual.srt` / `bilingual.vtt` — 双语字幕
- `transcript/azure_chunks/` — STT 切片中间产物（不入 git）

## 制作管线（pipeline v3.1）

1. **STT + Diarize** — Azure `gpt-4o-transcribe-diarize`，5 分钟切片，全程 `unset HTTPS_PROXY/HTTP_PROXY/ALL_PROXY` 走直连
2. **Speaker reassign** — Copilot GPT-5.4 校正成 Host / Guest
3. **翻译** — Copilot GPT-5.4 批量翻译
4. **TTS** — Edge TTS 双音色（晓晓 = Host，云扬 = Guest）
5. **字幕** — 按 `tts_cache` 真实音频时长累加（scheme B），与中文 mp3 严格对齐

## 数据

- 英文段落：**377** utterances
- LLM 重判分布：**Host 206** 段 / **Guest 171** 段
- TTS 句子：**370** lines
- 字幕条数：**370**
