#!/bin/bash

# Script to test the embedded sidecar daemon

set -e

echo "🧪 Testing Embedded Sidecar Daemon"
echo "===================================="

cd "$(dirname "$0")/.."

# Colors for messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Build sidecar
echo ""
echo "📦 Step 1: Building sidecar..."
if yarn build:sidecar-macos; then
    echo -e "${GREEN}✅ Sidecar build successful${NC}"
else
    echo -e "${RED}❌ Sidecar build failed${NC}"
    exit 1
fi

# 2. Check that files exist
echo ""
echo "🔍 Step 2: Checking files..."
BINARIES_DIR="src-tauri/binaries"

if [ ! -d "$BINARIES_DIR" ]; then
    echo -e "${RED}❌ binaries/ directory not found${NC}"
    exit 1
fi

# Check required files
MISSING_FILES=()

# Check uv
if [ ! -f "$BINARIES_DIR/uv" ]; then
    MISSING_FILES+=("uv")
fi

# Check .venv
if [ ! -d "$BINARIES_DIR/.venv" ]; then
    MISSING_FILES+=(".venv")
fi

# Check uv-trampoline (may have different names depending on triplet)
TRAMPOLINE_FOUND=false
for file in "$BINARIES_DIR"/uv-trampoline-*; do
    if [ -f "$file" ]; then
        TRAMPOLINE_FOUND=true
        break
    fi
done

if [ "$TRAMPOLINE_FOUND" = false ]; then
    MISSING_FILES+=("uv-trampoline-*")
fi

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing files: ${MISSING_FILES[*]}${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required files are present${NC}"

# 3. Test uv
echo ""
echo "🔧 Step 3: Testing uv..."
cd "$BINARIES_DIR"
if ./uv --version > /dev/null 2>&1; then
    UV_VERSION=$(./uv --version)
    echo -e "${GREEN}✅ uv works: $UV_VERSION${NC}"
else
    echo -e "${RED}❌ uv does not work${NC}"
    exit 1
fi

# 4. Test Python
echo ""
echo "🐍 Step 4: Testing embedded Python..."
if ./uv python list > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Embedded Python detected${NC}"
else
    echo -e "${RED}❌ Embedded Python not found${NC}"
    exit 1
fi

# 5. Check venv
echo ""
echo "📦 Step 5: Checking venv..."
if [ -d ".venv" ] && [ -f ".venv/pyvenv.cfg" ]; then
    echo -e "${GREEN}✅ Venv present${NC}"
else
    echo -e "${RED}❌ Venv not found or invalid${NC}"
    exit 1
fi

# 6. Check reachy-mini
echo ""
echo "🤖 Step 6: Checking reachy-mini..."
if ./uv pip list | grep -q "reachy-mini"; then
    DAEMON_VERSION=$(./uv pip list | grep "^reachy-mini " | awk '{print $2}')
    echo -e "${GREEN}✅ reachy-mini installed: $DAEMON_VERSION${NC}"
else
    echo -e "${RED}❌ reachy-mini not installed${NC}"
    exit 1
fi

# 7. Test trampoline (optional, requires robot)
echo ""
echo "🚀 Step 7: Testing trampoline..."
TRAMPOLINE=$(ls uv-trampoline-* 2>/dev/null | head -n 1)
if [ -n "$TRAMPOLINE" ] && [ -x "$TRAMPOLINE" ]; then
    echo -e "${GREEN}✅ Trampoline found: $TRAMPOLINE${NC}"
    echo -e "${YELLOW}⚠️  Full test requires a connected robot${NC}"
else
    echo -e "${RED}❌ Trampoline not found or not executable${NC}"
    exit 1
fi

cd - > /dev/null

echo ""
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}✅ All sidecar tests passed!${NC}"
echo -e "${GREEN}====================================${NC}"
