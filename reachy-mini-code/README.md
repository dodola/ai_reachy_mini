# Reachy Mini 代码库索引

## 目录结构

```
reachy-mini-code/
├── official/                    # 官方仓库
│   ├── reachy_mini/            # 主 SDK 仓库
│   ├── reachy_mini_conversation_demo/  # 对话应用示例
│   ├── reachy_mini_dances_library/     # 舞蹈动作库
│   └── reachy-mini-desktop-app/        # 桌面控制应用
├── community/                   # 社区项目
│   ├── f1commentator/          # F1 赛车评论员
│   ├── baby-reachy-mini-companion/  # 婴儿陪伴机器人
│   ├── reachy_mini_3d_web_viz/ # 3D Web 可视化
│   ├── reachy_mini_home_assistant/  # Home Assistant 集成
│   ├── reachy_mini_phone_teleop/    # 手机遥操作
│   ├── hand_tracker_v2/        # 手部追踪
│   ├── spaceship_game/         # 太空船游戏
│   ├── reachy_mini_simon/      # Simon 记忆游戏
│   └── reachy_mini_radio/      # 收音机应用
└── examples/                    # 本地示例代码
```

## 官方仓库详解

### 1. reachy_mini (主仓库)
**路径:** `official/reachy_mini/`

**核心内容:**
- Python SDK (`src/reachy_mini/`)
- Daemon 服务 (`src/reachy_mini/daemon/`)
- 示例代码 (`examples/`)
- 文档 (`docs/`)
- 硬件描述 (`src/reachy_mini/descriptions/`)
- 配置文件 (`src/reachy_mini/assets/`)

**官方示例:**
| 文件 | 功能 |
|------|------|
| `minimal_demo.py` | 最小示例，天线摆动 |
| `goto_interpolation_playground.py` | 运动插值演示 |
| `joy_controller.py` | 游戏手柄控制 |
| `look_at_image.py` | 视觉追踪 |
| `mini_head_position_gui.py` | 头部位置 GUI |
| `sound_record.py` | 音频录制 |
| `sound_play.py` | 音频播放 |
| `sound_doa.py` | 声源定位 |
| `imu_example.py` | IMU 数据读取 |
| `take_picture.py` | 拍照 |
| `recorded_moves.py` | 动作录制回放 |
| `sequence.py` | 动作序列 |
| `custom_media_manager.py` | 自定义媒体管理 |

### 2. reachy_mini_conversation_demo
**路径:** `official/reachy_mini_conversation_demo/`

**功能:** AI 对话应用参考实现
- VAD (语音活动检测)
- ASR (语音识别)
- LLM (大语言模型)
- TTS (语音合成)
- 面部追踪
- 情感表达

### 3. reachy_mini_dances_library
**路径:** `official/reachy_mini_dances_library/`

**功能:** 预定义舞蹈动作库
- 多种舞蹈动作
- 符号化动作定义
- 可直接调用

### 4. reachy-mini-desktop-app
**路径:** `official/reachy-mini-desktop-app/`

**功能:** 桌面控制应用
- 可视化界面
- 电机控制
- 摄像头预览
- 应用管理

## 社区项目详解

### 🏎️ F1 赛车评论员 (f1commentator)
**链接:** https://huggingface.co/spaces/d10g/f1commentator
**Stars:** 205

**功能:**
- 互动式 F1 赛事评论系统
- 实时赛事数据接入
- 机器人语音播报
- 富有表现力的动作反馈

**技术亮点:**
- API 数据集成
- 语音合成
- 动作编排

---

### 🤖 婴儿陪伴机器人 (baby-reachy-mini-companion)
**链接:** https://huggingface.co/spaces/ravediamond/baby-reachy-mini-companion
**Stars:** 167

**功能:**
- 完全本地化的 AI 陪伴
- 专为婴幼儿设计
- 语音交互
- 安全的动作限制

**技术亮点:**
- 本地 LLM 推理
- 儿童安全模式
- 语音识别

---

### 🦾 3D Web 可视化 (reachy_mini_3d_web_viz)
**链接:** https://huggingface.co/spaces/8bitkick/reachy_mini_3d_web_viz
**Stars:** 27

**功能:**
- 浏览器中实时 3D 可视化
- 机器人状态同步
- 远程监控

**技术亮点:**
- Three.js 3D 渲染
- WebSocket 实时通信
- 跨平台访问

---

