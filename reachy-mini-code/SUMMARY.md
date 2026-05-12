# Reachy Mini 代码库完整总结

## 📊 代码统计

- **Python 文件总数:** 459 个
- **官方仓库:** 4 个
- **社区项目:** 9 个
- **官方示例:** 16 个

## 📁 目录结构

```
reachy-mini-code/
├── README.md                    # 代码库索引
├── official/                    # 官方仓库
│   ├── reachy_mini/            # 主 SDK 仓库 ⭐
│   ├── reachy_mini_conversation_demo/  # 对话应用示例
│   ├── reachy_mini_dances_library/     # 舞蹈动作库
│   └── reachy-mini-desktop-app/        # 桌面控制应用
├── community/                   # 社区项目
│   ├── f1commentator/          # F1 赛车评论员 🏎️
│   ├── baby-reachy-mini-companion/  # 婴儿陪伴机器人 👶
│   ├── reachy_mini_3d_web_viz/ # 3D Web 可视化 🦾
│   ├── reachy_mini_home_assistant/  # Home Assistant 集成 🏠
│   ├── reachy_mini_phone_teleop/    # 手机遥操作 📱
│   ├── hand_tracker_v2/        # 手部追踪 👋
│   ├── spaceship_game/         # 太空船游戏 🚀
│   ├── reachy_mini_simon/      # Simon 记忆游戏 🎮
│   └── reachy_mini_radio/      # 收音机应用 📻
└── examples/                    # 本地示例代码
```

## 🎯 核心代码结构

### 主 SDK 仓库 (`official/reachy_mini/`)

```
src/reachy_mini/
├── reachy_mini.py              # 主类 (41KB)
├── __init__.py                 # 包初始化
├── daemon/                     # Daemon 服务
│   ├── app/                    # 应用管理
│   ├── motor/                  # 电机控制
│   └── media/                  # 媒体处理
├── kinematics/                 # 运动学
├── motion/                     # 动作控制
├── media/                      # 媒体管理
├── io/                         # 输入输出
├── utils/                      # 工具函数
├── tools/                      # 工具脚本
├── assets/                     # 资源文件
│   ├── config/                 # 配置文件
│   └── firmware/               # 固件
└── descriptions/               # 硬件描述
    └── reachy_mini/
        └── mjcf/               # MuJoCo 模型
```

## 🎮 官方示例详解

### 1. minimal_demo.py - 最小示例
**功能:** 基础控制，天线摆动
**学习点:**
- ReachyMini 连接
- create_head_pose() 使用
- set_target() 实时控制
- 正弦运动生成

### 2. joy_controller.py - 游戏手柄控制
**功能:** 使用游戏手柄控制头部和身体
**学习点:**
- pygame 集成
- 死区处理
- 轴映射
- 实时控制循环

### 3. sound_doa.py - 声源定位
**功能:** 检测说话者方向并看向声源
**学习点:**
- 麦克风阵列使用
- DoA (Direction of Arrival) 算法
- 坐标系变换
- look_at_world() 使用

### 4. sound_record.py - 音频录制
**功能:** 录制音频并保存为 WAV
**学习点:**
- 音频流处理
- 采样率配置
- 文件保存

### 5. sound_play.py - 音频播放
**功能:** 播放音频文件
**学习点:**
- 音频推送
- 流式播放
- 格式转换

### 6. take_picture.py - 拍照
**功能:** 获取摄像头画面
**学习点:**
- 帧获取
- 图像处理
- OpenCV 集成

### 7. look_at_image.py - 视觉追踪
**功能:** 追踪图像中的目标
**学习点:**
- 2D 视线控制
- 面部检测
- 实时追踪

### 8. mini_head_position_gui.py - 头部位置 GUI
**功能:** 图形界面控制头部
**学习点:
- GUI 开发
- 滑块控制
- 姿态可视化

### 9. goto_interpolation_playground.py - 运动插值
**功能:** 测试不同插值方法
**学习点:**
- 运动插值算法
- linear, minjerk, ease_in_out, cartoon
- 运动平滑度

