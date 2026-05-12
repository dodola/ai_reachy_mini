# IMU 传感器详解

## 概述

**IMU** = Inertial Measurement Unit (惯性测量单元)

Reachy Mini **Wireless 版本**内置 IMU 传感器，Lite 版本没有。

## IMU 包含的传感器

| 传感器 | 功能 | 单位 |
|--------|------|------|
| **加速度计** | 测量线性加速度 | m/s² |
| **陀螺仪** | 测量旋转角速度 | rad/s |
| **四元数** | 姿态表示 | (w, x, y, z) |
| **温度** | 传感器温度 | °C |

## 获取 IMU 数据

```python
from reachy_mini import ReachyMini

with ReachyMini() as mini:
    imu = mini.imu
    
    # 加速度计 (m/s²)
    accel_x, accel_y, accel_z = imu["accelerometer"]
    
    # 陀螺仪 (rad/s)
    gyro_x, gyro_y, gyro_z = imu["gyroscope"]
    
    # 四元数 (姿态)
    quat_w, quat_x, quat_y, quat_z = imu["quaternion"]
    
    # 温度 (°C)
    temperature = imu["temperature"]
```

## IMU 的实际用途

### 1. 姿态检测 (Orientation)

检测机器人是否倾斜、翻转。

```python
import math

def get_tilt_angle(accel):
    """计算倾斜角度"""
    roll = math.atan2(accel[1], accel[2])
    pitch = math.atan2(-accel[0], math.sqrt(accel[1]**2 + accel[2]**2))
    return math.degrees(roll), math.degrees(pitch)

with ReachyMini() as mini:
    accel = mini.imu["accelerometer"]
    roll, pitch = get_tilt_angle(accel)
    
    print(f"Roll: {roll:.1f}°, Pitch: {pitch:.1f}°")
    
    # 检测机器人是否被拿起
    if abs(accel[2]) < 5.0:  # 正常重力约 9.8
        print("机器人被拿起了！")
    
    # 检测机器人是否倾斜
    if abs(roll) > 30:
        print("机器人倾斜了！")
```

**应用场景:**
- 检测机器人是否被移动
- 安全保护 (倾斜时停止运动)
- 互动反馈 (摇晃时做出反应)

---

### 2. 运动检测 (Motion Detection)

检测机器人是否在移动、振动。

```python
import numpy as np

class MotionDetector:
    def __init__(self, threshold=2.0):
        self.threshold = threshold
        self.last_accel = None
    
    def is_moving(self, accel):
        if self.last_accel is None:
            self.last_accel = accel
            return False
        
        # 计算加速度变化
        delta = np.array(accel) - np.array(self.last_accel)
        magnitude = np.linalg.norm(delta)
        
        self.last_accel = accel
        return magnitude > self.threshold

# 使用
motion_detector = MotionDetector()

with ReachyMini() as mini:
    while True:
        accel = mini.imu["accelerometer"]
        
        if motion_detector.is_moving(accel):
            print("检测到运动！")
            # 做出反应
            mini.goto_target(antennas=[0.5, -0.5], duration=0.3)
```

**应用场景:**
- 防盗报警
- 运动触发交互
- 状态监控

---

### 3. 手势识别 (Gesture Recognition)

识别特定的运动模式，如摇晃、点头等。

```python
from collections import deque

class ShakeDetector:
    def __init__(self, window_size=20, threshold=3.0):
        self.accel_history = deque(maxlen=window_size)
        self.threshold = threshold
    
    def update(self, accel_x):
        self.accel_history.append(accel_x)
        
    def is_shaking(self):
        if len(self.accel_history) < 10:
            return False
        
        # 检测方向变化
        sign_changes = 0
        for i in range(1, len(self.accel_history)):
            if self.accel_history[i] * self.accel_history[i-1] < 0:
                sign_changes += 1
        
        # 检测幅度
        amplitude = max(self.accel_history) - min(self.accel_history)
        
        return sign_changes > 5 and amplitude > self.threshold

# 使用 - 摇晃说 "不"
shake_detector = ShakeDetector()

with ReachyMini() as mini:
    while True:
        accel = mini.imu["accelerometer"]
        shake_detector.update(accel[0])
        
        if shake_detector.is_shaking():
            print("检测到摇晃！")
            mini.play_move(moves.get("no"))
```

**应用场景:**
- 摇晃头部说 "不"
- 点头说 "是"
- 自定义手势交互

---

### 4. 自稳定 (Self-Stabilization)

保持头部水平或指向特定方向。

```python
import numpy as np
from scipy.spatial.transform import Rotation as R

def stabilize_head(mini, target_orientation=None):
    """保持头部稳定"""
    if target_orientation is None:
        target_orientation = np.eye(3)
    
    # 获取当前姿态
    current_quat = mini.imu["quaternion"]
    current_rotation = R.from_quat([current_quat[1], current_quat[2], 
                                     current_quat[3], current_quat[0]])
    
    # 计算需要的补偿
    error_rotation = target_orientation @ current_rotation.inv()
    error_euler = error_rotation.as_euler('xyz', degrees=True)
    
    # 应用补偿
    mini.set_target(
        head=create_head_pose(
            roll=-error_euler[0],
            pitch=-error_euler[1],
            degrees=True
        )
    )

# 使用
with ReachyMini() as mini:
    while True:
        stabilize_head(mini)
        time.sleep(0.02)
```

