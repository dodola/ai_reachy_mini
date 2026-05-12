# Python SDK 参考

## 连接

```python
from reachy_mini import ReachyMini

# 自动检测连接类型
with ReachyMini() as mini:
    # 您的代码
    pass

# 强制本地连接 (Lite)
with ReachyMini(connection_mode="localhost_only") as mini:
    pass

# 强制网络连接 (Wireless)
with ReachyMini(connection_mode="network") as mini:
    pass
```

## 运动控制

### goto_target() - 平滑运动

在点之间平滑插值。可以控制 `head`、`antennas` 和 `body_yaw`。

```python
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose
import numpy as np

with ReachyMini() as mini:
    # 同时移动所有部件
    mini.goto_target(
        head=create_head_pose(z=10, mm=True),        # 向上 10mm
        antennas=np.deg2rad([45, 45]),               # 天线展开
        body_yaw=np.deg2rad(30),                     # 转动身体
        duration=2.0,                                # 耗时 2 秒
        method="minjerk"                             # 平滑加速度
    )
```

**插值方法:**
- `linear` - 线性插值
- `minjerk` (默认) - 最小加加速度
- `ease_in_out` - 缓入缓出
- `cartoon` - 卡通风格

### set_target() - 即时控制

绕过插值，直接设置目标。用于高频控制。

```python
with ReachyMini() as mini:
    # 即时移动
    mini.set_target(
        head=create_head_pose(yaw=30, degrees=True),
        antennas=[0.3, -0.3]
    )
```

### create_head_pose() - 创建头部姿态

```python
from reachy_mini.utils import create_head_pose

# 使用毫米和度数
pose = create_head_pose(
    x=0,      # X 平移 (mm)
    y=0,      # Y 平移 (mm)
    z=10,     # Z 平移 (mm)
    roll=15,  # Roll 旋转 (度)
    pitch=0,  # Pitch 旋转 (度)
    yaw=30,   # Yaw 旋转 (度)
    mm=True,  # 使用毫米单位
    degrees=True  # 使用度数单位
)

# 使用弧度和米
pose = create_head_pose(
    z=0.01,           # 10mm = 0.01m
    roll=np.deg2rad(15),
    yaw=np.deg2rad(30)
)
```

## 传感器

### 摄像头

```python
from reachy_mini import ReachyMini

with ReachyMini(media_backend="default") as mini:
    # 获取一帧图像
    frame = mini.media.get_frame()
    # 返回 numpy 数组，形状 (height, width, 3)，数据类型 uint8
```

### IMU (仅 Wireless 版本)

```python
with ReachyMini() as mini:
    imu_data = mini.imu
    
    # 加速度计 (m/s^2)
    accel_x, accel_y, accel_z = imu_data["accelerometer"]
    
    # 陀螺仪 (rad/s)
    gyro_x, gyro_y, gyro_z = imu_data["gyroscope"]
    
    # 四元数 (w, x, y, z)
    quat_w, quat_x, quat_y, quat_z = imu_data["quaternion"]
    
    # 温度 (°C)
    temperature = imu_data["temperature"]
```

### 音频

```python
from reachy_mini import ReachyMini
from scipy.signal import resample
import time

with ReachyMini(media_backend="default") as mini:
    # 初始化音频设备
    mini.media.start_recording()
    mini.media.start_playing()
    
    # 录制
    samples = mini.media.get_audio_sample()
    
    # 重采样 (如果需要)
    samples = resample(
        samples, 
        mini.media.get_output_audio_samplerate() * len(samples) / mini.media.get_input_audio_samplerate()
    )
    
    # 播放
    mini.media.push_audio_sample(samples)
    time.sleep(len(samples) / mini.media.get_output_audio_samplerate())
    
    # 获取声源方向
    # 0 弧度 = 左, π/2 弧度 = 前/后, π 弧度 = 右
    doa, is_speech_detected = mini.media.get_DoA()
    
    # 释放音频设备
    mini.media.stop_recording()
    mini.media.stop_playing()
```

**音频数据格式:**
- `get_audio_sample()` - 返回形状 `(samples, 2)` 的 float32 数组，采样率 16kHz
- `push_audio_sample()` - 期望形状 `(samples, 1 或 2)` 的 float32 数组，采样率 16kHz

## 媒体后端选项

| 后端 | 说明 | 使用场景 |
|------|------|----------|
| `default` | 自动检测 | 大多数情况 |
| `local` | 本地 IPC | 同一台机器 |
| `webrtc` | WebRTC 流 | 远程连接 |
| `no_media` | 禁用媒体 | 直接硬件访问 |

```python
# 使用默认后端
with ReachyMini(media_backend="default") as mini:
    pass

# 禁用媒体 (直接访问硬件)
with ReachyMini(media_backend="no_media") as mini:
    import cv2
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
```

## 电机控制

```python
with ReachyMini() as mini:
    # 启用电机 (僵硬)
    mini.enable_motors()
    
    # 禁用电机 (松弛)
    mini.disable_motors()
    
    # 启用重力补偿
    mini.enable_gravity_compensation()
```

## 动作录制与回放

```python
from reachy_mini import ReachyMini

with ReachyMini() as mini:
    # 开始录制
    mini.start_recording()
    
    # ... 机器人移动 ...
    
    # 停止录制并获取数据
    recorded_data = mini.stop_recording()
```

### 使用预定义动作库

```python
from reachy_mini.motion.recorded_move import RecordedMoves

with ReachyMini() as mini:
    # 加载动作库
    moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
    
    # 播放动作
    mini.play_move(moves.get("happy"), initial_goto_duration=1.0)
```

## 视觉控制

### 2D 视线控制 (图像坐标)

```python
with ReachyMini() as mini:
    # 看图像中的某个点
    # (0,0) 是左上角
    mini.look_at_image(x=320, y=240)
```

### 3D 视线控制 (世界坐标)

```python
with ReachyMini() as mini:
    # 看世界坐标系中的某个点
    mini.look_at_world(x=0.5, y=0, z=0.3)
```

## HTTP & WebSocket API

Daemon 提供 REST API:

```bash
# API 文档
http://localhost:8000/docs

# 获取状态
GET /api/state/full

# WebSocket 实时更新
ws://localhost:8000/api/state/ws/full
```

## 录制移动

```python
with ReachyMini() as mini:
    # 开始录制
    mini.start_recording()
    
    # ... 机器人移动 ...
    
    # 停止录制
    recorded_data = mini.stop_recording()
```

## 状态查询

```python
with ReachyMini() as mini:
    # 获取完整状态
    state = mini.state
    print(state)
    
    # 获取 daemon 状态
    status = mini.client.get_status()
    print(status)
```

## 错误处理

```python
from reachy_mini import ReachyMini

try:
    with ReachyMini() as mini:
        # 您的代码
        pass
except ConnectionError:
    print("无法连接到 daemon")
except Exception as e:
    print(f"错误: {e}")
```

## 最佳实践

1. **使用上下文管理器:** 始终使用 `with` 语句
2. **检查连接:** 在操作前确保连接成功
3. **处理异常:** 捕获并处理可能的错误
4. **释放资源:** 使用完毕后释放媒体设备
5. **选择合适的运动方法:** 
   - `goto_target()` 用于手势和动画
   - `set_target()` 用于实时控制

## 相关链接

- [核心概念与架构](./核心概念与架构.md)
- [媒体架构](./媒体架构.md)
- [示例代码](../09-示例代码/示例代码集合.md)
- [故障排除指南](../07-故障排除/常见问题与解决方案.md)
