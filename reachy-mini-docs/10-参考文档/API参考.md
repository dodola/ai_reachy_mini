# API 参考

## ReachyMini 类

### 构造函数

```python
ReachyMini(
    connection_mode: str = "auto",
    media_backend: str = "default"
)
```

**参数:**
- `connection_mode` - 连接模式
  - `"auto"` - 自动检测 (默认)
  - `"localhost_only"` - 本地连接 (Lite)
  - `"network"` - 网络连接 (Wireless)
- `media_backend` - 媒体后端
  - `"default"` - 自动检测 (默认)
  - `"local"` - 本地 IPC
  - `"webrtc"` - WebRTC 流
  - `"no_media"` - 禁用媒体

### 方法

#### goto_target()

平滑运动到目标位置。

```python
goto_target(
    head: np.ndarray | None = None,
    antennas: np.ndarray | list | None = None,
    body_yaw: float | None = None,
    duration: float = 0.5,
    method: str = "minjerk"
)
```

**参数:**
- `head` - 头部姿态 (6DOF)
- `antennas` - 天线角度 [左, 右] (弧度)
- `body_yaw` - 身体旋转 (弧度)
- `duration` - 运动持续时间 (秒)
- `method` - 插值方法
  - `"linear"` - 线性
  - `"minjerk"` - 最小加加速度 (默认)
  - `"ease_in_out"` - 缓入缓出
  - `"cartoon"` - 卡通风格

#### set_target()

即时设置目标位置。

```python
set_target(
    head: np.ndarray | None = None,
    antennas: np.ndarray | list | None = None,
    body_yaw: float | None = None
)
```

**参数:** 同 `goto_target()`

#### look_at_image()

看向图像中的 2D 点。

```python
look_at_image(x: int, y: int)
```

**参数:**
- `x` - 图像 X 坐标 (0 = 左)
- `y` - 图像 Y 坐标 (0 = 上)

#### look_at_world()

看向世界坐标系中的 3D 点。

```python
look_at_world(x: float, y: float, z: float)
```

**参数:**
- `x` - X 坐标 (前方)
- `y` - Y 坐标 (左方)
- `z` - Z 坐标 (上方)

#### enable_motors()

启用电机 (僵硬模式)。

```python
enable_motors()
```

#### disable_motors()

禁用电机 (松弛模式)。

```python
disable_motors()
```

#### enable_gravity_compensation()

启用重力补偿 (柔软模式)。

```python
enable_gravity_compensation()
```

#### start_recording()

开始录制动作。

```python
start_recording()
```

#### stop_recording()

停止录制并返回数据。

```python
stop_recording() -> RecordedMove
```

**返回:** 录制的动作数据

#### play_move()

播放录制的动作。

```python
play_move(
    move: RecordedMove,
    initial_goto_duration: float = 1.0
)
```

**参数:**
- `move` - 录制的动作数据
- `initial_goto_duration` - 初始移动持续时间 (秒)

#### release_media()

释放媒体设备。

```python
release_media()
```

#### acquire_media()

重新获取媒体设备。

```python
acquire_media()
```

### 属性

#### state

获取机器人当前状态。

```python
state: dict
```

#### imu

获取 IMU 数据 (仅 Wireless)。

```python
imu: dict
```

**返回:**
```python
{
    "accelerometer": (x, y, z),  # m/s^2
    "gyroscope": (x, y, z),      # rad/s
    "quaternion": (w, x, y, z),
    "temperature": float          # °C
}
```

#### media

媒体管理器。

```python
media: MediaManager
```

---

## MediaManager 类

### 方法

#### start_recording()

开始音频录制。

```python
start_recording()
```

#### stop_recording()

停止音频录制。

```python
stop_recording()
```

#### start_playing()

开始音频播放。

```python
start_playing()
```

#### stop_playing()

停止音频播放。

```python
stop_playing()
```

#### get_frame()

获取摄像头帧。

```python
get_frame() -> np.ndarray
```

**返回:** 形状 `(height, width, 3)` 的 uint8 数组

#### get_audio_sample()

获取音频样本。

```python
get_audio_sample() -> np.ndarray
```

**返回:** 形状 `(samples, 2)` 的 float32 数组，采样率 16kHz

#### push_audio_sample()

推送音频样本进行播放。

```python
push_audio_sample(audio: np.ndarray)
```

**参数:**
- `audio` - 形状 `(samples, 1 或 2)` 的 float32 数组，采样率 16kHz

#### get_DoA()

获取声源方向。

```python
get_DoA() -> tuple[float, bool]
```

**返回:** (方向弧度, 是否检测到语音)

