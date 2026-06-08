"""
Main application window for NVibrant GUI.
Simplified single-slider design that applies to all ports.
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
    update_systemd_service,
)


class NVibrantWindow(Adw.ApplicationWindow):
    """Main application window — single slider for all ports"""

    def __init__(self, app: Adw.Application):
        super().__init__(
            application=app,
            title="NVibrant",
            default_width=420,
            default_height=300
        )
        self.ports: list[DisplayPort] = []
        self._updating_scales = False
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the initial UI layout"""
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(
            title="NVibrant",
            subtitle="Digital Vibrance Controller — Ver 1.0"
        ))

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
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
        """Build the simplified single-slider main page"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Content area
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_vexpand(True)

        # Driver info banner
        self.info_banner = Adw.Banner()
        self.info_banner.set_revealed(False)
        main_box.append(self.info_banner)

        # Vibrance card
        frame = Gtk.Frame()
        frame.add_css_class("card")
        card_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card_inner.set_margin_start(20)
        card_inner.set_margin_end(20)
        card_inner.set_margin_top(20)
        card_inner.set_margin_bottom(20)

        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("video-display-symbolic")
        icon.set_pixel_size(24)
        title_row.append(icon)
        title_label = Gtk.Label(label="Digital Vibrance")
        title_label.add_css_class("heading")
        title_label.set_hexpand(True)
        title_label.set_xalign(0)
        title_row.append(title_label)
        card_inner.append(title_row)

        # Slider + percentage label
        slider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_hexpand(True)
        self.scale.set_draw_value(False)
        self.scale.add_mark(0, Gtk.PositionType.BOTTOM, "0%")
        self.scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.scale.connect("value-changed", self._on_scale_changed)

        self.percent_label = Gtk.Label()
        self.percent_label.set_width_chars(5)
        self.percent_label.add_css_class("title-1")

        slider_box.append(self.scale)
        slider_box.append(self.percent_label)
        card_inner.append(slider_box)

        # Raw slider + label
        raw_slider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.raw_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1023, 1)
        self.raw_scale.set_hexpand(True)
        self.raw_scale.set_draw_value(False)
        self.raw_scale.add_mark(0, Gtk.PositionType.BOTTOM, "0")
        self.raw_scale.add_mark(500, Gtk.PositionType.BOTTOM, "500")
        self.raw_scale.add_mark(1023, Gtk.PositionType.BOTTOM, "1023")
        self.raw_scale.connect("value-changed", self._on_raw_scale_changed)

        self.raw_label = Gtk.Label()
        self.raw_label.set_width_chars(5)
        self.raw_label.add_css_class("title-1")

        raw_slider_box.append(self.raw_scale)
        raw_slider_box.append(self.raw_label)
        card_inner.append(raw_slider_box)

        # Preset buttons
        presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        presets_box.set_halign(Gtk.Align.CENTER)
        for pct_val, pct_text in [(0, "0%"), (50, "50%"), (60, "60%"), (80, "80%"), (100, "100%")]:
            btn = Gtk.Button(label=pct_text)
            btn.add_css_class("pill")
            if pct_val == 80:
                btn.add_css_class("suggested-action")
            btn.connect("clicked", self._on_preset, pct_val)
            presets_box.append(btn)
        card_inner.append(presets_box)

        frame.set_child(card_inner)
        content.append(frame)

        # Info: applies to all displays
        info_label = Gtk.Label(label="Applies to all connected displays")
        info_label.add_css_class("dim-label")
        info_label.add_css_class("caption")
        content.append(info_label)

        main_box.append(content)

        # Bottom action bar
        action_bar = Gtk.ActionBar()

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        self.status_label.add_css_class("dim-label")
        self.status_label.set_hexpand(True)
        action_bar.pack_start(self.status_label)

        reset_btn = Gtk.Button(label="Reset")
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

        # Load saved value and port info
        self._load_async()
        return main_box

    def _load_async(self) -> None:
        """Load ports and config in background"""
        def worker():
            # Load config FIRST so we can pass values to nvibrant
            # This prevents nvibrant from resetting vibrance to 0
            saved = load_config()
            ports = get_current_ports(saved_values=saved)
            GLib.idle_add(self._on_loaded, ports, saved)
        threading.Thread(target=worker, daemon=True).start()

    def _on_loaded(self, ports: list[DisplayPort], saved: list[int] | None) -> None:
        """Handle loaded data on main thread"""
        self.ports = ports

        # Show driver info
        driver_ver = get_driver_version()
        active_count = len([p for p in ports if p.status == PortStatus.CONNECTED])
        self.info_banner.set_title(
            f"NVIDIA Driver v{driver_ver} — {active_count} active display(s)"
        )
        self.info_banner.set_revealed(True)

        # Restore saved value (use first non-zero value from config)
        self._updating_scales = True
        if saved:
            # Find the highest saved value (they should all be the same)
            max_val = max(saved)
            pct = vibrance_to_percent(max_val)
            self.scale.set_value(pct)
            self.raw_scale.set_value(max_val)
            self.status_label.set_label(f"Config loaded — {pct}%")
        else:
            # Read current value from connected port
            for port in ports:
                if port.status == PortStatus.CONNECTED and port.current_vibrance > 0:
                    pct = vibrance_to_percent(port.current_vibrance)
                    self.scale.set_value(pct)
                    self.raw_scale.set_value(port.current_vibrance)
                    break
            else:
                self.scale.set_value(0)
                self.raw_scale.set_value(0)
            self.status_label.set_label("Ready")
        self._updating_scales = False

        self._update_label(self.scale.get_value())
        self._update_raw_label(self.raw_scale.get_value())
        return False

    # ─── Event Handlers ──────────────────────────────────────────────────

    def _on_scale_changed(self, scale: Gtk.Scale) -> None:
        pct = scale.get_value()
        self._update_label(pct)
        if not self._updating_scales:
            self._updating_scales = True
            raw = percent_to_vibrance(int(pct))
            self.raw_scale.set_value(raw)
            self._update_raw_label(raw)
            self._updating_scales = False

    def _on_raw_scale_changed(self, scale: Gtk.Scale) -> None:
        raw = scale.get_value()
        self._update_raw_label(raw)
        if not self._updating_scales:
            self._updating_scales = True
            pct = vibrance_to_percent(int(raw))
            self.scale.set_value(pct)
            self._update_label(pct)
            self._updating_scales = False

    def _update_label(self, pct: float) -> None:
        """Update the percentage display"""
        self.percent_label.set_label(f"{int(pct)}%")
        if pct > 0:
            self.percent_label.remove_css_class("dim-label")
            self.percent_label.add_css_class("success")
        else:
            self.percent_label.remove_css_class("success")
            self.percent_label.add_css_class("dim-label")

    def _update_raw_label(self, raw: float) -> None:
        """Update the raw value display"""
        self.raw_label.set_label(f"{int(raw)}")
        if raw > 0:
            self.raw_label.remove_css_class("dim-label")
            self.raw_label.add_css_class("success")
        else:
            self.raw_label.remove_css_class("success")
            self.raw_label.add_css_class("dim-label")

    def _on_preset(self, _btn: Gtk.Button, pct: int) -> None:
        self.scale.set_value(pct)

    def _on_refresh(self, _btn: Gtk.Button) -> None:
        self._build_ui()

    def _on_apply(self, _btn: Gtk.Button) -> None:
        pct = int(self.scale.get_value())
        raw = int(self.raw_scale.get_value())

        # Build values for all ports (same value)
        port_count = len(self.ports) if self.ports else 5
        values = [raw] * port_count

        self.status_label.set_label("Applying & Saving config...")

        def worker():
            success, output = apply_vibrance(values)
            if success:
                save_config(values)
                update_systemd_service(raw, port_count)
            GLib.idle_add(self._on_apply_done, success, pct)
        threading.Thread(target=worker, daemon=True).start()

    def _on_apply_done(self, success: bool, pct: int) -> None:
        if success:
            self.status_label.set_label(f"✓ Applied {pct}%")
        else:
            self.status_label.set_label("✗ Failed — check terminal for details")
        return False

    def _on_reset(self, _btn: Gtk.Button) -> None:
        self.scale.set_value(0)
        self.raw_scale.set_value(0)
        self.status_label.set_label("Reset to 0% — click Apply to confirm")

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
