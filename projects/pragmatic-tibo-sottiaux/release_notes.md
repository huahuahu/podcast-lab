# EP64 · Codex 是如何打造的：对话 Tibo Sottiaux · 完整中文版

## 节目简介

Gergely Orosz 对话 OpenAI 的 Tibo Sottiaux：从 Google 与研究基础设施经历，聊到 Codex 的早期探索、Rust 选择、开源的收益与代价，以及兼容其他模型的取舍。进一步讨论执行框架和模型如何共同演进、智能体时代的软件开发与代码审查、维护和架构成本的变化，以及 Codex 与 ChatGPT 合并的工程挑战，最后谈个人工作方式和给工程师的建议。保留完整赞助、开场和收尾。

- 原节目：The Pragmatic Engineer — Building Codex with Tibo Sottiaux（2026-09-09）。
- 主持人 / 嘉宾：Gergely Orosz / Tibo Sottiaux。
- 原节目链接：https://newsletter.pragmaticengineer.com/p/building-codex-with-tibo-sottiaux
- 完整中文版：1:07:45（4065.480 秒），128 kbps MP3，65,049,694 bytes；不是 Telegram 压缩版。
- 中文配音：Gergely 使用云希，Tibo 使用云扬；不仿原声。

# 中文版章节

- **00:00:00** 开场
- **00:07:10** 在 Google 工作
- **00:12:32** 是什么吸引 Tibo 加入 OpenAI
- **00:15:20** Codex 的早期岁月
- **00:18:04** 为什么 Codex 用 Rust 构建
- **00:20:48** 为什么 Codex 开源
- **00:24:34** Codex 为什么兼容其他模型
- **00:31:10** Harness 如何工作
- **00:35:01** Harness 与模型的改进
- **00:38:54** Codex 背后的软件开发生命周期
- **00:43:44** Codex 的代码审查
- **00:48:28** 维护与架构
- **00:52:09** AI 工具如何扩展工程师的能力
- **00:57:06** 合并：ChatGPT 与 Codex
- **01:01:07** Tibo 如何使用 Codex 与 ChatGPT
- **01:03:31** 给想从事 AI 的工程师的建议

按语义入口映射至中文 PCM 时间轴；原节目时钟和映射证据见 transcript/chapter_mapping.json。


## 制作与技术验收

使用官方逐字稿进行完整内容中译：75 个对话轮次覆盖 1528 个官方源片段，保留赞助、开场与收尾。133/133 个严格 TTS 片段通过完整文本边界匹配、哈希、全解码与非静音检查，无文本截短或失败静音占位；片段间 350ms 为设计停顿。原片和中文成品均全文件解码通过。16 章已嵌入 MP3，并提供 Podcasting 2.0 章节 JSON。

全片本机离线 Whisper 回转录的规范化字符序列相似度为 98.63%，首尾完整；这是语音覆盖辅助对照，**不是翻译准确率，也不等于人工听校**。

## 免责声明与质量边界

**非官方 AI 中文配音，不代表 The Pragmatic Engineer、OpenAI 或嘉宾官方发布或认可。** 原节目及内容权利归原权利人，原始内容请以上方官方节目为准。未完成全片人工试听、声纹验证或翻译准确率测量。官方逐字稿中少量混合说话人、跨轮断句，以及专名推断与英文术语发音仍有不确定性。广告、产品能力和规模数据为原节目表述，未经独立核实。

## 下载与订阅

- [完整中文 MP3](https://github.com/huahuahu/podcast-lab/releases/download/v0.65.0-pragmatic-tibo-sottiaux/podcast_zh.mp3)
- [16 章 JSON](https://github.com/huahuahu/podcast-lab/releases/download/v0.65.0-pragmatic-tibo-sottiaux/chapters.json)
- [RSS 订阅](https://huahuahu.github.io/podcast-lab/rss.xml)
- 音频 SHA-256：`fb1bb7228f05eb5f8ab27033d7908fb384b880537047b0628abe62d7f5154936`
