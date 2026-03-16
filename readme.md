# SORTR — Image Organizer (Desktop Photo Sorting App)

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.x-green)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#-pre-built-executables)

SORTR is a lightweight, keyboard-driven desktop image organizer for sorting large collections of photos and screenshots.
Scan a folder, triage each image one by one (move / delete / skip), preview every pending change,
then apply them all in a single batch — **nothing is touched until you confirm**.

---

## Table of Contents

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Pre-built Executables](#-pre-built-executables)
- [Running from Source](#-running-from-source)
- [Usage Guide](#-usage-guide)
- [Keyboard Shortcuts](#-keyboard-shortcuts)
- [Customising Folders](#-customising-folders)
- [Supported Image Formats](#-supported-image-formats)
- [Building Executables](#-building-executables)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

- **Recursive scanning** — finds all images in a directory tree automatically.
- **Keyboard-first workflow** — press your configured folder keys to move, `D` to delete, `S` to skip, `Z` to undo.
- **Non-destructive staging** — changes are recorded but never applied until you click **RUN**.
- **Review screen** — see a full summary (with counts) before committing any changes.
- **Collision-safe moves** — files are renamed with a numeric suffix if a name clash occurs.
- **Configurable destinations** — folder templates are editable in the UI and persisted across app restarts.
- **Standalone executables** — single-file binaries for Windows, macOS, and Linux; no Python required.
- **Responsive UI** — works on laptop screens and large monitors.

---

## 📸 Screenshots

> _Add screenshots of the Setup, Sort, Review, and Results screens here._

---

## 📦 Pre-built Executables

Download the latest release for your platform from the
[Releases](../../releases) page.

| Platform | File | Notes |
|---|---|---|
| Windows | `sortr-windows.exe` | Double-click to run; opens a native desktop window |
| macOS | `SORTR.app` | Drag to Applications; Universal Binary (Intel + Apple Silicon) |
| Linux | `sortr-linux` | `chmod +x sortr-linux && ./sortr-linux` |

All executables are **fully self-contained** — no Python, no Flask, no additional installs required.

---

## 🚀 Running from Source

### Prerequisites

- Python **3.9** or newer
- pip

### Install

```bash
# Clone the repository
git clone https://github.com/your-username/sortr.git
cd sortr

# (Recommended) create an isolated virtual environment
python -m venv .venv

# Activate — Windows
.venv\Scripts\activate
# Activate — macOS / Linux
source .venv/bin/activate

# Install runtime dependencies
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Then open **http://127.0.0.1:5050** in any modern browser.
When the server starts it prints the exact URL to the terminal.

---

## 🖱️ Usage Guide

### 1 — Setup

1. Enter the **Source Directory** — the folder containing images to sort
   (e.g. `C:\Users\you\Downloads` or `/home/you/Pictures/Unsorted`).
2. Enter the **Destination Parent Directory** — the root folder where sorted
   sub-folders will be created (e.g. `~/Pictures`).
   The default is your system's `Pictures` directory.
3. Click **SCAN**. SORTR recursively finds every supported image and lists
   the destination folders that will be created under the parent.

### 2 — Sort

Each image is displayed full-screen. For each one:

| What you want | How to do it |
|---|---|
| Move to a folder | Press the folder key shown in the panel |
| Delete the image | Press `D` |
| Leave it in place | Press `S` (skip) |
| Change your mind | Press `Z` (undo last decision) |

A progress bar and counter track how many images remain.

### 3 — Review

Click **REVIEW →** (or finish the last image) to see the full list of pending changes.

- A stat card shows totals for moves, deletes, skips, and undecided images.
- Every file is listed with its intended action and destination.
- Use **← KEEP SORTING** to go back and continue triaging.

### 4 — Apply

Click **▶ RUN — APPLY CHANGES** to execute all moves and deletions at once.
The results screen shows exactly how many files were moved, deleted, skipped, or errored.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|---|---|
| Configured folder keys | Move current image to the matching folder |
| `D` | Mark current image for deletion |
| `S` | Skip (leave in place) |
| `Z` | Undo last decision and step back |

Keyboard shortcuts are active only on the **Sort** screen and are ignored when a text input has focus.

---

## 🗂️ Customising Folders

Folder types are editable directly in the **Setup** screen:

1. Use **Edit Folder Types** to add/remove rows and change each key + label.
2. Click **Save Folder Types** to persist your template list.
3. You can also scan immediately; the active template list is saved with the scan.

Keys must be single characters and unique. Sub-folders are created automatically
under the destination parent the first time a file is moved there.

Saved templates are stored in your user profile at:

- Windows: `C:\Users\<you>\.sortr\folders.json`
- macOS/Linux: `~/.sortr/folders.json`

---

## 🖼️ Supported Image Formats

`JPG` · `JPEG` · `PNG` · `GIF` · `BMP` · `WEBP` · `TIFF` · `TIF`
`SVG` · `ICO` · `HEIC` · `HEIF` · `RAW` · `CR2` · `NEF` · `ARW` · `DNG` · `AVIF`

> **Note:** RAW formats (CR2, NEF, ARW, DNG) are recognised and moved/deleted correctly,
> but browser preview may not render them.

---

## 🔨 Building Executables

Build scripts are in the `build/` directory. Each script:

1. Creates (or reuses) a virtual environment with all dependencies.
2. Runs PyInstaller with the `sortr.spec` spec file.
3. Outputs the final binary into `dist/`.

### Windows

```bat
build\build_windows.bat
```

Output: `dist\sortr-windows.exe`

### macOS

```bash
bash build/build_macos.sh
```

Output: `dist/SORTR.app` (Universal Binary — runs natively on both Intel and Apple Silicon).

> **Notarisation:** to distribute outside the App Store, sign and notarise with
> `codesign` and `xcrun notarytool` after building.

### Linux

```bash
bash build/build_linux.sh
```

Output: `dist/sortr-linux` (single ELF binary).

### Prerequisites for building

```bash
pip install pyinstaller
# or install all dev dependencies:
pip install -r requirements.txt
```

### How the bundle works

`sortr.spec` instructs PyInstaller to:

- Include `index.html` as a bundled data file.
- Hide-import all Flask/Werkzeug/Jinja2 sub-modules that static analysis can miss.
- Enable UPX compression (if installed) to reduce binary size.
- On macOS, produce a `.app` bundle with proper `Info.plist` metadata.

At runtime, `app.py` detects `sys.frozen` and uses `sys._MEIPASS` to locate
the bundled `index.html`, then opens the default browser automatically.

---

## 📁 Project Structure

```
sortr/
├── app.py              # Flask backend — all API routes and file operations
├── index.html          # Single-page frontend (Jinja2 template + vanilla JS)
├── sortr.spec          # PyInstaller build specification
├── requirements.txt    # Python runtime + build dependencies
├── .gitignore
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── build/
    ├── build_windows.bat   # Windows build script
    ├── build_linux.sh      # Linux build script
    └── build_macos.sh      # macOS build script
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on
how to report bugs, suggest features, and submit pull requests.

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

