# Jensen Huang × Dwarkesh · TPU 竞争、卖芯片给中国、Nvidia 的供应链护城河

| 项目 | 值 |
| --- | --- |
| 标题 | Jensen Huang – TPU competition, why we should sell chips to China, & Nvidia's supply chain moat |
| 来源 | [Dwarkesh Podcast](https://www.dwarkesh.com/p/jensen-huang) — Dwarkesh Patel |
| YouTube | https://youtu.be/Hrbq66XqtCo |
| 主持 | Dwarkesh Patel (Host) · Jensen Huang (Guest) |
| 发布日期 | 2026-04-15 |
| 时长 | 103:12（源音频）/ 中文 TTS 101:30 |
| slug | dwarkesh-jensen-huang-2026 |
| Status | 英文字幕（YouTube 人工字幕）✅ · LLM speaker reassign ✅ · 中文翻译 ✅ · 中文 TTS 双男声 ✅ · 字幕 ✅ |
| Release | [`v0.12.0-dwarkesh-jensen-huang-2026`](https://github.com/huahuahu/podcast-lab/releases/tag/v0.12.0-dwarkesh-jensen-huang-2026) |

## 简介

Dwarkesh Patel 与 Nvidia CEO Jensen Huang 长聊 1 小时 43 分。主线是 Nvidia 的真正护城河到底是什么——不是 CUDA，而是它对全球先进半导体供应链的掌控；以及由此延伸出的几个硬话题：Google TPU 会不会撼动 Nvidia 的地位、Anthropic 大量算力跑在 TPU 上意味着什么、应不应该卖 AI 芯片给中国、Nvidia 为什么不直接做 hyperscaler、对 OpenAI 等客户的投资节奏与遗憾。Jensen 在被 Dwarkesh 反复追问下少有地正面回答了「ASIC 利润空间」「为什么没更早投 Anthropic」之类的问题。

A long conversation between Dwarkesh Patel and Nvidia CEO Jensen Huang. Topics: Nvidia's real moat (the bottlenecked semiconductor supply chain, not CUDA), TPU competition and Anthropic's TPU usage, whether the US should sell AI chips to China, why Nvidia doesn't become a hyperscaler, and Jensen's regret about not investing in Anthropic earlier.

## 文件清单

- `source/audio.mp3` — 原始录音（不入 git）
- `source/*.en.vtt` — YouTube 人工英文字幕（用作 STT 替代）
- `audio/podcast_zh.mp3` — 中文双人 TTS（不入 git，GitHub Release 下载）
- `transcript/dialog_en.json` — 英文对话（YouTube 字幕合并 + LLM Host/Guest 校正）
- `transcript/dialog_zh.json` — 中文翻译
- `transcript/dialog_zh_mv.json` — multivoice TTS 输入
- `transcript/subtitles/zh.srt` / `zh.vtt` — 中文字幕（按中文 mp3 时长对齐）
- `transcript/subtitles/bilingual.srt` / `bilingual.vtt` — 双语字幕

## 制作管线（pipeline v3.1，本期跳过 Azure STT）

1. **STT** — **跳过 Azure**，直接抓 YouTube 人工英文字幕（`yt-dlp --write-sub --sub-lang en`），合并成 ~30s 一段
2. **Speaker reassign** — Copilot GPT-5.4 根据内容把每段判成 Host (Dwarkesh) / Guest (Jensen)
3. **Smart merge** — 去 backchannel + 合并相邻同 speaker 短段
4. **翻译** — Copilot GPT-5.4 批量翻译
5. **TTS** — Edge TTS 双男声（云希 = Host Dwarkesh，云扬 = Guest Jensen）
6. **字幕** — 按 `tts_cache` 真实音频时长累加（scheme B），与中文 mp3 严格对齐

## 数据

- 英文段落：**228** utterances
- LLM 重判分布：**Host 70** 段 / **Guest 158** 段
- TTS 句子：**228** lines
- 字幕条数：**228**
- 中文 mp3：**101 分 30 秒**, 34.4 MB

## 备注

- **没用 Azure** — 因为 Dwarkesh 给 YouTube 上传了人工精校英文字幕，质量比 STT 还高，省了 ~$1 的 Azure 费用和切片时间
- **音色** — 主持人和嘉宾都是男的，所以 Host 用「云希 zh-CN-YunxiNeural」（温和男声）替代默认的女声「晓晓」，Guest 还是「云扬 zh-CN-YunyangNeural」
