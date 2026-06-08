import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw
import sys

class NVibrantApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.test.app')

    def do_activate(self):
        win = Adw.ApplicationWindow(application=self)
        win.present()
        print("Window presented. You can close it now.", flush=True)

app = NVibrantApp()
sys.exit(app.run(sys.argv))