### 10. recorded_moves.py - 动作录制回放
**功能:** 录制和回放动作
**学习点:**
- 动作录制
- 数据序列化
- 动作回放

### 11. sequence.py - 动作序列
**功能:** 创建复杂动作序列
**学习点:**
- 动作编排
- 时间同步
- 序列执行

### 12. imu_example.py - IMU 数据
**功能:** 读取 IMU 传感器数据
**学习点:**
- 加速度计
- 陀螺仪
- 四元数

### 13. custom_media_manager.py - 自定义媒体管理
**功能:** 直接访问硬件
**学习点:**
- 媒体后端切换
- OpenCV 直接访问
- sounddevice 直接访问

### 14. rerun_viewer.py - 可视化查看器
**功能:** Rerun 可视化集成
**学习点:**
- 3D 可视化
- 数据流可视化

### 15. reachy_compliant_demo.py - 合规演示
**功能:** 重力补偿模式
**学习点:
- 电机模式切换
- 手动示教
- 合规控制

## 🌟 社区项目亮点

### 🏎️ F1 赛车评论员 (205 stars)
**技术栈:**
- OpenF1 API 数据集成
- ElevenLabs TTS 语音合成
- 210 个评论模板
- 5 种兴奋度级别
- 5 种评论视角
- Web UI 控制面板

**创新点:**
- 实时赛事数据驱动
- 富有表现力的机器人动作
- 多样化评论生成

---

### 👶 婴儿陪伴机器人 (167 stars)
**技术栈:**
- 本地 LLM 推理
- 语音识别
- 安全动作限制
- 儿童友好界面

**创新点:**
- 完全本地化处理
- 婴儿安全模式
- 教育互动设计

---

### 🦾 3D Web 可视化 (27 stars)
**技术栈:**
- Three.js 3D 渲染
- WebSocket 实时通信
- 响应式设计

**创新点:**
- 浏览器中实时 3D
- 远程状态监控
- 跨平台访问

---

### 🏠 Home Assistant 集成 (21 stars)
**技术栈:**
- Home Assistant API
- MQTT 协议
- 自动化脚本

**创新点:**
- 智能家居控制
- 语音助手功能
- 场景自动化

---

### 📱 手机遥操作 (6 stars)
**技术栈:**
- WebRTC 视频流
- 传感器数据映射
- 触摸控制

**创新点:**
- 陀螺仪控制
- 实时视频反馈
- 移动端优化

---

### 👋 手部追踪 (105 stars)
**技术栈:**
- MediaPipe 手部检测
- 计算机视觉
- 实时控制循环

**创新点:**
- 实时手部追踪
- 手势识别
- 自然交互

---

### 🚀 太空船游戏 (50+ stars)
**技术栈:**
- Canvas 游戏渲染
- 头部姿态映射
- 天线按钮交互

**创新点:**
- 头部作为摇杆
- 天线作为按钮
- 沉浸式游戏体验

---

### 🎮 Simon 记忆游戏 (30+ stars)
**技术栈:**
- 天线按钮交互
- 音频反馈
- 游戏逻辑

**创新点:**
- 无 GUI 设计
- 天线交互模式
- 声音反馈

---

### 📻 收音机应用 (10 stars)
**技术栈:**
- 流媒体播放
- 语音识别
- 天线动画

**创新点:**
- 语音控制
- 自然语言点歌
- 天线动画反馈

## 🔧 关键代码模式

### 1. 基础连接
```python
from reachy_mini import ReachyMini

with ReachyMini() as mini:
    # 您的代码
    pass
```

### 2. 头部控制
```python
from reachy_mini.utils import create_head_pose

head_pose = create_head_pose(
    x=0, y=0, z=10,  # 平移 (mm)
    roll=0, pitch=15, yaw=30,  # 旋转 (度)
    mm=True, degrees=True
)
mini.goto_target(head=head_pose, duration=1.0)
```

