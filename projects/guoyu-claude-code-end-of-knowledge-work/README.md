# 郭宇｜Claude Code：知识工作者的终结

| 项目 | 值 |
| --- | --- |
| 标题 | 郭宇 × 单向街东京：Claude Code / 知识工作者的终结 |
| 来源 | <https://www.youtube.com/watch?v=rwueq7n_3yA> |
| 场合 | 单向街东京 现场对谈 |
| 演讲者 | 郭宇（前字节跳动早期工程师，现居东京） |
| 时长 | 37:28 |
| 语言 | 中文（普通话） |
| Status | 音频 ✅ · 字幕（YouTube 自动 + 繁简转换）✅ · 博客整理 ✅ |

## 文件清单

- `source/audio.mp3` — 原始中文音频（49 MB，yt-dlp，不入 git）
- `source/transcript_zh.txt` — 字幕去时间戳后的纯文本（用于博客整理）
- `transcript/subtitles/zh.srt` / `zh.vtt` — 中文字幕（1127 cues，简体）
- `transcript/subtitles/zh.raw.vtt` — YouTube 原始自动字幕（繁体）
- `transcript/dialog_zh.json` — `[{start,end,text}]` 结构化字幕
- `blog/post.md` — 博客整理（10 节，约 5 KB）
- `scripts/vtt_to_srt.py` — VTT → SRT + 繁→简转换器

## 制作管线（vs 标准 pipeline 的偏差）

| 步骤 | 标准 pipeline | 本项目 |
| --- | --- | --- |
| 1. 下载 | yt-dlp 抽 mp3 | ✅ 同 |
| 2. STT + Diarize | Azure `gpt-4o-transcribe-diarize` | ❌ 跳过 |
| 2.5 Speaker reassign | LLM Host/Guest | ❌ 跳过 |
| 3. 翻译 | Copilot GPT-5.4（英→中） | ❌ 跳过（源就是中文） |
| 4. TTS | edge-tts 双音色 | ❌ 跳过（直接用原音频） |
| 5. 字幕 | 按 TTS 时长重对齐 | ✅ 直接用 YouTube 自动字幕 + opencc 繁→简 |

**为什么不走 Azure STT**：试过一次（607 段，8 个 chunk，跑了 ~10 分钟），发现两个坑：
1. `gpt-4o-transcribe-diarize` 默认把中文音频翻成英文输出
2. diarize 把对话切得过碎，单 chunk 内识别出多达 11 个 speaker

YouTube 自动字幕已经是中文 + 时间戳，opencc 转简体即可，秒出。

## 下一步（可选）

- 想要切 chapter / show notes：用 `dialog_zh.json` 的时间戳手切
- 想要双语字幕：跑一遍翻译，目前没做
- 想发布：原音频不是自己作品，谨慎处理版权
