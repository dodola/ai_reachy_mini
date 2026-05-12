export class UIManager {
    constructor(statusElement, jointsListElement) {
        this.statusDot = statusElement.querySelector('.status-dot');
        this.statusText = statusElement.querySelector('#status-text') || statusElement;
        this.jointsListEl = jointsListElement;

        this.jointColors = {
            'head yaw': '#f472b6',
            'head pitch': '#60a5fa',
            'head roll': '#fbbf24',
            'left antenna': '#34d399',
            'right antenna': '#a78bfa',
            'body yaw': '#fb923c'
        };
    }

    updateStatus(message, type = '') {
        if (type === 'connected') {
            this.statusDot.className = 'status-dot connected';
            this.statusText.textContent = 'Connected';
        } else if (type === 'disconnected') {
            this.statusDot.className = 'status-dot disconnected';
            this.statusText.textContent = 'Connecting...';
        } else if (type === 'error') {
            this.statusDot.className = 'status-dot disconnected';
            this.statusText.textContent = 'Connection error';
        } else if (message) {
            this.statusDot.className = 'status-dot loading';
            this.statusText.textContent = message;
        }
    }

    updateJointsDisplay(data) {
        let html = '';
        const jointValues = {};

        // Display head pose
        if (data.head_pose) {
            const yaw = data.head_pose.yaw * 180 / Math.PI;
            const pitch = data.head_pose.pitch * 180 / Math.PI;
            const roll = data.head_pose.roll * 180 / Math.PI;

            html += this.createJointRow('head yaw', yaw);
            html += this.createJointRow('head pitch', pitch);
            html += this.createJointRow('head roll', roll);

            jointValues['head yaw'] = yaw;
            jointValues['head pitch'] = pitch;
            jointValues['head roll'] = roll;
        }

        // Display antennas
        if (data.antennas_position && Array.isArray(data.antennas_position)) {
            const leftAntenna = data.antennas_position[0] * 180 / Math.PI;
            const rightAntenna = data.antennas_position[1] * 180 / Math.PI;

            html += this.createJointRow('left antenna', leftAntenna);
            html += this.createJointRow('right antenna', rightAntenna);

            jointValues['left antenna'] = leftAntenna;
            jointValues['right antenna'] = rightAntenna;
        }

        // Display body yaw
        if (data.body_yaw !== undefined) {
            const bodyYaw = data.body_yaw * 180 / Math.PI;
            html += this.createJointRow('body yaw', bodyYaw);
            jointValues['body yaw'] = bodyYaw;
        }

        this.jointsListEl.innerHTML = html || '<div class="joint-row"><span class="joint-label">No data</span></div>';

        return jointValues;
    }

    createJointRow(name, value) {
        const color = this.jointColors[name] || '#ffffff';
        const sign = value >= 0 ? '+' : '';
        return `<div class="joint-row">
            <span class="joint-label">
                <span class="joint-dot" style="background-color: ${color}"></span>
                ${name}
            </span>
            <span class="joint-value">${sign}${value.toFixed(1)}</span>
        </div>`;
    }
}
