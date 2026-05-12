// Reachy F1 Commentator - Web UI JavaScript
// Version: 2.0 - Fixed DOM initialization

// LocalStorage keys
const STORAGE_KEYS = {
    API_KEY: 'reachy_f1_elevenlabs_api_key',
    VOICE_ID: 'reachy_f1_elevenlabs_voice_id'
};

// Session state
const state = {
    mode: 'quick_demo',
    selectedYear: null,
    selectedRace: null,
    playbackSpeed: 1,
    elevenLabsApiKey: '',
    elevenLabsVoiceId: 'HSSEHuB5EziJgTfCVmC6',
    status: 'idle',
    statusPollInterval: null
};

// DOM elements (will be initialized after DOM loads)
let elements = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');
    
    // Initialize DOM elements
    elements = {
        mode: document.getElementById('mode'),
        year: document.getElementById('year'),
        race: document.getElementById('race'),
        playbackSpeed: document.getElementById('playbackSpeed'),
        apiKey: document.getElementById('apiKey'),
        voiceId: document.getElementById('voiceId'),
        startBtn: document.getElementById('startBtn'),
        stopBtn: document.getElementById('stopBtn'),
        raceSelection: document.getElementById('raceSelection'),
        statusIndicator: document.getElementById('statusIndicator'),
        statusText: document.getElementById('statusText'),
        progressPanel: document.getElementById('progressPanel'),
        qaPanel: document.getElementById('qaPanel'),
        questionInput: document.getElementById('questionInput'),
        askBtn: document.getElementById('askBtn'),
        answerPanel: document.getElementById('answerPanel'),
        answerText: document.getElementById('answerText'),
        currentLap: document.getElementById('currentLap'),
        totalLaps: document.getElementById('totalLaps'),
        elapsedTime: document.getElementById('elapsedTime')
    };
    
    // Check for missing elements
    for (const [key, element] of Object.entries(elements)) {
        if (!element) {
            console.error(`Element not found: ${key}`);
        }
    }
    
    loadSavedCredentials();
    setupEventListeners();
    loadYears();
});

// Load saved credentials from localStorage and server
function loadSavedCredentials() {
    // Try localStorage first (immediate)
    const savedApiKey = localStorage.getItem(STORAGE_KEYS.API_KEY);
    const savedVoiceId = localStorage.getItem(STORAGE_KEYS.VOICE_ID);
    
    if (savedApiKey) {
        elements.apiKey.value = savedApiKey;
        state.elevenLabsApiKey = savedApiKey;
    }
    
    if (savedVoiceId) {
        elements.voiceId.value = savedVoiceId;
        state.elevenLabsVoiceId = savedVoiceId;
    }
    
    // Then try to load from server (more permanent)
    loadServerConfig();
}

// Load configuration from server
async function loadServerConfig() {
    try {
        const response = await fetch('/api/config');
        if (response.ok) {
            const data = await response.json();
            
            // Only override if server has values and localStorage doesn't
            if (data.elevenlabs_api_key && !localStorage.getItem(STORAGE_KEYS.API_KEY)) {
                elements.apiKey.value = data.elevenlabs_api_key;
                state.elevenLabsApiKey = data.elevenlabs_api_key;
            }
            
            if (data.elevenlabs_voice_id && !localStorage.getItem(STORAGE_KEYS.VOICE_ID)) {
                elements.voiceId.value = data.elevenlabs_voice_id;
                state.elevenLabsVoiceId = data.elevenlabs_voice_id;
            }
        }
    } catch (error) {
        console.log('Server config not available (this is normal)');
    }
}

// Save credentials to both localStorage and server
function saveCredentials() {
    const apiKey = elements.apiKey.value;
    const voiceId = elements.voiceId.value;
    
    // Save to localStorage (immediate)
    if (apiKey) {
        localStorage.setItem(STORAGE_KEYS.API_KEY, apiKey);
    }
    if (voiceId) {
        localStorage.setItem(STORAGE_KEYS.VOICE_ID, voiceId);
    }
    
    // Save to server (permanent)
    saveServerConfig(apiKey, voiceId);
}

