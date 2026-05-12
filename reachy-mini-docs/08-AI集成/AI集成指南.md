# AI 集成指南

## 概述

Reachy Mini 专为 AI 构建者设计。本指南介绍如何集成 LLM 和共享您的工作。

## 构建应用

我们提供 CLI 工具来生成、检查和发布标准应用结构 (兼容 Hugging Face Spaces)。

详见 [构建和发布应用](../06-应用开发/应用开发指南.md)

## JavaScript Web 应用

想要零安装、跨平台、在浏览器中运行的应用？查看 [JavaScript SDK 和 Web 应用](https://huggingface.co/docs/reachy_mini/SDK/javascript-sdk) 指南 - 构建静态 Hugging Face Spaces，从任何设备 (包括手机) 通过 WebRTC 控制机器人。

## HTTP & WebSocket API

构建仪表板或非 Python 控制器？Daemon 通过 REST 暴露完全控制。

* **文档:** `http://localhost:8000/docs`
* **获取状态:** `GET /api/state/full`
* **WebSocket:** `ws://localhost:8000/api/state/ws/full`

## AI 实验技巧

### 对话演示

查看我们的参考实现，结合 VAD (语音活动检测)、LLM 和 TTS:
[reachy_mini_conversation_demo](https://github.com/pollen-robotics/reachy_mini_conversation_demo)

### 自定义视觉/音频管道

如果您的 AI 管道需要直接访问摄像头或麦克风 (例如自定义 OpenCV 检测器、带 sounddevice 的 Whisper)，您可以使用 `media_backend="no_media"` 停用内置媒体管理器。

```python
from reachy_mini import ReachyMini

with ReachyMini(media_backend="no_media") as mini:
    # 直接使用 OpenCV
    import cv2
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    
    # 直接使用 sounddevice
    import sounddevice as sd
    audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1)
    sd.wait()
```

## LLM 集成

### 语音识别
- Whisper
- Wav2Vec2

### 语音合成
- Bark
- SpeechT5

### 视觉
- ViT
- CLIP
- YOLO

### 语言模型
- LLaMA
- Mistral
- GPT 系列

### 多模态
- GPT-4V
- LLaVA

## 对话应用示例

对话应用是 AI 集成的参考实现:

### 功能
- 自然语言交互
- 语音识别和语音合成
- 可自定义个性和知识库
- LLM 驱动的响应
- 面部追踪
- 情感表达

### 架构
```
用户语音 → VAD → ASR → LLM → TTS → 机器人语音
                    ↓
              面部追踪 → 头部运动
                    ↓
              情感分析 → 天线/身体运动
```

### 关键代码模式

```python
from reachy_mini import ReachyMini
import openai

class ConversationApp(ReachyMiniApp):
    def run(self, reachy_mini, stop_event):
        # 初始化
        reachy_mini.media.start_recording()
        reachy_mini.media.start_playing()
        
        while not stop_event.is_set():
            # 录制用户语音
            audio = reachy_mini.media.get_audio_sample()
            
            # 语音识别
            text = transcribe(audio)
            
            # LLM 处理
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": text}]
            )
            
            # 语音合成
            speech = synthesize(response)
            
            # 播放
            reachy_mini.media.push_audio_sample(speech)
            
            # 移动机器人
            express_emotion(reachy_mini, response.emotion)
```

## 发布应用

向全球 Reachy Mini 社区分享您的创意:

1. 使用 SDK 构建应用
2. 创建 Hugging Face Space
3. 添加 `reachy-mini` 标签
4. 发布并与数百万 Hugging Face 用户分享

详见 [应用开发指南](../06-应用开发/应用开发指南.md)

## 示例 AI 应用

| 应用 | AI 功能 | 链接 |
|------|---------|------|
| Conversation App | LLM, ASR, TTS | [GitHub](https://github.com/pollen-robotics/reachy_mini_conversation_app) |
| Hand Tracker | 计算机视觉 | [HF Space](https://huggingface.co/spaces/pollen-robotics/hand_tracker_v2) |
| Face Tracker | 面部检测 | 社区贡献 |

## 最佳实践

### 1. 选择合适的后端
- **默认:** 自动检测
- **本地:** 最低延迟
- **WebRTC:** 远程访问
- **无媒体:** 直接硬件访问

### 2. 处理延迟
- 使用本地后端减少延迟
- 异步处理 AI 管道
- 流式处理音频/视频

### 3. 错误处理
- 捕获网络错误
- 实现重试逻辑
- 提供回退响应

### 4. 资源管理
- 释放未使用的资源
- 监控内存使用
- 优化模型大小

## 中国用户特别说明

### 访问 HuggingFace
```bash
export HF_ENDPOINT=https://hf-mirror.com/
```

### 访问 OpenAI API
需要配置 VPN 或使用代理。

### 替代方案
考虑使用本地模型或国内 AI 服务。

## 相关链接

- [应用开发指南](../06-应用开发/应用开发指南.md)
- [Python SDK 参考](../04-SDK文档/Python-SDK参考.md)
- [媒体架构](../04-SDK文档/媒体架构.md)
- [故障排除指南](../07-故障排除/常见问题与解决方案.md)
