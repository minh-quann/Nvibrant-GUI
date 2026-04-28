#!/usr/bin/env python3
"""
NVibrant GUI - NVIDIA Digital Vibrance Controller
A GTK4/Adwaita GUI for controlling per-display vibrance via nvibrant.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from gi.repository import Gtk, Adw, GLib, Gio, Pango


# ─── Constants ────────────────────────────────────────────────────────────────

NVIBRANT_REPO = "https://github.com/Tremeschin/nvibrant.git"
CLONE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nvibrant")
APP_ID = "com.github.nvibrant.gui"

# Vibrance range: -1024 (grayscale/0%) to 1023 (max/200%), 0 = 100% (default)
VIBRANCE_MIN = -1024
VIBRANCE_MAX = 1023
VIBRANCE_DEFAULT = 0


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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def vibrance_to_percent(value: int) -> int:
    """Convert raw vibrance (-1024..1023) to percentage (0..200)"""
    return round((value - VIBRANCE_MIN) / (VIBRANCE_MAX - VIBRANCE_MIN) * 200)


def percent_to_vibrance(percent: int) -> int:
    """Convert percentage (0..200) to raw vibrance (-1024..1023)"""
    return round(VIBRANCE_MIN + (percent / 200) * (VIBRANCE_MAX - VIBRANCE_MIN))


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


def check_clone_exists() -> bool:
    """Check if nvibrant repo is cloned locally"""
    return os.path.isdir(os.path.join(CLONE_DIR, ".git"))


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


def get_current_ports() -> list[DisplayPort]:
    """Query nvibrant for current display port states (read-only, sets 0)"""
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


# ─── Widgets ──────────────────────────────────────────────────────────────────

class PortRow(Gtk.Box):
    """A row with slider to control vibrance for one display port"""

    def __init__(self, port: DisplayPort):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.port = port
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        # Card-like frame
        frame = Gtk.Frame()
        frame.add_css_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_margin_top(16)
        inner.set_margin_bottom(16)

        # Header row: port info + status badge
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Port icon
        icon_name = "video-display-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        icon.add_css_class("dim-label")
        header.append(icon)

        # Port label
        label_text = f"Port {port.index} — {port.port_type}"
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        label.add_css_class("heading")
        label.set_hexpand(True)
        header.append(label)

        # Status badge
        status_label = Gtk.Label()
        if port.status == PortStatus.CONNECTED:
            status_label.set_label("● Connected")
            status_label.add_css_class("success")
        else:
            status_label.set_label("○ Disconnected")
            status_label.add_css_class("dim-label")
        header.append(status_label)

        inner.append(header)

        # Slider area (only for connected ports)
        if port.status == PortStatus.CONNECTED:
            slider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

            # Percentage label
            self.percent_label = Gtk.Label()
            self.percent_label.set_width_chars(5)
            self.percent_label.add_css_class("title-2")

            # Scale/slider: 0% to 200%
            self.scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, 0, 200, 1
            )
            self.scale.set_hexpand(True)
            self.scale.set_draw_value(False)
            self.scale.add_mark(0, Gtk.PositionType.BOTTOM, "0%")
            self.scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
            self.scale.add_mark(200, Gtk.PositionType.BOTTOM, "200%")

            # Set initial value
            initial_pct = vibrance_to_percent(port.current_vibrance)
            self.scale.set_value(initial_pct)
            self._update_label(initial_pct)
            self.scale.connect("value-changed", self._on_scale_changed)

            slider_box.append(self.scale)
            slider_box.append(self.percent_label)
            inner.append(slider_box)

            # Quick preset buttons
            presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            presets_box.set_halign(Gtk.Align.CENTER)
            for pct_value, pct_label in [(50, "50%"), (100, "100%"), (125, "125%"), (150, "150%"), (200, "200%")]:
                btn = Gtk.Button(label=pct_label)
                btn.add_css_class("pill")
                if pct_value == 100:
                    btn.add_css_class("suggested-action")
                btn.connect("clicked", self._on_preset, pct_value)
                presets_box.append(btn)
            inner.append(presets_box)
        else:
            # Disabled overlay
            dim = Gtk.Label(label="No display connected on this port")
            dim.add_css_class("dim-label")
            dim.set_margin_top(8)
            dim.set_margin_bottom(8)
            inner.append(dim)
            self.scale = None
            self.percent_label = None

        frame.set_child(inner)
        self.append(frame)

    def _update_label(self, pct: float) -> None:
        """Update the percentage display label"""
        self.percent_label.set_label(f"{int(pct)}%")
        if pct > 100:
            self.percent_label.remove_css_class("warning")
            self.percent_label.add_css_class("success")
        elif pct < 100:
            self.percent_label.remove_css_class("success")
            self.percent_label.add_css_class("warning")
        else:
            self.percent_label.remove_css_class("success")
            self.percent_label.remove_css_class("warning")

    def _on_scale_changed(self, scale: Gtk.Scale) -> None:
        """Handle slider value change"""
        self._update_label(scale.get_value())

    def _on_preset(self, _btn: Gtk.Button, pct: int) -> None:
        """Set slider to preset value"""
        if self.scale:
            self.scale.set_value(pct)

    def get_vibrance(self) -> int:
        """Get current raw vibrance value from slider"""
        if self.scale:
            return percent_to_vibrance(int(self.scale.get_value()))
        return VIBRANCE_DEFAULT


# ─── Main Window ──────────────────────────────────────────────────────────────

class NVibrantWindow(Adw.ApplicationWindow):
    """Main application window"""

    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NVibrant", default_width=600, default_height=500)
        self.port_rows: list[PortRow] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the initial UI layout"""
        # Main layout
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(
            title="NVibrant",
            subtitle="Digital Vibrance Controller"
        ))

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh displays")
        refresh_btn.connect("clicked", self._on_refresh)
        header.pack_start(refresh_btn)

        toolbar_view.add_top_bar(header)

        # Check if nvibrant is available
        if not check_nvibrant_installed():
            toolbar_view.set_content(self._build_setup_page())
        else:
            toolbar_view.set_content(self._build_main_page())

        self.set_content(toolbar_view)

    def _build_setup_page(self) -> Gtk.Widget:
        """Build the setup/clone page when nvibrant is not available"""
        status_page = Adw.StatusPage()
        status_page.set_icon_name("applications-graphics-symbolic")
        status_page.set_title("NVibrant Not Found")
        status_page.set_description(
            "nvibrant is required to control display vibrance.\n"
            "Click below to install it via pip, or clone the repository."
        )

        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)

        # Install via pip/uvx button
        install_btn = Gtk.Button(label="Install via pip (pip install nvibrant)")
        install_btn.add_css_class("suggested-action")
        install_btn.add_css_class("pill")
        install_btn.connect("clicked", self._on_install_pip)
        btn_box.append(install_btn)

        # Clone repo button
        clone_btn = Gtk.Button(label="Clone Repository")
        clone_btn.add_css_class("pill")
        clone_btn.connect("clicked", self._on_clone)
        btn_box.append(clone_btn)

        # Spinner for loading state
        self.setup_spinner = Gtk.Spinner()
        self.setup_spinner.set_visible(False)
        btn_box.append(self.setup_spinner)

        self.setup_status = Gtk.Label()
        self.setup_status.add_css_class("dim-label")
        self.setup_status.set_visible(False)
        btn_box.append(self.setup_status)

        status_page.set_child(btn_box)
        return status_page

    def _build_main_page(self) -> Gtk.Widget:
        """Build the main vibrance control page"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Scrollable area for port rows
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.ports_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.ports_box.set_margin_top(8)
        self.ports_box.set_margin_bottom(8)

        # Loading indicator
        self.main_spinner = Gtk.Spinner()
        self.main_spinner.set_spinning(True)
        self.main_spinner.set_margin_top(48)
        self.ports_box.append(self.main_spinner)

        scrolled.set_child(self.ports_box)
        main_box.append(scrolled)

        # Bottom action bar
        action_bar = Gtk.ActionBar()

        # Status label
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        self.status_label.add_css_class("dim-label")
        action_bar.pack_start(self.status_label)

        # Reset button
        reset_btn = Gtk.Button(label="Reset All")
        reset_btn.add_css_class("destructive-action")
        reset_btn.add_css_class("pill")
        reset_btn.connect("clicked", self._on_reset)
        action_bar.pack_end(reset_btn)

        # Apply button
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.add_css_class("pill")
        apply_btn.connect("clicked", self._on_apply)
        action_bar.pack_end(apply_btn)

        main_box.append(action_bar)

        # Load ports in background
        self._load_ports_async()

        return main_box

    def _load_ports_async(self) -> None:
        """Load display ports in a background thread"""
        def worker():
            ports = get_current_ports()
            GLib.idle_add(self._populate_ports, ports)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _populate_ports(self, ports: list[DisplayPort]) -> None:
        """Populate port rows in the UI (runs on main thread)"""
        # Clear existing children
        child = self.ports_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.ports_box.remove(child)
            child = next_child

        self.port_rows.clear()

        if not ports:
            empty = Adw.StatusPage()
            empty.set_icon_name("dialog-warning-symbolic")
            empty.set_title("No Display Ports Found")
            empty.set_description("Could not detect any GPU display outputs.\nMake sure nvidia drivers are loaded.")
            self.ports_box.append(empty)
            return

        # Driver info banner
        try:
            driver_ver = open("/sys/module/nvidia/version").read().strip()
            info = Adw.Banner()
            info.set_title(f"NVIDIA Driver v{driver_ver} — {len([p for p in ports if p.status == PortStatus.CONNECTED])} active display(s)")
            info.set_revealed(True)
            self.ports_box.append(info)
        except (FileNotFoundError, PermissionError):
            pass

        # Add port rows
        for port in ports:
            row = PortRow(port)
            self.port_rows.append(row)
            self.ports_box.append(row)

        self.status_label.set_label("Ready — Adjust sliders and click Apply")
        return False

    # ─── Event handlers ──────────────────────────────────────────────────

    def _on_refresh(self, _btn: Gtk.Button) -> None:
        """Refresh display port list"""
        self._build_ui()

    def _on_apply(self, _btn: Gtk.Button) -> None:
        """Apply vibrance settings to all ports"""
        if not self.port_rows:
            return

        # Build values list (all ports, including disconnected)
        values = [row.get_vibrance() for row in self.port_rows]
        self.status_label.set_label("Applying...")

        def worker():
            success, output = apply_vibrance(values)
            pcts = [vibrance_to_percent(v) for v in values]
            GLib.idle_add(self._on_apply_done, success, output, pcts)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_apply_done(self, success: bool, output: str, pcts: list[int]) -> None:
        """Handle apply result on main thread"""
        if success:
            connected = [(i, p) for i, p in enumerate(pcts) if self.port_rows[i].port.status == PortStatus.CONNECTED]
            summary = ", ".join(f"Port {self.port_rows[i].port.index}: {p}%" for i, p in connected)
            self.status_label.set_label(f"✓ Applied — {summary}")
        else:
            self.status_label.set_label(f"✗ Failed — check terminal for details")
        return False

    def _on_reset(self, _btn: Gtk.Button) -> None:
        """Reset all sliders to 100% (default/no effect)"""
        for row in self.port_rows:
            if row.scale:
                row.scale.set_value(100)
        self.status_label.set_label("Sliders reset to 100% — click Apply to confirm")

    def _on_install_pip(self, btn: Gtk.Button) -> None:
        """Install nvibrant via pip"""
        btn.set_sensitive(False)
        self.setup_spinner.set_visible(True)
        self.setup_spinner.set_spinning(True)
        self.setup_status.set_visible(True)
        self.setup_status.set_label("Installing nvibrant via pip...")

        def worker():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "nvibrant"],
                    capture_output=True, text=True, timeout=120
                )
                success = result.returncode == 0
                msg = "Installation complete!" if success else f"Failed: {result.stderr[:200]}"
            except Exception as e:
                success = False
                msg = str(e)
            GLib.idle_add(self._on_install_done, success, msg)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_clone(self, btn: Gtk.Button) -> None:
        """Clone nvibrant repository"""
        btn.set_sensitive(False)
        self.setup_spinner.set_visible(True)
        self.setup_spinner.set_spinning(True)
        self.setup_status.set_visible(True)
        self.setup_status.set_label(f"Cloning {NVIBRANT_REPO}...")

        def worker():
            try:
                result = subprocess.run(
                    ["git", "clone", NVIBRANT_REPO, CLONE_DIR],
                    capture_output=True, text=True, timeout=120
                )
                success = result.returncode == 0
                msg = "Clone complete!" if success else f"Failed: {result.stderr[:200]}"
            except Exception as e:
                success = False
                msg = str(e)
            GLib.idle_add(self._on_install_done, success, msg)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_install_done(self, success: bool, msg: str) -> None:
        """Handle install/clone result"""
        self.setup_spinner.set_spinning(False)
        self.setup_spinner.set_visible(False)
        self.setup_status.set_label(msg)
        if success:
            # Rebuild UI to show main page
            self._build_ui()
        return False


# ─── Application ──────────────────────────────────────────────────────────────

class NVibrantApp(Adw.Application):
    """Main GTK Application"""

    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self) -> None:
        """Activate the application"""
        win = NVibrantWindow(self)
        win.present()


def main() -> None:
    app = NVibrantApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
