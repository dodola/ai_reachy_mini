# Wireless 版本有线连接指南

## 概述

Reachy Mini **Wireless 版本**支持多种连接方式，包括有线连接。

## 连接方式对比

| 连接方式 | Lite | Wireless |
|----------|------|----------|
| **USB 直连** | ✅ 支持 | ❌ 不支持 |
| **WiFi** | ❌ 不支持 | ✅ 支持 |
| **以太网 (有线)** | ❌ 不支持 | ✅ 支持 |

## 为什么 Wireless 不能 USB 直连？

**技术原因:**
- Lite 版本的控制板通过 USB 暴露机器人接口
- Wireless 版本的 CM4 控制板没有这个功能
- USB-C 端口仅用于:
  - 充电
  - 连接 USB 设备 (如 U 盘)
  - 以太网适配器

## 有线连接方案

### 方案 1: USB-C 转以太网适配器 (推荐)

```
Reachy Mini Wireless ←USB-C→ 以太网适配器 ←网线→ 路由器/电脑
```

**所需设备:**
- USB-C 转以太网适配器 (~$15-25)
- 以太网网线

**优点:**
- ✅ 稳定的有线连接
- ✅ 低延迟
- ✅ 适合会议/酒店 WiFi 受限环境

**设置步骤:**
1. 将 USB-C 适配器插入机器人的 USB-C 端口
2. 连接以太网网线
3. 机器人会自动获取 IP 地址
4. 通过 `reachy-mini.local` 或 IP 地址连接

**推荐产品:**
- Anker USB-C 转以太网适配器
- TP-Link UE300
- 通用 USB-C 转 RJ45 适配器

---

### 方案 2: WiFi 连接 (无线)

```
Reachy Mini Wireless ←WiFi→ 路由器 ←WiFi/有线→ 您的电脑
```

**优点:**
- ✅ 无需额外设备
- ✅ 完全无线

**缺点:**
- ❌ 信号可能不稳定
- ❌ 会议/酒店 WiFi 可能有客户端隔离

**设置步骤:**
1. 开机，机器人创建 WiFi 热点
2. 使用 Reachy Mini Control 应用连接
3. 配置连接到您的 WiFi
4. 通过 `reachy-mini.local` 访问

---

### 方案 3: SSH 直连 (开发用)

```bash
# 连接到机器人内部的 Raspberry Pi
ssh pollen@reachy-mini.local
# 密码: root

# 在机器人上直接运行代码
python your_script.py
```

**优点:**
- ✅ 无需外部电脑运行代码
- ✅ 代码在机器人本地执行

---

## 网络配置

### WiFi 连接

1. **首次设置:**
   - 开机，机器人创建 WiFi 热点
   - 使用 Reachy Mini Control 应用
   - 点击 "First time connecting..."
   - 按照说明配置 WiFi

2. **连接后访问:**
   ```bash
   # 通过 mDNS
   ping reachy-mini.local
   
   # 或通过 IP 地址
   # 查找 IP: 检查路由器 DHCP 客户端列表
   ```

### 以太网连接

1. **连接适配器:**
   - 插入 USB-C 转以太网适配器
   - 连接网线

2. **自动配置:**
   - 机器人会自动获取 IP 地址
   - 通过 `reachy-mini.local` 访问

---

## 网络发现

如果 `reachy-mini.local` 不解析:

### 方法 1: 检查路由器
```
登录路由器管理界面
查看 DHCP 客户端列表
找到 "reachy-mini" 设备
```

### 方法 2: 使用 Reachy Mini Control
```
打开 Reachy Mini Control 应用
它会自动发现网络上的机器人
```

### 方法 3: 扫描子网
```bash
# Linux/Mac
for i in $(seq 1 254); do
  curl -sf --connect-timeout 0.3 "http://192.168.1.${i}:8000/api/daemon/status" > /dev/null 2>&1 && echo "Found: 192.168.1.${i}"
done

# Windows (PowerShell)
1..254 | ForEach-Object {
  $ip = "192.168.1.$_"
  if (Test-Connection -ComputerName $ip -Count 1 -Quiet) {
    Write-Host "Found: $ip"
  }
}
```

