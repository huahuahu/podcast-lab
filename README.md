# Podcast Lab 🎧

把任何输入（YouTube、播客 RSS、本地文件、中文视频…）→ 一条**能在播客客户端订阅播放的节目**：mp3 + 封面 + 简介，按需翻译/字幕/章节。

---

## 🚀 管线总览（v4）

```
input (URL / 本地文件)
    │
    ▼
① ingest      → source/audio.mp3 + source/meta.json (+ transcript / thumbnail 如有)
    │
    ▼
② process     → 按 lane 决策
   ├─ passthrough（中文源）：不动音频，可选生成中文字幕
   └─ translate（英文源）：transcript → 翻译 → TTS → audio/podcast_zh.mp3
    │
    ▼
③ enrich      → cover.png（抓原图，失败 AI 兜底）+ summary.md
    │
    ▼
④ verify_local → 发布前最后一关
    │
    ▼
（手动）GitHub Release + docs/rss.xml + final_acceptance
```

设计原则：薄壳 + 厚 step。`pipeline.sh` 只 dispatch，实际工作在 `scripts/v4/{ingest,process,enrich,publish}/` 里。每一步输入输出都是文件，可单独跑、可单独测。

详细设计见 [`docs/PIPELINE_V4.md`](docs/PIPELINE_V4.md)。

---

## 🏃 一键跑

```bash
./scripts/pipeline.sh <slug> <url-or-path> [--lang zh|en|...] [--with-subs]

# 例：
./scripts/pipeline.sh lex-fridman-ep-400 https://youtu.be/xxx --lang en
./scripts/pipeline.sh guoyu-claude-code  https://www.youtube.com/watch?v=xxx --lang zh
./scripts/pipeline.sh local-talk         /path/to/audio.mp3 --lang zh
```

入口做的事：

1. `v4/ingest/detect.sh` 识别 URL → 选 adapter（youtube / local / …）下载音频和元数据
2. `v4/process/decide_lane.sh` 按 `meta.lang` + 是否有官方 transcript 决定 lane
3. `v4/enrich/cover_fetch.sh` 准备封面（原图 → resize → AI 兜底）
4. `v4/publish/verify_local.sh` 检查产物齐全

产物全部落到 `projects/<slug>/`：

```
projects/<slug>/
├── source/
│   ├── audio.mp3        # ingest 产出
│   ├── meta.json        # 统一元数据
│   ├── transcript.json  # 官方 transcript（若有）
│   └── thumbnail.*      # 原始封面（若有）
├── transcript/          # 仅 translate lane
│   ├── azure_chunks/    # Azure 切片中间产物（断点续传）
│   ├── dialog_en.json
│   └── dialog_zh.json
├── audio/
│   ├── podcast_zh.mp3   # 仅 translate lane（中文成品）
│   └── tts_cache/
├── cover.png            # 1400×1400
├── summary.md
└── chapters.json        # 仅 SSE 系列
```

---

## 🛠 单独跑某一步

每个 step 都可以独立调：

```bash
# 抓素材
scripts/v4/ingest/adapter_youtube.sh projects/<slug> <URL> en

# 决定 lane
scripts/v4/process/decide_lane.sh projects/<slug>

# 跑翻译 lane（英文源完整流程）
scripts/v4/process/lane_translate.sh projects/<slug>

# 中文源直通（可选生成字幕）
scripts/v4/process/lane_passthrough.sh projects/<slug> --with-subs

# 抓封面
scripts/v4/enrich/cover_fetch.sh projects/<slug>

# 本地校验
scripts/v4/publish/verify_local.sh projects/<slug>
```

translate lane 内部串的就是这些底层脚本（保留下来供 lane 复用）：

| 脚本 | 用途 |
|---|---|
| `azure_transcribe_diarize.sh` | Azure `gpt-4o-transcribe-diarize` 切片 STT + 说话人 |
| `reassign_speakers_llm.py` | LLM 跨 chunk 校正 speaker 标签 |
| `smart_merge_dialog.py` | 合并相邻同 speaker 句子 |
| `translate_dialog_copilot.py` | Copilot GPT 翻译，支持断点续传 |
| `audit_speakers_llm.py` | 翻译后再校验 speaker |
| `prepare_multivoice.py` + `multivoice_robust.py` | edge-tts 多音色合成 |
| `add_chapters.py` | 生成章节（仅 SSE 系列） |
| `rename_speakers.py` | 给 speaker 起名（手工辅助） |

### 选型理由

| 环节 | 选用 | 为什么 |
|---|---|---|
| **STT + Diarize** | Azure `gpt-4o-transcribe-diarize`（SSE 流式） | 一个 API 同时返回文字 + 时间戳 + 说话人。**访问 Azure 要直连**，长 SSE 走 VPN/proxy 容易断；跑前 `unset HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy` |
| **翻译** | GitHub Copilot `gpt-5.4` | 公司订阅免费；口语化、保留术语、上下文连贯 |
| **TTS** | `edge-tts` + `zh-CN-YunyangNeural` / `zh-CN-XiaoxiaoNeural` | 免费白嫖，多音色，音质自然 |

> ⚠️ Azure diarize 每个 chunk 的 `A/B` 标签独立，跨 chunk 不保证同一个人始终是 `A`。跑完 `reassign_speakers_llm.py` / `rename_speakers.py` 校一次。

> ⚠️ **永远不用 YouTube 自动字幕**。质量不可信，宁可走 STT 或要求用户提供官方 transcript。

