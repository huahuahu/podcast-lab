# EP37 · 把刹车踩下去：Dax Raad 谈 OpenCode 的爆炸增长与 AI 编程的真实代价

> The Pragmatic Engineer 2026 期，主持 Gergely Orosz × 嘉宾 Dax Raad（OpenCode 联合创始人）。

80 分钟的深度对谈，地点在迈阿密。OpenCode 是过去半年里增长最猛的开源 AI 编程 harness 之一，月活从年初的 65 万一路涨到接近 800 万。但有意思的是，开发它的人这次跑出来劝大家**慢下来**。

聊到的几条主线：
- Dax 的非典型路径：高中辍学创业、做电商 SaaS、转向 DevTools（SST），再到去年夏天突然蹿红的 OpenCode
- 为什么 OpenCode 起飞：定位「中立」——不绑大模型厂、不绑某家代码托管——而做 agent 的人不约而同需要这种瑞士军刀
- 推理（inference）到底有多赚钱：电费 + 折旧 = 成本下限，毛利率高得吓人，所以连 OpenAI 这种巨头都还在卷市场份额
- **Dax 那份引爆讨论的内部备忘录**：「我们在上线太多功能、塞进太多 hack，但我们并没有因此变快，只是感觉自己变快了」——给自己 startup 的现实泼冷水
- **"被压低的刺痛感" (the muted prickle)**：AI 之前你写 hack 自己会难受，下次还会记住；现在 agent 替你写了 hack，痛感外包给「未来的人」，判断力就这么慢慢钝化
- 怎么在每天被一千个人喊"你做错了"的情况下保住产品判断力
- 企业级 onboard（SSO / 权限 / 控制面）这些"无聊但必须"的事
- 为什么 quality 不能装：必须从每一个角落渗出来，包括做一些"看起来不理性"的事
- agent 时代怎么定义"程序员的好品位"——这是一辈子的事

## 制作说明
- 源音频：Substack 官方 mp3（80m05s，79MB）；YouTube 版本 `1VqKUrxR2C8`
- 转录：直接拿 Substack 官方带 word-level 时间戳和 speaker 标签的 transcription.json，跳过 Azure STT
  - 3 个 speaker cluster 自动归并成 2 人：SPEAKER_00（Gergely 念稿）+ SPEAKER_01（Gergely 访谈）→ Gergely；SPEAKER_02 → Dax
  - 1749 条原始 segment → 112 turns
- 翻译：GPT-5.4（via GitHub Copilot），dialog 级别批量
  - 修了几个 Whisper 错听：Doc Serrata → Dax Raad、Antisysys/Anthesitus → Antithesis、Entropic → Anthropic、Yeggie → Yegge
- TTS：edge-tts 多音色
  - Gergely Orosz → zh-CN-YunxiNeural（云希）
  - Dax Raad → zh-CN-YunyangNeural（云扬）
- 成片：97 分 46 秒 / 33.4 MB

## 致谢
- 原始内容版权归 The Pragmatic Engineer & Dax Raad 所有。本期为中文 AI 配音再创作，仅作语言可及性传播之用。
- Substack 原文：https://newsletter.pragmaticengineer.com/p/opencode
- 原视频：https://www.youtube.com/watch?v=1VqKUrxR2C8
- OpenCode：https://opencode.ai