---

## 特殊环境配置

### 会议/酒店 WiFi

许多会议和酒店 WiFi 启用**客户端隔离**，阻止设备间通信。

**解决方案:**
1. **使用手机热点** (推荐)
   ```
   手机热点 ←WiFi→ 机器人 + 电脑
   ```

2. **使用以太网适配器**
   ```
   机器人 ←以太网→ 电脑 (直连)
   ```

3. **使用 USB-C 转以太网适配器**
   ```
   机器人 ←USB-C→ 适配器 ←以太网→ 路由器
   ```

---

### 中国网络环境

#### 访问 HuggingFace
```bash
# 使用镜像
export HF_ENDPOINT=https://hf-mirror.com/
```

#### 访问 OpenAI API (对话应用)
需要配置 VPN 或使用代理。

**VPN 配置建议:**
1. 在路由器上配置 VPN
2. 或在机器人上配置 VPN
3. 白名单本地网络:
   - 192.168.0.0/16
   - 端口 22 (SSH)
   - 端口 8000 (Daemon)
   - 端口 5353 (mDNS)

---

## 连接方式选择建议

### 场景 1: 家庭/办公室
```
推荐: WiFi 连接
原因: 简单方便，信号稳定
```

### 场景 2: 会议/酒店
```
推荐: USB-C 转以太网适配器
原因: 避免 WiFi 客户端隔离问题
```

### 场景 3: 开发调试
```
推荐: SSH 直连 + WiFi
原因: 可以在机器人上直接运行代码
```

### 场景 4: 需要最低延迟
```
推荐: USB-C 转以太网适配器
原因: 有线连接延迟最低
```

### 场景 5: 展示/演示
```
推荐: WiFi + 手机热点备用
原因: 便携性好，有备用方案
```

---

## 购买建议

### USB-C 转以太网适配器

**价格:** $15-25

**规格:**
- USB 3.0
- 千兆以太网
- 兼容 Linux

**推荐产品:**
1. **Anker USB-C 转以太网适配器**
   - 价格: ~$20
   - 优点: 稳定，兼容性好

2. **TP-Link UE300**
   - 价格: ~$15
   - 优点: 便宜，性能好

3. **通用 USB-C 转 RJ45 适配器**
   - 价格: ~$10-15
   - 优点: 便宜

**购买链接:**
- Amazon: 搜索 "USB-C to Ethernet adapter"
- 淘宝: 搜索 "USB-C 转网口"

---

## 故障排除

### 问题: 以太网适配器不工作

**检查:**
1. 适配器是否兼容 Linux
2. 是否需要额外驱动
3. 网线是否正常

**解决:**
```bash
# SSH 到机器人
ssh pollen@reachy-mini.local

# 检查网络接口
ip addr show

# 检查 USB 设备
lsusb

# 重启网络服务
sudo systemctl restart networking
```

---

### 问题: WiFi 连接不稳定

**检查:**
1. 信号强度
2. 路由器距离
3. 干扰源

**解决:**
1. 靠近路由器
2. 使用 5GHz 频段
3. 避免微波炉等干扰源

---

### 问题: mDNS 不解析

**检查:**
1. 路由器是否支持 mDNS
2. 防火墙设置

**解决:**
1. 使用 IP 地址代替
2. 扫描子网查找 IP
3. 配置静态 IP

---

## 总结

### 连接方式对比

| 方式 | 稳定性 | 延迟 | 便携性 | 成本 |
|------|--------|------|--------|------|
| **WiFi** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $0 |
| **以太网** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | $15-25 |
| **SSH** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $0 |

### 推荐

**日常使用:** WiFi 连接
**专业使用:** 以太网适配器
**开发调试:** SSH 直连

**以太网适配器是有线连接的最佳选择！**

## 相关链接

- [Wireless 版本指南](../05-平台指南/Wireless版本指南.md)
- [Lite 版本指南](../05-平台指南/Lite版本指南.md)
- [故障排除指南](../07-故障排除/常见问题与解决方案.md)