---

## 🖼 单集封面图约定

每集都要单独生成一张封面，不要复用系列封面 `assets/cover.png`。

- 文件名：`docs/assets/<slug>.jpg`（修订版用 `<slug>-v2.jpg`）
- 尺寸：1400×1400（iTunes 最低 1400×1400，最大 3000×3000）
- 来源：`enrich/cover_fetch.sh` 自动处理（原图 thumbnail → og:image → AI 兜底），手工复用时优先 YouTube `https://i.ytimg.com/vi/<VIDEO_ID>/maxresdefault.jpg`

YouTube 缩略图（16:9）转方图（高斯模糊背景 + 原图居中）：

```bash
curl -sL -o /tmp/yt.jpg "https://i.ytimg.com/vi/<VIDEO_ID>/maxresdefault.jpg"
ffmpeg -y -i /tmp/yt.jpg \
  -filter_complex "[0:v]scale=1400:1400:force_original_aspect_ratio=increase,crop=1400:1400,gblur=sigma=30[bg];[0:v]scale=1400:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" \
  -q:v 2 docs/assets/<slug>.jpg
```

`maxresdefault` 偶尔 404 → 降级到 `hqdefault.jpg`。

---

## 📝 RSS `<podcast:transcript>` 约定

Overcast 等只取第一个 transcript 的 app 只会拿到顶部那条，所以顺序固定：

1. **VTT 在前，SRT 在后** — VTT 是 W3C 标准，podcast 生态支持更广
2. **VTT 加 `rel="captions"`** — 明确告诉 app 这是同步字幕（caption），Podverse 等会走 caption 模式
3. **SRT 不加 rel** — 作为文稿备胎

```xml
<podcast:transcript url=".../zh.vtt"        type="text/vtt"        language="zh" rel="captions"/>
<podcast:transcript url=".../bilingual.vtt" type="text/vtt"        language="zh" rel="captions"/>
<podcast:transcript url=".../zh.srt"        type="application/srt" language="zh"/>
<podcast:transcript url=".../bilingual.srt" type="application/srt" language="zh"/>
```

校验 XML：`python3 -c "import xml.etree.ElementTree as ET; ET.parse('docs/rss.xml')"`

---

## 📦 发布流程

`pipeline.sh` 跑完是「素材就绪 + 本地校验通过」。**正式上线**还要：

```bash
# 1) 上 Release
gh release create v0.X.0-<slug> \
  --repo huahuahu/podcast-lab \
  --title "..." --notes "..." \
  projects/<slug>/audio/podcast_zh.mp3 \
  projects/<slug>/cover.png

# 2) 编辑 docs/rss.xml 加 <item>，引用 cover + audio + transcript URL
# 3) git push（触发 GitHub Pages 部署）
# 4) 最后一关：等 Pages 上线 + 校验 RSS
scripts/v4/publish/final_acceptance.sh <slug>
```

`final_acceptance.sh` 会轮询 GitHub Pages（最多 90s），确保：
- ✅ RSS 里能找到本次 slug 的 `<item>`
- ✅ `<itunes:image>` HEAD 200
- ✅ `<enclosure>` HEAD 200 且 `Content-Length` > 0
- ✅ 章节 / 字幕（若有）URL 全部 200

跳过它就不算发布完成。

---

## 🔑 环境要求

### 必需
- `python3` ≥ 3.10
- `ffmpeg`, `ffprobe`, `jq`, `curl`, `yt-dlp`
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

## 🎙 音色参考

内置默认（在 `scripts/prepare_multivoice.py` 里改）：

| Speaker | Voice | 描述 |
|---|---|---|
| `Ethan` / `guest` | `zh-CN-YunyangNeural` | 云扬，男声，新闻播报风 |
| `Ryan` / `host`   | `zh-CN-XiaoxiaoNeural` | 晓晓，女声，主持人感 |
| `narrator`        | `zh-CN-YunxiNeural` | 云希，温和男声 |
| 其他              | `zh-CN-XiaoyiNeural` | 晓伊 |

---

## 💰 成本参考（2:50h 英文播客）

Azure `gpt-4o-transcribe-diarize` ~ $0.006 / 分钟 → 一集长播客约 **$1**。翻译 Copilot 免费，TTS edge-tts 免费。

---

## 🗂 Slug 命名

`<作者>-<主题>` 或 `<节目>-<编号>`，小写连字符：
- `ethan-evans-corp-politics`
- `lex-fridman-ep-400`
- `huberman-sleep-science`

---

## 🎬 已完成项目

- [ai-code-slop-coding-tool](./projects/ai-code-slop-coding-tool/) — 治 AI 代码肇邋的工具 (8m56s)
  → 🎧 [下载中文版](https://github.com/huahuahu/podcast-lab/releases/tag/v0.13.0-ai-code-slop-coding-tool)
- [dwarkesh-jensen-huang-2026](./projects/dwarkesh-jensen-huang-2026/) — Dwarkesh × Jensen Huang：Nvidia 的供应链护城河 (1h41m)
  → 🎧 [下载中文版](https://github.com/huahuahu/podcast-lab/releases/tag/v0.12.0-dwarkesh-jensen-huang-2026)
- [ethan-evans-corp-politics](./projects/ethan-evans-corp-politics/) — Retired Amazon VP 聊公司政治 (2h42m)
  → 🎧 [下载中文版](https://github.com/huahuahu/podcast-lab/releases/tag/v0.1.0-ethan-evans-zh)
