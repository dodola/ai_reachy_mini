# Reachy Mini 社区调研

> 更新时间：2026-05-12

---

## Twitter/X 热门推文 & 项目

### 1. Reachy Mini 全新大脑 — 开源语音后端 (2026-05-08)
- **作者**: @andimarafioti — 360 likes
- **内容**: 发布了完全开源的 Reachy Mini 语音后端。48小时内 3,000+ 台机器人已接入 Hugging Face 部署的版本。此前实时语音 API 每天要 $20+，现在免费了。
- **链接**: https://x.com/andimarafioti/status/2052746355777437730

### 2. Clement Delangue (HF CEO) 组装新版 Reachy Mini (2026-04-29)
- **作者**: @ClementDelangue
- **内容**: 用 HF 的 agent (ml intern) 不到一小时就创建了第一个 app，支持在真机和仿真中运行。
- **链接**: https://x.com/ClementDelangue/status/2049594975235490059

### 3. Computer Use Agent 嵌入 Reachy Mini (2026-02-18)
- **作者**: @reachymini
- **内容**: POC：把 Computer Use Agent 直接嵌入 Reachy Mini，实现语音控制电脑自动化。
- **链接**: https://x.com/reachymini

### 4. Gemini Live 集成 (2026-04)
- **作者**: @thorwebdev
- **内容**: 与 Hugging Face、Pollen Robotics 合作，将 Gemini Live 带到 Reachy Mini 对话应用。
- **链接**: https://x.com/thorwebdev/status/2043707152699740383

### 5. D&D 地下城主机器人 (2026-03-23)
- **作者**: @keval_shah14
- **内容**: 把 Reachy Mini 变成真人地下城主：听语音、角色扮演说话、追踪位置、掷骰子、跑完整 D&D 战役。
- **链接**: https://x.com/keval_shah14/status/2035873832570093760

### 6. 跳舞机器人 — 父女项目 (2026-03-22)
- **作者**: @karsenthil — 75 likes
- **内容**: 8岁女儿和爸爸用 Claude + Suno + Reachy Mini SDK 做了一个跳舞机器人：问 Reachy 想听什么歌 → AI 生成音乐 → 机器人跳舞。
- **链接**: https://x.com/karsenthil/status/2035827705988395509

### 7. Nvidia + Pollen Robotics App 大赛
- **内容**: 75 个参赛应用，社区投票选出 winner。

### 8. Reachy Mini 两个版本 (2026-03-24)
- **作者**: @cnxsoft
- **内容**: Reachy Mini Lite (连电脑) 和 Reachy Mini Wireless (树莓派 CM4，WiFi/蓝牙/加速度计/电池)。
- **链接**: https://x.com/cnxsoft/status/2036376253960429667

---

## Twitter 关键账号

| 账号 | 链接 |
|------|------|
| @reachymini (官方) | https://x.com/reachymini |
| @pollenrobotics | https://x.com/pollenrobotics |
| #ReachyMini 话题 | https://x.com/hashtag/ReachyMini |
| Reachy Mini Community | https://x.com/i/communities/2027943783036584438 |

---

## Twitter 趋势方向

- **语音 Agent** 是最热门方向（开源语音后端、Gemini Live、Computer Use）
- **创意互动**：D&D DM、跳舞机器人、音乐生成
- **低门槛开发**：HF agent 一小时内创建 app
- 社区活跃度在快速上升，3000+ 台机器人已联网

---

## GitHub 相关项目 (26 个公开仓库)

### 官方 & 高星项目

