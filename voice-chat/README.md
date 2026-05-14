# Voice Chat for Reachy Mini

让 Reachy Mini 通过 xiaozhi 协议实现 AI 语音聊天，利用机器人自带麦克风和音箱。

## 功能

- 🎤 **语音交互**: 通过 xiaozhi 服务器实现 ASR → LLM → TTS 完整流程
- 👂 **唤醒词**: 离线检测 "okay_nabu" 等唤醒词（可扩展）
- 📍 **声源追踪**: 检测说话人方向，头部自动转向
- 🤖 **MCP 关节控制**: AI 可以控制机器人头部、天线、身体和情绪动作
- 🔇 **停止词**: 检测 "stop" 停止词中断播放

## 架构

```
Reachy Mini 硬件
├── 麦克风阵列 → SDK get_audio_sample() → 16kHz PCM
├── 扬声器     ← SDK push_audio_sample() ← 16kHz PCM
└── 电机       ← SDK goto_target/set_target

voice-chat/ (Python 服务)
├── 麦克风 → 512采样块 → 唤醒词检测 → 触发 WS 连接
├── 麦克风 → OPUS编码 → WebSocket → xiaozhi 服务器
├── WebSocket → OPUS解码 → 重采样 → 扬声器
├── MCP 工具调用 → SDK 动作控制
└── DoA → 声源追踪 → 头部转向
```

## 安装

### 1. 系统依赖

```bash
# Raspberry Pi / 嵌入式 Linux
sudo apt-get install libopus0 libopus-dev

# Python 依赖
pip install -r requirements.txt

# 安装 reachy-mini-sdk
pip install reachy-mini-sdk
```

### 2. 配置

```bash
# 复制并编辑配置文件
cp config.yaml config.local.yaml
# 填入你的 xiaozhi.me token
```

### 3. 运行

```bash
python main.py --config config.local.yaml
# 或使用默认配置
python main.py
# 启用调试日志
python main.py -v
```

## 配置说明

| 项目 | 默认值 | 说明 |
|------|--------|------|
| `xiaozhi.server_url` | `wss://api.xiaozhi.me/v1/` | xiaozhi 服务器地址 |
| `xiaozhi.token` | `""` | 从 xiaozhi.me 获取的认证 token |
| `xiaozhi.protocol_version` | `3` | 协议版本 (1=raw, 2=+timestamp, 3=lightweight) |
| `audio.input_sample_rate` | `16000` | 麦克风采样率 |
| `audio.block_size` | `512` | 每次读取采样数 (32ms) |
| `wakeword.model` | `okay_nabu` | 唤醒词模型 |
| `wakeword.stop_model` | `stop` | 停止词模型 |
| `reachy.connection_mode` | `auto` | 连接模式 (auto/localhost_only/network) |
| `reachy.media_backend` | `local` | 媒体后端 (local/webrtc/no_media) |
| `motion.look_at_speaker` | `true` | 声源追踪 |

## MCP 工具

AI 可以通过以下工具控制机器人：

| 工具 | 说明 | 参数 |
|------|------|------|
| `reachy.goto_pose` | 平滑移动到指定姿态 | head, antennas, body_yaw, duration, method |
| `reachy.set_target` | 立即设置目标位置 | head, antennas, body_yaw |
| `reachy.emote` | 播放预设情绪 | name (happy/sad/curious/surprised/angry/neutral/thinking) |
| `reachy.look_at` | 看向 3D 坐标 | x, y, z |
| `reachy.set_volume` | 设置音量 | volume (0-100) |
| `reachy.enable_motors` | 启用电机 | — |
| `reachy.disable_motors` | 禁用电机 | — |

## 状态机

```
IDLE ──唤醒词──→ CONNECTING ──hello──→ LISTENING ──VAD结束──→ THINKING
  ↑                                                           │
  └─────── TTS播放完毕 ──── SPEAKING ←─── TTS开始 ←──────┘
```

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| `opuslib` 导入失败 | 安装 `libopus-dev` |
| 唤醒词不响应 | 检查麦克风是否在工作，尝试调整 sensitivity |
| 连接失败 | 检查 token 和网络连接 |
| 音频延迟 | 减小 block_size (256) 或 frame_duration (40) |
| OPUS 编码错误 | 降低 protocol_version 为 1 (raw PCM) |

## 相关项目

- [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) — ESP32 语音助手固件
- [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) — Python 后端服务器
- [reachy-mini-sdk](https://github.com/pollen-robotics/reachy-mini) — Reachy Mini Python SDK