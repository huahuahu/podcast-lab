# MAINTENANCE.md — podcast-lab 运维手册（活文档）

> 每次跑完一集或踩到新坑，**就来更新这份文件**。
> "每一次新看到的都是最新的逻辑"。
> 同时也是我（小爪）下次接手时的第一份参考。

---

## TL;DR — 一集新节目的标准流程

**开始之前：拿到本集的 EP 号**。查 docs/rss.xml 里最大的 `EPnn`，+1 就是本集号。
所有对外文案（release title / RSS title）都要以 `EPnn · ` 开头。
例：现在最新已发 `EP19 · ...`，下一集 = `EP20 · ...`。
快查脚本：`grep -oE 'EP[0-9]+' docs/rss.xml | sort -u | tail`。

假设拿到一个 YouTube 链接 `<URL>`：

```bash
cd ~/git/podcast-lab
CHUNK_SEC=1200 nohup ./scripts/pipeline.sh <slug> "<URL>" --lang en \
  > logs/<slug>.log 2>&1 < /dev/null & disown
```

> 应该不需要手动 export proxy——agent 运行环境默认已有；Azure 那步需要不走代理，`azure_transcribe_diarize.sh` 在包里自己 unset。

跑完后（产物 `projects/<slug>/audio/podcast_zh.mp3`）：

```bash
# 1. 写 release notes（看 dialog_zh.json 几句关键内容）
edit projects/<slug>/release_notes.md

# 2. cover（会自动镜像到 docs/assets/covers/）+ verify
bash scripts/enrich/cover_fetch.sh projects/<slug>
bash scripts/publish/verify_local.sh projects/<slug>

# 3. release
TAG=v0.X.0-<slug>
gh release create "$TAG" projects/<slug>/audio/podcast_zh.mp3 \
  --title "..." --notes-file projects/<slug>/release_notes.md

# 4. 改 docs/rss.xml：插一个 <item>，更新 lastBuildDate
edit docs/rss.xml

# 5. push
git add docs/rss.xml docs/assets/covers/<slug>.png && \
  git commit -m "release $TAG" && git push

# 6. 验收
bash scripts/publish/final_acceptance.sh <slug>
```

---

## 关键约束（容易忘）

### 1. 代理 — 默认不管，只有 Azure 需要 unset
- agent 进程默认已走代理（`HTTPS_PROXY` 等环境变量一般已组装好）→ yt-dlp / gh / curl 都能直接走
- **唯一需要不走代理的是 Azure**（SSE 连接走代理会被别）→ `azure_transcribe_diarize.sh` 已在包里自己 unset，不需要外部干预
- ⚠️ 别在外面 `unset HTTPS_PROXY`——会让同一句里调用的 yt-dlp / gh 掏不到网

### 2. Azure diarize 必须切片
- 名义 25MB 上限，但**实际单次能吃的音频远少于 25MB**（接近 1h 的音频会直接被拒，报 "Audio file might be corrupted or unsupported"）
- 稳妥配置：`CHUNK_SEC=1200`（20min/片，约 5MB）
- `CHUNK_SEC=0` = 整台一次塞，**目前不可行**，下次哪个版本 Azure 解禁了再说

### 3. edge-tts 音色名必须真实存在
- 加新音色到 `configs/series.json` 前一定 `python3 -m edge_tts --list-voices | grep zh-` 核对
- 我编过的不存在的音色：`zh-CN-YunhaoNeural`（不存在！会让整个 TTS 在第一句 Freeberg 那里崩掉）
- 当前可用普通话男声只有 4 个：Yunyang / Yunjian / Yunxi / Yunxia
- 要第 5 个男声 → 用 `zh-TW-YunJheNeural` 或 `zh-HK-WanLungNeural`（我们 Freeberg 用的就是这个）

### 4. 多人节目（>2 speakers）的 speaker 对齐
- Azure diarize 每个 chunk 内部独立判 A/B/C，**跨 chunk 编号不连贯**
- 所以 4 人 All-In 不能用 host/guest 二分类
- 解决：`scripts/align_speakers_multi.py` 用 GPT-5.4 + `series.json` 里的 `personas` 把每片 A/B/C 映射成全局人名
- `lane_translate.sh` 自动调用（前提：`series.multi_speaker = true` 且 `series.personas` 有人物画像）
- ⚠️ 局限：发言少 / 风格不鲜明的角色（如 Freeberg 在某些 chunk）会被标 Unknown，落到 fallback 女声

