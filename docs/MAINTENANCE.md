# MAINTENANCE.md — podcast-lab 运维手册（活文档）

> 每次跑完一集或踩到新坑，**就来更新这份文件**。
> "每一次新看到的都是最新的逻辑"。
> 同时也是我（小爪）下次接手时的第一份参考。

---

## TL;DR — 一集新节目的标准流程

**开始之前：拿到本集的 EP 号 + tag**。以前手算过两次，现在直接：
```bash
scripts/publish/next_ep.sh <slug>             # 看一眼
eval "$(scripts/publish/next_ep.sh -e <slug>)" # 导出 $EP / $EP_NUM / $TAG
```
所有对外文案（release title / RSS title）都要以 `$EP · ` 开头。
release tag 规律：`EP{n}` → `v0.{n+1}.0-<slug>`（务必走脚本，别手算。上次 EP23 手算成 v0.23.0 撞了 EP22）。

假设拿到一个 YouTube 链接 `<URL>`：

```bash
cd ~/git/podcast-lab
CHUNK_SEC=1200 nohup ./scripts/pipeline.sh <slug> "<URL>" --lang en \
  > logs/<slug>.log 2>&1 < /dev/null & disown
```

> 应该不需要手动 export proxy——agent 运行环境默认已有；Azure 那步需要不走代理，`azure_transcribe_diarize.sh` 在包里自己 unset。

跑完后（产物 `projects/<slug>/audio/podcast_zh.mp3`）：

