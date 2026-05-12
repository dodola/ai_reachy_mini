#!/bin/bash

# Standalone script to test daemon installation and launch from develop branch
# Usage: bash scripts/test-daemon-develop.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Testing Daemon from Develop Branch (Standalone)${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

# 1. Clean up old daemons
echo -e "${BLUE}🧹 Step 1: Cleaning up old daemons...${NC}"
if [ -f "./scripts/daemon/kill-daemon.sh" ]; then
    bash ./scripts/daemon/kill-daemon.sh > /dev/null 2>&1 || true
    sleep 1
fi
echo -e "${GREEN}✅ Cleanup completed${NC}"
echo ""

# 2. Build sidecar with develop
echo -e "${BLUE}📦 Step 2: Building sidecar with develop...${NC}"
export REACHY_MINI_SOURCE=develop

if [ -f "./scripts/build/build-sidecar-unix.sh" ]; then
    bash ./scripts/build/build-sidecar-unix.sh
else
    echo -e "${RED}❌ build-sidecar-unix.sh not found${NC}"
    exit 1
fi

if [ ! -d "src-tauri/binaries" ] || [ ! -f "src-tauri/binaries/uv" ]; then
    echo -e "${RED}❌ Sidecar build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Sidecar built successfully with develop${NC}"
echo ""

# 3. Check installed version
echo -e "${BLUE}🔍 Step 3: Checking installed version...${NC}"
cd src-tauri/binaries

if ./uv pip list | grep -q "reachy-mini"; then
    DAEMON_VERSION=$(./uv pip list | grep "^reachy-mini " | awk '{print $2}')
    DAEMON_LOCATION=$(./uv pip show reachy-mini | grep "Location:" | awk '{print $2}' || echo "unknown")
    echo -e "${GREEN}✅ reachy-mini installed: $DAEMON_VERSION${NC}"
    echo -e "${BLUE}   Location: $DAEMON_LOCATION${NC}"
    
    # Check if it's from GitHub (develop)
    if echo "$DAEMON_LOCATION" | grep -q "github"; then
        echo -e "${GREEN}   ✓ Installed from GitHub (develop)${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Installed from PyPI (not develop)${NC}"
    fi
else
    echo -e "${RED}❌ reachy-mini not installed${NC}"
    exit 1
fi

cd "$PROJECT_DIR"
echo ""

# 4. Find trampoline
echo -e "${BLUE}🚀 Step 4: Preparing launch...${NC}"
BINARIES_DIR="src-tauri/binaries"
TRAMPOLINE=$(ls "$BINARIES_DIR"/uv-trampoline-* 2>/dev/null | head -n 1)

if [ -z "$TRAMPOLINE" ]; then
    echo -e "${RED}❌ uv-trampoline not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Trampoline found: $(basename "$TRAMPOLINE")${NC}"
echo ""

# 5. Launch daemon
echo -e "${BLUE}🤖 Step 5: Launching daemon...${NC}"

# Use absolute path of trampoline
TRAMPOLINE_ABS="$PROJECT_DIR/$TRAMPOLINE"

# Launch daemon in background
echo -e "${YELLOW}   Launching: $TRAMPOLINE_ABS run python -m reachy_mini.daemon.app.main --kinematics-engine Placo${NC}"

# Create log file for daemon
DAEMON_LOG="$PROJECT_DIR/daemon-develop-test.log"
echo "=== Daemon log started at $(date) ===" > "$DAEMON_LOG"

# Change to binaries directory so uv-trampoline can find resources
cd "$BINARIES_DIR"

# Launch daemon and redirect logs
"$TRAMPOLINE_ABS" run python -m reachy_mini.daemon.app.main --kinematics-engine Placo >> "$DAEMON_LOG" 2>&1 &
DAEMON_PID=$!

# Return to project directory
cd "$PROJECT_DIR"

echo -e "${GREEN}✅ Daemon launched (PID: $DAEMON_PID)${NC}"
echo -e "${BLUE}   Logs: $DAEMON_LOG${NC}"
echo ""

# 6. Wait for daemon to be ready
echo -e "${BLUE}⏳ Step 6: Waiting for daemon to start...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
DAEMON_READY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
    
    # Check if process is still alive
    if ! kill -0 "$DAEMON_PID" 2>/dev/null; then
        echo -e "${RED}❌ Daemon stopped (check logs: $DAEMON_LOG)${NC}"
        exit 1
    fi
    
    # Test if daemon responds
    if curl -s -f http://localhost:8000/api/daemon/status > /dev/null 2>&1; then
        DAEMON_READY=true
        break
    fi
    
    echo -n "."
done

echo ""

if [ "$DAEMON_READY" = true ]; then
    echo -e "${GREEN}✅ Daemon ready after ${ATTEMPT}s${NC}"
else
    echo -e "${RED}❌ Daemon did not respond after ${MAX_ATTEMPTS}s${NC}"
    echo -e "${YELLOW}   Check logs: $DAEMON_LOG${NC}"
    echo -e "${YELLOW}   PID: $DAEMON_PID${NC}"
    kill "$DAEMON_PID" 2>/dev/null || true
    exit 1
fi

echo ""

# 7. Test daemon
echo -e "${BLUE}🧪 Step 7: Testing daemon...${NC}"

# Test 1: Status
echo -n "   Test status... "
if STATUS=$(curl -s http://localhost:8000/api/daemon/status 2>/dev/null); then
    echo -e "${GREEN}✅${NC}"
    echo "      Response: $STATUS"
else
    echo -e "${RED}❌${NC}"
fi

# Test 2: Version
echo -n "   Test version... "
if VERSION=$(curl -s http://localhost:8000/api/daemon/version 2>/dev/null); then
    echo -e "${GREEN}✅${NC}"
    echo "      Version: $VERSION"
else
    echo -e "${YELLOW}⚠️  Version endpoint not available${NC}"
fi

echo ""

# 8. Show last lines of logs
echo -e "${BLUE}📋 Last lines of logs:${NC}"
tail -n 10 "$DAEMON_LOG" | sed 's/^/   /'

echo ""
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}✅ Test successful!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo -e "${BLUE}📝 Information:${NC}"
echo "   - Daemon PID: $DAEMON_PID"
echo "   - Logs: $DAEMON_LOG"
echo "   - API: http://localhost:8000"
echo ""
echo -e "${YELLOW}To stop the daemon:${NC}"
echo "   kill $DAEMON_PID"
echo "   or"
echo "   bash ./scripts/daemon/kill-daemon.sh"
echo ""
echo -e "${YELLOW}To see logs in real-time:${NC}"
echo "   tail -f $DAEMON_LOG"
echo ""

