/**
 * reachy-mini.js — Offline Browser SDK for controlling a Reachy Mini robot.
 * Connects directly to the local daemon via WebSocket + REST API.
 * No HuggingFace auth required.
 *
 * QUICK START
 * ───────────
 *   import { ReachyMini } from "./reachy-mini.js";
 *   const robot = new ReachyMini();
 *
 *   // 1. Connect to local daemon
 *   await robot.connect();
 *
 *   // 2. Send commands
 *   robot.setHeadPose(0, 10, -5);    // roll, pitch, yaw in degrees
 *   robot.setAntennas(30, -30);       // right, left in degrees
 *
 *   // 3. Receive live state (emitted at ~20Hz via WebSocket)
 *   robot.addEventListener("state", (e) => {
 *       const { head, antennas } = e.detail;
 *   });
 *
 *   // 4. Cleanup
 *   robot.disconnect();
 *
 *
 * STATE MACHINE
 * ─────────────
 *   'disconnected' ──connect()──▸ 'connected' (streaming state via WS)
 *        ▴ disconnect()
 *        └──────────────────────┘
 *
 *
 * CONSTRUCTOR OPTIONS
 * ───────────────────
 *   new ReachyMini({
 *     daemonUrl:  string,   // default: "http://localhost:8000"
 *   })
 */

// ─── Math utilities ──────────────────────────────────────────────────────────

export function degToRad(deg) { return deg * Math.PI / 180; }
export function radToDeg(rad) { return rad * 180 / Math.PI; }

export function rpyToMatrix(rollDeg, pitchDeg, yawDeg) {
    const r = degToRad(rollDeg), p = degToRad(pitchDeg), y = degToRad(yawDeg);
    const cy = Math.cos(y), sy = Math.sin(y);
    const cp = Math.cos(p), sp = Math.sin(p);
    const cr = Math.cos(r), sr = Math.sin(r);
    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, 0],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - sy * sr, 0],
        [-sp,     cp * sr,                cp * cr,                0],
        [0,       0,                      0,                      1],
    ];
}

export function matrixToRpy(m) {
    return {
        roll:  radToDeg(Math.atan2(m[2][1], m[2][2])),
        pitch: radToDeg(Math.asin(-m[2][0])),
        yaw:   radToDeg(Math.atan2(m[1][0], m[0][0])),
    };
}

// ─── ReachyMini class (offline) ──────────────────────────────────────────────

export class ReachyMini extends EventTarget {

    constructor(options = {}) {
        super();
        this._daemonUrl = options.daemonUrl || 'http://localhost:8000';
        this._wsUrl = this._daemonUrl.replace(/^http/, 'ws') + '/api/state/ws/full';

        this._state = 'disconnected';
        this._robotState = {
            head: { roll: 0, pitch: 0, yaw: 0 },
            antennas: { right: 0, left: 0 },
            motorMode: null,
            headMatrix: null,
            antennasRad: [0, 0],
            bodyYaw: 0,
        };

        this._ws = null;
        this._stateRefreshInterval = null;
    }

    get state() { return this._state; }
    get robotState() { return this._robotState; }
    get isAuthenticated() { return true; } // always "authenticated" offline
    get username() { return 'local'; }

    // ─── Lifecycle ───────────────────────────────────────────────────────

    /**
     * Connect to local daemon via WebSocket for real-time state.
     * Also verifies daemon is running via REST health check.
     */
    async connect() {
        if (this._state !== 'disconnected') throw new Error('Already connected');

        // Health check
        try {
            const res = await fetch(`${this._daemonUrl}/api/daemon/status`);
            if (!res.ok) throw new Error(`Daemon returned ${res.status}`);
        } catch (e) {
            throw new Error(`Cannot reach daemon at ${this._daemonUrl}: ${e.message}`);
        }

        // Open WebSocket for state streaming
        return new Promise((resolve, reject) => {
            this._ws = new WebSocket(this._wsUrl);

            this._ws.onopen = () => {
                this._state = 'connected';
                this._emit('connected', {});
                resolve();
            };

            this._ws.onmessage = (ev) => {
                try {
                    const data = JSON.parse(ev.data);
                    this._handleStateMessage(data);
                } catch (_) {}
            };

            this._ws.onerror = (e) => {
                this._emit('error', { source: 'websocket', error: e });
                if (this._state === 'disconnected') reject(new Error('WebSocket error'));
            };

            this._ws.onclose = () => {
                if (this._state !== 'disconnected') {
                    this._state = 'disconnected';
                    this._emit('disconnected', { reason: 'WebSocket closed' });
                }
            };
        });
    }

    /**
     * Disconnect from daemon.
     */
    disconnect() {
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
        if (this._stateRefreshInterval) {
            clearInterval(this._stateRefreshInterval);
            this._stateRefreshInterval = null;
        }
        this._state = 'disconnected';
        this._emit('disconnected', { reason: 'user' });
    }

    // ─── Commands via REST API ───────────────────────────────────────────

