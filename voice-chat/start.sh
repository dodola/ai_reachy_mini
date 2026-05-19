#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CONDA_ENV="voice-chat"
CONDA_BASE="$HOME/miniconda3"

# Activate conda env
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

# Ensure conda env bin is in PATH
export PATH="$CONDA_PREFIX/bin:$PATH"

# Ensure portaudio is available (needed by sounddevice)
if ! conda list portaudio >/dev/null 2>&1; then
    echo "Installing portaudio..."
    conda install -y -c conda-forge portaudio
fi

# Kill old daemon if running (use ps+kill to avoid pkill hang)
for pid in $(ps aux | grep reachy-mini-daemon | grep -v grep | awk '{print $2}'); do
    kill "$pid" 2>/dev/null || true
done
sleep 1

# Start reachy-mini-daemon in background
reachy-mini-daemon &
DAEMON_PID=$!

# Wait for daemon to be ready
echo "Waiting for daemon to start..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo "Daemon is ready (PID: $DAEMON_PID)"
        break
    fi
    sleep 1
done

if ! curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "ERROR: Daemon failed to start within 30s"
    kill $DAEMON_PID 2>/dev/null || true
    exit 1
fi

# Run main app
python main.py --config config.yaml "$@"
APP_EXIT=$?

# Cleanup daemon on exit
kill $DAEMON_PID 2>/dev/null || true
exit $APP_EXIT