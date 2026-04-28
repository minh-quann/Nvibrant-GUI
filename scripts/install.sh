#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install.sh — Install NVibrant GUI system-wide
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_SRC="$SCRIPT_DIR/nvibrant_gui/data/nvibrant-gui.desktop"
DESKTOP_DST="$HOME/.local/share/applications/nvibrant-gui.desktop"

echo "╔══════════════════════════════════════════════╗"
echo "║       NVibrant GUI — Installer               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Step 1: Install the Python package
echo "→ Installing Python package..."
pip install --user "$SCRIPT_DIR" || python3 -m pip install --user "$SCRIPT_DIR"
echo "  ✓ Package installed"

# Step 2: Install .desktop file
echo "→ Installing .desktop launcher..."
mkdir -p "$(dirname "$DESKTOP_DST")"
cp "$DESKTOP_SRC" "$DESKTOP_DST"
echo "  ✓ Desktop entry installed at $DESKTOP_DST"

# Step 3: Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    echo "  ✓ Desktop database updated"
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✓ Installation complete!                    ║"
echo "║                                              ║"
echo "║  Run:  nvibrant-gui                          ║"
echo "║  Or find 'NVibrant' in your app launcher     ║"
echo "╚══════════════════════════════════════════════╝"
