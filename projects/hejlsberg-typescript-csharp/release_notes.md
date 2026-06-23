# EP26 · Anders Hejlsberg：从 Turbo Pascal 到 C# 到 TypeScript

Anders Hejlsberg 在 Gergely Orosz 的 Pragmatic Engineer 播客上聊自己 40 年语言设计生涯。一个人接连主导了 Turbo Pascal、Delphi、C# 和 TypeScript——历史上"最被广泛使用的编程语言"里有三种出自他手。81 分钟干货。

三段职业生涯的幕后故事：

- **Turbo Pascal / Borland**：丹麦高中时代被 HP 2100 磁芯内存机点燃，自己写编译器卖给爱好者，后来被 Borland 收编。Turbo Pascal 当年用 49.99 美元的价格 + 整套 IDE，把"编译器是上千刀的工业品"这件事一锤砸碎。
- **C# / Microsoft**：Sun 和 Microsoft 围绕 Java 的那场官司是 C# 真正的起点——没有那场诉讼，Anders 不会被挖去 Microsoft，C# 也很可能不会被立项。聊了 async/await 状态机改写、LINQ、records、跨平台 .NET 的取舍。
- **TypeScript**：在 Microsoft 内部把它开源是当年的大事；为什么 TypeScript 选择 *结构化类型* 而不是名义类型；为什么编译器最近用 Go 重写而不是 Rust 或者 C#。

还有一些贯穿三段经历的元观点：

- **IDE 和编程语言密不可分**——从 Turbo Pascal 的集成开发环境到今天 TypeScript + VS Code 的语言服务，"语言"的边界其实一直包括工具。
- **AI 不改变语言设计的本质**：模型再强，下面那一层"代码到底要表达什么"还是要靠人想清楚；agents 越多，"审代码、搭架构、把握全局"的人就越重要。
- **小团队 > 委员会**：真正出色的技术成果几乎都来自一小撮愿意互相挑刺的人。

---

🎙 双人对话版自动配音（Host = Xiaoxiao 女声 / Guest = Yunyang 男声 = Anders）。

⚙️ 流水线: yt-dlp → Azure `gpt-4o-transcribe-diarize`（CHUNK_SEC=1200，约 76 分钟英文原片切 4 片）→ GPT-5.4 中译（244 turns）→ host/guest LLM 对齐 + audit → edge-tts 双音色合成，中文版 81m14s。

📺 原片：[TypeScript, C# and Turbo Pascal with Anders Hejlsberg](https://www.youtube.com/watch?v=K-Xv8D8NjTk) — The Pragmatic Engineer / Gergely Orosz (76m01s)
