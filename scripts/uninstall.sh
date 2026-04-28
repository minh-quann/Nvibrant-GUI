#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# uninstall.sh — Uninstall NVibrant GUI
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DESKTOP_DST="$HOME/.local/share/applications/nvibrant-gui.desktop"
ICON_DST="$HOME/.local/share/icons/hicolor/scalable/apps/nvibrant-gui.svg"

echo "╔══════════════════════════════════════════════╗"
echo "║       NVibrant GUI — Uninstaller             ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Step 1: Uninstall the Python package
echo "→ Uninstalling Python package..."
pip uninstall -y nvibrant-gui 2>/dev/null || python3 -m pip uninstall -y nvibrant-gui 2>/dev/null || true
echo "  ✓ Package uninstalled"

# Step 2: Remove .desktop file
echo "→ Removing .desktop launcher..."
rm -f "$DESKTOP_DST"
echo "  ✓ Desktop entry removed"

# Step 3: Remove icon
echo "→ Removing app icon..."
rm -f "$ICON_DST"
echo "  ✓ Icon removed"

# Step 3: Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    echo "  ✓ Desktop database updated"
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✓ Uninstallation complete!                  ║"
echo "╚══════════════════════════════════════════════╝"
