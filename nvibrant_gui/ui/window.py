"""
Main application window for NVibrant GUI.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import threading
from gi.repository import Gtk, Adw, GLib

from nvibrant_gui.core.constants import DisplayPort, PortStatus
from nvibrant_gui.core.backend import (
    check_nvibrant_installed,
    get_current_ports,
    get_driver_version,
    apply_vibrance,
    install_via_pip,
    clone_repo,
    vibrance_to_percent,
    percent_to_vibrance,
    save_config,
    load_config,
)
from nvibrant_gui.ui.port_row import PortRow


class NVibrantWindow(Adw.ApplicationWindow):
    """Main application window"""

    def __init__(self, app: Adw.Application):
        super().__init__(
            application=app,
            title="NVibrant",
            default_width=600,
            default_height=500
        )
        self.port_rows: list[PortRow] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the initial UI layout"""
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(
            title="NVibrant",
            subtitle="Digital Vibrance Controller"
        ))

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh displays")
        refresh_btn.connect("clicked", self._on_refresh)
        header.pack_start(refresh_btn)

        toolbar_view.add_top_bar(header)

        # Show setup or main page
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

        install_btn = Gtk.Button(label="Install via pip (pip install nvibrant)")
        install_btn.add_css_class("suggested-action")
        install_btn.add_css_class("pill")
        install_btn.connect("clicked", self._on_install_pip)
        btn_box.append(install_btn)

        clone_btn = Gtk.Button(label="Clone Repository")
        clone_btn.add_css_class("pill")
        clone_btn.connect("clicked", self._on_clone)
        btn_box.append(clone_btn)

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

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.ports_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.ports_box.set_margin_top(8)
        self.ports_box.set_margin_bottom(8)

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
        self.status_label.set_hexpand(True)
        action_bar.pack_start(self.status_label)

        reset_btn = Gtk.Button(label="Reset All")
        reset_btn.add_css_class("destructive-action")
        reset_btn.add_css_class("pill")
        reset_btn.connect("clicked", self._on_reset)
        action_bar.pack_end(reset_btn)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.add_css_class("pill")
        apply_btn.connect("clicked", self._on_apply)
        action_bar.pack_end(apply_btn)

        main_box.append(action_bar)

        self._load_ports_async()
        return main_box

    def _load_ports_async(self) -> None:
        """Load display ports in background thread"""
        def worker():
            ports = get_current_ports()
            saved = load_config()
            GLib.idle_add(self._populate_ports, ports, saved)
        threading.Thread(target=worker, daemon=True).start()

    def _populate_ports(self, ports: list[DisplayPort], saved: list[int] | None) -> None:
        """Populate port rows in UI (main thread)"""
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
            empty.set_description("Could not detect any GPU display outputs.")
            self.ports_box.append(empty)
            return

        # Driver info banner
        driver_ver = get_driver_version()
        active_count = len([p for p in ports if p.status == PortStatus.CONNECTED])
        info = Adw.Banner()
        info.set_title(f"NVIDIA Driver v{driver_ver} — {active_count} active display(s)")
        info.set_revealed(True)
        self.ports_box.append(info)

        # If saved config exists, restore slider values
        for port in ports:
            row = PortRow(port)
            # Restore saved value for this port if available
            if saved and port.index < len(saved):
                saved_pct = vibrance_to_percent(saved[port.index])
                if row.scale:
                    row.scale.set_value(saved_pct)
            self.port_rows.append(row)
            self.ports_box.append(row)

        if saved:
            self.status_label.set_label("Config loaded — click Apply to re-apply")
        else:
            self.status_label.set_label("Ready — Adjust sliders and click Apply")
        return False

    # ─── Event Handlers ──────────────────────────────────────────────────

    def _on_refresh(self, _btn: Gtk.Button) -> None:
        self._build_ui()

    def _on_apply(self, _btn: Gtk.Button) -> None:
        if not self.port_rows:
            return
        values = [row.get_vibrance() for row in self.port_rows]
        self.status_label.set_label("Applying...")

        def worker():
            success, output = apply_vibrance(values)
            if success:
                # Save config for persistence
                save_config(values)
            pcts = [vibrance_to_percent(v) for v in values]
            GLib.idle_add(self._on_apply_done, success, output, pcts)
        threading.Thread(target=worker, daemon=True).start()

    def _on_apply_done(self, success: bool, output: str, pcts: list[int]) -> None:
        if success:
            connected = [
                (i, p) for i, p in enumerate(pcts)
                if self.port_rows[i].port.status == PortStatus.CONNECTED
            ]
            summary = ", ".join(
                f"Port {self.port_rows[i].port.index}: {p}%"
                for i, p in connected
            )
            self.status_label.set_label(f"✓ Applied & Saved — {summary}")
        else:
            self.status_label.set_label("✗ Failed — check terminal for details")
        return False

    def _on_reset(self, _btn: Gtk.Button) -> None:
        for row in self.port_rows:
            if row.scale:
                row.scale.set_value(0)
        self.status_label.set_label("Sliders reset to 0% (default) — click Apply to confirm")

    def _on_install_pip(self, btn: Gtk.Button) -> None:
        btn.set_sensitive(False)
        self.setup_spinner.set_visible(True)
        self.setup_spinner.set_spinning(True)
        self.setup_status.set_visible(True)
        self.setup_status.set_label("Installing nvibrant via pip...")

        def worker():
            success, msg = install_via_pip()
            GLib.idle_add(self._on_install_done, success, msg)
        threading.Thread(target=worker, daemon=True).start()

    def _on_clone(self, btn: Gtk.Button) -> None:
        btn.set_sensitive(False)
        self.setup_spinner.set_visible(True)
        self.setup_spinner.set_spinning(True)
        self.setup_status.set_visible(True)
        self.setup_status.set_label("Cloning repository...")

        def worker():
            success, msg = clone_repo()
            GLib.idle_add(self._on_install_done, success, msg)
        threading.Thread(target=worker, daemon=True).start()

    def _on_install_done(self, success: bool, msg: str) -> None:
        self.setup_spinner.set_spinning(False)
        self.setup_spinner.set_visible(False)
        self.setup_status.set_label(msg)
        if success:
            self._build_ui()
        return False
