### 中文摘要

Dave Smith 和 Jameson Dance 在 Soft Skills Engineering 第 516 期回答两个问题：

1. **新来一个特别教条的 Scrum master，开 daily 像上幼儿园——我这是无理取闹吗？** 听众公司每天开站会，新 Scrum master 严格按工单一条一条问状态，整个会经常拖到 30 分钟。听众觉得 daily 应该是聊卡点 / 求助，而不是从头到尾复述工作。Dave / Jameson 的看法：(a) **这其实根本不是"会议太长"的问题，根本问题是「你们公司有个全职 Scrum master」**——他们俩的暴论是，凡是把 Scrum master 做成全职岗位的公司都会出问题，因为这个岗位真要做好其实只占 5%，剩下 95% 应该是工程师 / EM / PM 顺手做的事；(b) 全职 Scrum master 因为没别的可干，**会把流程当成自己的产品来"管理"**，于是就有了细到工单粒度的 daily；(c) 听众**不是无理取闹**，但单靠抱怨流程改不了——这是组织结构问题，得换工作或忍着；(d) 顺带把 LinkedIn 上自封的 agile coach、Scrum master 认证课统统嘲讽一遍。

2. **我们公司的产品经理根本不懂产品，作为工程师我该怎么办？** 听众在做内部平台 / 基础设施类产品，PM 和 EM 都不懂技术，skip-level 反而要求听众"确保这两个人被同步到"。Dave / Jameson 的看法：(a) 内部技术产品的 PM **必须有技术背景**，否则提不出有价值的路线图想法，最后只会退化成"传话项目经理"；(b) 这又是一个"表面上是某个人不行，实际上是组织把人放错岗位"的问题，**真要解决就只能重组**——所以打长期战，五到十年内自己升到 director 把架构改了（半开玩笑半认真）；(c) 短期实操建议是**给 PM 设个工程师面试编码门槛**，过不了就别再上白板指点江山；(d) 这一段聊到亚马逊那种 PMT (Product Manager Technical) vs TPM (Technical Program Manager) 的命名地狱，顺带承认产品经理本身就是行业里最难的工作之一，不是在贬低这个角色，而是在贬低**把不合适的人放到这个岗位**这件事。

### 制作流水线

原始来源：[Soft Skills Engineering Episode 516](https://softskills.audio/2026/06/08/episode-516-not-a-baby-and-my-product-manager-doesn't-know-the-product/)（36m50s 英文原片，34MB mp3）。

流程：本地 mp3 → Azure diarize STT（2 片切，CHUNK_SEC=1200）→ GPT 跨片 Host/Guest 重新归属 → smart-merge → GPT 翻译 → audit speakers → edge-tts 双男声（云希 Host + 云扬 Guest）→ SSE 章节自动分章，中文版约 36m。

封面由 image_generate 按 SSE 系列设计语言生成。
