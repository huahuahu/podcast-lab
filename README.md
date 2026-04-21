# Podcast Lab 🎧

把视频/音频（YouTube、播客、讲座等）自动转成**双人中文播客 mp3**。

---

## 🚀 管线总览

```
YouTube URL
    │
    ▼
① yt-dlp 下载音频 ─────────────────────────── source/audio.mp3
    │
    ▼
② Azure gpt-4o-transcribe-diarize (SSE 流)
   STT + speaker 一步到位 ──────────────────── transcript/dialog_en.json
                                             （带 speaker + start/end + text）
    │
    ▼
③ GitHub Copilot GPT-5.4 翻译 ─────────────── transcript/dialog_zh.json
    │
    ▼
④ edge-tts 双音色配音 + ffmpeg concat
    │
    ▼
audio/podcast_zh.mp3  🎧
```

### 选型理由

| 环节 | 选用 | 为什么 |
|---|---|---|
| **STT + Diarize** | Azure `gpt-4o-transcribe-diarize`（SSE 流式） | 一个 API 同时返回文字 + 时间戳 + 说话人；免本地 pyannote、免 HF token、免长时间跑模型 |
| **翻译** | GitHub Copilot `gpt-5.4` | 公司订阅免费；口语化、保留术语、上下文连贯 |
| **TTS** | `edge-tts` + `zh-CN-YunyangNeural` / `zh-CN-XiaoxiaoNeural` | 免费白嫖 Microsoft Edge 协议；支持多音色；音质自然 |

> ⚠️ Azure diarize 模型每个 chunk 的 `A/B` 独立诊断，跨 chunk 不保证同一个人始终是 `A`。跑完用 `rename_speakers.py` 校一次即可。

---

## 🏃 一键跑

```bash
./scripts/pipeline.sh <slug> <youtube_url>
# 例：./scripts/pipeline.sh lex-fridman-ep-400 https://youtu.be/xxx
```

产物全部落到 `projects/<slug>/`：

```
projects/<slug>/
├── source/audio.mp3                    # yt-dlp 下的原音频
├── transcript/
│   ├── azure_chunks/                   # Azure 切片中间产物（.sse + .segs.json，断点续传用）
│   ├── dialog_en.json                  # Azure 合并后的英文对话（speaker + start/end）
│   └── dialog_zh.json                  # GPT-5.4 中文翻译
└── audio/
    ├── podcast_zh.mp3                  # 最终成品（.gitignored）
    └── tts_cache/                      # 单句 mp3 缓存（.gitignored）
```

---

## 📋 分步手动运行

### ① 下载
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  -o "projects/<slug>/source/audio.%(ext)s" <URL>
```

### ② STT + Diarize（Azure 一步到位）
```bash
./scripts/azure_transcribe_diarize.sh \
  projects/<slug>/source/audio.mp3 \
  projects/<slug>/transcript
# 直接产出 projects/<slug>/transcript/dialog_en.json
# 切片中间产物在 transcript/azure_chunks/（断点续传）
```

可选：给 speaker 起名
```bash
python3 scripts/rename_speakers.py \
  projects/<slug>/transcript/dialog_en.json \
  SPEAKER_00=Host SPEAKER_01=Guest
```

### ③ 翻译（Copilot GPT-5.4）
```bash
python3 -u scripts/translate_dialog_copilot.py \
  projects/<slug>/transcript/dialog_en.json \
  projects/<slug>/transcript/dialog_zh.json \
  --batch-size 8
```

支持**断点续传**（同输出文件时跳过已完成 batch）。

### ④ TTS 合成
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
- `ffmpeg`, `ffprobe`, `jq`, `curl`
- `yt-dlp`
- Python 包：`edge-tts`
- **Azure OpenAI 凭证** → `~/.openclaw/credentials/azure-openai.json`（需要 `deployments.diarize`）
- **GitHub Copilot token** → `~/.openclaw/credentials/github-copilot.token.json`

### 环境变量（可选）
```bash
export AZURE_OPENAI_CRED_FILE=~/.openclaw/credentials/azure-openai.json
export OPENCLAW_SECRETS=~/.openclaw/secrets/env.sh
export CHUNK_SEC=600   # Azure 切片长度，默认 10 分钟
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

Azure `gpt-4o-transcribe-diarize` ~ $0.006 / 分钟 → 一集长播客约 **$1 左右**。
翻译 Copilot 免费，TTS edge-tts 免费。

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
- **Status:** STT+Diarize ✅ · Translate ✅ · TTS ✅
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
