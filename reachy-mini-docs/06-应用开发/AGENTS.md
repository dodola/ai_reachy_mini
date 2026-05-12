# AGENTS.md - AI 开发指南

本指南帮助 AI 代理协助用户开发 Reachy Mini 应用。

---

## 代理行为

### 首先: 检查 agents.local.md

**在做任何其他事情之前**，在当前目录中搜索 `agents.local.md`:

```
IF agents.local.md 存在:
    立即读取它
    它包含用户配置和会话上下文
ELSE:
    → 运行 skills/setup-environment.md 设置环境
```

此文件存储用户的机器人类型、偏好和设置状态。始终首先检查它。

### 做一名教师

除非用户明确要求:
- 在进行过程中解释概念
- 鼓励提问 ("如果您需要更多细节，请告诉我")
- 引导非技术用户完成每一步
- 不要假设先前的知识

### 始终创建 Python 应用

创建应用时:
- **始终使用 Python** - Python 应用可通过机器人的应用商店发现和共享
- **永远不要手动创建应用文件夹** - 始终使用应用助手 (处理元数据、入口点、结构)
- **如果命令失败** - 请用户在他们的终端中运行; 不要尝试复杂的解决方法
- **Web UI 放在 `static/`** - Python 应用可以有 Web 前端

```bash
# 默认模板 (最小应用 - 适合大多数情况):
reachy-mini-app-assistant create <app_name> <path> --publish

# 对话模板 (用于 LLM 集成、语音、让机器人说话):
reachy-mini-app-assistant create --template conversation <app_name> <path> --publish
```

详见 `skills/create-app.md`。JS-only 应用尚不支持发现/共享。

### 编码前始终创建 plan.md

在实现任何应用之前:
1. 在应用目录中创建 `plan.md`
2. 写下您对用户需求的理解
3. 列出您的技术方法
4. 在 `plan.md` 中提出澄清问题并提供答案字段
5. 在编码前等待答案

### 在 agents.local.md 中保留笔记

使用 `agents.local.md` 存储:
- 用户的机器人类型 (Lite/Wireless)
- 环境偏好
- 对未来会话有用的上下文
- 保持简洁

---

## 机器人基础

**Reachy Mini** 是一个小型富有表现力的机器人:

| 组件 | 描述 |
|------|------|
| **头部** | 6 DOF: x, y, z, roll, pitch, yaw (通过 Stewart 平台) |
| **身体** | 绕垂直轴旋转 |
| **天线** | 2 个电机，也可用作物理按钮 |

**硬件变体:**
- **Lite:** USB 连接到笔记本电脑 (完整计算能力)
- **Wireless:** 板载 CM4，通过 WiFi 连接 (有限计算)

---

## SDK 要点

### 连接

```python
from reachy_mini import ReachyMini

with ReachyMini() as mini:
    # 您的代码
```

### 两种运动方法

| 方法 | 使用场景 |
|------|----------|
| `goto_target()` | **默认** - 用于至少持续 0.5 秒的手势的平滑插值 |
| `set_target()` | 用于 10Hz+ 的实时控制循环 (追踪) |

### 基本示例

参见并运行 `examples/minimal_demo.py` - 演示连接、头部运动和天线控制。

### 编写代码前

- 阅读 `docs/source/SDK/python-sdk.md` 了解 API 概述
- 浏览 `src/reachy_mini/reachy_mini.py` 了解方法签名和文档字符串
- 检查 `examples/` 了解可运行的代码模式

---

## REST API

Daemon 在 `http://{daemon-ip}:8000/api` 暴露 HTTP/WebSocket API。

- **Lite:** `localhost:8000` (daemon 在您的机器上运行)
- **Wireless:** `reachy-mini.local:8000` 或机器人的 IP 地址

**使用 REST API:** Web UI、非 Python 客户端、远程控制、通过 HTTP 的 AI/LLM 集成。

**交互式文档:** `http://{daemon-ip}:8000/docs` (当 daemon 运行时)

详见 `skills/rest-api.md`。

---

## 平台兼容性

| 设置 | 计算 | 摄像头 | 说明 |
|------|------|--------|------|
| **Lite** | 完整 (笔记本) | 直接 USB | 最灵活，最适合开发 |
| **Wireless (本地)** | 有限 (CM4) | 直接 | 内存/CPU 受限 |
| **Wireless (流式)** | 完整 (笔记本) | 通过网络 | 有一定追踪质量损失 |
| **仿真** | 完整 | 无 | 无法测试摄像头功能 |

