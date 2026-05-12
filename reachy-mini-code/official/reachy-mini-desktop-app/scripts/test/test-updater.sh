#!/bin/bash

# Script to test the update system

set -e

echo "🧪 Testing Update System"
echo "==================================="

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. Check configuration
echo ""
echo "🔍 Step 1: Checking configuration..."
CONFIG_FILE="src-tauri/tauri.conf.json"

if ! grep -q '"updater"' "$CONFIG_FILE"; then
    echo -e "${RED}❌ Updater configuration not found in tauri.conf.json${NC}"
    exit 1
fi

if grep -q '"active": false' "$CONFIG_FILE"; then
    echo -e "${YELLOW}⚠️  Update system is disabled${NC}"
    echo "   Enable it in tauri.conf.json to test"
fi

echo -e "${GREEN}✅ Configuration found${NC}"

# 2. Check dependencies
echo ""
echo "📦 Step 2: Checking dependencies..."
if grep -q "@tauri-apps/plugin-updater" package.json; then
    echo -e "${GREEN}✅ Updater plugin installed${NC}"
else
    echo -e "${RED}❌ Updater plugin not installed${NC}"
    echo "   Run: yarn install"
    exit 1
fi

# 3. Check signing keys
echo ""
echo "🔐 Step 3: Checking signing keys..."
if [ -f ~/.tauri/reachy-mini.key.pub ]; then
    PUBKEY=$(cat ~/.tauri/reachy-mini.key.pub)
    echo -e "${GREEN}✅ Public key found${NC}"
    echo "   Key: ${PUBKEY:0:50}..."
else
    echo -e "${YELLOW}⚠️  Public key not found${NC}"
    echo "   Generate with: yarn tauri signer generate -w ~/.tauri/reachy-mini.key"
fi

# 4. Create mock server for testing (optional)
echo ""
echo "🌐 Step 4: Mock server for testing..."
MOCK_DIR="test-updates"
if [ ! -d "$MOCK_DIR" ]; then
    echo "   Creating mock server..."
    mkdir -p "$MOCK_DIR/darwin-aarch64/0.1.0"
    cat > "$MOCK_DIR/darwin-aarch64/0.1.0/update.json" <<EOF
{
  "version": "0.2.0",
  "notes": "Test version for development",
  "pub_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "platforms": {
    "darwin-aarch64": {
      "signature": "test-signature-placeholder",
      "url": "http://localhost:8080/test-update.tar.gz"
    }
  }
}
EOF
    echo -e "${GREEN}✅ Mock server created in $MOCK_DIR${NC}"
else
    echo -e "${BLUE}ℹ️  Mock server already exists${NC}"
fi

# 5. Instructions
echo ""
echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}📋 Test Instructions:${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""
echo "1. Start a mock HTTP server:"
echo -e "   ${YELLOW}cd $MOCK_DIR && python3 -m http.server 8080${NC}"
echo ""
echo "2. Configure endpoint in tauri.conf.json:"
echo -e "   ${YELLOW}\"endpoints\": [\"http://localhost:8080/{{target}}/{{current_version}}/update.json\"]${NC}"
echo ""
echo "3. Launch app in dev mode:"
echo -e "   ${YELLOW}yarn tauri:dev${NC}"
echo ""
echo "4. Check in browser console:"
echo "   - Update check logs"
echo "   - That useUpdater hook works"
echo ""
echo -e "${GREEN}✅ Test configuration ready!${NC}"
