"""
Backend logic for interacting with nvibrant CLI.
Handles detection, parsing output, and applying vibrance values.
"""

import os
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
    CONFIG_DIR,
    CONFIG_FILE,
    SYSTEMD_DIR,
    SYSTEMD_SERVICE,
)


# ─── Conversion Helpers ──────────────────────────────────────────────────────

def vibrance_to_percent(value: int) -> int:
    """Convert raw vibrance (0..1023) to percentage (0..100)
    0% = 0 (default, no effect), 100% = 1023 (max saturation)"""
    clamped = max(0, min(VIBRANCE_MAX, value))
    return round(clamped / VIBRANCE_MAX * 100)


def percent_to_vibrance(percent: int) -> int:
    """Convert percentage (0..100) to raw vibrance (0..1023)
    0% = 0 (default, no effect), 100% = 1023 (max saturation)"""
    return round(percent / 100 * VIBRANCE_MAX)


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

def get_current_ports(saved_values: list[int] | None = None) -> list[DisplayPort]:
    """Query nvibrant for current display port states.
    If saved_values provided, pass them to avoid resetting vibrance to 0."""
    try:
        cmd = ["uvx", "nvibrant"]
        if saved_values:
            cmd += [str(v) for v in saved_values]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15
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


# ─── Config Persistence ──────────────────────────────────────────────────────

def save_config(values: list[int]) -> None:
    """Save vibrance values to config file"""
    import json
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = {"vibrance_values": values}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_config() -> list[int] | None:
    """Load saved vibrance values from config file"""
    import json
    if not os.path.isfile(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        return config.get("vibrance_values")
    except (json.JSONDecodeError, KeyError):
        return None


# ─── Systemd Service ─────────────────────────────────────────────────────────

_SERVICE_TEMPLATE = """[Unit]
Description=Apply nvibrant {raw_val}
After=graphical.target

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 3
ExecStart=/usr/bin/uvx nvibrant {args}

[Install]
WantedBy=default.target
"""


def update_systemd_service(raw_val: int, port_count: int) -> None:
    """Update and enable systemd user service for autostart on login"""
    args = " ".join([str(raw_val)] * port_count)
    service_content = _SERVICE_TEMPLATE.format(raw_val=raw_val, args=args)

    os.makedirs(SYSTEMD_DIR, exist_ok=True)
    with open(SYSTEMD_SERVICE, "w") as f:
        f.write(service_content)

    # Reload and enable
    subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        capture_output=True, timeout=5
    )
    subprocess.run(
        ["systemctl", "--user", "enable", "nvibrant.service"],
        capture_output=True, timeout=5
    )

