// Live Race Dashboard JavaScript

class RaceDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.eventHistory = [];
        this.maxEvents = 20;
        
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            connectionText: document.getElementById('connectionText'),
            currentLap: document.getElementById('currentLap'),
            raceLeader: document.getElementById('raceLeader'),
            fastestLap: document.getElementById('fastestLap'),
            racePhase: document.getElementById('racePhase'),
            positionTower: document.getElementById('positionTower'),
            eventsFeed: document.getElementById('eventsFeed')
        };
    }
    
    init() {
        console.log('Initializing Race Dashboard...');
        this.connectWebSocket();
        this.loadInitialState();
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
        
        console.log(`Connecting to WebSocket: ${wsUrl}`);
        this.updateConnectionStatus('connecting');
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleUpdate(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('error');
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.updateConnectionStatus('error');
            this.attemptReconnect();
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connectWebSocket(), this.reconnectDelay);
        } else {
            console.error('Max reconnection attempts reached');
            this.updateConnectionStatus('failed');
        }
    }
    
    updateConnectionStatus(status) {
        const statusIndicator = this.elements.connectionStatus;
        const statusText = this.elements.connectionText;
        
        statusIndicator.className = 'status-indicator';
        
        switch (status) {
            case 'connecting':
                statusText.textContent = 'Connecting...';
                break;
            case 'connected':
                statusIndicator.classList.add('connected');
                statusText.textContent = 'Connected';
                break;
            case 'disconnected':
                statusIndicator.classList.add('disconnected');
                statusText.textContent = 'Disconnected';
                break;
            case 'error':
            case 'failed':
                statusIndicator.classList.add('disconnected');
                statusText.textContent = 'Connection Failed';
                break;
        }
    }
    
    async loadInitialState() {
        try {
            console.log('Loading initial race state...');
            const response = await fetch('/api/dashboard/state');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Initial state loaded:', data);
            
            this.updateRaceInfo(data.race_info);
            this.updatePositions(data.positions);
            
            if (data.recent_events && data.recent_events.length > 0) {
                this.eventHistory = data.recent_events;
                this.updateEventsFeed();
            }
        } catch (error) {
            console.error('Failed to load initial state:', error);
        }
    }
    
    handleUpdate(data) {
        console.log('Received update:', data.type);
        
        if (data.type === 'state_update') {
            if (data.race_info) {
                this.updateRaceInfo(data.race_info);
            }
            
            if (data.positions) {
                this.updatePositions(data.positions);
            }
            
            if (data.last_event) {
                this.addEvent(data.last_event);
            }
        }
    }
    
    updateRaceInfo(info) {
        if (!info) return;
        
        // Current lap
        if (info.current_lap !== undefined && info.total_laps !== undefined) {
            this.elements.currentLap.textContent = `${info.current_lap} / ${info.total_laps}`;
        }
        
        // Race leader
        if (info.leader) {
            this.elements.raceLeader.textContent = info.leader;
        }
        
        // Fastest lap
        if (info.fastest_lap_holder && info.fastest_lap_time) {
            this.elements.fastestLap.textContent = `${info.fastest_lap_holder} (${info.fastest_lap_time})`;
        } else if (info.fastest_lap_holder) {
            this.elements.fastestLap.textContent = info.fastest_lap_holder;
        }
        
        // Race phase
        if (info.race_phase) {
            this.elements.racePhase.textContent = info.race_phase;
            
            // Add color coding
            const phaseElement = this.elements.racePhase;
            phaseElement.style.color = this.getPhaseColor(info.race_phase);
        }
        
        // Safety car indicator
        if (info.safety_car) {
            this.elements.racePhase.textContent += ' 🚗 SC';
        }
    }
    
    getPhaseColor(phase) {
        const colors = {
            'START': '#00d25b',
            'MID_RACE': '#ffab00',
            'FINISH': '#e10600'
        };
        return colors[phase] || '#ffffff';
    }
    
    updatePositions(positions) {
        if (!positions || positions.length === 0) {
            this.elements.positionTower.innerHTML = '<div class="loading">No position data available</div>';
            return;
        }
        
        const html = positions.map(p => this.createPositionItem(p)).join('');
        this.elements.positionTower.innerHTML = html;
    }
    
    createPositionItem(position) {
        const tireClass = this.getTireClass(position.tire_compound);
        const tireLabel = this.getTireLabel(position.tire_compound);
        
        return `
            <div class="position-item">
                <div class="position-number">${position.position}</div>
                <div class="driver-info">
                    <div class="driver-name">${position.driver}</div>
                </div>
                <div class="gap-info">${position.gap_to_leader}</div>
                <div class="tire-indicator ${tireClass}">${tireLabel}</div>
                <div class="pit-count">${position.pit_stops}</div>
            </div>
        `;
    }
    
    getTireClass(compound) {
        const compoundLower = (compound || '').toLowerCase();
        if (compoundLower.includes('soft')) return 'tire-soft';
        if (compoundLower.includes('medium')) return 'tire-medium';
        if (compoundLower.includes('hard')) return 'tire-hard';
        return '';
    }
    
    getTireLabel(compound) {
        const compoundLower = (compound || '').toLowerCase();
        if (compoundLower.includes('soft')) return 'S';
        if (compoundLower.includes('medium')) return 'M';
        if (compoundLower.includes('hard')) return 'H';
        return '?';
    }
    
    addEvent(event) {
        // Add to history
        this.eventHistory.unshift(event);
        
        // Keep only last N events
        if (this.eventHistory.length > this.maxEvents) {
            this.eventHistory = this.eventHistory.slice(0, this.maxEvents);
        }
        
        this.updateEventsFeed();
    }
    
    updateEventsFeed() {
        if (this.eventHistory.length === 0) {
            this.elements.eventsFeed.innerHTML = `
                <div class="event-item">
                    <span class="event-time">--:--</span>
                    <span class="event-text">Waiting for events...</span>
                </div>
            `;
            return;
        }
        
        const html = this.eventHistory.map(event => this.createEventItem(event)).join('');
        this.elements.eventsFeed.innerHTML = html;
    }
    
    createEventItem(event) {
        const eventClass = this.getEventClass(event.type);
        const eventText = this.formatEventText(event);
        const eventTime = this.formatEventTime(event);
        
        return `
            <div class="event-item ${eventClass}">
                <span class="event-time">${eventTime}</span>
                <span class="event-text">${eventText}</span>
            </div>
        `;
    }
    
    getEventClass(eventType) {
        const typeMap = {
            'OVERTAKE': 'event-overtake',
            'PIT_STOP': 'event-pit',
            'FLAG': 'event-flag',
            'FASTEST_LAP': 'event-fastest-lap',
            'SAFETY_CAR': 'event-flag'
        };
        return typeMap[eventType] || '';
    }
    
    formatEventText(event) {
        const data = event.data || {};
        
        switch (event.type) {
            case 'OVERTAKE':
                return `${data.overtaking_driver} overtakes ${data.overtaken_driver}`;
            
            case 'PIT_STOP':
                const duration = data.pit_duration ? ` (${data.pit_duration.toFixed(1)}s)` : '';
                const tire = data.tire_compound ? ` → ${data.tire_compound}` : '';
                return `${data.driver} pits${duration}${tire}`;
            
            case 'FASTEST_LAP':
                const lapTime = data.lap_time ? ` - ${data.lap_time.toFixed(3)}s` : '';
                return `${data.driver} sets fastest lap${lapTime}`;
            
            case 'FLAG':
                return `${data.flag_type} flag${data.message ? ': ' + data.message : ''}`;
            
            case 'SAFETY_CAR':
                return `Safety Car ${data.status}${data.reason ? ': ' + data.reason : ''}`;
            
            default:
                return `${event.type}: ${JSON.stringify(data)}`;
        }
    }
    
    formatEventTime(event) {
        if (event.lap_number) {
            return `Lap ${event.lap_number}`;
        }
        
        if (event.timestamp) {
            const date = new Date(event.timestamp);
            return date.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
        }
        
        return '--:--';
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');
    const dashboard = new RaceDashboard();
    dashboard.init();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        dashboard.disconnect();
    });
});