// Save configuration to server
async function saveServerConfig(apiKey, voiceId) {
    try {
        await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                elevenlabs_api_key: apiKey,
                elevenlabs_voice_id: voiceId
            })
        });
    } catch (error) {
        console.log('Could not save to server (this is normal in some environments)');
    }
}

function setupEventListeners() {
    if (!elements.mode || !elements.year || !elements.startBtn || !elements.stopBtn) {
        console.error('Required elements not found for event listeners');
        return;
    }
    
    elements.mode.addEventListener('change', handleModeChange);
    elements.year.addEventListener('change', handleYearChange);
    elements.startBtn.addEventListener('click', handleStart);
    elements.stopBtn.addEventListener('click', handleStop);
    
    // Q&A button handler
    if (elements.askBtn && elements.questionInput) {
        elements.askBtn.addEventListener('click', handleAskQuestion);
        elements.questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleAskQuestion();
            }
        });
    }
    
    // Save form values to state
    if (elements.playbackSpeed) {
        elements.playbackSpeed.addEventListener('change', (e) => {
            state.playbackSpeed = parseInt(e.target.value);
        });
    }
    
    if (elements.apiKey) {
        elements.apiKey.addEventListener('change', (e) => {
            state.elevenLabsApiKey = e.target.value;
            saveCredentials(); // Save when API key changes
        });
    }
    
    if (elements.voiceId) {
        elements.voiceId.addEventListener('change', (e) => {
            state.elevenLabsVoiceId = e.target.value;
            saveCredentials(); // Save when voice ID changes
        });
    }
}

function handleModeChange(e) {
    state.mode = e.target.value;
    
    if (state.mode === 'full_race') {
        elements.raceSelection.style.display = 'block';
    } else {
        elements.raceSelection.style.display = 'none';
    }
}

async function loadYears() {
    console.log('loadYears() called');
    console.log('elements.year:', elements.year);
    
    try {
        const response = await fetch('/api/races/years');
        console.log('Years API response:', response.status);
        
        const data = await response.json();
        console.log('Years data:', data);
        
        if (data.years && data.years.length > 0) {
            elements.year.innerHTML = '<option value="">Select year...</option>';
            data.years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                elements.year.appendChild(option);
            });
            console.log('Years loaded successfully:', data.years);
        }
    } catch (error) {
        console.error('Failed to load years:', error);
        elements.year.innerHTML = '<option value="">Error loading years</option>';
    }
}

async function handleYearChange(e) {
    const year = e.target.value;
    state.selectedYear = year;
    
    console.log('Year changed to:', year);
    
    if (!year) {
        elements.race.innerHTML = '<option value="">Select year first</option>';
        return;
    }
    
    elements.race.innerHTML = '<option value="">Loading...</option>';
    
    try {
        const response = await fetch(`/api/races/${year}`);
        console.log('Races API response:', response.status);
        
        const data = await response.json();
        console.log('Races data:', data);
        
        if (data.races && data.races.length > 0) {
            elements.race.innerHTML = '<option value="">Select race...</option>';
            data.races.forEach(race => {
                const option = document.createElement('option');
                option.value = race.session_key;
                
                // Format date to just show date without time (e.g., "2024-03-02")
                const dateOnly = race.date.split('T')[0];
                
                // Format: "Location - Date" (e.g., "Bahrain - 2024-03-02")
                option.textContent = `${race.country} - ${dateOnly}`;
                
                elements.race.appendChild(option);
            });
            console.log('Races loaded successfully:', data.races.length);
        } else {
            elements.race.innerHTML = '<option value="">No races found</option>';
        }
    } catch (error) {
        console.error('Failed to load races:', error);
        elements.race.innerHTML = '<option value="">Error loading races</option>';
    }
}

