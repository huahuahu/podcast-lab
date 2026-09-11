# EP64 发布完成与公网验收

- 标题：EP64 · Codex 是如何打造的：对话 Tibo Sottiaux · 完整中文版
- Tag：`v0.65.0-pragmatic-tibo-sottiaux`（复用已有公开非草稿 Release，未创建/上传/改 tag/重做音频）
- 验收时间（UTC）：2026-09-11T09:38:29.210024+00:00
- RSS 与封面发布提交：`08b543f9cbaf36caecbd193d1054cb47c0aa78a5`；已确认 origin/master 一致。
- GitHub Pages 部署成功：https://github.com/huahuahu/podcast-lab/actions/runs/34585107074

## 公开链接

- release: https://github.com/huahuahu/podcast-lab/releases/tag/v0.65.0-pragmatic-tibo-sottiaux
- audio: https://github.com/huahuahu/podcast-lab/releases/download/v0.65.0-pragmatic-tibo-sottiaux/podcast_zh.mp3
- chapters: https://github.com/huahuahu/podcast-lab/releases/download/v0.65.0-pragmatic-tibo-sottiaux/chapters.json
- cover: https://huahuahu.github.io/podcast-lab/assets/covers/pragmatic-tibo-sottiaux.png
- rss: https://huahuahu.github.io/podcast-lab/rss.xml
- source: https://newsletter.pragmaticengineer.com/p/building-codex-with-tibo-sottiaux

## 实测结果

| 项目 | 结果 |
|---|---|
| RSS | HTTP 200，64 个 item，EP64 GUID 唯一，enclosure length=65049694 |
| 历史条目 | 发布前 63 个 item 按顺序逐项比较完全一致；公开 RSS 与本地字节一致 |
| 音频 | 公开 GET HTTP 200，完整下载 65,049,694 bytes |
| 音频 SHA-256 | `fb1bb7228f05eb5f8ab27033d7908fb384b880537047b0628abe62d7f5154936`，与本地及 Release digest 一致 |
| 封面 | 公开 GET HTTP 200，413,506 bytes，内容与本地完全相同 |
| chapters.json | HTTP 200，1,417 bytes，可解析，16 章，与本地完全相同 |
| final_acceptance.sh | 退出码 0，音频/封面/章节 HEAD 全部 200 |
| 既有用户修改 | MAINTENANCE 及两个 LLM 脚本 SHA-256 保持不变，未纳入提交 |

音频 1:07:45，云希/云扬双人，16 章。非官方 AI 中文配音；未全片人工听校，ASR 相似度不代表翻译准确率。

## 过程边界

Pages 部署完成前首次封面 GET 为 404，部署成功后重新读取为 200。验收脚本在等待 RSS 时有既有整数表达式警告，随后通过；未修改公共脚本，另用 XML 解析补核全部历史条目、资源 URL 和大小。没有变更代理、网络、服务或读取凭据。

详细机器证据：`evidence/published-verification.json`；原本地 `delivery_report.md` / `acceptance.json` 保留为发布前历史，不代表当前发布状态。全部音频和中间缓存保留。发布证据提交使用明确文件清单，不包含其他项目或无关 untracked。
