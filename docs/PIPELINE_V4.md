# Pipeline v4 — 多源播客制作管线

> 目的：把任何输入（中文视频 / 播客网页 / 英文 YouTube / 直链 mp3）→ 一条**能在播客客户端订阅播放的节目**。
> RSS item 必备：缩略图、简介、音频；按需：章节、字幕。

## 设计原则

1. **薄壳 + 厚 step**：`pipeline.sh` 只负责 dispatch，实际工作在 `steps/` 里
2. **统一中间产物 schema**：每一步的输入输出都是文件，可单独跑、可单独测
3. **永远不用 YouTube 自动字幕**：质量不可信，宁可走 STT 或要求用户提供
4. **AI 生成是兜底**：缩略图、简介都先尝试从源头抓

## 目录结构

```
scripts/
  pipeline.sh              # 入口：dispatch + 串联
  v4/
    ingest/                # 第 1 层：拿到 audio + meta + transcript（如有）
      detect.sh            # URL → adapter 名
      adapter_youtube.sh
      adapter_podcast_rss.sh
      adapter_dwarkesh.sh  # 站点专属：抓官方 transcript
      adapter_softskills.sh
      adapter_local.sh
    process/               # 第 2 层：可选的翻译 + TTS（仅非中文源）
      lane_passthrough.sh  # 中文源：不动音频，可选生成中文字幕（whisper 兜底）
      lane_translate.sh    # 英文源：transcript → 翻译 → TTS
    enrich/                # 第 3 层：简介、章节、封面
      summary_llm.sh       # LLM 生成中文简介
      chapters_sse.sh      # 仅 SSE 系列：从 transcript 切章节
      cover_fetch.sh       # 优先抓原图，失败再 AI
    publish/               # 第 4 层：GitHub Release + RSS + Pages
      release.sh
      rss_add_item.sh
      verify.sh            # 检查 URL 200、RSS valid
tests/
  fixtures/                # 极小测试素材
  test_ingest.sh
  test_enrich.sh
  test_publish.sh
  test_e2e.sh
projects/
  <slug>/
    source/
      audio.mp3            # 由 ingest 产出
      meta.json            # 统一元数据（schema 见下）
      transcript.json      # 官方 transcript（若 ingest 拿到）
      thumbnail.<ext>      # 原始封面（若有）
    transcript/            # 由 process 产出（同现有 pipeline）
    audio/                 # 由 process 产出（仅英文源 TTS 输出）
    blog/post.md           # 可选
    chapters.json          # 仅 SSE 系列
    summary.md             # 由 enrich/summary_llm 产出
    cover.png              # 由 enrich/cover_fetch 产出（已 resize 到 1400）
    .state.json            # 记录跑到哪一步、用了哪条 lane
```

## 统一 meta.json schema

```json
{
  "slug": "guoyu-claude-code-end-of-knowledge-work",
  "source_url": "https://www.youtube.com/watch?v=rwueq7n_3yA",
  "source_kind": "youtube" | "podcast_rss" | "dwarkesh" | "softskills" | "local" | "direct_mp3",
  "title": "...",
  "author": "郭宇 / 单向街东京",
  "lang": "zh" | "en" | "ja" | ...,
  "duration_sec": 2249,
  "thumbnail_url": "...",            // 原始可下载链接
  "has_official_transcript": true | false,
  "transcript_kind": "official_with_speakers" | "official_plain" | "youtube_auto" | "none",
  "series": "softskills_engineering" | null,
  "needs_chapters": true | false,    // 默认 false，仅 softskills 系列 true
  "lane": "passthrough" | "translate"
}
```

`lane` 决策表：

| `lang` | `has_official_transcript` | → `lane` |
|---|---|---|
| `zh` | * | `passthrough` |
| `en` | true (with speakers) | `translate`（用官方 transcript，不调 Azure） |
| `en` | false | `translate`（调 Azure STT） |

> ⚠️ 不信任 `youtube_auto`：英文 YouTube 自动字幕**不算** official transcript，仍走 STT。

## 各 adapter 行为

### `adapter_youtube.sh`
- `yt-dlp -x --audio-format mp3` → `source/audio.mp3`
- `yt-dlp --write-thumbnail` → `source/thumbnail.jpg`
- 元数据填 lang_hint（自动检测 / 用户提供）
- **永远不**抓 YouTube 字幕（自动 / 用户上传都不抓，质量不可信）
- 如果 URL 同时存在已知专属 adapter（如 dwarkesh 视频也在 YouTube），主入口优先 dispatch 到专属 adapter