async function handleStart() {
    // Validate inputs
    if (state.mode === 'full_race' && !elements.race.value) {
        alert('Please select a race');
        return;
    }
    
    if (!state.elevenLabsApiKey) {
        const proceed = confirm('No ElevenLabs API key provided. Audio will be disabled. Continue?');
        if (!proceed) return;
    }
    
    // Prepare configuration
    const config = {
        mode: state.mode,
        session_key: state.mode === 'full_race' ? parseInt(elements.race.value) : null,
        commentary_mode: 'enhanced',  // Always use enhanced mode
        playback_speed: state.playbackSpeed,
        elevenlabs_api_key: state.elevenLabsApiKey,
        elevenlabs_voice_id: state.elevenLabsVoiceId
    };
    
    // Disable start button
    elements.startBtn.disabled = true;
    elements.stopBtn.disabled = false;
    
    try {
        const response = await fetch('/api/commentary/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.status === 'started') {
            updateStatus('playing');
            startStatusPolling();
        } else if (data.status === 'error') {
            alert(`Error: ${data.message}`);
            elements.startBtn.disabled = false;
            elements.stopBtn.disabled = true;
        }
    } catch (error) {
        console.error('Failed to start commentary:', error);
        alert('Failed to start commentary. Check console for details.');
        elements.startBtn.disabled = false;
        elements.stopBtn.disabled = true;
    }
}

async function handleStop() {
    elements.stopBtn.disabled = true;
    
    try {
        const response = await fetch('/api/commentary/stop', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'stopped') {
            updateStatus('stopped');
            stopStatusPolling();
            elements.startBtn.disabled = false;
        }
    } catch (error) {
        console.error('Failed to stop commentary:', error);
        elements.stopBtn.disabled = false;
    }
}

function startStatusPolling() {
    if (state.statusPollInterval) {
        clearInterval(state.statusPollInterval);
    }
    
    state.statusPollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/commentary/status');
            const data = await response.json();
            
            updateStatus(data.state);
            
            if (data.state === 'playing') {
                elements.progressPanel.style.display = 'block';
                elements.currentLap.textContent = data.current_lap;
                elements.totalLaps.textContent = data.total_laps;
                elements.elapsedTime.textContent = data.elapsed_time;
            } else if (data.state === 'idle' || data.state === 'stopped') {
                stopStatusPolling();
                elements.startBtn.disabled = false;
                elements.stopBtn.disabled = true;
            }
        } catch (error) {
            console.error('Failed to get status:', error);
        }
    }, 1000);
}

function stopStatusPolling() {
    if (state.statusPollInterval) {
        clearInterval(state.statusPollInterval);
        state.statusPollInterval = null;
    }
}

function updateStatus(status) {
    state.status = status;
    
    // Update indicator
    elements.statusIndicator.className = `status-indicator ${status}`;
    
    // Update text
    const statusTexts = {
        'idle': 'Idle',
        'loading': 'Loading...',
        'playing': 'Playing',
        'stopped': 'Stopped'
    };
    
    elements.statusText.textContent = statusTexts[status] || status;
    
    // Show/hide progress panel and Q&A panel
    if (status === 'playing') {
        elements.progressPanel.style.display = 'block';
        if (elements.qaPanel) {
            elements.qaPanel.style.display = 'block';
        }
    } else if (status === 'idle') {
        elements.progressPanel.style.display = 'none';
        if (elements.qaPanel) {
            elements.qaPanel.style.display = 'none';
        }
    }
}

async function handleAskQuestion() {
    const question = elements.questionInput.value.trim();
    
    if (!question) {
        alert('Please enter a question');
        return;
    }
    
    // Disable button while processing
    elements.askBtn.disabled = true;
    elements.askBtn.textContent = 'Thinking...';
    
    try {
        const response = await fetch('/api/qa/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Show answer
        elements.answerText.textContent = data.answer;
        elements.answerPanel.style.display = 'block';
        
        // Clear input
        elements.questionInput.value = '';
        
    } catch (error) {
        console.error('Error asking question:', error);
        alert('Failed to get answer. Please try again.');
    } finally {
        // Re-enable button
        elements.askBtn.disabled = false;
        elements.askBtn.textContent = 'Ask Question';
    }
}
