# Voice Chat for Reachy Mini

让 Reachy Mini 通过 xiaozhi 协议实现 AI 语音聊天，利用机器人自带麦克风和音箱。

## 功能

- 🎤 **语音交互**: 通过 xiaozhi 服务器实现 ASR → LLM → TTS 完整流程
- 👂 **唤醒词**: 离线检测 "okay_nabu" 等唤醒词（可扩展）
- 😊 **人脸追踪**: MediaPipe FaceLandmarker 实时追踪人脸，头部跟随
- 🎭 **表情检测**: 从面部 blendshapes 检测情绪，天线随表情动
- 👁️ **视觉理解**: Gemma 4 本地多模态 AI，看图说话，理解场景
- 📍 **声源追踪**: 检测说话人方向，头部自动转向
- 🤖 **MCP 关节控制**: AI 可以控制机器人头部、天线、身体和情绪动作
- 🔇 **停止词**: 检测 "stop" 停止词中断播放

## 架构

```
PC + RTX 4060 16GB
├── Ollama + Gemma 4 12B (本地多模态推理)
│   └── 摄像头 → 场景描述 / 视觉问答
│
Reachy Mini 硬件
├── 麦克风阵列 → SDK get_audio_sample() → 16kHz PCM
├── 扬声器     ← SDK push_audio_sample() ← 16kHz PCM
├── 摄像头     → SDK get_frame() → MediaPipe → 人脸追踪/表情
└── 电机       ← SDK goto_target/set_target

voice-chat/ (Python 服务)
├── 麦克风 → 512采样块 → 唤醒词检测 → 触发 WS 连接
├── 麦克风 → OPUS编码 → WebSocket → xiaozhi 服务器
├── WebSocket → OPUS解码 → 重采样 → 扬声器
├── 摄像头 → MediaPipe FaceLandmarker → 头部追踪 + 表情检测
├── 摄像头 → Gemma 4 (Ollama) → 场景描述 / 视觉问答
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

# 人脸追踪需要 MediaPipe（可选，无摄像头设备可跳过）
pip install mediapipe

# 下载 MediaPipe 模型（首次运行会自动下载，也可手动）
# 模型文件: face_landmarker_v2.task
mkdir -p models
wget -O models/face_landmarker_v2.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker_v2/float16/latest/face_landmarker_v2.task
```

### 2. 配置

```bash
# 复制并编辑配置文件
cp config.yaml config.local.yaml
# OTA 激活默认开启 — 自动获取 websocket 地址和 token，无需手动填写
# 如需手动指定，将 activation.enabled 设为 false 并填入 server_url 和 token
```

### 3. 运行

```bash
python main.py --config config.local.yaml
# 或使用默认配置
python main.py
# 启用调试日志
python main.py -v
# 禁用人脸追踪（无摄像头或节省 CPU）
python main.py --no-face-tracking
```

## OTA 激活（xiaozhi-esp32 兼容）

voice-chat 复刻了 xiaozhi-esp32 的完整激活流程，启动时自动完成：

1. **CheckVersion** — POST 系统信息到 OTA URL，获取 websocket 配置和激活挑战
2. **Activate** — 如有激活挑战，POST 到 `/activate` 端点完成设备认证
3. **连接** — 使用 OTA 返回的 websocket URL 和 token 建立 WS 连接

激活成功后无需在配置文件中手动填写 `server_url` 和 `token`。

```python
# xiaozhi-esp32 流程对照：
# C++:  Ota::CheckVersion()    → POST / OTA → 解析 websocket/config
# Py:   check_and_activate()   → aiohttp POST → ActivationResult
#
# C++:  Ota::Activate()         → POST /activate {challenge, hmac}
# Py:   check_and_activate()   → POST /activate {} (无序列号)
#
# C++:  WebsocketProtocol::OpenAudioChannel()  → 从 NVS 读取 url/token
# Py:   XiaozhiClient.apply_activation()       → 从 ActivationResult 更新连接参数
```

### 激活配置

