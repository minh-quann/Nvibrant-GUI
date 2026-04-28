"""
Backend logic for interacting with nvibrant CLI.
Handles detection, parsing output, and applying vibrance values.
"""

import re
import subprocess
import sys

from nvibrant_gui.core.constants import (
    DisplayPort,
    PortStatus,
    VIBRANCE_MIN,
    VIBRANCE_MAX,
    VIBRANCE_DEFAULT,
    CLONE_DIR,
    NVIBRANT_REPO,
)


# ─── Conversion Helpers ──────────────────────────────────────────────────────

def vibrance_to_percent(value: int) -> int:
    """Convert raw vibrance (-1024..1023) to percentage (0..200)"""
    return round((value - VIBRANCE_MIN) / (VIBRANCE_MAX - VIBRANCE_MIN) * 200)


def percent_to_vibrance(percent: int) -> int:
    """Convert percentage (0..200) to raw vibrance (-1024..1023)"""
    return round(VIBRANCE_MIN + (percent / 200) * (VIBRANCE_MAX - VIBRANCE_MIN))


# ─── NVibrant Detection ──────────────────────────────────────────────────────

def check_nvibrant_installed() -> bool:
    """Check if nvibrant is available via uvx"""
    try:
        result = subprocess.run(
            ["uvx", "nvibrant"],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_driver_version() -> str:
    """Get current NVIDIA driver version"""
    try:
        return open("/sys/module/nvidia/version").read().strip()
    except (FileNotFoundError, PermissionError):
        return "Unknown"


# ─── Output Parsing ──────────────────────────────────────────────────────────

def parse_nvibrant_output(output: str) -> list[DisplayPort]:
    """Parse nvibrant stdout to extract display port info"""
    ports: list[DisplayPort] = []
    # Pattern: • (0, DP  ) • Set vibrance (    0) • Success/None
    pattern = re.compile(
        r'•\s*\((\d+),\s*(\w+)\s*\)\s*•\s*Set vibrance\s*\(\s*(-?\d+)\)\s*•\s*(\w+)'
    )
    for match in pattern.finditer(output):
        idx = int(match.group(1))
        port_type = match.group(2).strip()
        vibrance = int(match.group(3))
        status_str = match.group(4).strip()
        status = PortStatus.CONNECTED if status_str == "Success" else PortStatus.DISCONNECTED
        ports.append(DisplayPort(idx, port_type, vibrance, status))
    return ports


# ─── NVibrant Commands ────────────────────────────────────────────────────────

def get_current_ports() -> list[DisplayPort]:
    """Query nvibrant for current display port states"""
    try:
        result = subprocess.run(
            ["uvx", "nvibrant"],
            capture_output=True, text=True, timeout=15
        )
        return parse_nvibrant_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def apply_vibrance(values: list[int]) -> tuple[bool, str]:
    """Apply vibrance values via nvibrant. Returns (success, output)."""
    args = ["uvx", "nvibrant"] + [str(v) for v in values]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, str(e)


# ─── Install / Clone ─────────────────────────────────────────────────────────

def install_via_pip() -> tuple[bool, str]:
    """Install nvibrant via pip"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "nvibrant"],
            capture_output=True, text=True, timeout=120
        )
        success = result.returncode == 0
        msg = "Installation complete!" if success else f"Failed: {result.stderr[:200]}"
        return success, msg
    except Exception as e:
        return False, str(e)


def clone_repo() -> tuple[bool, str]:
    """Clone nvibrant repository"""
    try:
        result = subprocess.run(
            ["git", "clone", NVIBRANT_REPO, CLONE_DIR],
            capture_output=True, text=True, timeout=120
        )
        success = result.returncode == 0
        msg = "Clone complete!" if success else f"Failed: {result.stderr[:200]}"
        return success, msg
    except Exception as e:
        return False, str(e)
