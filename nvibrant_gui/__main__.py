"""
Application entry point — NVibrant GUI.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import sys
from gi.repository import Adw

from nvibrant_gui import __app_id__
from nvibrant_gui.ui.window import NVibrantWindow


class NVibrantApp(Adw.Application):
    """Main GTK Application"""

    def __init__(self):
        super().__init__(application_id=__app_id__)

    def do_activate(self) -> None:
        win = NVibrantWindow(self)
        win.present()


def main() -> None:
    app = NVibrantApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
