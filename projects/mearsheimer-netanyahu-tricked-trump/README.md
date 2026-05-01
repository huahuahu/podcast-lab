# Mearsheimer × Napolitano · Netanyahu 把 Trump 骗进战争

| 项目 | 值 |
| --- | --- |
| 标题 | Prof. John Mearsheimer · Netanyahu Tricked Trump Into War |
| 来源 | [Judging Freedom](https://judgenap.com/) — Judge Andrew Napolitano |
| 主持 | Judge Andrew Napolitano (Host) · Prof. John Mearsheimer (Guest) |
| 发布日期 | 2026-04-14 |
| 时长 | 28:13（源音频）/ 中文 TTS 25:42 |
| slug | mearsheimer-netanyahu-tricked-trump |
| Status | 英文 STT ✅ · LLM speaker reassign ✅ · 中文翻译 ✅ · 中文 TTS 双音色 ✅ · 字幕 ✅ |
| Release | [`v0.11.0-mearsheimer-netanyahu-tricked-trump`](https://github.com/huahuahu/podcast-lab/releases/tag/v0.11.0-mearsheimer-netanyahu-tricked-trump) |

## 简介

Napolitano 法官与 Mearsheimer 教授围绕一个判断展开对话：以色列人——尤其是 Netanyahu——把 Trump 总统骗进了一场针对 Iran 的战争，事先承诺 96 小时收兵，事后却让美国深陷其中无法脱身。两人从 Islamabad 的"假谈判"、Vance 在背后给 Netanyahu 汇报、Hezbollah 与 Lebanon 的局势，一路谈到游说集团对美国对伊政策的支配，几乎没有任何谈判空间留给 Trump。

Judge Napolitano and Prof. John Mearsheimer argue that Netanyahu tricked Trump into a war he can't get out of: the "96-hour" promise was a lie, the Islamabad talks were theater (with Vance reporting back to Netanyahu mid-negotiation), and on Lebanon and the broader Iran question Israel is calling the shots while the US lobby boxes Washington in.

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
2. **Speaker reassign** — Copilot GPT-5.4 校正成 Host (Napolitano) / Guest (Mearsheimer)
3. **翻译** — Copilot GPT-5.4 批量翻译
4. **TTS** — Edge TTS 双音色（晓晓 = Host，云扬 = Guest）
5. **字幕** — 按 `tts_cache` 真实音频时长累加（scheme B），与中文 mp3 严格对齐

## 数据

- 英文段落：**133** utterances
- LLM 重判分布：**Host 50** 段 / **Guest 83** 段
- TTS 句子：**133** lines
- 字幕条数：**133**
