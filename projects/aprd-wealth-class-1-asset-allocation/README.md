# 财富智慧课 · 第一节 家庭资产配置（APRD 系列）

| 项目 | 值 |
| --- | --- |
| 标题 | 财富智慧课·第一节 家庭资产配置 |
| 来源 | APRD 系列内部分享课 |
| 录制日期 | 2026-04-27 |
| 时长 | 02:09:31（ffprobe 实测 7771.6s） |
| 音频格式 | 原始 m4a（AAC 16kHz mono），发布转码为 mp3（VBR q4） |
| slug | aprd-wealth-class-1-asset-allocation |

## 简介

APRD 财富智慧课第一节，主讲人系统梳理当下中国家庭面对的财富管理路径与挑战：通胀对货币购买力的侵蚀、复利与时间的关系、超额储蓄怎么处置、以及个人在「财富战场上场」之前要先做好的功课。最后用约 50 分钟讲家庭资产配置的实操方法。

## 文件清单

- `source/audio.m4a` — 原始录音（不入 git）
- `audio/podcast_zh.mp3` — 发布版 mp3（不入 git，发到 GitHub Release）
- `transcript/dialog_en.json` — Azure `gpt-4o-mini-transcribe` STT 结果（schema 沿用 dialog_en.json，但内容是中文）
- `transcript/subtitles/zh.srt` / `zh.vtt` — 中文字幕，时间戳来自 STT
- `transcript/azure_chunks/` — STT 切片中间产物（不入 git）

## 制作管线

1. `ffmpeg -c:a libmp3lame -q:a 4` 转 mp3
2. `scripts/azure_transcribe_mini.sh` 调 Azure OpenAI `gpt-4o-mini-transcribe`，5 分钟切片，断点续传
3. `scripts/make_subtitles_simple.py` 把 STT JSON 切成 ≤40 字单行字幕，按字数比例分配时间戳
4. 内容保持原音频、原说话人、原中文，不翻译、不重写、不 TTS、不 diarize
