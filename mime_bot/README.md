# Mime Bot (Offline)

Reachy Mini 实时面部模仿应用 — 完全离线运行，无需 HuggingFace 登录。

打开页面，授权摄像头，机器人就会实时模仿你的面部表情。

## 运行方式

### 1. 确保 daemon 运行
```bash
# 连接 Reachy Mini 到电脑，daemon 会自动启动在 localhost:8000
```

### 2. 启动本地服务器
```bash
cd mime_bot
python3 -m http.server 8080
```

### 3. 打开浏览器
```
http://localhost:8080
```

## 功能

- 52 个 ARKit 面部混合形状实时追踪（MediaPipe FaceLandmarker）
- 头部 6DoF 姿态直接映射
- 天线和身体 yaw 自由路由调节
- 镜像模式
- 实时混合形状监控条

## 技术栈

- 纯前端 JS（无构建步骤）
- MediaPipe FaceLandmarker（CDN 加载）
- WebSocket 直连本地 daemon（端口 8000）
- REST API 发送控制命令

## 与原版区别

| 原版 (HF Space) | 离线版 |
|---|---|
| HF OAuth 登录 | 无需登录 |
| 信令服务器发现机器人 | 直连 localhost:8000 |
| WebRTC 数据通道 | WebSocket + REST API |
| HF CDN MediaPipe | 仍用 CDN（可改本地） |
