# Reachy Mini SDK 安装指南

## 系统支持

| 操作系统 | 支持状态 |
|----------|----------|
| 🐧 Linux | ✅ 支持 |
| 🍎 macOS | ✅ 支持 |
| 🪟 Windows | ✅ 支持 |

## 前置要求

| 工具 | 版本 | 用途 |
|------|------|------|
| 🐍 Python | 3.10 - 3.12 | 运行 Reachy Mini SDK |
| 📂 Git | 最新 | 下载源代码和应用 |
| 📦 Git LFS | 最新 | 下载模型资源 |

## 步骤 1: 安装 Python

我们推荐使用 `uv` - 一个快速的 Python 包管理器。

### Linux / macOS

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证安装
uv --version

# 安装 Python 3.12
uv python install 3.12 --default
```

### Windows

```powershell
# 安装 uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 验证安装
uv --version

# 安装 Python 3.12
uv python install 3.12 --default
```

## 步骤 2: 安装 Git 和 Git LFS

### Linux (Ubuntu/Debian)

```bash
sudo apt install git git-lfs
git lfs install
```

### macOS

```bash
# 安装 Homebrew (如果未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 对于 Apple Silicon (M1, M2 等)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# 安装 Git 和 Git LFS
brew install git git-lfs
git lfs install
```

### Windows

1. 下载并安装 Git: https://git-scm.com/install/windows
2. 安装后运行:
```bash
git lfs install
```

## 步骤 3: 创建虚拟环境

```bash
# 创建虚拟环境
uv venv reachy_mini_env --python 3.12

# 激活虚拟环境
# Linux/macOS:
source reachy_mini_env/bin/activate

# Windows:
reachy_mini_env\Scripts\activate
```

> **成功标志:** 命令行提示符前应显示 `(reachy_mini_env)`

### Windows 脚本执行权限

如果遇到权限问题:

1. 以管理员身份打开 PowerShell
2. 运行:
```powershell
Set-ExecutionPolicy RemoteSigned
```
3. 关闭管理员终端，打开普通终端
4. 再次激活虚拟环境

## 步骤 4: 安装 Reachy Mini SDK

### 标准安装 (推荐)

```bash
uv pip install "reachy-mini"
```

### 包含仿真支持

```bash
uv pip install "reachy-mini[mujoco]"
```

### 开发者安装 (从源码)

```bash
git clone https://github.com/pollen-robotics/reachy_mini
cd reachy_mini
uv sync

# 包含仿真支持
uv sync --extra mujoco
```

## Linux 额外步骤

### 安装 GStreamer

```bash
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
```

### 设置 USB 权限

```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d3", MODE="0666", GROUP="dialout"
SUBSYSTEM=="usb", ATTRS{idVendor}=="38fb", ATTRS{idProduct}=="1001", MODE="0666", GROUP="dialout"' \
| sudo tee /etc/udev/rules.d/99-reachy-mini.rules

sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG dialout $USER
```

> **注意:** 注销并重新登录以使更改生效！

## 验证安装

```bash
# 检查 SDK 版本
python -c "import reachy_mini; print(reachy_mini.__version__)"

# 检查 daemon 是否可用
reachy-mini-daemon --help
```

## 安装桌面应用 (可选)

Reachy Mini Control 桌面应用提供图形界面:

- **下载地址:** https://hf.co/reachy-mini/#/download
- **功能:** 可视化工具、应用启动器、系统设置

## 更新 SDK

```bash
uv pip install -U reachy-mini
```

## 卸载 SDK

```bash
uv pip uninstall reachy-mini
```

## 常见安装问题

### 问题: pip 安装失败
**解决方案:**
```bash
# 升级 pip
uv pip install --upgrade pip

# 清除缓存
uv pip cache purge
```

### 问题: MuJoCo 安装失败 (macOS)
**解决方案:**
```bash
# 使用 pip 而不是 uv
pip install "reachy-mini[mujoco]"
```

### 问题: GStreamer 错误
**解决方案:**
确保安装了所有 GStreamer 插件包。

### 问题: 权限被拒绝 (Linux)
**解决方案:**
确保已添加 udev 规则并重新登录。

## 下一步

- [快速入门指南](./快速入门指南.md) - 运行第一个程序
- [Python SDK 参考](../04-SDK文档/Python-SDK参考.md) - 学习 API
- [故障排除指南](../07-故障排除/常见问题与解决方案.md) - 解决问题
