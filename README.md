# Podcast Lab 🎧

把视频/音频源（YouTube、播客、讲座等）转成**中文播客音频**。

## 目录结构

```
podcast-lab/
├── projects/
│   └── <slug>/              # 每个项目独立文件夹
│       ├── README.md        # 项目元信息 (源 URL, 状态, 笔记)
│       ├── source/          # 原始音视频 (.gitignored)
│       ├── transcript/
│       │   ├── en.txt       # 英文/原文转录
│       │   └── cn.txt       # 中文翻译
│       └── audio/
│           └── cn-podcast.mp3  # 最终中文播客 (.gitignored)
├── scripts/                 # 通用处理脚本
└── archive/                 # 已完成/废弃的项目
```

## Slug 命名建议

`<作者>-<主题>` 或 `<节目>-<编号>`，全小写连字符：
- `ethan-evans-corp-politics`
- `lex-fridman-ep-400`
- `huberman-sleep-science`

## 工作流

1. **下载**  →  `projects/<slug>/source/audio.mp3`
   ```bash
   yt-dlp -x --audio-format mp3 -o "projects/<slug>/source/audio.%(ext)s" <URL>
   ```

2. **英文转录**  →  `transcript/en.txt`
   ```bash
   python3 -c "import mlx_whisper; \
     r = mlx_whisper.transcribe('projects/<slug>/source/audio.mp3', \
         path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='en'); \
     open('projects/<slug>/transcript/en.txt','w').write(r['text'])"
   ```

3. **翻译**  →  `transcript/cn.txt`
   - 手工/LLM 分段翻译（口语化、适合播客，说话人使用简体中文为主，夹杂英文单词。常用词：播客、podcast、网址、地址、GitHub、OpenClaw、翻译、音频、视频、YouTube、API、token、模型。请用简体中文输出，保留英文技术名词不翻译。）

4. **TTS**  →  `audio/cn-podcast.mp3`
   ```bash
   python3 -c "import asyncio, edge_tts; \
     text=open('projects/<slug>/transcript/cn.txt').read(); \
     asyncio.run(edge_tts.Communicate(text,'zh-CN-XiaoxiaoNeural').save('projects/<slug>/audio/cn-podcast.mp3'))"
   ```

## 每个项目 README 模板

```markdown
# <Title>

- **Source:** <URL>
- **Duration:** ~X min
- **Status:** 转录 ⏳ · 翻译 ⏳ · 音频 ⏳
```

## 依赖

- `yt-dlp`, `ffmpeg` — 下载/处理音频
- `mlx-whisper` (Apple Silicon) 或 `whisper` — 转录
- `edge-tts` — 免费中文 TTS
