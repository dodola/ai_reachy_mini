import { SceneManager } from './SceneManager.js';
import { RobotManager } from './RobotManager.js';
import { ChartManager } from './ChartManager.js';
import { UIManager } from './UIManager.js';
import { WebSocketManager } from './WebSocketManager.js';
import { InteractionManager } from './InteractionManager.js';

export class App {
    constructor() {
        this.sceneManager = null;
        this.robotManager = null;
        this.chartManager = null;
        this.uiManager = null;
        this.webSocketManager = null;
        this.interactionManager = null;

        this.init();
    }

    async init() {
        const statusBtn = document.getElementById('status-text');
        statusBtn?.addEventListener('click', () => {
            window.open('http://localhost:8080', '_blank', 'noopener,noreferrer');
        });

        // Show connect card (will be hidden when WebSocket connects)
        const launchCard = document.getElementById('launch-card');
        launchCard.hidden = false;

        // Initialize DOM elements
        const container = document.getElementById('container');
        const statusEl = document.getElementById('status');
        const jointsListEl = document.getElementById('joints-list');
        const chartCanvas = document.getElementById('chart');

        // Initialize managers
        this.sceneManager = new SceneManager(container);
        this.uiManager = new UIManager(statusEl, jointsListEl);
        this.chartManager = new ChartManager(chartCanvas);

        // Initialize robot manager with status callback and environment map
        this.robotManager = new RobotManager((message) => {
            this.uiManager.updateStatus(message);
        }, this.sceneManager.envMap);

        // Initialize WebSocket manager
        this.webSocketManager = new WebSocketManager(
            this.uiManager,
            this.robotManager,
            this.chartManager
        );

        try {
            // Load robot
            const robot = await this.robotManager.loadRobot();
            this.sceneManager.add(robot);

            // Initialize interaction manager for drag controls
            const params = new URLSearchParams(location.search);
            const wsUrl = params.get("ws") || "ws://127.0.0.1:8000/api/state/ws/full";
            const apiBaseUrl = wsUrl.replace(/^ws/, 'http').replace(/\/api\/.*$/, '');
            this.interactionManager = new InteractionManager(
                this.sceneManager,
                this.robotManager,
                apiBaseUrl
            );
            this.webSocketManager.setInteractionManager(this.interactionManager);

            // Connect WebSocket
            this.uiManager.updateStatus('Connecting...');
            this.webSocketManager.connect();

        } catch (error) {
            console.error('Failed to initialize app:', error);
            this.uiManager.updateStatus(`Failed to load: ${error.message}`, 'error');
        }

        // Start animation loop
        this.sceneManager.animate();
    }
}
