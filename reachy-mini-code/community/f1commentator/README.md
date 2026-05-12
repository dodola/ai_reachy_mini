---
title: Reachy Mini F1 Commentator
emoji: 🏎️
colorFrom: red
colorTo: blue
sdk: static
pinned: false
short_description: An interactive F1 race commentary system for Reachy Mini
tags:
 - reachy_mini
 - reachy_mini_python_app
---

# 🏎️ Reachy F1 Commentator

An interactive F1 race commentary system for Reachy Mini that generates organic, context-rich commentary with audio synthesis and synchronized robot movements.

## Features

- 🎙️ **Enhanced Organic Commentary** - 210 templates with varied perspectives (technical, strategic, dramatic)
- 🏁 **Quick Demo Mode** - 2-3 minute pre-configured demonstration
- 📊 **Full Historical Race Mode** - Replay any F1 race from OpenF1 API
- 🔊 **Audio Synthesis** - ElevenLabs text-to-speech integration
- 🤖 **Robot Movements** - Synchronized head movements with commentary
- 🌐 **Web UI** - Browser-based race selection and playback control
- ⚡ **Configurable Speed** - 1x, 5x, 10x, or 20x playback speed

## Installation

### Via Reachy Mini App Assistant

The easiest way to install this app on your Reachy Mini:

```bash
reachy-mini-app-assistant install reachy-f1-commentator
```

### Manual Installation

```bash
pip install git+https://huggingface.co/spaces/YOUR_USERNAME/reachy-f1-commentator
```

## Usage

### Starting the App

The app runs automatically when started from the Reachy Mini dashboard. It will:
1. Start a web server at `http://localhost:5173` (or configured port)
2. Open the web UI for race selection
3. Wait for you to configure and start commentary

### Web UI Controls

**Mode Selection:**
- **Quick Demo** - 2-3 minute demonstration with pre-configured events
- **Full Historical Race** - Select from available F1 races

**Race Selection** (Full Historical Race mode):
- **Year** - Select from available years (2018-2024)
- **Race** - Select specific race from chosen year

**Configuration:**
- **Commentary Mode** - Basic or Enhanced (Enhanced recommended)
- **Playback Speed** - 1x (real-time), 5x, 10x, or 20x
- **ElevenLabs API Key** - Your ElevenLabs API key for audio synthesis
- **Voice ID** - ElevenLabs voice ID (default provided)

**Controls:**
- **Start Commentary** - Begin playback with selected configuration
- **Stop** - Halt active commentary

### Configuration

#### ElevenLabs API Key

To enable audio synthesis, you need an ElevenLabs API key:

1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Get your API key from the dashboard
3. Enter it in the Web UI before starting commentary

#### Environment Variables (Optional)

You can also set credentials via environment variables:

```bash
export ELEVENLABS_API_KEY="your_api_key_here"
export ELEVENLABS_VOICE_ID="your_voice_id_here"
```

## Quick Demo Mode

Perfect for showcasing the system without internet connectivity:

- Pre-configured 2-3 minute demonstration
- Includes overtakes, pit stops, fastest lap, and incidents
- Demonstrates commentary variety and robot movements
- No OpenF1 API connection required

## Full Historical Race Mode

Experience past F1 races with generated commentary:

- Select from 100+ historical races (2018-2024)
- Configurable playback speed (1x to 20x)
- Real race data from OpenF1 API
- Complete race commentary with all significant events

## Enhanced Commentary System

The enhanced commentary system generates organic, natural-sounding commentary:

- **210 Templates** - Extensive variety prevents repetition
- **5 Excitement Levels** - Calm to dramatic based on event significance
- **5 Perspectives** - Technical, strategic, dramatic, positional, historical
- **Context Enrichment** - Multiple data points per commentary
- **Narrative Tracking** - Detects battles, comebacks, strategy divergence
- **Frequency Controls** - Prevents repetitive content patterns

### Example Commentary

**Basic Mode:**
```
"Hamilton gets past Verstappen! Up to P1!"
```

**Enhanced Mode:**
```
"Fantastic overtake by Hamilton on Verstappen, now in P1!"
"There it is! Hamilton takes the lead from Verstappen!"
"Hamilton makes a brilliant move on Verstappen for P1!"
```

## Requirements

- **Reachy Mini** (or simulation mode)
- **Python 3.9+**
- **ElevenLabs API Key** (for audio synthesis)
- **Internet Connection** (for Full Historical Race mode)

## Development

### Running in Standalone Mode

For development and testing without the Reachy Mini framework:

```bash
# Method 1: Run main module directly (recommended)
python -m reachy_f1_commentator.main

# Method 2: Use the app.py wrapper
python reachy_f1_commentator/app.py
```

The app will:
- Auto-detect and connect to Reachy if available
- Fall back to text-only mode if Reachy is not connected
- Start web server on http://localhost:8080

### Testing Reachy Connection

To verify Reachy Mini connection and audio capabilities:

```bash
python test_reachy_audio_connection.py
```

This will check:
- ✅ Reachy Mini SDK installation
- ✅ Connection to Reachy
- ✅ Audio capabilities
- ✅ Simple audio playback test

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_enhanced_commentary_generator.py

# Run with coverage
pytest --cov=reachy_f1_commentator
```

## Architecture

```
reachy_f1_commentator/
├── main.py                    # ReachyMiniF1Commentator app class
├── static/                    # Web UI assets
│   ├── index.html
│   ├── main.js
│   └── style.css
├── src/                       # Commentary generation components
│   ├── enhanced_commentary_generator.py
│   ├── speech_synthesizer.py
│   ├── motion_controller.py
│   └── ...
├── config/                    # Configuration and templates
│   ├── enhanced_templates.json
│   └── config_enhanced_example.json
└── tests/                     # Test suite
```

## Credits

Based on the **F1 Commentary Robot** project with **Enhanced Organic Commentary System**.

### Key Features:
- Enhanced commentary generation with 210 templates
- Context enrichment from multiple OpenF1 API endpoints
- Event significance scoring with context bonuses
- Narrative thread tracking (battles, comebacks, strategy)
- Dynamic commentary styles (5 excitement levels × 5 perspectives)
- Frequency controls for content variety

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on the repository
- Check the documentation
- Join the Reachy Mini community

## Acknowledgments

- **Pollen Robotics** - Reachy Mini platform
- **Hugging Face** - App hosting and distribution
- **OpenF1** - Historical race data API
- **ElevenLabs** - Text-to-speech synthesis