```bash
# 1. 写 release notes
edit projects/<slug>/release_notes.md

# 2. cover 镜像 + verify
bash scripts/enrich/cover_fetch.sh projects/<slug>
bash scripts/publish/verify_local.sh projects/<slug>

# 3. release（上面 eval 过后 $TAG 已在环境里）
gh release create "$TAG" projects/<slug>/audio/podcast_zh.mp3 \
  --title "$EP · ..." --notes-file projects/<slug>/release_notes.md
# 撞 tag 了？`gh release edit <old> --tag <new>` 能原地 rename

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
- 所有 RSS / release title 都以 `EPnn · 中文标题` 开头，两位数补零。
- **拿 EP 号 + tag 走脚本**：`scripts/publish/next_ep.sh <slug>` （或 `-e` 形式给 eval）。
  - 脚本里编码的规律：`EP{n}` → `v0.{n+1}.0-<slug>`。历史有几集不严格合规律（如 EP21=v0.22.0），但当前最新几集都是。
  - tag 发错了：`gh release edit <old-tag> --tag <new-tag>` 能原地 rename。
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

### 9. Substack 官方 transcript
- **触发条件**：源是 Substack 托管的播客（如 Pragmatic Engineer、Lenny's Podcast、Stratechery 等），文章顶部按钮里有 "Transcript" 标签。
- **不要**手动找文章正文里的 transcript（很多发布人只在播放器里挂，正文里不贴）。
- **正确姿势**：抓页面 HTML，里面有签名好的 CloudFront 直链（24 小时有效）：
  ```bash
  curl -sL <substack-post-url> -o /tmp/post.html
  grep -oE 'https://substackcdn.com/video_upload/post/[0-9]+/[a-f0-9-]+/[0-9]+/(en\.vtt|transcription\.json|unaligned_transcription\.json)[^"]+' /tmp/post.html | sort -u
  ```
  三个文件：
  - `en.vtt` — 标准 WebVTT，带 `<v SPEAKER_XX>` 行内 speaker 标签
  - `transcription.json` — **最有价值**，word-level 时间戳 + 每词的 speaker（`SPEAKER_00`/`SPEAKER_01` ...）+ confidence score
  - `unaligned_transcription.json` — 备用，没对齐的 segments
  下载时记得带 referer：
  ```bash
  curl -sSL -A "Mozilla/5.0" -e "<substack-post-url>" -o transcription.json "<signed-url>"
  ```
- **转 dialog_en.json**：每个 segment 按 word.speaker 投票选出 segment 级 speaker，连续同 speaker 合并；SPEAKER_00/01 映射成真实人名（主持人/嘉宾）。160 段一集大概合并到 156 turns。
- **meta.json 配套**：
  - `has_official_transcript: true`、`transcript_kind: "substack"`
  - `voices: { "主持人名": "zh-CN-YunxiNeural", "嘉宾名": "zh-CN-YunyangNeural" }`（放在 `source/meta.json` 里）
- **lane_translate.sh 行为**：`has_official_transcript=true` 时自动跳过 Azure STT + reassign_speakers + audit_speakers（2026-06-13 修），直接走翻译 → TTS。
- **省的成本**：3h 长访谈一次省 ~30 min 切片转录 + 整套 Azure 调用费，speaker 标注还更准（官方 diarize > 我们二次清洗的）。
- **代码参考**：EP36 hightower-kubernetes-retiring，参考 `transcript/substack_*.{vtt,json}` 和当时的处理脚本片段。

### 10. B 站多 P 视频（playlist）手工拼接
- pipeline 默认仅拿 p1（yt-dlp 不加 `--yes-playlist` 时）。多 P 讲座（如 chenshangjun 5P 、qianliqun 2P）需要手工介入：
  ```bash
  cd projects/<slug>/source
  yt-dlp -x --audio-format mp3 --audio-quality 0 \
    -o "p%(playlist_index)s.%(ext)s" --yes-playlist "<url>"
  printf "file 'p1.mp3'\nfile 'p2.mp3'\n" > concat.txt   # 按顺序列全
  ffmpeg -y -f concat -safe 0 -i concat.txt -c copy audio.mp3
  trash p*.mp3 concat.txt
  ```
- meta.json 手寫（参考 qianliqun-gushi-xinbian），lane=passthrough，lang=zh，duration_sec 用 `ffprobe -show_entries format=duration` 拿。
- TODO: 以后可考虑给 youtube adapter 加 `MULTI_P=1` 开关自动走这个流程。

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
| 成片时长 << 源时长（缺前/后段） | Azure 某个 chunk 6 次重试全挂被 skip，pipeline 继续 | **kjzzd-s10e14 踩过**：chunk_001 全挂只剩 chunk_002，成片只有后 20min。verify_local 当时没卡住（它只看 source/audio.mp3）。补救：`trash chunk_NNN.mp3` 后**只重跑 azure_transcribe_diarize.sh**（已有 segs 的 chunk 会跳过），再删 `.smart-merged / .speakers-* / dialog_zh* / audio/podcast_zh.mp3 / tts_cache` 重跑 lane_translate。TODO：verify_local 应该比对 `audio/podcast_zh.mp3 时长 vs source 时长`，差距 > 10% 直接 FAIL |

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

## 踩过的新坑（待整理）

- **2026-06-11 EP35 查屏球**：B 站 `yt-dlp` 又开始全员 `HTTP 412 Precondition Failed`（任意 BV、任意 cookies、impersonate chrome 都救不了，2026-06-09 版本也一样）。
  - 救场方案：**BBDown**（C# 写的 B 站专用下载器）。装法：从 `gh release view -R nilaoda/BBDown` 拿 osx-arm64 zip，解到 `/tmp/bbdown/BBDown`，chmod +x。
  - 用法：`/tmp/bbdown/BBDown --audio-only --work-dir <proj>/source -F audio <url>` → 出 `audio.m4a` → ffmpeg 转 mp3。
  - 元数据走 B 站官方 API：`curl -A Mozilla 'https://api.bilibili.com/x/web-interface/view?bvid=<BV>'`，title/pic/duration/owner 都在 `.data` 里，比 yt-dlp 稳。
  - meta.json / cover_fetch.sh / verify_local.sh 走老流程；release_notes 手写；rss 手插。
  - **TODO**：要么给 `adapter_youtube.sh` 加 BBDown fallback，要么独立写一个 `adapter_bilibili.sh`（推荐后者，B 站走专用工具更可控）。

- **2026-06-02 EP515**：直接把 SSE 的 mp3 enclosure URL（`https://dts.podtrac.com/redirect.mp3/download.softskills.audio/sse-515.mp3?source=rss`）喂给 pipeline，`detect.sh` 看到 `softskills.audio` 就返回 adapter=softskills，但 `adapter_softskills.sh` 还没实现，直接 `❌ adapter not implemented yet: softskills` 退出。
  - **临时绕路**：`curl -L -o /tmp/xxx.mp3 <enclosure>` 下载本地，再 `pipeline.sh <slug> /tmp/xxx.mp3 --lang en` 走 local adapter。
  - **TODO**：要么实现 `adapter_softskills.sh`（其实可以直接当 direct_mp3 处理），要么把 detect.sh 的 softskills 模式收窄到网页（`*softskills.audio/2*` 之类），让 enclosure 直链落到 direct_mp3。

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