**应用场景:**
- 移动中保持头部稳定
- 补偿外部干扰
- 平台稳定

---

### 5. 碰撞检测 (Collision Detection)

检测是否撞到物体。

```python
def detect_collision_by_imu(mini, threshold=15.0):
    """
    通过 IMU 检测碰撞
    
    原理：碰撞会产生突然的加速度变化
    """
    accel = mini.imu["accelerometer"]
    magnitude = np.linalg.norm(accel)
    
    # 正常重力约 9.8 m/s²
    # 碰撞会产生更大的加速度
    return magnitude > threshold

# 使用
with ReachyMini() as mini:
    while True:
        if detect_collision_by_imu(mini):
            print("碰撞检测！")
            mini.disable_motors()  # 安全停止
            break
        time.sleep(0.02)
```

**应用场景:**
- 安全保护
- 避免损坏
- 互动反馈

---

### 6. 重力补偿 (Gravity Compensation)

感知重力方向，补偿头部重量。

```python
def improved_gravity_compensation(mini):
    """使用 IMU 数据改进重力补偿"""
    accel = mini.imu["accelerometer"]
    
    # 归一化加速度向量（重力方向）
    gravity_direction = accel / np.linalg.norm(accel)
    
    # 计算补偿扭矩
    # 这需要运动学模型
    compensation = calculate_gravity_compensation(gravity_direction)
    
    return compensation
```

**应用场景:**
- 更自然的运动
- 减少电机负载
- 节能

---

### 7. 导航辅助 (Navigation Aid)

配合其他传感器进行定位。

```python
class SimpleOdometry:
    def __init__(self):
        self.position = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])
        self.last_time = None
    
    def update(self, accel, dt):
        """简单的航位推算"""
        # 积分加速度得到速度
        self.velocity += np.array([accel[0], accel[1]]) * dt
        
        # 积分速度得到位置
        self.position += self.velocity * dt
        
        return self.position.copy()

# 使用
odometry = SimpleOdometry()

with ReachyMini() as mini:
    t0 = time.time()
    while True:
        accel = mini.imu["accelerometer"]
        dt = time.time() - t0
        t0 = time.time()
        
        position = odometry.update(accel, dt)
        print(f"位置: x={position[0]:.2f}, y={position[1]:.2f}")
```

**应用场景:**
- 简单的运动追踪
- 配合视觉定位
- 记录运动轨迹

---

## 完整应用示例

### 摇晃说 "不"，点头说 "是"

```python
import numpy as np
from collections import deque
from reachy_mini import ReachyMini
from reachy_mini.motion.recorded_move import RecordedMoves

class GestureRecognizer:
    def __init__(self):
        self.accel_x_history = deque(maxlen=30)
        self.accel_z_history = deque(maxlen=30)
        self.last_gesture_time = 0
        self.cooldown = 2.0  # 秒
    
    def update(self, accel):
        self.accel_x_history.append(accel[0])
        self.accel_z_history.append(accel[2])
    
    def detect_shake(self):
        """检测摇晃（左右移动）"""
        if len(self.accel_x_history) < 15:
            return False
        
        sign_changes = 0
        for i in range(1, len(self.accel_x_history)):
            if self.accel_x_history[i] * self.accel_x_history[i-1] < 0:
                sign_changes += 1
        
        amplitude = max(self.accel_x_history) - min(self.accel_x_history)
        return sign_changes > 4 and amplitude > 3.0
    
    def detect_nod(self):
        """检测点头（上下移动）"""
        if len(self.accel_z_history) < 15:
            return False
        
        sign_changes = 0
        for i in range(1, len(self.accel_z_history)):
            if self.accel_z_history[i] * self.accel_z_history[i-1] < 0:
                sign_changes += 1
        
        amplitude = max(self.accel_z_history) - min(self.accel_z_history)
        return sign_changes > 4 and amplitude > 3.0
    
    def get_gesture(self):
        """获取检测到的手势"""
        current_time = time.time()
        
        if current_time - self.last_gesture_time < self.cooldown:
            return None
        
        if self.detect_shake():
            self.last_gesture_time = current_time
            return "shake"
        
        if self.detect_nod():
            self.last_gesture_time = current_time
            return "nod"
        
        return None

# 使用
moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
gesture_recognizer = GestureRecognizer()

with ReachyMini() as mini:
    print("摇晃机器人说 '不'，点头说 '是'...")
    
    while True:
        accel = mini.imu["accelerometer"]
        gesture_recognizer.update(accel)
        
        gesture = gesture_recognizer.get_gesture()
        
        if gesture == "shake":
            print("检测到摇晃 - 说 '不'!")
            mini.play_move(moves.get("no"), initial_goto_duration=0.5)
        
        elif gesture == "nod":
            print("检测到点头 - 说 '是'!")
            mini.play_move(moves.get("yes"), initial_goto_duration=0.5)
        
        time.sleep(0.02)
```