### 🏠 Home Assistant 集成 (reachy_mini_home_assistant)
**链接:** https://huggingface.co/spaces/djhui5710/reachy_mini_home_assistant
**Stars:** 21

**功能:**
- 与 Home Assistant 深度集成
- 智能家居控制
- 语音助手功能
- 自动化场景

**技术亮点:**
- Home Assistant API
- MQTT 集成
- 自动化脚本

---

### 📱 手机遥操作 (reachy_mini_phone_teleop)
**链接:** https://huggingface.co/spaces/apirrone/reachy_mini_phone_teleop
**Stars:** 6

**功能:**
- 手机控制机器人
- 陀螺仪映射
- 触摸控制
- 实时视频流

**技术亮点:**
- WebRTC 视频流
- 传感器数据映射
- 响应式 UI

---

### 👋 手部追踪 (hand_tracker_v2)
**链接:** https://huggingface.co/spaces/pollen-robotics/hand_tracker_v2
**Stars:** 105

**功能:**
- 实时手部追踪
- 机器人跟随手部动作
- 手势识别

**技术亮点:**
- MediaPipe 手部检测
- 计算机视觉
- 实时控制循环

---

### 🚀 太空船游戏 (spaceship_game)
**链接:** https://huggingface.co/spaces/apirrone/spaceship_game
**Stars:** 50+

**功能:**
- 头部作为摇杆控制
- 天线作为按钮
- 趣味游戏体验

**技术亮点:**
- 头部姿态映射
- 天线交互模式
- Canvas 游戏渲染

---

### 🎮 Simon 记忆游戏 (reachy_mini_simon)
**链接:** https://huggingface.co/spaces/apirrone/reachy_mini_simon
**Stars:** 30+

**功能:**
- 经典 Simon 游戏
- 天线作为输入
- 声音反馈
- 无 GUI 设计

**技术亮点:**
- 天线按钮交互
- 音频反馈
- 游戏逻辑

---

### 📻 收音机应用 (reachy_mini_radio)
**链接:** https://huggingface.co/spaces/pollen-robotics/reachy_mini_radio
**Stars:** 10

**功能:**
- 语音控制电台
- 自然语言点歌
- 天线交互

**技术亮点:**
- 流媒体播放
- 语音识别
- 天线动画

## 其他有趣项目

### 🏎️ F1 评论员
- 实时赛事播报
- 富有表现力的动作
- 数据驱动的评论

### 👶 婴儿陪伴
- 安全的交互模式
- 本地 AI 处理
- 儿童友好的设计

### 🎨 皮肤系统
- 可更换的外观
- 3D 打印支持
- 社区共享

### 🕰️ 时钟应用
- 天线显示时间
- 创意交互设计

### 🎸 尤克里里调音器
- 音频分析
- 视觉反馈

## 快速开始

### 运行官方示例
```bash
cd reachy-mini-code/official/reachy_mini

# 安装 SDK
pip install -e .

# 运行示例
python examples/minimal_demo.py
```

### 运行社区项目
```bash
cd reachy-mini-code/community/f1commentator

# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

## 学习路径

### 初学者
1. `official/reachy_mini/examples/minimal_demo.py` - 基础控制
2. `official/reachy_mini/examples/sound_record.py` - 音频录制
3. `official/reachy_mini/examples/take_picture.py` - 拍照

### 中级开发者
1. `official/reachy_mini_conversation_demo/` - AI 对话
2. `community/hand_tracker_v2/` - 计算机视觉
3. `community/spaceship_game/` - 游戏开发

### 高级开发者
1. `official/reachy_mini/src/reachy_mini/` - SDK 源码
2. `official/reachy_mini/src/reachy_mini/daemon/` - Daemon 实现
3. `community/reachy_mini_home_assistant/` - 系统集成

## 相关链接

- [官方文档库](../reachy-mini-docs/README.md)
- [GitHub 主仓库](https://github.com/pollen-robotics/reachy_mini)
- [Hugging Face 社区](https://huggingface.co/spaces?q=reachy_mini)
- [Discord 社区](https://discord.gg/Y7FgMqHsub)

## 贡献指南

欢迎贡献新的示例和项目！

1. Fork 项目
2. 创建功能分支
3. 提交 Pull Request
4. 添加 `reachy_mini` 标签

## 许可证

- 官方代码: Apache 2.0
- 硬件设计: Creative Commons BY-SA-NC
- 社区项目: 各项目自定义许可证
