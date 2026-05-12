#!/bin/bash

# Script to test the complete application

set -e

echo "🧪 Testing Complete Application"
echo "=================================="

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. Check that sidecar is built
echo ""
echo "📦 Step 1: Checking sidecar..."
if [ ! -d "src-tauri/binaries" ] || [ ! -f "src-tauri/binaries/uv" ]; then
    echo -e "${YELLOW}⚠️  Sidecar not built, building now...${NC}"
    yarn build:sidecar-macos
fi
echo -e "${GREEN}✅ Sidecar ready${NC}"

# 2. Build app in debug mode (faster)
echo ""
echo "🔨 Step 2: Building app (debug mode)..."
if yarn tauri build --debug; then
    echo -e "${GREEN}✅ Build successful${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

# 3. Check that bundle exists
echo ""
echo "🔍 Step 3: Checking bundle..."
BUNDLE_PATH="src-tauri/target/debug/bundle"

if [ "$(uname)" == "Darwin" ]; then
    APP_PATH="$BUNDLE_PATH/macos/Reachy Mini Control.app"
    if [ ! -d "$APP_PATH" ]; then
        echo -e "${RED}❌ macOS bundle not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Bundle found: $APP_PATH${NC}"
    
    # Check resources
    RESOURCES_PATH="$APP_PATH/Contents/Resources"
    if [ -d "$RESOURCES_PATH" ]; then
        echo -e "${BLUE}📁 Resources in bundle:${NC}"
        ls -la "$RESOURCES_PATH" | head -10
    fi
fi

# 4. Test instructions
echo ""
echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}📋 Test Instructions:${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""
echo "1. Open the app:"
echo -e "   ${YELLOW}open \"$APP_PATH\"${NC}"
echo ""
echo "2. Check system logs:"
echo -e "   ${YELLOW}log stream --predicate 'process == \"reachy-mini-control\"' --level debug${NC}"
echo ""
echo "3. Test that daemon responds:"
echo -e "   ${YELLOW}curl http://localhost:8000/api/daemon/status${NC}"
echo ""
echo "4. Test checklist:"
echo "   [ ] App starts without error"
echo "   [ ] Daemon starts automatically"
echo "   [ ] USB connection is detected"
echo "   [ ] 3D scan works"
echo "   [ ] Robot commands work"
echo ""
echo -e "${GREEN}✅ Build completed, ready for testing!${NC}"
