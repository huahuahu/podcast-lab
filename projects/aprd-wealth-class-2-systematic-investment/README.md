# 财富智慧课 · 第二节 健康财富管理进阶课（APRD 系列）

| 项目 | 值 |
| --- | --- |
| 标题 | APRD 健康嘉年华 · 线上财富智慧课二：健康财富管理进阶课，用系统化投资构筑终身养老财富 |
| 来源 | APRD 健康嘉年华内部分享课（线上） |
| 录制日期 | 2026-05-08 |
| 时长 | 约 1:48:24（ffprobe 实测 6504s） |
| 音频格式 | 原始 mp3（来自会议录像 mp4 提取） |
| slug | aprd-wealth-class-2-systematic-investment |

## 简介

APRD 财富智慧课第二节，主讲人系统讲解如何用系统化投资构筑终身养老财富，是第一节《家庭资产配置》的进阶续篇。

## 文件清单

- `source/audio.mp3` — 原始录音（不入 git）
- `source/meta.json` — ingest 元数据
- `cover.png` — 封面图
- `transcript/dialog_en.json` — Azure `gpt-4o-mini-transcribe` STT 结果（schema 沿用 dialog_en.json，但内容是中文）
- `transcript/subtitles/zh.srt` / `zh.vtt` — 中文字幕，时间戳来自 STT
- `transcript/azure_chunks/` — STT 切片中间产物（不入 git）

## 制作管线

跟第一节一致：

1. `ffmpeg` 从录像 mp4 提取 mp3
2. `scripts/_restored/azure_transcribe_mini.sh` 调 Azure OpenAI `gpt-4o-mini-transcribe`，5 分钟切片，断点续传
3. `scripts/_restored/make_subtitles_simple.py` 把 STT JSON 切成 ≤40 字单行字幕，按字数比例分配时间戳
4. 内容保持原音频、原说话人、原中文，不翻译、不重写、不 TTS、不 diarize

> 注：旧 v3 转录脚本（`azure_transcribe_mini.sh` / `make_subtitles_simple.py`）在 v4 切换时被删过，这里临时从 git 历史恢复到 `scripts/_restored/`。等 v4 lane_passthrough 接上 faster-whisper 后再统一迁移。
