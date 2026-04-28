"""
PortRow widget — slider control for a single display port.
"""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk

from nvibrant_gui.core.constants import DisplayPort, PortStatus, VIBRANCE_DEFAULT
from nvibrant_gui.core.backend import vibrance_to_percent, percent_to_vibrance


class PortRow(Gtk.Box):
    """A card with slider to control vibrance for one display port"""

    def __init__(self, port: DisplayPort):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.port = port
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        # Card frame
        frame = Gtk.Frame()
        frame.add_css_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_margin_top(16)
        inner.set_margin_bottom(16)

        # Header: port info + status
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        icon = Gtk.Image.new_from_icon_name("video-display-symbolic")
        icon.set_pixel_size(24)
        icon.add_css_class("dim-label")
        header.append(icon)

        label = Gtk.Label(label=f"Port {port.index} — {port.port_type}")
        label.set_xalign(0)
        label.add_css_class("heading")
        label.set_hexpand(True)
        header.append(label)

        status_label = Gtk.Label()
        if port.status == PortStatus.CONNECTED:
            status_label.set_label("● Connected")
            status_label.add_css_class("success")
        else:
            status_label.set_label("○ Disconnected")
            status_label.add_css_class("dim-label")
        header.append(status_label)

        inner.append(header)

        # Slider (connected ports only)
        if port.status == PortStatus.CONNECTED:
            slider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

            self.percent_label = Gtk.Label()
            self.percent_label.set_width_chars(5)
            self.percent_label.add_css_class("title-2")

            self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
            self.scale.set_hexpand(True)
            self.scale.set_draw_value(False)
            self.scale.add_mark(0, Gtk.PositionType.BOTTOM, "0%")
            self.scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
            self.scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")

            initial_pct = vibrance_to_percent(port.current_vibrance)
            self.scale.set_value(initial_pct)
            self._update_label(initial_pct)
            self.scale.connect("value-changed", self._on_scale_changed)

            slider_box.append(self.scale)
            slider_box.append(self.percent_label)
            inner.append(slider_box)

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
            inner.append(presets_box)
        else:
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
        if pct > 0:
            self.percent_label.remove_css_class("warning")
            self.percent_label.add_css_class("success")
        else:
            self.percent_label.remove_css_class("success")
            self.percent_label.remove_css_class("warning")

    def _on_scale_changed(self, scale: Gtk.Scale) -> None:
        self._update_label(scale.get_value())

    def _on_preset(self, _btn: Gtk.Button, pct: int) -> None:
        if self.scale:
            self.scale.set_value(pct)

    def get_vibrance(self) -> int:
        """Get current raw vibrance value from slider"""
        if self.scale:
            return percent_to_vibrance(int(self.scale.get_value()))
        return VIBRANCE_DEFAULT