| 项目 | 默认值 | 说明 |
|------|--------|------|
| `xiaozhi.activation.enabled` | `true` | 启用 OTA 激活 |
| `xiaozhi.activation.ota_url` | `https://api.tenclass.net/xiaozhi/ota/` | OTA 接口地址 |
| `xiaozhi.activation.ota_url_override` | `""` | 覆盖 OTA 地址（留空用默认） |
| `xiaozhi.activation.max_activate_retries` | `10` | 激活重试次数 |
| `xiaozhi.activation.activate_retry_delay` | `3.0` | 重试间隔（秒） |
| `xiaozhi.activation.http_timeout` | `30.0` | HTTP 请求超时（秒） |

禁用激活后，使用配置文件中的 `xiaozhi.server_url` 和 `xiaozhi.token` 连接（兼容手动模式）。

## 配置说明

| 项目 | 默认值 | 说明 |
|------|--------|------|
| `xiaozhi.server_url` | `wss://api.xiaozhi.me/v1/` | 兜底连接地址，激活后自动覆盖 |
| `xiaozhi.token` | `""` | 认证 token（激活后自动填充） |
| `xiaozhi.protocol_version` | `3` | 协议版本 (1=raw, 2=+timestamp, 3=lightweight) |
| `audio.input_sample_rate` | `16000` | 麦克风采样率 |
| `audio.block_size` | `512` | 每次读取采样数 (32ms) |
| `wakeword.model` | `okay_nabu` | 唤醒词模型 |
| `wakeword.stop_model` | `stop` | 停止词模型 |
| `reachy.connection_mode` | `auto` | 连接模式 (auto/localhost_only/network) |
| `reachy.media_backend` | `local` | 媒体后端 (local/webrtc/no_media) |
| `motion.look_at_speaker` | `true` | 声源追踪 |
| `vision.enabled` | `true` | 人脸追踪总开关 |
| `vision.fps` | `15` | 人脸检测帧率 |
| `vision.head_amp_yaw` | `1.0` | 头部偏转放大系数 |
| `vision.smoothing` | `0.3` | 人脸追踪平滑系数 |

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
| `reachy.look_around` | 用摄像头观察环境并回答问题 | question (可选) |
| `reachy.describe_scene` | 描述当前场景 | detail (brief/normal/detailed) |

## 视觉理解 (Gemma 4)

借助于本地运行的 **Gemma 4** 多模态模型，机器人可以"看懂"周围环境：

### 安装 Ollama + Gemma 4

```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 拉取模型（根据 GPU 选择）
# RTX 4060 16GB 推荐:
ollama pull gemma3:12b       # 约 7GB VRAM，平衡速度和质量

# 其他选项:
# ollama pull gemma3:4b    # 约 3GB VRAM，最快
# ollama pull gemma3:27b    # 约 10GB VRAM，最强
```

### 视觉交互示例

通过 xiaozhi 对话，AI 可以主动调用视觉 MCP 工具：

```
用户: "你看到了什么？"
AI:  [调用 reachy.look_around] → "我看到一个穿蓝色衬衫的人坐在书桌前..."

用户: "桌上有多少本书？"
AI:  [调用 reachy.look_around question="桌上有多少本书？"] → "桌上有3本书..."

用户: "描述一下房间"
AI:  [调用 reachy.describe_scene detail="detailed"] → "房间里有..."
```

### 视觉配置

| 项目 | 默认值 | 说明 |
|------|--------|------|
| `gemma.enabled` | `true` | 视觉理解开关 |
| `gemma.model` | `gemma3:12b` | Ollama 模型名 |
| `gemma.ollama_url` | `http://localhost:11434` | Ollama API 地址 |
| `gemma.auto_describe_interval` | `0` | 自动描述间隔(秒)，0=关 |
| `gemma.max_history` | `10` | 场景历史最大条数 |

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
| MediaPipe 启动失败 | 安装 `mediapipe`，下载模型到 `models/` 目录 |
| 人脸追踪延迟 | 降低 `vision.fps` (10) 或使用 `--no-face-tracking` |
| CPU 占用过高 | 关闭人脸追踪或降低帧率 |

## 相关项目

- [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) — ESP32 语音助手固件
- [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) — Python 后端服务器
- [reachy-mini-sdk](https://github.com/pollen-robotics/reachy-mini) — Reachy Mini Python SDK