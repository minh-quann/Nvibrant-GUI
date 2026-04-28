"""
Constants and type definitions for NVibrant GUI.
"""

import os
from dataclasses import dataclass
from enum import Enum

# ─── App Constants ────────────────────────────────────────────────────────────

NVIBRANT_REPO = "https://github.com/Tremeschin/nvibrant.git"
CLONE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "nvibrant-gui", "nvibrant")
APP_ID = "com.github.nvibrant.gui"

# Vibrance range: -1024 (grayscale/0%) to 1023 (max/200%), 0 = 100% (default)
VIBRANCE_MIN = -1024
VIBRANCE_MAX = 1023
VIBRANCE_DEFAULT = 0


# ─── Types ────────────────────────────────────────────────────────────────────

class PortStatus(Enum):
    """Display port connection status"""
    CONNECTED = "Success"
    DISCONNECTED = "None"


@dataclass
class DisplayPort:
    """Represents a physical GPU display output"""
    index: int
    port_type: str  # DP, HDMI, etc.
    current_vibrance: int
    status: PortStatus