---

## 没有 IMU 的替代方案

### Lite 版本或 Lite + RPi4 方案

#### 方案 1: 外接 IMU 传感器

```python
# Raspberry Pi 4 + MPU6050/MPU9250 (~$10)
import smbus
import math

class ExternalIMU:
    def __init__(self, address=0x68):
        self.bus = smbus.SMBus(1)
        self.address = address
        # 唤醒 MPU6050
        self.bus.write_byte_data(self.address, 0x6B, 0)
    
    def read_accel(self):
        data = self.bus.read_i2c_block_data(self.address, 0x3B, 6)
        x = (data[0] << 8) | data[1]
        y = (data[2] << 8) | data[3]
        z = (data[4] << 8) | data[5]
        
        # 转换为有符号整数
        if x > 32767: x -= 65536
        if y > 32767: y -= 65536
        if z > 32767: z -= 65536
        
        # 转换为 m/s²
        x = x / 16384.0 * 9.81
        y = y / 16384.0 * 9.81
        z = z / 16384.0 * 9.81
        
        return x, y, z
    
    def read_gyro(self):
        data = self.bus.read_i2c_block_data(self.address, 0x43, 6)
        x = (data[0] << 8) | data[1]
        y = (data[2] << 8) | data[3]
        z = (data[4] << 8) | data[5]
        
        if x > 32767: x -= 65536
        if y > 32767: y -= 65536
        if z > 32767: z -= 65536
        
        # 转换为 rad/s
        x = x / 131.0 * math.pi / 180
        y = y / 131.0 * math.pi / 180
        z = z / 131.0 * math.pi / 180
        
        return x, y, z

# 使用
imu = ExternalIMU()

while True:
    accel = imu.read_accel()
    gyro = imu.read_gyro()
    print(f"Accel: {accel}, Gyro: {gyro}")
    time.sleep(0.1)
```

**购买链接:**
- MPU6050: ~$5-10
- MPU9250: ~$15-20 (包含磁力计)

---

#### 方案 2: 使用摄像头 + 计算机视觉

```python
import cv2
import cv2.aruco as aruco
import numpy as np

class VisionBasedOrientation:
    def __init__(self):
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_250)
        self.parameters = aruco.DetectorParameters_create()
        self.camera_matrix = None  # 需要标定
        self.dist_coeffs = None    # 需要标定
    
    def detect_orientation(self, frame):
        """使用 ArUco 标记检测姿态"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = aruco.detectMarkers(
            gray, self.aruco_dict, parameters=self.parameters
        )
        
        if ids is not None and self.camera_matrix is not None:
            rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
                corners, 0.05, self.camera_matrix, self.dist_coeffs
            )
            return rvec[0][0], tvec[0][0]
        
        return None, None

# 使用
vision = VisionBasedOrientation()

with ReachyMini() as mini:
    while True:
        frame = mini.media.get_frame()
        rvec, tvec = vision.detect_orientation(frame)
        
        if rvec is not None:
            print(f"Rotation: {rvec}, Translation: {tvec}")
```

---

#### 方案 3: 使用电机编码器

```python
def estimate_orientation_from_motors(mini):
    """通过电机位置推断头部姿态"""
    head_joints, antennas = mini.get_current_joint_positions()
    
    # head_joints 包含 6 个 Stewart 平台电机位置
    # 使用运动学计算头部姿态
    
    # 这需要正运动学模型
    # 可以使用 PlacoKinematics
    from reachy_mini.kinematics import PlacoKinematics
    
    solver = PlacoKinematics(urdf_path, 0.02)
    head_pose = solver.forward_kinematics(head_joints)
    
    return head_pose
```

---

## 总结

### IMU 的核心价值

| 功能 | 重要性 | 替代方案 |
|------|--------|----------|
| **姿态检测** | ⭐⭐⭐⭐ | 摄像头+ArUco |
| **运动检测** | ⭐⭐⭐ | 外接 IMU |
| **自稳定** | ⭐⭐⭐⭐ | 编码器反馈 |
| **手势识别** | ⭐⭐⭐ | 摄像头 |
| **碰撞检测** | ⭐⭐⭐⭐ | 电流检测 |
| **重力补偿** | ⭐⭐⭐⭐ | 预计算 |

### 是否需要 IMU？

**需要 IMU 如果:**
- 需要检测机器人被移动/拿起
- 需要摇晃/倾斜交互
- 需要移动中的稳定
- 需要碰撞检测

**不需要 IMU 如果:**
- 固定位置使用
- 主要使用摄像头交互
- 可以外接传感器
- 预算有限

### 推荐方案

**Lite + Raspberry Pi 4 + 外接 IMU (~$10-15)**

总成本: ~$310-315

获得:
- ✅ 独立运行
- ✅ WiFi/以太网
- ✅ IMU 功能
- ✅ 更强的计算能力
- ✅ 更低的总价

## 相关链接

- [硬件规格详解](./硬件规格详解.md)
- [Wireless vs Lite 对比](./Wireless-vs-Lite对比.md)
- [Python SDK 参考](../04-SDK文档/Python-SDK参考.md)