    async _postCommand(endpoint, body) {
        try {
            const res = await fetch(`${this._daemonUrl}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            return res.ok;
        } catch (e) {
            console.error('Command error:', e);
            return false;
        }
    }

    /**
     * Set head orientation (degrees).
     */
    setHeadPose(roll, pitch, yaw) {
        const matrix = rpyToMatrix(roll, pitch, yaw);
        return this._postCommand('/api/head/target', {
            head_pose: matrix.flat(),
        });
    }

    /**
     * Set antenna positions (degrees).
     */
    setAntennas(rightDeg, leftDeg) {
        return this._postCommand('/api/antennas/target', {
            antennas: [degToRad(rightDeg), degToRad(leftDeg)],
        });
    }

    /**
     * Set body yaw (radians).
     */
    setBodyYaw(yawRad) {
        return this._postCommand('/api/body/target', {
            body_yaw: yawRad,
        });
    }

    /**
     * Set full target (head + antennas + body) in one call.
     */
    setFullTarget({ head, antennas, bodyYaw } = {}) {
        const body = {};
        if (head) body.head_pose = Array.isArray(head[0]) ? head.flat() : head;
        if (antennas) body.antennas = antennas;
        if (bodyYaw !== undefined && bodyYaw !== null) body.body_yaw = bodyYaw;
        return this._postCommand('/api/move/set_target', body);
    }

    /**
     * Smooth interpolated goto.
     */
    gotoTarget({ head, antennas, bodyYaw, duration } = {}) {
        const body = { duration: Number(duration) || 0.5 };
        if (head) body.head_pose = Array.isArray(head[0]) ? head.flat() : head;
        if (antennas) body.antennas = antennas;
        if (bodyYaw !== undefined && bodyYaw !== null) body.body_yaw = bodyYaw;
        return this._postCommand('/api/move/goto_target', body);
    }

    /**
     * Set motor mode.
     */
    setMotorMode(mode) {
        return this._postCommand('/api/motor/mode', { mode });
    }

    /**
     * Wake up animation.
     */
    async wakeUp() {
        await this.setMotorMode('enabled');
        return this._postCommand('/api/move/play/wake_up', {});
    }

    /**
     * Go to sleep animation.
     */
    gotoSleep() {
        return this._postCommand('/api/move/play/goto_sleep', {});
    }

    /**
     * Play a sound file on the robot.
     */
    playSound(file) {
        return this._postCommand('/api/audio/play', { file });
    }

    /**
     * Check if motors are awake.
     */
    isAwake() {
        const mode = this._robotState?.motorMode;
        return mode === 'enabled' || mode === 'gravity_compensation';
    }

    /**
     * Ensure robot is awake.
     */
    async ensureAwake(timeoutMs = 1000) {
        if (this._robotState?.motorMode === undefined) {
            await new Promise((resolve) => {
                const done = () => {
                    this.removeEventListener('state', done);
                    clearTimeout(timer);
                    resolve();
                };
                const timer = setTimeout(done, timeoutMs);
                this.addEventListener('state', done);
            });
        }
        if (this.isAwake()) return true;
        await this.wakeUp();
        return true;
    }

    /**
     * Get daemon version.
     */
    async getVersion() {
        try {
            const res = await fetch(`${this._daemonUrl}/api/daemon/status`);
            const data = await res.json();
            return data.version || null;
        } catch (_) {
            return null;
        }
    }

    // ─── State handling ──────────────────────────────────────────────────

    _handleStateMessage(data) {
        // WebSocket sends full state at ~20Hz
        if (data.head_pose) {
            this._robotState.head = matrixToRpy(data.head_pose);
            this._robotState.headMatrix = data.head_pose;
        }
        if (data.antennas) {
            this._robotState.antennas = {
                right: radToDeg(data.antennas[0]),
                left:  radToDeg(data.antennas[1]),
            };
            this._robotState.antennasRad = [data.antennas[0], data.antennas[1]];
        }
        if (data.body_yaw !== undefined && data.body_yaw !== null) {
            this._robotState.bodyYaw = data.body_yaw;
        }
        if (data.motor_mode) this._robotState.motorMode = data.motor_mode;
        if (data.is_move_running !== undefined) this._robotState.isMoveRunning = data.is_move_running;
        if (data.timestamp) this._robotState.timestamp = data.timestamp;
        this._emit('state', { ...this._robotState });
    }

    // ─── Video helper ────────────────────────────────────────────────────

    /**
     * For offline mode, camera is accessed directly via getUserMedia.
     * This is a no-op — use getUserMedia in your app code instead.
     */
    attachVideo(videoElement) {
        // In offline mode, video comes from local webcam, not robot
        return () => {};
    }

    // ─── Audio (no-op for offline) ───────────────────────────────────────

    setAudioMuted(muted) {}
    setMicMuted(muted) {}
    get micSupported() { return false; }
    get micMuted() { return true; }
    get audioMuted() { return true; }

    // ─── Private ─────────────────────────────────────────────────────────

    _emit(name, detail) {
        this.dispatchEvent(new CustomEvent(name, { detail }));
    }

    // No-op stubs for compatibility
    async startSession() {}
    async stopSession() {}
    async authenticate() { return true; }
    login() {}
    logout() {}
    sendRaw(data) { return false; }
    requestState() { return true; }
    getVolume() { return Promise.resolve(null); }
    setVolume() { return Promise.resolve(null); }
    getMicrophoneVolume() { return Promise.resolve(null); }
    setMicrophoneVolume() { return Promise.resolve(null); }
}

export default ReachyMini;
