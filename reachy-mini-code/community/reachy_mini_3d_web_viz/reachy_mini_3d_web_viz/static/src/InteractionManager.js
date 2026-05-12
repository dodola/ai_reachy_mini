import * as THREE from 'three';

// Head offset in Three.js Y-up coordinates (robot Z becomes Three.js Y)
const HEAD_Y_OFFSET = 0.177;

export class InteractionManager {
    constructor(sceneManager, robotManager, apiBaseUrl = 'http://127.0.0.1:8000') {
        this.sceneManager = sceneManager;
        this.robotManager = robotManager;
        this.apiBaseUrl = apiBaseUrl;

        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        this.isDragging = false;
        this.dragStart = new THREE.Vector2();
        this.currentHeadPose = { x: 0, y: 0, z: 0, roll: 0, pitch: 0, yaw: 0 };
        this.dragStartPose = null;

        this.setupEventListeners();
    }

    setupEventListeners() {
        const canvas = this.sceneManager.renderer.domElement;

        canvas.addEventListener('pointerdown', (e) => this.onPointerDown(e));
        canvas.addEventListener('pointermove', (e) => this.onPointerMove(e));
        canvas.addEventListener('pointerup', (e) => this.onPointerUp(e));
        canvas.addEventListener('pointerleave', (e) => this.onPointerUp(e));
    }

    onPointerDown(event) {
        return; // Disable interaction for now
        const rect = this.sceneManager.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.sceneManager.camera);

        if (this.robotManager.robot) {
            const intersects = this.raycaster.intersectObject(this.robotManager.robot, true);

            if (intersects.length > 0) {
                this.isDragging = true;
                this.dragStart.set(event.clientX, event.clientY);
                this.dragStartPose = { ...this.currentHeadPose };
                this.sceneManager.controls.enabled = false;
                this.updateHint(true);
            }
        }
    }

    onPointerMove(event) {
        if (!this.isDragging) return;

        const deltaX = (event.clientX - this.dragStart.x) * 0.001;
        const deltaY = (event.clientY - this.dragStart.y) * 0.001;

        // Shift key = move in XY plane, otherwise rotate pitch/yaw
        if (event.shiftKey) {
            // Translate in X/Y plane
            this.currentHeadPose.x = this.dragStartPose.x + deltaX;
            this.currentHeadPose.y = this.dragStartPose.y - deltaY;
        } else {
            // Rotate pitch/yaw
            this.currentHeadPose.yaw = this.dragStartPose.yaw + deltaX * 2;
            this.currentHeadPose.pitch = this.dragStartPose.pitch + deltaY * 2;
        }
    }

    onPointerUp(event) {
        this.sceneManager.controls.autoRotate = false;
        // if (this.isDragging) {
        //     this.isDragging = false;
        //     this.sceneManager.controls.enabled = true;
        //     this.sendPoseToRobot();
        // }
    }

    updateHint(dragging) {
        const hint = document.getElementById('controls-hint');
        if (hint) {
            if (dragging) {
                hint.innerHTML = '<kbd>Drag</kbd> rotate head · <kbd>Shift+Drag</kbd> move head · Release to apply';
            } else {
                hint.innerHTML = '<kbd>Drag</kbd> rotate · <kbd>Scroll</kbd> zoom · <kbd>Shift+Drag</kbd> pan · <kbd>Click robot</kbd> to control';
            }
        }
    }

    // Sync from WebSocket head_pose data
    syncToRobotPose(headPose) {
        if (this.isDragging) return;
        this.currentHeadPose = {
            x: headPose.x || 0,
            y: headPose.y || 0,
            z: headPose.z || 0,
            roll: headPose.roll || 0,
            pitch: headPose.pitch || 0,
            yaw: headPose.yaw || 0
        };
    }

    async sendPoseToRobot() {
        const payload = {
            head_pose: this.currentHeadPose,
            duration: 0.5,
            interpolation: 'minjerk'
        };

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/move/goto`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                console.warn('Failed to send pose to robot:', response.status);
            }
        } catch (error) {
            console.warn('Error sending pose to robot:', error);
        }
    }
}
