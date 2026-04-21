# Podcast Lab 🎧

把视频/音频（YouTube、播客、讲座等）自动转成**双人中文播客 mp3**。

---

## 🚀 推荐管线（v2）

```
YouTube URL
    │
    ▼
① yt-dlp 下载音频 ─────────────── source/audio.mp3
    │
    ├──► ② SiliconFlow SenseVoice (STT) ────── transcript/en-raw.txt
    │
    └──► ③ pyannote speaker-diarization-3.1 ── diarization/segments.json
                                                    │
    ④ 合并时间戳对齐 ◄──────────────────────────────┘
        │
        ▼
    transcript/dialog_en.json  （带 speaker + start/end）
        │
        ▼
    ⑤ GitHub Copilot GPT-5.4 翻译 ──── transcript/dialog_zh.json
        │
        ▼
    ⑥ edge-tts 双音色配音 + ffmpeg concat
        │
        ▼
    audio/podcast_zh.mp3  🎧
```

### 选型理由

| 环节 | 选用 | 为什么 |
|---|---|---|
| **STT** | SiliconFlow `FunAudioLLM/SenseVoiceSmall` | 云端快、便宜（~¥0.01/min）、中英混音友好；本地 whisper.cpp 要 10+ 分钟，云端 3 分钟搞定 |
| **说话人分离** | `pyannote/speaker-diarization-3.1`（本地） | 没有成熟的云端 API；本地 M1+MPS 够快 |
| **翻译** | GitHub Copilot `gpt-5.4` | 公司订阅免费；口语化、保留术语、上下文连贯 |
| **TTS** | `edge-tts` + `zh-CN-YunyangNeural` / `zh-CN-XiaoxiaoNeural` | 免费白嫖 Microsoft Edge 协议；支持多音色；音质自然 |

### 替代方案（无公司订阅时）

| 原方案 | 替代 | 成本 |
|---|---|---|
| Copilot GPT-5.4 | SiliconFlow Qwen2.5-72B / DeepSeek-V3 | ~¥0.5-1 |
| SF SenseVoice | 本地 whisper.cpp | ¥0（但慢） |

---

## 🏃 一键跑

```bash
./scripts/pipeline.sh <slug> <youtube_url>
# 例：./scripts/pipeline.sh lex-fridman-ep-400 https://youtu.be/xxx
```

产物全部落到 `projects/<slug>/`：

```
projects/<slug>/
├── source/audio.mp3            # yt-dlp 下的原音频
├── diarization/segments.json   # pyannote 分段
├── transcript/
│   ├── siliconflow.txt         # SF SenseVoice 整体转录
│   ├── dialog_en.json          # whisper + pyannote 合并对话
│   └── dialog_zh.json          # GPT-5.4 中文翻译
└── audio/
    ├── podcast_zh.mp3          # 最终成品（.gitignored）
    └── tts_cache/              # 单句 mp3 缓存（.gitignored）
```

---

## 📋 分步手动运行

### ① 下载
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  -o "projects/<slug>/source/audio.%(ext)s" <URL>
```

### ② STT（SiliconFlow 云端，推荐）
```bash
./scripts/sf_transcribe_all.sh \
  projects/<slug>/source/audio.mp3 \
  projects/<slug>/transcript
```

**或者本地 whisper.cpp**：
```bash
whisper-cli -m ~/.openclaw/models/whisper/ggml-large-v3-turbo.bin \
  -f projects/<slug>/source/audio_16k.wav -oj -of transcript/whisper
python3 scripts/whisper_to_segs.py transcript/whisper.json transcript/whisper_segs.json
```

### ③ 说话人分离（本地 pyannote）
```bash
source ~/.openclaw/secrets/env.sh   # 需要 HF_TOKEN
python3 scripts/diarize.py \
  projects/<slug>/source/audio.mp3 \
  -o projects/<slug>/diarization/segments.json \
  --num-speakers 2
```

### ④ 合并时间戳（whisper + pyannote → 带 speaker 的对话）
```bash
python3 scripts/transcribe_diarized.py \
  --audio projects/<slug>/source/audio_16k.wav \
  --transcript projects/<slug>/transcript/whisper_segs.json \
  --segments projects/<slug>/diarization/segments.json \
  -o projects/<slug>/transcript/dialog_en.json
```

可选：改 speaker 名
```bash
python3 scripts/rename_speakers.py \
  projects/<slug>/transcript/dialog_en.json \
  SPEAKER_00=Host SPEAKER_01=Guest
