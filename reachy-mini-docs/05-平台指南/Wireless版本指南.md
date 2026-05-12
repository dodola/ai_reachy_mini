# Reachy Mini (Wireless) 版本指南

## 概述

**Reachy Mini (Wireless)** 是自主版本，由 Raspberry Pi Compute Module 4 (CM4) 驱动。它使用内部电池和 WiFi 连接独立运行。

## 1. 组装

Reachy Mini 以套件形式提供。组装是您旅程的第一步！

- **所需时间:** 2 到 3 小时
- **工具:** 盒子里包含所有工具
- **说明:** 强烈建议同时参考视频指南和手册

### 组装资源

| 资源 | 链接 | 说明 |
|------|------|------|
| 交互式数字指南 | [在线指南](https://huggingface.co/spaces/pollen-robotics/Reachy_Mini_Assembly_Guide) | 包含短视频循环 |
| 完整组装视频 | [YouTube](https://www.youtube.com/watch?v=WeKKdnuXca4) | 带章节的视频 |

> **提示:** 强烈建议打开**在线指南**或**组装视频**，与纸质手册一起使用。在线版本包含每个步骤的短视频片段，使组装更容易理解。

## 2. 首次启动和 WiFi 配置

组装完成后，需要将机器人连接到 WiFi 网络。

### 步骤 1: 开机
打开 Reachy Mini 的电源。

### 步骤 2: 下载 Reachy Mini Control
如果还没有，请从[官方网站](https://hf.co/reachy-mini/#/download)下载并安装 **Reachy Mini Control** 应用。

### 步骤 3: 运行应用
打开 **Reachy Mini Control**，点击底部链接 **"First time connecting..."**。

### 步骤 4: 按照说明操作
应用将引导您完成连接过程。它会要求您连接到机器人的 WiFi AP，然后配置您的 WiFi。

## 3. 更新系统

在进一步操作之前，强烈建议将机器人更新到最新版本。

1. 使用 **Reachy Mini Control** 连接到机器人
2. 连接后，点击 **"⚙️"** 设置标签
3. 转到 **System Updates** 部分
4. 如果有新版本可用，按照屏幕说明安装

## 4. 使用机器人

现在您的机器人已上线并更新，可以开始控制它了！

### 使用 Reachy Mini Control
- 可视化工具
- 应用启动器
- 系统设置

### 安装和运行应用
- 从应用商店安装社区应用
- 直接从仪表板启动应用

### 使用 Python 编程
```bash
# 安装 SDK
uv pip install "reachy-mini"

# 运行脚本
python your_script.py
```

## 5. SSH 连接到内部 Raspberry Pi

如果需要通过 SSH 连接到 Reachy Mini 的内部 Raspberry Pi:

### 连接信息
```bash
ssh pollen@reachy-mini.local
# 用户名: pollen
# 密码: root
```

### 检查系统完整性
```bash
reachyminios_check
```

### 激活 Python 环境
```bash
source /venvs/apps_venv/bin/activate
```

### 在机器人上运行代码
```bash
python your_script.py
```

## 6. 网络配置

### WiFi 连接
- 机器人创建 WiFi 热点
- 通过 Reachy Mini Control 配置连接到您的 WiFi
- 连接后可通过 `reachy-mini.local` 访问

### 网络发现
如果 `reachy-mini.local` 不解析:
1. 检查路由器的 DHCP 客户端列表
2. 使用 Reachy Mini Control 应用发现机器人
3. 扫描子网:
```bash
for i in $(seq 1 254); do
  curl -sf --connect-timeout 0.3 "http://192.168.1.${i}:8000/api/daemon/status" > /dev/null 2>&1 && echo "Found: 192.168.1.${i}"
done
```

## 7. 电源管理

### 电池信息
- **类型:** LiFePO4
- **容量:** 2000mAh
- **电压:** 6.4V
- **能量:** 12.8Wh
- **续航:** 2-4 小时

### 电量指示
- 🟢 绿色 - 电量充足
- 🟠 橙色 - 电量中等
- 🔴 红色 - 需要充电

### 充电
使用 USB-C 充电。

> **注意:** 无法通过软件查看电池状态，只有 LED 指示灯。

## 8. 高级功能

### 重新刷写 Raspberry Pi ISO
如果需要重新安装系统:
- [重新刷写 ISO 指南](https://huggingface.co/docs/reachy_mini/platforms/reachy_mini/reflash_the_rpi_ISO)

### 从特定分支安装 Daemon
- [从分支安装指南](https://huggingface.co/docs/reachy_mini/platforms/reachy_mini/install_daemon_from_branch)

### 开发工作流
- [开发工作流指南](https://huggingface.co/docs/reachy_mini/platforms/reachy_mini/development_workflow)

## 9. 故障排除

### 常见问题

**问题: WiFi 热点不显示**
- 检查主板上的开关是否在 "debug" 位置 (不是 "download")
- 如果开关位置正确但仍看不到 AP，可能需要重新刷写 ISO

**问题: 无法通过 USB-C 连接**
- Wireless 版本不像 Lite 版那样通过 USB 暴露机器人
- 使用 WiFi 或 SSH 连接

**问题: 会议/酒店 WiFi 无法通信**
- 许多会议和酒店 WiFi 启用了客户端隔离
- 解决方案: 使用手机热点

**问题: 中国访问 HuggingFace**
使用镜像:
```bash
export HF_ENDPOINT=https://hf-mirror.com/
```

## 10. 硬件接口

### 后面板
- 电源开关
- USB-C 端口 (仅数据，不充电)
- 电源指示灯

### 内部接口
- Raspberry Pi CM4
- 电机连接
- 摄像头 CSI
- 麦克风阵列

## 相关链接

- [硬件规格详解](../02-硬件规格/硬件规格详解.md)
- [SDK 安装指南](../03-快速入门/SDK安装指南.md)
- [快速入门指南](../03-快速入门/快速入门指南.md)
- [故障排除指南](../07-故障排除/常见问题与解决方案.md)
