# sortr.spec
# PyInstaller build specification for SORTR.
#
# Produces a single-file executable that includes:
#   - The Flask application (app.py)
#   - The HTML template (index.html) as a bundled data file
#   - All Flask / Werkzeug / Jinja2 dependencies
#
# Usage:
#   pyinstaller sortr.spec --noconfirm
#
# Cross-platform notes:
#   Windows : outputs  dist/sortr-windows.exe
#   macOS   : outputs  dist/SORTR.app  (run build/build_macos.sh for arch flags)
#   Linux   : outputs  dist/sortr-linux

import sys
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE

# ── Determine output name per platform ───────────────────────────────────────
if sys.platform == "win32":
    exe_name = "sortr-windows"
elif sys.platform == "darwin":
    exe_name = "SORTR"
else:
    exe_name = "sortr-linux"

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    # Bundle index.html into the root of the extraction directory so that
    # get_resource_path("index.html") resolves correctly at runtime.
    datas=[("index.html", ".")],
    # Modules that PyInstaller's static analysis can miss in Flask/Werkzeug.
    hiddenimports=[
        "flask",
        "flask.templating",
        "jinja2",
        "jinja2.ext",
        "webview",
        "webview.platforms.edgechromium",
        "werkzeug",
        "werkzeug.routing",
        "werkzeug.serving",
        "werkzeug.exceptions",
        "werkzeug.middleware.shared_data",
        "click",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy packages that are definitely not needed.
        "tkinter",
        "matplotlib",
        "numpy",
        "PIL",
        "scipy",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=exe_name,
    # Use a windowed app on Windows so the executable behaves like a desktop
    # application (no attached terminal window).
    console=False,
    # UPX compresses the binary (reduces size ~30-50%) when UPX is installed.
    upx=True,
    upx_exclude=[],
    # Single-file mode: everything is extracted to a temp dir at launch.
    onefile=True,
    # Version metadata (Windows PE header).
    version_file=None,
    # Icon files — add platform-specific icons here if desired:
    # icon="assets/icon.ico",  # Windows
    # icon="assets/icon.icns", # macOS
)

# ── macOS .app bundle ─────────────────────────────────────────────────────────
# BUNDLE is only meaningful on macOS; on other platforms it is a no-op.
app = BUNDLE(
    exe,
    name="SORTR.app",
    icon=None,
    bundle_identifier="com.sortr.app",
    info_plist={
        "CFBundleName": "SORTR",
        "CFBundleDisplayName": "SORTR",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        # Allow running on both Intel and Apple Silicon via Rosetta.
        "LSMinimumSystemVersion": "11.0",
    },
)