- 0 弧度 = 左
- π/2 弧度 = 前/后
- π 弧度 = 右

#### get_input_audio_samplerate()

获取输入音频采样率。

```python
get_input_audio_samplerate() -> int
```

#### get_output_audio_samplerate()

获取输出音频采样率。

```python
get_output_audio_samplerate() -> int
```

#### get_input_channels()

获取输入通道数。

```python
get_input_channels() -> int
```

#### get_output_channels()

获取输出通道数。

```python
get_output_channels() -> int
```

---

## create_head_pose() 函数

创建头部姿态矩阵。

```python
create_head_pose(
    x: float = 0,
    y: float = 0,
    z: float = 0,
    roll: float = 0,
    pitch: float = 0,
    yaw: float = 0,
    mm: bool = False,
    degrees: bool = False
) -> np.ndarray
```

**参数:**
- `x` - X 平移 (默认: 米)
- `y` - Y 平移 (默认: 米)
- `z` - Z 平移 (默认: 米)
- `roll` - Roll 旋转 (默认: 弧度)
- `pitch` - Pitch 旋转 (默认: 弧度)
- `yaw` - Yaw 旋转 (默认: 弧度)
- `mm` - 使用毫米单位
- `degrees` - 使用度数单位

**返回:** 4x4 齐次变换矩阵

---

## RecordedMoves 类

加载预定义动作库。

```python
RecordedMoves(repo_id: str)
```

**参数:**
- `repo_id` - Hugging Face 仓库 ID

### 方法

#### get()

获取指定动作。

```python
get(name: str) -> RecordedMove
```

**参数:**
- `name` - 动作名称

**返回:** 录制的动作数据

**示例:**
```python
from reachy_mini.motion.recorded_move import RecordedMoves

moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
happy_move = moves.get("happy")
```

---

## ReachyMiniApp 类

应用基类。

```python
class ReachyMiniApp:
    custom_app_url: str | None = None
    
    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        raise NotImplementedError
    
    def wrapped_run(self):
        # 处理连接、启动服务等
        pass
    
    def stop(self):
        # 设置 stop_event
        pass
```

### 属性

#### custom_app_url

Web UI URL。

```python
custom_app_url: str | None = None
```

设置后，应用会自动启动 FastAPI 服务器。

#### settings_app

FastAPI 应用实例 (用于定义路由)。

```python
settings_app: FastAPI
```

### 方法

#### run()

主应用逻辑。必须实现。

```python
def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
    while not stop_event.is_set():
        # 您的应用逻辑
        pass
```

#### wrapped_run()

包装运行。处理连接和服务启动。

```python
def wrapped_run(self):
    pass
```

#### stop()

停止应用。

```python
def stop(self):
    pass
```

---

## REST API 端点

### 状态

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/state/full` | GET | 获取完整状态 |
| `/api/state/ws/full` | WebSocket | 实时状态更新 |
| `/api/daemon/status` | GET | 获取 daemon 状态 |

### 应用管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/apps/list` | GET | 列出已安装应用 |
| `/api/apps/install` | POST | 安装应用 |
| `/api/apps/start-app/{name}` | POST | 启动应用 |
| `/api/apps/stop-current-app` | POST | 停止当前应用 |

### 电机控制

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/motors/enable` | POST | 启用电机 |
| `/api/motors/disable` | POST | 禁用电机 |
| `/api/motors/scan` | POST | 扫描电机 |

### 文档

| 端点 | 说明 |
|------|------|
| `/docs` | 交互式 API 文档 |
| `/openapi.json` | OpenAPI 规范 |

---

## 常量

### 安全限制

```python
HEAD_PITCH_LIMIT = (-40, 40)      # 度
HEAD_ROLL_LIMIT = (-40, 40)       # 度
HEAD_YAW_LIMIT = (-180, 180)      # 度
BODY_YAW_LIMIT = (-160, 160)      # 度
YAW_DELTA_LIMIT = 65              # 度 (头-身)
```

### 电机 ID

```python
MOTOR_IDS = {
    "body_rotation": 10,
    "stewart_1": 11,
    "stewart_2": 12,
    "stewart_3": 13,
    "stewart_4": 14,
    "stewart_5": 15,
    "stewart_6": 16,
    "left_antenna": 17,
    "right_antenna": 18,
}
```

### 插值方法

```python
INTERPOLATION_METHODS = [
    "linear",
    "minjerk",
    "ease_in_out",
    "cartoon",
]
```

---

## 相关链接

- [Python SDK 参考](../04-SDK文档/Python-SDK参考.md)
- [核心概念与架构](../04-SDK文档/核心概念与架构.md)
- [示例代码](../09-示例代码/示例代码集合.md)
