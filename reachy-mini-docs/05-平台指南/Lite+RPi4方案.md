# Reachy Mini Lite + Raspberry Pi 4 方案

## 概述

如果您已有 **Raspberry Pi 4**，这是**最佳性价比方案**！

```
Reachy Mini Lite ($299) + 您的 Raspberry Pi 4 ($0)
────────────────────────────────────────────────────
总成本: $299
```

**vs Wireless ($449)**

**节省: $150** 🎉

## 方案对比

| 方案 | 成本 | 功能 | 便携性 |
|------|------|------|--------|
| **Lite** | $299 | ⭐⭐⭐ | ⭐⭐ |
| **Wireless** | $449 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Lite + RPi4** | $299 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 实现方案

### 方案 1: USB 连接 (推荐)

```
┌─────────────┐     USB      ┌─────────────┐     WiFi     ┌─────────────┐
│ Reachy Mini │◄────────────►│ Raspberry   │◄────────────►│  您的电脑   │
│   Lite      │              │ Pi 4        │              │  或手机     │
└─────────────┘              └─────────────┘              └─────────────┘
```

**实现步骤:**
1. Raspberry Pi 4 运行 daemon
2. 通过 USB 连接到 Reachy Mini Lite
3. Raspberry Pi 4 连接 WiFi
4. 从电脑/手机远程控制

**优点:**
- ✅ 无线控制
- ✅ 成本低
- ✅ 计算能力更强 (RPi 4)

---

### 方案 2: 以太网连接

```
┌─────────────┐     USB      ┌─────────────┐   以太网    ┌─────────────┐
│ Reachy Mini │◄────────────►│ Raspberry   │◄───────────►│  路由器     │
│   Lite      │              │ Pi 4        │              │             │
└─────────────┘              └─────────────┘              └──────┬──────┘
                                                                 │
                                                           ┌─────▼─────┐
                                                           │  您的电脑 │
                                                           └───────────┘
```

---

## 性能对比

| 规格 | Raspberry Pi 4 | CM4 (Wireless) |
|------|----------------|----------------|
| **CPU** | BCM2711 (4核) | BCM2711 (4核) |
| **RAM** | 2/4/8 GB | 4 GB |
| **存储** | microSD | 16GB eMMC |
| **WiFi** | ✅ | ✅ |
| **以太网** | ✅ (原生) | ✅ (需适配器) |
| **USB** | 4 个 | 1 个 |
| **价格** | 您已有 | ~$75 |

**结论:** Raspberry Pi 4 性能相当或更好！

## 具体实现

### 步骤 1: 设置 Raspberry Pi 4

```bash
# 1. 安装 Raspberry Pi OS
# 下载: https://www.raspberrypi.com/software/

# 2. 安装 Python 和依赖
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# 3. 创建虚拟环境
python3 -m venv reachy_env
source reachy_env/bin/activate

# 4. 安装 Reachy Mini SDK
pip install reachy-mini
```

### 步骤 2: 连接 Reachy Mini Lite

```bash
# 1. 用 USB 线连接 Reachy Mini Lite 到 Raspberry Pi 4

# 2. 启动 daemon
reachy-mini-daemon
```

### 步骤 3: 远程控制

```bash
# 在电脑上安装 SDK
pip install reachy-mini

# 连接到 Raspberry Pi 4 上的 daemon
python your_script.py
# SDK 会自动发现网络上的 daemon
```

## 完整功能对比

| 功能 | Lite | Wireless | Lite + RPi4 |
|------|------|----------|-------------|
| **独立运行** | ❌ | ✅ | ✅ |
| **WiFi** | ❌ | ✅ | ✅ |
| **以太网** | ❌ | ✅ (需适配器) | ✅ (原生) |
| **IMU** | ❌ | ✅ | ❌ |
| **电池** | ❌ | ✅ | ❌ |
| **便携性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **计算能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **成本** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 与 Wireless 的差异

### ✅ Lite + RPi4 优势
- **价格:** $299 vs $449 (节省 $150)
- **计算能力:** RPi 4 可能更强
- **以太网:** 原生支持，无需适配器
- **USB 端口:** RPi 4 有 4 个 USB 端口
- **灵活性:** 可以随时断开 RPi4 单独使用

### ❌ Lite + RPi4 劣势
- **便携性:** 需要额外的 RPi4 设备
- **IMU:** 没有惯性测量单元
- **电池:** 需要外接电源
- **集成度:** 不如 Wireless 紧凑
- **美观:** 线缆更多

## 电源方案

### 方案 A: 有线供电

```
墙壁插座 → 电源适配器 → Reachy Mini Lite
墙壁插座 → USB 电源 → Raspberry Pi 4
```

