# NVibrant GUI

> GTK4/Adwaita GUI for controlling **NVIDIA Digital Vibrance** per display output on Wayland.

A graphical frontend for [nvibrant](https://github.com/Tremeschin/nvibrant) — configure digital vibrance (color saturation) on each physical GPU port independently, without needing X11 or `nvidia-settings`.

## ✨ Features

- **Per-port vibrance control** — Individual sliders (0%–200%) for each GPU display output (DP, HDMI)
- **Auto-detect** — Automatically detects connected/disconnected displays
- **Quick presets** — One-click buttons for 50%, 100%, 125%, 150%, 200%
- **Setup wizard** — If `nvibrant` isn't installed, offers one-click install via `pip` or clone
- **Driver info** — Shows current NVIDIA driver version and active display count
- **Native look** — Built with GTK4 + Libadwaita, follows your system theme

## 📁 Project Structure

```
Nvibrant-GUI/
├── nvibrant_gui/              # Python package
│   ├── __init__.py            # Package metadata & version
│   ├── __main__.py            # Entry point (python -m nvibrant_gui)
│   ├── core/                  # Backend logic
│   │   ├── __init__.py
│   │   ├── constants.py       # Types, enums, constants
│   │   └── backend.py         # nvibrant CLI interaction
│   ├── ui/                    # GTK4 widgets
│   │   ├── __init__.py
│   │   ├── window.py          # Main application window
│   │   └── port_row.py        # Per-port slider widget
│   └── data/                  # Desktop entry & resources
│       ├── __init__.py
│       └── nvibrant-gui.desktop
├── scripts/
│   ├── install.sh             # Install script
│   └── uninstall.sh           # Uninstall script
├── pyproject.toml             # Python package config
└── README.md
```

## 📦 Requirements

- **Python** ≥ 3.10
- **GTK4** + **Libadwaita** (`libadwaita-1`, `python3-gi`)
- **NVIDIA proprietary driver** with `nvidia_drm.modeset=1`
- **uvx** (recommended) or **pip** to run `nvibrant`

### Arch Linux

```bash
sudo pacman -S python-gobject gtk4 libadwaita
```

### Fedora

```bash
sudo dnf install python3-gobject gtk4 libadwaita
```

### Ubuntu/Debian

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-dev
```

## 🚀 Install

```bash
git clone https://github.com/your-user/Nvibrant-GUI.git
cd Nvibrant-GUI

# One-liner install (package + .desktop entry)
bash scripts/install.sh
```

After installation:
- Run from terminal: `nvibrant-gui`
- Or find **NVibrant** in your application launcher

## 🗑️ Uninstall

```bash
bash scripts/uninstall.sh
```

## 🖥️ Usage

1. Launch the app → it auto-detects all GPU display outputs
2. Connected displays show a **slider** (0%–200%) and **preset buttons**
3. Adjust vibrance per port as desired
4. Click **Apply** to send settings via `nvibrant`
5. Click **Reset All** to return all sliders to 100% (default)

| Percentage | Raw Value | Effect |
|:---:|:---:|:---|
| 0% | -1024 | Grayscale |
| 100% | 0 | Default (no change) |
| 200% | 1023 | Maximum saturation |

## 🔄 Dev / Run without install

```bash
cd Nvibrant-GUI
python3 -m nvibrant_gui
```

## 📜 License

GPL-3.0-or-later — Same license as [nvibrant](https://github.com/Tremeschin/nvibrant).

## 🙏 Credits

- [Tremeschin/nvibrant](https://github.com/Tremeschin/nvibrant) — The CLI backend that makes this possible
