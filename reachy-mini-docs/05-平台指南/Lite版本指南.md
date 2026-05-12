# Reachy Mini Lite 版本指南

## 概述

**Reachy Mini Lite** 是用于教育和开发的系留版本。它需要计算机来运行其智能。

## 1. 组装

Reachy Mini 以套件形式提供。组装是您旅程的第一步！

- **所需时间:** 2 到 3 小时
- **工具:** 盒子里包含所有工具
- **说明:** 强烈建议同时参考视频指南和手册

### 组装资源

| 资源 | 链接 | 说明 |
|------|------|------|
| 交互式数字指南 | [在线指南](https://huggingface.co/spaces/pollen-robotics/Reachy_Mini_LITE_Assembly_Guide) | 包含短视频循环 |
| 完整组装视频 | [YouTube](https://www.youtube.com/watch?v=PC5Yx950nMY) | 带章节的视频 |

> **提示:** 强烈建议打开**在线指南**或**组装视频**，与纸质手册一起使用。在线版本包含每个步骤的短视频片段，使组装更容易理解。

## 2. 连接

### 步骤 1: 接通电源
使用提供的电源适配器将机器人插入墙壁插座。

### 步骤 2: 连接数据线
将 USB 电缆从机器人连接到计算机。

## 3. 下载 Reachy Mini Control

> **警告:** 
> - **ARM64 系统 (DGX, Jetson, Surface 等) 和不常见的 Linux 发行版:** 桌面应用可能无法在您的系统上工作。
> - **替代方案:** 如果桌面应用无法在您的设置上工作，您可以直接安装和使用 [Python SDK](../03-快速入门/SDK安装指南.md) - 这是完全支持且有效的控制机器人的方式！

**Reachy Mini Control** 桌面应用是机器人的指挥中心。它包括可视化工具、应用启动器和系统设置 - 无需命令行。

### 下载链接
- [官方网站下载](https://hf.co/reachy-mini/#/download) (推荐用于 Windows, macOS, Linux)
- [GitHub Releases](https://github.com/pollen-robotics/reachy-mini-desktop-app/releases) (用于特定版本)

### 自动更新
安装后，只需打开应用。它会自动检查并安装应用和机器人内部软件的最新更新。

## 4. 使用机器人

现在一切已连接并安装完毕，可以开始使用了！

### 使用桌面应用功能
- 实时可视化
- 电机控制
- 摄像头画面
- 麦克风测试

### 安装和运行社区应用
- 从应用商店安装
- 一键启动
- 自动管理依赖

### 使用 Python 编程
```bash
# 激活虚拟环境
source reachy_mini_env/bin/activate

# 运行脚本
python your_script.py
```

## 4. Python SDK 直接使用

如果桌面应用无法工作，可以直接使用 Python SDK:

### 安装
```bash
# 创建虚拟环境
uv venv reachy_mini_env --python 3.12

# 激活环境
source reachy_mini_env/bin/activate

# 安装 SDK
uv pip install "reachy-mini"
```

### 启动 Daemon
```bash
reachy-mini-daemon
```

### 运行脚本
```bash
python your_script.py
```

## 5. 硬件接口

### 后面板
- 电源连接器 (7V-5A)
- USB-C 端口 (数据)

### 前面板
- 摄像头
- 麦克风阵列
- 扬声器

## 6. 电源要求

- **输入电压:** 7V
- **电流:** 5A
- **功率:** 35W
- **连接器:** 专用电源适配器

> **重要:** USB 连接不足以驱动电机。必须使用电源适配器。

## 7. USB 连接

### 连接类型
- **数据:** USB-C
- **协议:** USB 2.0
- **驱动:** 自动安装

### 连接检查
```bash
# Linux
lsusb | grep "1a86:55d3"

# macOS
system_profiler SPUSBDataType | grep -A 5 "Reachy"

# Windows
# 在设备管理器中查看
```

## 8. 摄像头设置

### 暗图像问题 (Lite 版本)

如果图像较暗，需要调整曝光时间:

#### macOS
使用 [CameraController](https://github.com/itaybre/CameraController)

#### Linux
```bash
sudo apt install qv4l2
qv4l2
```

#### Windows
使用 [Webcam Settings](https://www.softpedia.com/get/Internet/WebCam/Webcam-Settings-Tool.shtml) 或 [ManyCam](https://manycam.com/)

### 高级摄像头控制

使用 v4l2-ctl (Linux):
```bash
# 安装
sudo apt install v4l-utils

# 列出控件
v4l2-ctl -l

# 设置自动曝光
v4l2-ctl --set-ctrl=exposure_auto_priority=1
```

## 9. 音频设置

### 检查音频设备
```bash
# Linux
arecord -l  # 录音设备
aplay -l    # 播放设备

# macOS
system_profiler SPAudioDataType

# Windows
# 在声音设置中查看
```

### 音量调整 (Linux)
```bash
alsamixer
# 设置 PCM1 到 100%
# 使用 PCM,0 调整全局音量

# 永久保存
CARD=$(aplay -l | grep -i "reSpeaker" | head -n1 | sed -n 's/^card \([0-9]*\):.*/\1/p')
amixer -c "$CARD" set PCM,1 100%
sudo alsactl store "$CARD"
```

## 10. 故障排除

### 常见问题

**问题: 桌面应用无法启动**
- 检查是否为 ARM64 系统
- 尝试直接使用 Python SDK

**问题: 电机不响应**
- 确保电源适配器已连接 (USB 不够)
- 检查电缆连接
- 重启 daemon

**问题: 图像太暗**
- 调整摄像头曝光设置
- 使用摄像头控制应用

**问题: 音频不工作**
- 检查麦克风电缆方向
- 验证音频设备检测

**问题: USB 连接问题**
- 尝试不同的 USB 端口
- 检查驱动安装
- 重启计算机

## 11. 与 Wireless 版本的区别

| 特性 | Lite | Wireless |
|------|------|----------|
| 计算 | 外部计算机 | 板载 CM4 |
| 连接 | USB | WiFi |
| 电源 | 有线 | 电池 + 有线 |
| IMU | 无 | 有 |
| 独立性 | 需要计算机 | 独立运行 |

## 相关链接

- [硬件规格详解](../02-硬件规格/硬件规格详解.md)
- [SDK 安装指南](../03-快速入门/SDK安装指南.md)
- [快速入门指南](../03-快速入门/快速入门指南.md)
- [故障排除指南](../07-故障排除/常见问题与解决方案.md)
