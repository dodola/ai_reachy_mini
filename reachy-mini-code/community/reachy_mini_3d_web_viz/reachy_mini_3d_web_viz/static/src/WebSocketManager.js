import { RobotStateClient } from './RobotState.js';

export class WebSocketManager {
    constructor(uiManager, robotManager, chartManager) {
        this.uiManager = uiManager;
        this.robotManager = robotManager;
        this.chartManager = chartManager;
        this.interactionManager = null;

        const params = new URLSearchParams(location.search);
        this.WS_URL = params.get("ws") || "ws://127.0.0.1:8000/api/state/ws/full?with_head_joints=true";
        this.robotClient = new RobotStateClient(this.WS_URL);
    }

    setInteractionManager(interactionManager) {
        this.interactionManager = interactionManager;
    }

    connect() {
        this.robotClient.onStateChange((event, data) => {
            if (event === 'connected') {
                this.uiManager.updateStatus('', 'connected');
           
                const jointsList = document.getElementById('joints-list');
                if (jointsList && jointsList.parentElement) {
                    jointsList.parentElement.hidden = false;
                }
                const historyDiv = document.getElementById('chart-wrapper');
                if (historyDiv && historyDiv.parentElement) {
                    historyDiv.parentElement.hidden = false;
                }
                const launchCard = document.getElementById('launch-card');
                if (launchCard) {
                    launchCard.hidden = true;
                }
            } else if (event === 'disconnected') {
                this.uiManager.updateStatus('', 'disconnected');
            } else if (event === 'error') {
                // this.uiManager.updateStatus('', 'error');
            } else if (event === 'data') {
                this.robotManager.updateJoints(data);
                const jointValues = this.uiManager.updateJointsDisplay(data);
                this.chartManager.updateChart(jointValues);
                // Sync ghost target for interaction controls
                if (this.interactionManager && data.head_pose) {
                    this.interactionManager.syncToRobotPose(data.head_pose);
                }
            }
        });
        this.robotClient.connect();
    }
}
