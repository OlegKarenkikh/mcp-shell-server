#!/bin/bash
# Run this on the host server before first deploy
# Usage: bash setup-host.sh

set -e

WORKSPACE="/opt/mcp-workspace"

echo "=== MCP Shell Server: Host Setup ==="

# 1. Create workspace directory
echo "[1/3] Creating workspace: $WORKSPACE"
mkdir -p "$WORKSPACE"

# 2. Check git is available on host (optional, git runs inside container)
echo "[2/3] Checking prerequisites..."
if command -v docker &> /dev/null; then
    echo "  Docker: $(docker --version)"
else
    echo "  WARNING: Docker not found (Coolify should handle this)"
fi

# 3. Check DNS (optional)
DOMAIN="mcp.olegk.su"
echo "[3/3] Checking DNS for $DOMAIN..."
if command -v dig &> /dev/null; then
    IP=$(dig +short "$DOMAIN" 2>/dev/null)
    if [ -n "$IP" ]; then
        echo "  $DOMAIN -> $IP"
    else
        echo "  WARNING: $DOMAIN not resolving yet. Add A record."
    fi
else
    echo "  (dig not installed, skipping DNS check)"
fi

echo ""
echo "=== Done! ==="
echo "Workspace ready at: $WORKSPACE"
echo "Next: deploy via Coolify with WORKSPACE_PATH=$WORKSPACE"