```

### ⑤ 翻译（GPT-5.4 via Copilot，推荐）
```bash
python3 -u scripts/translate_dialog_copilot.py \
  projects/<slug>/transcript/dialog_en.json \
  projects/<slug>/transcript/dialog_zh.json \
  --batch-size 8
```

**不想用 Copilot？** 走 SF Qwen：
```bash
python3 -u scripts/translate_dialog.py \
  projects/<slug>/transcript/dialog_en.json \
  projects/<slug>/transcript/dialog_zh.json
```

两个脚本都支持**断点续传**（同输出文件时跳过已完成 batch）。

### ⑥ TTS 合成
```bash
python3 scripts/prepare_multivoice.py \
  projects/<slug>/transcript/dialog_zh.json \
  projects/<slug>/transcript/dialog_zh_mv.json

python3 -u scripts/multivoice_robust.py \
  projects/<slug>/transcript/dialog_zh_mv.json \
  -o projects/<slug>/audio/podcast_zh.mp3 \
  --cache-dir projects/<slug>/audio/tts_cache
```

`multivoice_robust.py` 特性：45s 超时 + 3 次重试 + 长句截短保底 + cache_dir 断点续传。

---

## 🔑 环境要求

### 必需
- `python3`（3.10+）
- `ffmpeg`, `ffprobe`
- `yt-dlp`
- Python 包：`edge-tts`, `pyannote.audio` (4.x)

### 可选 / 按需
- `whisper-cli`（Homebrew `ggml`）+ 模型文件 `ggml-large-v3-turbo.bin`
- **SiliconFlow API key** → 存 `~/.openclaw/secrets.json` 里 `providers.siliconflow.apiKey`
- **GitHub Copilot token** → 存 `~/.openclaw/credentials/github-copilot.token.json`
- **HuggingFace token** → `HF_TOKEN` 环境变量（pyannote 用）

### 路径/模型覆盖（避免硬编码）
```bash
export WHISPER_CLI=/opt/homebrew/bin/whisper-cli
export WHISPER_MODEL=~/.openclaw/models/whisper/ggml-large-v3-turbo.bin
export OPENCLAW_SECRETS=~/.openclaw/secrets/env.sh
```

---

## 🎙️ 音色参考

内置默认（可在 `scripts/prepare_multivoice.py` 里改）：

| Speaker | Voice | 描述 |
|---|---|---|
| `Ethan` / `guest` | `zh-CN-YunyangNeural` | 云扬，男声，新闻播报风 |
| `Ryan` / `host` | `zh-CN-XiaoxiaoNeural` | 晓晓，女声，主持人感 |
| `narrator` | `zh-CN-YunxiNeural` | 云希，温和男声 |
| 其他 | `zh-CN-XiaoyiNeural` | 晓伊 |

---

## 💰 成本参考（2:50h 英文播客）

| 方案 | 费用 |
|---|---|
| SF STT + Copilot 翻译 + edge-tts | **~¥2**（仅 STT） |
| 本地 whisper + Copilot 翻译 + edge-tts | **¥0** |
| 本地 whisper + SF Qwen 翻译 + edge-tts | **~¥1** |
| 全云端（OpenAI STT + GPT-4o + OpenAI TTS） | ~¥60-100 |

---

## 📦 发布到 Release（mp3 >50MB 时）

```bash
gh release create v0.x-<slug> \
  --repo huahuahu/podcast-lab \
  --title "..." --notes "..." \
  projects/<slug>/audio/podcast_zh.mp3
```

---

## 📝 每个项目的 README 模板

```markdown
# <Title>

- **Source:** <YouTube URL>
- **Duration:** ~X min
- **Speakers:** 2 (Host + Guest)
- **Status:** STT ✅ · Diarize ✅ · Translate ✅ · TTS ✅
- **Release:** https://github.com/huahuahu/podcast-lab/releases/tag/vX.Y.Z
```

---

## 🗂 Slug 命名

`<作者>-<主题>` 或 `<节目>-<编号>`，小写连字符：
- `ethan-evans-corp-politics`
- `lex-fridman-ep-400`
- `huberman-sleep-science`

---

## 🎬 已完成项目

- [ethan-evans-corp-politics](./projects/ethan-evans-corp-politics/) — Retired Amazon VP 聊公司政治 (2h42m)
  → 🎧 [下载中文版](https://github.com/huahuahu/podcast-lab/releases/tag/v0.1.0-ethan-evans-zh)