| 项目 | Stars | 描述 | 语言 |
|------|-------|------|------|
| [pollen-robotics/reachy-mini-motor-controller](https://github.com/pollen-robotics/reachy-mini-motor-controller) | 64 | 底层电机通信控制 (Dynamixel) | Rust |
| [algoryn-nl/reachy-mini-esp32-eyes](https://github.com/algoryn-nl/reachy-mini-esp32-eyes) | 27 | ESP32 可控眼睛硬件 mod | C |
| [dwain-barnes/reachy_mini_conversation_app_local](https://github.com/dwain-barnes/reachy_mini_conversation_app_local) | 11 | 完全本地版对话 app (Ollama/LM Studio) | Python |
| [iizukak/awesome-reachy-mini](https://github.com/iizukak/awesome-reachy-mini) | 8 | Reachy Mini 资源精选列表 | - |
| [iizukak/reachy_mini_turbowarp](https://github.com/iizukak/reachy_mini_turbowarp) | 8 | TurboWarp/Scratch 3.0 控制扩展 | TypeScript |
| [ha-china/ha-reachy-mini-card](https://github.com/ha-china/ha-reachy-mini-card) | 5 | Home Assistant 仪表盘卡片 | JavaScript |

### AI Agent / 语音交互

| 项目 | Stars | 描述 | 语言 |
|------|-------|------|------|
| [phola/reachy-brain](https://github.com/phola/reachy-brain) | 3 | 本地 AI 大脑：Whisper STT + Gemma 4 + Kokoro TTS (Apple Silicon) | Python |
| [thc1006/reachy-mini-agent](https://github.com/thc1006/reachy-mini-agent) | 1 | 实时语音+视觉 AI Agent：Ollama + Whisper + Kokoro/Edge TTS + WebRTC | Python |
| [haasonsaas/jarvis](https://github.com/haasonsaas/jarvis) | 0 | 具身 AI 助手：30Hz 存在感应、智能家居控制、多用户记忆 | Python |
| [Maelwalser/Reachy_gemini_with_facial_recognition](https://github.com/Maelwalser/Reachy_gemini_with_facial_recognition) | 0 | Gemini + 人脸识别 + RAG + 模仿模式 | Python |
| [margauxxhu/reachy-coach](https://github.com/margauxxhu/reachy-coach) | 0 | 演讲教练：Whisper 测语速/填充词，Claude 反馈 | Python |

### 创意应用

| 项目 | Stars | 描述 | 语言 |
|------|-------|------|------|
| [CharlesCNorton/reachy-dance](https://github.com/CharlesCNorton/reachy-dance) | 0 | 节拍同步跳舞 | Python |
| [brucechou1983/chord-guessing-game](https://github.com/brucechou1983/chord-guessing-game) | 0 | 音乐听力训练游戏 | Python |
| [brucechou1983/reachy_mini_conversation_app_zh-TW](https://github.com/brucechou1983/reachy_mini_conversation_app_zh-TW) | 2 | 台湾繁体中文版对话 app | Python |
| [halton/coco](https://github.com/halton/coco) | 0 | 可可 — 中文学习伴侣机器人 | Python |

### 行业应用

| 项目 | Stars | 描述 | 语言 |
|------|-------|------|------|
| [amitlals/sap-warehouse-copilot](https://github.com/amitlals/sap-warehouse-copilot) | 1 | SAP 仓库语音副驾：NVIDIA NIM + Riva Speech AI | Python |
| [arkalia-luna-system/bbia-sim](https://github.com/arkalia-luna-system/bbia-sim) | 0 | 认知机器人引擎：AI 情感 + 视觉 + MuJoCo 仿真 | Python |

### SDK & 工具

| 项目 | Stars | 描述 | 语言 |
|------|-------|------|------|
| [akshaykokane/reachy_mini-csharp-sdk](https://github.com/akshaykokane/reachy_mini-csharp-sdk) | 2 | 非官方 .NET SDK | C# |
| [mysticrenji/hello-reachy-mini](https://github.com/mysticrenji/hello-reachy-mini) | 1 | 工程角度探索 Reachy Mini | Python |

---

## 关键资源链接

| 资源 | 链接 |
|------|------|
| 官方 SDK | https://github.com/pollen-robotics/reachy_mini |
| HF Space (仿真) | https://huggingface.co/spaces/pollen-robotics/Reachy_Mini |
| 官网 | https://reachymini.dev |
| Seeed Studio 合作博客 | https://www.seeedstudio.com/blog/2026/01/06/reachy-mini-an-open-journey-built-together-with-hugging-face-pollen-robotics-seeed-studio/ |

---

## 最值得关注的项目

1. **reachy-mini-agent** — 今天还在更新，全栈本地 AI agent (Ollama + Whisper + Kokoro + WebRTC)
2. **reachy-brain** — Apple Silicon 本地推理，Whisper + Gemma 4 + Kokoro TTS
3. **jarvis** — 智家居集成，30Hz 存在感应循环
4. **reachy-mini-conversation-app-local** — 完全本地版对话 app，无需云端 API
5. **awesome-reachy-mini** — 资源精选列表，持续更新
