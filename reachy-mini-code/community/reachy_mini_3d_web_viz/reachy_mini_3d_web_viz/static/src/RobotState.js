export class RobotStateClient {
    constructor(wsUrl = "ws://127.0.0.1:8000/api/state/ws/full") {
        this.wsUrl = wsUrl;
        this.ws = null;
        this.listeners = [];
        this.reconnectDelay = 3000;
        this.autoReconnect = true;
    }

    connect() {
        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => this.notifyListeners('connected', null);

        this.ws.onmessage = (event) => {
            try {
                this.notifyListeners('data', JSON.parse(event.data));
            } catch (e) {
                this.notifyListeners('error', e);
            }
        };

        this.ws.onerror = (error) => this.notifyListeners('error', error);

        this.ws.onclose = () => {
            this.notifyListeners('disconnected', null);
            if (this.autoReconnect) {
                setTimeout(() => this.connect(), this.reconnectDelay);
            }
        };
    }

    disconnect() {
        this.autoReconnect = false;
        this.ws?.close();
    }

    onStateChange(callback) {
        this.listeners.push(callback);
    }

    notifyListeners(event, data) {
        this.listeners.forEach(cb => cb(event, data));
    }
}