### 5. 集数编号 EPnn
- 所有 RSS / release title 都以 `EPnn · 中文标题` 开头。
- 两位数补零（`EP01`、`EP19`）。
- 发一集前先查下集号：
  ```bash
  grep -oE 'EP[0-9]+' docs/rss.xml | sort -u | tail -n 1
  ```
  加 1 即本集 EP 号。
- **release tag 编号规律：`EP{n}` 对应 `v0.{n+1}.0-<slug>`**（以下免再踩：EP22=v0.23.0，EP23=v0.24.0）。发前先看 `gh release list`。如果 tag 发错了，`gh release edit <old-tag> --tag <new-tag>` 能原地 rename。
- `gh release create --title` 也要带 EP 号（release notes 正文不强制）。
- 历史补编号：EP01-EP19 是在 EP19 之后用一段 Python 脚本按 `pubDate` 升序回填的；以后如果发现号位冲突或错位，可从 git 历史捞出来重跑。

### 6. 章节（add_chapters）
- `lane_translate.sh` 末尾根据 “meta.series == softskills_engineering” 或 **slug 前缀 `sse-`** 触发，所以本地 mp3 / direct_mp3 进来的 SSE 集也会自动分章。
- 内置 `detect_sse` 靠 LEAD 词则（“说下一个问题” / “亲爱的 SSE”等）划分 Q1/Q2，中译本偶尔会让 LEAD 变迷路。只识出 1–2 章时：
  1. 看 `transcript/dialog_zh.json` 手工找 Q1/Q2 入口 idx（提示词：“亲爱 / 这位听众 / Anon E. Mouse / 该不该…”）
  2. 读 `transcript/timings.json` 拿 `start_ms`，手写 `transcript/chapters.json`（样本：sse-512）
  3. 跑 `python3 scripts/add_chapters.py <proj>`，会读已有 chapters.json 重写 mp3。
  4. 重传 release（`gh release upload ... --clobber`）并同步 RSS 里的 `enclosure length`（看 `curl -sIL <mp3-url> | grep content-length`）。

### 7. 本地 / direct_mp3 进来的 “series=null” 坑
- `adapter_local.sh` / `direct_mp3` 写 `meta.json` 时 `series=null`。以前会让 `lane_translate` 最后那步 add_chapters 被跳过（于是 sse-512 首发没带章节）。
- 2026-05-12 已修：`lane_translate.sh` 识 “meta.series == softskills_engineering” **或** slug 前缀 `sse-`。以后添 adapter 时，最好同样考虑根据 slug 前缀推导 series。

### 8. 支持的源站点（`scripts/ingest/detect.sh`）
- `youtube` adapter 靠 yt-dlp，实际上 yt-dlp 支持的站都能复用，但 `detect.sh` 是白名单，需要在 case 里手动加路由。
- 已路由到 youtube adapter 的源：`youtube.com` / `youtu.be` / `bilibili.com` / `b23.tv`。
- 遇到新站（微博视频 / X / TikTok 等）先试 `yt-dlp --dump-single-json <url>`，能拿到 title/duration 就给 detect.sh 加一行路由到 youtube adapter 即可。

---

## 常见挂法 & 自救

| 现象 | 原因 | 处理 |
|---|---|---|
| `yt-dlp metadata failed` | 代理在外面被人手动 unset 了 | 别在 shell 里 unset；agent 默认已走代理 |
| `Audio file might be corrupted or unsupported` | Azure 单次吃太大 | 用 `CHUNK_SEC=1200` 切片 |
| 翻译挂在 batch X，`SSL: UNEXPECTED_EOF` | Copilot endpoint 偶发抖动 | **重跑同一条命令**（断点续传，已译的不重做）|
| 翻译挂 `IDE token expired` | 正常，脚本会自动续 token | 不用管 |
| TTS 进程突然消失（无报错） | 父进程被信号收走 | 重跑 lane_translate（cache 在） |
| `NoAudioReceived` 单句失败 | 某句翻译只剩个 `。` 之类 | **已修**：`multivoice_robust.py` 用 200ms / 500ms 静音兜底，不再中断 |
| Freeberg 突然变女声 | speaker 对齐落到 Unknown | 当前已知缺陷；后续要加跨片声纹比对 |