### `adapter_dwarkesh.sh` / `adapter_softskills.sh`
- 抓官方网页 transcript（dwarkesh.com 已知有 speaker 标签）
- 用 token-stream 与音频对齐还原时间戳
- 输出 `source/transcript.json`，标 `has_official_transcript: true`
- 音频从 RSS enclosure 抓（不走 YouTube 二压）

### `adapter_podcast_rss.sh`
- 输入 RSS URL 或单集网页 → 找到 `<enclosure>` mp3 → 下载
- 如 RSS 含 `<podcast:transcript>` 标签 → 抓回来
- 无 transcript → 标 `transcript_kind: "none"`

### `adapter_local.sh`
- 本地文件 → 拷到 `source/`
- 用户必须提供 `--lang` `--title`

## Process Lanes

### `lane_passthrough.sh`（中文源）
1. 不动 `source/audio.mp3`，最终发布的就是它
2. 字幕：默认**不做**。用户显式 `--with-subs` 时用 **faster-whisper** 本地跑（**永远不**用 YouTube 自动字幕）

### `lane_translate.sh`（英文源）
分两支：
- **有官方 transcript**：直接进翻译/TTS，跳过 STT 和 LLM speaker reassign
- **无官方 transcript**：走现有完整 pipeline（Azure STT → LLM speaker → smart merge → 翻译 → 二次校验 → TTS）

## Enrich

### `summary_llm.sh`
- 输入：`transcript.json` 或 `dialog_zh.json`
- 输出：`summary.md`（200 字内中文 description）
- 用 Copilot GPT

### `chapters_sse.sh`（**仅 SSE**）
- 检测 `meta.series == "softskills_engineering"`，否则直接 exit 0
- 从 transcript 找 host 的 "OK so the next question..." 类切口，生成 chapters.json

### `cover_fetch.sh`
1. 有 `source/thumbnail.*` → resize 到 1400×1400 → 完
2. 没有 → 抓 source_url 的 og:image → 同上
3. 还没有 → AI 兜底（image_generate）

## Publish

### `release.sh`
- 上 GitHub Release，slug + version 自增
- 字幕 / 章节 一并放进 release assets

### `rss_add_item.sh`
- 模板化生成新 `<item>`
- 自动填 `<itunes:image>` / `<itunes:duration>` / `<podcast:chapters>`（若有）

### `verify.sh`
- `xmllint` 校验 RSS
- HEAD 请求所有 enclosure / thumbnail / transcript URL，全部 200

### `final_acceptance.sh`（每次发布最后一步，强制跑）
发布后等 GitHub Pages 部署（最多 90s 轮询），确认线上状态：
- ✅ `rss.xml` 里能找到本次 slug 的 `<item>`
- ✅ `<item>` 里 `<itunes:image>` 存在且 HEAD 200
- ✅ `<enclosure>` URL HEAD 200 且 `Content-Length` > 0
- ✅ 章节（若 SSE）/ 字幕（若英文源）URL 全部 200
- ❌ 任何一项失败 → 退出非 0，并打印失败清单

这步是「上线后真实可订阅」的硬保证，跳过它就不算发布完成。

## 测试策略

| 测试 | 形式 | 是否调真 API |
|---|---|---|
| `test_ingest.sh` | 跑各 adapter detect 逻辑 + mock URL | 否 |
| `test_enrich.sh` | 给假 transcript → 检查 summary 非空、chapters 仅 SSE 触发 | 调 1 次 LLM |
| `test_publish.sh` | 给假 project → 跑 verify | 否 |
| `test_e2e.sh` | 60s 短视频跑完整 lane_passthrough | 否（无 LLM/TTS） |
| `tests/integration_real.sh` | 手动跑，真实跑一遍英文 lane | 是 |
| `final_acceptance.sh` | 每次 publish 后自动跑，校验 RSS 上线 + 缩略图/音频 URL 200 | 是（HEAD 而已） |

## 兼容性

- 旧 `scripts/pipeline.sh` 保留，不动；新入口在 `scripts/pipeline.sh` 加 `--v4` flag 切到新管线
- 现有项目（sse-511 等）不重跑，新输入默认走 v4
- 旧 `azure_transcribe_diarize.sh` 等 step 脚本被 `lane_translate.sh` 复用，不重写