### 方案 B: 移动电源 (可选)

```
移动电源 → Raspberry Pi 4
墙壁插座 → Reachy Mini Lite (需要 7V-5A)
```

**注意:** Reachy Mini Lite 需要 7V-5A 电源，普通移动电源无法供电

## 添加 IMU (可选)

如果需要 IMU 功能，可以添加外部传感器:

```bash
# 安装 I2C 工具
sudo apt install python3-smbus i2c-tools

# 启用 I2C
sudo raspi-config
# 选择 Interface Options → I2C → Enable

# 安装 MPU6050 库
pip install mpu6050-raspberrypi
```

**代码示例:**

```python
from mpu6050 import mpu6050
import time

# 初始化 IMU
imu = mpu6050(0x68)

while True:
    # 读取加速度
    accel = imu.get_accel_data()
    print(f"Accel: {accel}")
    
    # 读取陀螺仪
    gyro = imu.get_gyro_data()
    print(f"Gyro: {gyro}")
    
    time.sleep(0.1)
```

**总成本:** ~$310-315 (含 IMU 传感器)

## 网络配置

### WiFi 配置

```bash
# 在 Raspberry Pi 4 上配置 WiFi
sudo raspi-config
# 选择 System Options → Wireless LAN

# 或使用命令行
sudo nmcli device wifi connect "SSID" password "PASSWORD"
```

### SSH 配置

```bash
# 启用 SSH
sudo raspi-config
# 选择 Interface Options → SSH → Enable

# 从电脑连接
ssh pi@raspberrypi.local
# 默认密码: raspberry
```

### 静态 IP (可选)

```bash
# 编辑 dhcpcd.conf
sudo nano /etc/dhcpcd.conf

# 添加以下内容
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

## 自动启动

### 设置 daemon 自动启动

```bash
# 创建 systemd 服务
sudo nano /etc/systemd/system/reachy-mini.service
```

**文件内容:**

```ini
[Unit]
Description=Reachy Mini Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/home/pi/reachy_env/bin/reachy-mini-daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**启用服务:**

```bash
sudo systemctl enable reachy-mini.service
sudo systemctl start reachy-mini.service

# 检查状态
sudo systemctl status reachy-mini.service
```

## 故障排除

### 问题: USB 连接不稳定

**检查:**
1. USB 线是否正常
2. USB 端口是否供电不足

**解决:**
1. 使用高质量 USB 线
2. 使用带电源的 USB Hub
3. 尝试不同的 USB 端口

---

### 问题: daemon 无法启动

**检查:**
1. Python 环境是否正确
2. SDK 是否安装成功

**解决:**
```bash
# 激活环境
source reachy_env/bin/activate

# 检查 SDK
python -c "import reachy_mini; print(reachy_mini.__version__)"

# 手动启动 daemon
reachy-mini-daemon --verbose
```

---

### 问题: 无法远程连接

**检查:**
1. 网络是否正常
2. daemon 是否运行
3. 防火墙设置

**解决:**
```bash
# 检查 daemon 状态
sudo systemctl status reachy-mini.service

# 检查端口
netstat -tlnp | grep 8000

# 检查防火墙
sudo ufw status
sudo ufw allow 8000
```

## 总结

### Lite + Raspberry Pi 4 方案优势

| 优势 | 说明 |
|------|------|
| **成本低** | 节省 $150 |
| **性能强** | RPi 4 计算能力 |
| **灵活性** | 可断开单独使用 |
| **扩展性** | 4 个 USB 端口 |
| **以太网** | 原生支持 |

### 推荐配置

```
Reachy Mini Lite ($299)
+ Raspberry Pi 4 (已有)
+ USB 线 (已有)
+ 电源适配器 (含)
+ MPU6050 IMU (可选, ~$10)
────────────────────────
总计: $299 或 $309
```

### 适用人群

- ✅ 已有 Raspberry Pi 4 的用户
- ✅ 预算有限但想要无线功能
- ✅ 需要更强计算能力
- ✅ 开发者和创客
- ✅ 教育机构

### 获得的功能

- ✅ 独立运行
- ✅ WiFi/以太网连接
- ✅ 远程控制
- ✅ 强大的计算能力
- ✅ IMU (外接)
- ❌ 无电池 (需外接电源)

**这是最佳性价比方案！** 🏆

## 相关链接

- [性价比分析](../01-概述/性价比分析.md)
- [Lite 版本指南](./Lite版本指南.md)
- [IMU 传感器详解](../02-硬件规格/IMU传感器详解.md)
- [SDK 安装指南](../03-快速入门/SDK安装指南.md)