---

## 仓库结构（关键文件）

```
~/git/podcast-lab/
├─ scripts/
│   ├─ pipeline.sh                       # 一键入口（ingest → process → enrich → verify）
│   ├─ azure_transcribe_diarize.sh       # Azure STT，含 unset proxy + 切片 + SSE 解析
│   ├─ align_speakers_multi.py           # ⭐ 多人节目跨片 speaker 对齐
│   ├─ _merge_chunks.py                  # 合并 chunk segs.json，speaker 字段透传人名
│   ├─ smart_merge_dialog.py             # 合并背景音/同人短句
│   ├─ translate_dialog_copilot.py       # GPT-5.4 中译（断点续传）
│   ├─ reassign_speakers_llm.py          # 2 人节目跨 chunk 校 host/guest
│   ├─ audit_speakers_llm.py             # 2 人节目翻译后再校一次
│   ├─ prepare_multivoice.py             # 把 dialog_zh + voices 配置 → 喂给 multivoice
│   ├─ multivoice_robust.py              # ⭐ edge-tts 多音色合成 + 静音兜底
│   ├─ add_chapters.py                   # 给最终 mp3 加章节
│   ├─ ingest/                           # 各平台 adapter (youtube, local, …)
│   ├─ process/                          # decide_lane + lane_translate / lane_passthrough
│   │   └─ lane_translate.sh             # ⭐ 主流水线（含 multi-speaker hook）
│   ├─ enrich/cover_fetch.sh             # 封面，自动镜像到 docs/assets/covers/
│   ├─ publish/verify_local.sh           # 发布前 sanity check
│   ├─ publish/final_acceptance.sh       # GitHub Pages 上线后验收
│   └─ lib/meta.sh                       # 元数据读写小工具
│
├─ configs/series.json                   # ⭐ 系列 → personas + voices + 各种开关
├─ projects/<slug>/                      # 单集工作目录（gitignored 大文件）
│   ├─ source/audio.mp3, meta.json, thumbnail.jpg
│   ├─ transcript/
│   │   ├─ azure_chunks/                 # 每片 mp3 + segs.json
│   │   ├─ .speakers-aligned.json        # speaker 对齐缓存
│   │   ├─ dialog_en.json
│   │   ├─ dialog_zh.json
│   │   └─ timings.json
│   ├─ audio/
│   │   ├─ tts_cache/                    # 每句 mp3 缓存，gitignored
│   │   └─ podcast_zh.mp3                # 最终成品
│   ├─ cover.png
│   └─ release_notes.md
│
├─ docs/
│   ├─ rss.xml                           # ⭐ 发布到 GitHub Pages 的 podcast feed
│   ├─ assets/covers/<slug>.png
│   ├─ MAINTENANCE.md                    # ← 你正在读这个
│   └─ PIPELINE_V4.md                    # v4 设计文档
│
└─ logs/<slug>.log                       # 每集跑流水线的日志
```

---

## 凭证

- Azure: `~/.openclaw/credentials/azure-openai.json`
  - 必须有 `deployments.diarize`（值是 `gpt-4o-transcribe-diarize` 之类的部署名）
- GitHub Copilot token: `~/.openclaw/credentials/github-copilot.token.json`（用于翻译 + speaker 对齐）
- gh CLI: 已用 `huahuahu` 账号登录

---

## 维护规则（写给未来的我）

1. **每次跑完一集**，看下 `logs/<slug>.log` 有无新错误模式 → 写进上面"常见挂法"。
2. **每改一个脚本默认值**或加一个新机制 → 来更新对应章节，不要只 commit 代码。
3. **加新音色 / 新 series** → 直接到"配置约束"那段补一笔。
4. **删了某个废弃脚本** → 同步更新"仓库结构"。
5. 这个文件不要怕长。**搜得到 > 简洁**。