### 3. 天线控制
```python
mini.goto_target(antennas=[0.5, -0.5], duration=0.5)
```

### 4. 身体旋转
```python
import numpy as np
mini.goto_target(body_yaw=np.deg2rad(30), duration=1.0)
```

### 5. 实时控制
```python
while True:
    # 计算目标
    mini.set_target(head=head_pose, antennas=antennas)
    time.sleep(0.02)  # 50 Hz
```

### 6. 音频录制
```python
mini.media.start_recording()
samples = mini.media.get_audio_sample()  # (samples, 2) float32
mini.media.stop_recording()
```

### 7. 音频播放
```python
mini.media.start_playing()
mini.media.push_audio_sample(audio_data)
mini.media.stop_playing()
```

### 8. 摄像头
```python
frame = mini.media.get_frame()  # (h, w, 3) uint8
```

### 9. 声源定位
```python
doa, is_speech = mini.media.get_DoA()  # 弧度
```

### 10. IMU 数据
```python
imu = mini.imu
accel = imu["accelerometer"]  # m/s^2
gyro = imu["gyroscope"]      # rad/s
quat = imu["quaternion"]     # (w, x, y, z)
```

## 📚 学习路径

### 🟢 初学者 (1-2 天)
1. **minimal_demo.py** - 基础控制
2. **take_picture.py** - 摄像头使用
3. **sound_record.py** - 音频录制
4. **goto_interpolation_playground.py** - 运动理解

### 🟡 中级开发者 (3-5 天)
1. **joy_controller.py** - 外设集成
2. **sound_doa.py** - 传感器融合
3. **hand_tracker_v2/** - 计算机视觉
4. **spaceship_game/** - 游戏开发

### 🔴 高级开发者 (1-2 周)
1. **reachy_mini/src/** - SDK 源码研究
2. **conversation_demo/** - AI 集成
3. **home_assistant/** - 系统集成
4. **custom_media_manager.py** - 硬件直接访问

## 🛠️ 开发环境设置

### 安装 SDK
```bash
# 创建虚拟环境
uv venv reachy_mini_env --python 3.12
source reachy_mini_env/bin/activate

# 安装 SDK
uv pip install "reachy-mini"

# 安装开发依赖
cd reachy-mini-code/official/reachy_mini
pip install -e .
```

### 运行示例
```bash
# 启动 daemon (Lite)
reachy-mini-daemon

# 或启动仿真
reachy-mini-daemon --sim

# 运行示例
python examples/minimal_demo.py
```

## 🔗 相关资源

### 官方资源
- [文档库](../reachy-mini-docs/README.md)
- [GitHub 主仓库](https://github.com/pollen-robotics/reachy_mini)
- [Hugging Face](https://huggingface.co/reachy-mini)

### 社区资源
- [Discord 社区](https://discord.gg/Y7FgMqHsub)
- [Hugging Face Spaces](https://huggingface.co/spaces?q=reachy_mini)

### 学习资源
- [应用开发指南](../reachy-mini-docs/06-应用开发/应用开发指南.md)
- [Python SDK 参考](../reachy-mini-docs/04-SDK文档/Python-SDK参考.md)
- [故障排除指南](../reachy-mini-docs/07-故障排除/常见问题与解决方案.md)

## 📝 贡献指南

### 如何贡献
1. Fork 项目
2. 创建功能分支
3. 编写测试
4. 提交 Pull Request

### 代码规范
- 遵循 PEP 8
- 添加类型注解
- 编写文档字符串
- 保持测试覆盖

## 🎉 总结

Reachy Mini 拥有丰富的开源生态系统:

- **官方代码:** 完整的 SDK、daemon、示例和工具
- **社区项目:** 创新的应用和游戏
- **学习资源:** 详细的文档和教程
- **活跃社区:** Discord 和 Hugging Face

无论您是初学者还是高级开发者，都能找到适合的学习路径和项目灵感。

**开始您的 Reachy Mini 开发之旅吧！** 🤖
