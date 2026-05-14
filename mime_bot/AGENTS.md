# mime_bot — agent guide (Offline Version)

A short brief for any agent picking this app up. **Read these first**, in order:

1. **[`plan.md`](plan.md)** — the design spec (scope, locked decisions, layout, default mappings).
2. **[`main.js`](main.js)** — single-file app logic: camera → FaceLandmarker → mapping → 20 Hz send loop → tuner UI → blendshape monitor → shutdown.

The Space is now **fully offline** — connects directly to the local daemon at `localhost:8000` via WebSocket + REST API. No HuggingFace auth required.

---

## App at a glance

Live face mimicry via local daemon. Webcam → MediaPipe FaceLandmarker (52 ARKit blendshapes + 4×4 head transformation matrix) → mapping → robot at 20 Hz. Head pose is locked to direct geometric mapping (amplitude-only tuning); body yaw + L/R antennas are free-routed via a `{feature, weight}` rule editor.

## Locked decisions (do not silently change)

- **Offline mode**: No HF OAuth, no signaling server, no WebRTC. Direct WebSocket + REST to `localhost:8000`.
- **MediaPipe pinned to `@mediapipe/tasks-vision@0.10.35`** via CDN. If bumping, verify both `/+esm` and `/wasm/` directory exist on jsdelivr first.
- **MediaPipe import is lazy** (inside `initFaceLandmarker()`), *not* at module top.
- **Smooth startup uses `Motor.softReturnToBase`** (pin current → enable torque → daemon-side scaled goto).
- **Pitch sign is empirically flipped** in `matrixToRollPitchYaw` (`pitch = -atan2(-m12, m22)`). Don't flip it back without re-testing.
- **Mirror mode default = ON, applied at the mapper** by negating `head_yaw` in the feature dict.
- **Antenna idle bias = `[-0.1745, +0.1745]` rad** ([right, left]).
- **20 Hz send / 15 Hz monitor tick / 30 fps face tracking**.
- **No persistence**. Reset = in-memory deep-copy of `DEFAULT_CONFIG`.

## Out of scope (explicit user cuts)

- ❌ Video file upload, YouTube ingest, screen capture
- ❌ Move recording / save / replay / library
- ❌ Multi-preset library (only the default rule set + tuner)
- ❌ Persistence of any kind
- ❌ HuggingFace auth / signaling server / WebRTC
