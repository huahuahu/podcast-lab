# Podcast Lab 🎧

把视频/音频源（YouTube、Podcast、讲座等）转成中文播客音频。

## 目录结构

```
podcast-lab/
├── sources/            # 原始源文件（视频链接、下载的音频）
├── transcripts/
│   ├── en/             # 英文转录文本
│   └── cn/             # 中文翻译文本
├── audio/
│   └── output/         # 最终中文播客音频 (.mp3)
├── scripts/            # 处理脚本（下载、转录、翻译、TTS）
└── archive/            # 已完成项目归档
```

## 工作流

1. **下载音频** → `sources/`
   ```bash
   yt-dlp -x --audio-format mp3 -o "sources/{name}.%(ext)s" <URL>
   ```

2. **英文转录** → `transcripts/en/`
   - 用 mlx-whisper (本地，Apple Silicon 加速)

3. **翻译成中文** → `transcripts/cn/`

4. **生成播客音频** → `audio/output/`
   - 用 edge-tts (zh-CN-XiaoxiaoNeural 等)

## 每个项目建议结构

每个项目在各目录下用统一 slug，例如 `ethan-evans-corp-politics`：
- `sources/ethan-evans-corp-politics.mp3`
- `transcripts/en/ethan-evans-corp-politics.txt`
- `transcripts/cn/ethan-evans-corp-politics.txt`
- `audio/output/ethan-evans-corp-politics.mp3`

## 注意

- `sources/` 和 `audio/` 里的大文件已在 `.gitignore` 忽略
- 只有脚本、转录文本进 git