---

## 安全限制

| 关节 | 范围 |
|------|------|
| 头部 pitch/roll | [-40, +40] 度 |
| 头部 yaw | [-180, +180] 度 |
| 身体 yaw | [-160, +160] 度 |
| Yaw Delta (头-身) | 最大 65° 差异 |

与身体的轻微碰撞是安全的。SDK 自动限制值。

详见 `docs/source/SDK/core-concept.md`。

---

## 示例应用

| 应用 | 关键模式 | 来源 |
|------|----------|------|
| **reachy_mini_conversation_app** | AI 集成、控制循环、LLM 工具 | [GitHub](https://github.com/pollen-robotics/reachy_mini_conversation_app) |
| **marionette** | 录制运动、安全扭矩、HF 数据集 | [HF Space](https://huggingface.co/spaces/RemiFabre/marionette) |
| **fire_nation_attacked** | 头部作为控制器、排行榜、游戏 | [HF Space](https://huggingface.co/spaces/RemiFabre/fire_nation_attacked) |
| **spaceship_game** | 头部作为摇杆、天线按钮 | [HF Space](https://huggingface.co/spaces/apirrone/spaceship_game) |
| **reachy_mini_radio** | 天线交互模式 | [HF Space](https://huggingface.co/spaces/pollen-robotics/reachy_mini_radio) |
| **reachy_mini_simon** | 无 GUI 模式 (天线启动) | [HF Space](https://huggingface.co/spaces/apirrone/reachy_mini_simon) |
| **hand_tracker_v2** | 基于摄像头的控制循环 | [HF Space](https://huggingface.co/spaces/pollen-robotics/hand_tracker_v2) |
| **reachy_mini_dances_library** | 符号运动定义 | [GitHub](https://github.com/pollen-robotics/reachy_mini_dances_library) |

---

## 文档

完整 SDK 文档在 `docs/source/`:

| 主题 | 文件 |
|------|------|
| 快速入门 | `docs/source/SDK/quickstart.md` |
| Python SDK | `docs/source/SDK/python-sdk.md` |
| 核心概念 | `docs/source/SDK/core-concept.md` |
| AI 集成 | `docs/source/SDK/integration.md` |
| 故障排除 | `docs/source/troubleshooting.md` |

平台特定指南 (Lite, Wireless, 仿真)，参见 `docs/source/platforms/`。

---

## 技能参考

当您需要详细知识时，在 `skills/` 中阅读这些文件:

| 技能 | 使用场景 |
|------|----------|
| **setup-environment.md** | 第一次会话，没有 `agents.local.md` |
| **create-app.md** | 使用 `reachy-mini-app-assistant` 创建新应用 |
| **control-loops.md** | 构建实时响应应用 (追踪、游戏) |
| **motion-philosophy.md** | 选择 `goto_target` 和 `set_target` |
| **safe-torque.md** | 启用/禁用电机而不抖动 |
| **ai-integration.md** | 构建 LLM 驱动的应用 |
| **symbolic-motion.md** | 数学定义运动 (舞蹈、节奏) |
| **interaction-patterns.md** | 使用天线作为按钮，头部作为控制器 |
| **debugging.md** | 应用崩溃、连接问题、基本检查 |
| **testing-apps.md** | 交付前测试 (仿真 vs 物理) |
| **rest-api.md** | 非 Python 客户端的 HTTP/WebSocket API |
| **deep-dive-docs.md** | 何时阅读完整 SDK 文档 |

---

## 快速参考

**电机名称:** `body_rotation`, `stewart_1-6`, `right_antenna`, `left_antenna`

**插值方法:** `linear`, `minjerk` (默认), `ease_in_out`, `cartoon`

**情感库:**
```python
from reachy_mini.motion.recorded_move import RecordedMoves
moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
mini.play_move(moves.get("happy"), initial_goto_duration=1.0)
```

---

## 社区

- **应用指南:** https://huggingface.co/blog/pollen-robotics/make-and-publish-your-reachy-mini-apps
- **源代码:** https://github.com/pollen-robotics/reachy_mini
- **社区应用:** https://huggingface.co/spaces?q=reachy_mini
- **Discord:** https://discord.gg/Y7FgMqHsub
