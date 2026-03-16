"""
SORTR — Image Organizer
=======================
A Flask-based web application that lets users scan a directory of images,
decide per-image whether to move, delete, or skip each one, preview all
pending changes, and finally apply them in a single batch operation.

All file operations are performed only when the user confirms via the
"RUN" step, so nothing is destructive until explicitly issued.

Usage (development):
    python app.py
    # Then open http://127.0.0.1:5050 in a browser.

Usage (standalone executable built with PyInstaller):
    ./sortr   (or sortr.exe on Windows)
    # The app opens a browser window automatically.
"""

import os
import sys
import json
import shutil
import socket
import threading
import webbrowser
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_file, render_template

try:
    import webview
except Exception:
    webview = None

# ── Version ──────────────────────────────────────────────────────────────────
__version__ = "1.0.0"


def get_resource_path(relative_path: str) -> str:
    """
    Return the absolute path to a bundled resource file.

    When running as a PyInstaller one-file executable, all data files are
    extracted to a temporary directory stored in ``sys._MEIPASS``.  During
    normal development ``__file__`` is used as the base instead.
    """
    if getattr(sys, "frozen", False):
        # Running inside a PyInstaller bundle
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


# Point Flask at the directory that contains index.html.  This works for both
# the normal development run and the frozen executable bundle.
app = Flask(__name__, template_folder=get_resource_path("."))

# ── Destination folders config ──────────────────────────────────────────────
# Folder templates are user-editable and persisted to disk.
DEFAULT_FOLDER_TEMPLATES = [
    {"key": "1", "label": "Work"},
    {"key": "2", "label": "Personal"},
    {"key": "3", "label": "Projects"},
    {"key": "4", "label": "Reference"},
    {"key": "5", "label": "Archive"},
    {"key": "6", "label": "Receipts"},
    {"key": "7", "label": "Other"},
]

CONFIG_DIR = Path.home() / ".sortr"
FOLDER_TEMPLATES_FILE = CONFIG_DIR / "folders.json"

# Default destination parent used when the user has not yet supplied one.
DEFAULT_DEST_PARENT = str(Path.home() / "Pictures")

# Full set of recognised image file extensions (lower-case).
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".tiff", ".tif", ".svg", ".ico", ".heic", ".heif",
    ".raw", ".cr2", ".nef", ".arw", ".dng", ".avif",
}


def normalize_folder_templates(raw_templates) -> list:
    """
    Validate and normalize a folder template list.

    Each template must be a dict containing:
      ``key``   — single-character shortcut
      ``label`` — destination folder label
    """
    if not isinstance(raw_templates, list):
        raise ValueError("Folder templates must be a list")
    if not raw_templates:
        raise ValueError("At least one destination folder is required")

    normalized = []
    seen_keys = set()

    for entry in raw_templates:
        if not isinstance(entry, dict):
            raise ValueError("Each folder template must be an object")

        key = str(entry.get("key", "")).strip()
        label = str(entry.get("label", "")).strip()

        if len(key) != 1:
            raise ValueError("Each folder key must be exactly 1 character")
        key_norm = key.lower()
        if key_norm in seen_keys:
            raise ValueError(f"Duplicate folder key: {key}")
        if not label:
            raise ValueError("Folder labels cannot be empty")

        seen_keys.add(key_norm)
        normalized.append({"key": key, "label": label})

    return normalized


def load_folder_templates() -> list:
    """Load persisted folder templates, or fall back to defaults."""
    if not FOLDER_TEMPLATES_FILE.exists():
        return DEFAULT_FOLDER_TEMPLATES.copy()

    try:
        data = json.loads(FOLDER_TEMPLATES_FILE.read_text(encoding="utf-8"))
        return normalize_folder_templates(data)
    except Exception:
        return DEFAULT_FOLDER_TEMPLATES.copy()


def save_folder_templates(templates: list) -> None:
    """Persist folder templates to the local user config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    FOLDER_TEMPLATES_FILE.write_text(
        json.dumps(templates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


folder_templates = load_folder_templates()

# ── In-memory session state ─────────────────────────────────────────────────
# A single global dict holds all runtime state for the current sorting session.
# Because this is a local single-user tool there is no need for proper session
# management or a database — state is reset when a new scan is started or after
# the user applies changes.
session_state = {
    "source_dir": None,
    "images": [],
    "current_index": 0,
    "destination_parent": None,
    "folder_templates": [],
    "folders": [],
    # Maps relative file path → decision dict:
    #   {"action": "move", "dest_label": str, "dest_path": str}
    #   {"action": "delete"}
    #   {"action": "skip"}
    "decisions": {},
}


def expand(path: str) -> str:
    """Expand ``~`` and resolve symlinks / relative segments in *path*."""
    return str(Path(path).expanduser().resolve())


def compute_destination_folders(parent_dir: str, templates: Optional[list] = None) -> list:
    """
    Build a list of destination folder descriptors from the active templates
    config, rooted at *parent_dir*.

    Each returned dict contains:
      ``key``   — keyboard shortcut string
      ``label`` — human-readable folder name
      ``path``  — absolute filesystem path
    """
    root = expand(parent_dir)
    active_templates = templates if templates is not None else folder_templates
    return [
        {
            "key": folder["key"],
            "label": folder["label"],
            "path": os.path.join(root, folder["label"]),
        }
        for folder in active_templates
    ]


def get_active_folder_templates() -> list:
    """Return session templates when available, otherwise persisted templates."""
    return session_state["folder_templates"] or folder_templates


def get_active_folders() -> list:
    """Return the current session's folder list, or the default if none set."""
    return session_state["folders"] or compute_destination_folders(
        DEFAULT_DEST_PARENT,
        get_active_folder_templates(),
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the single-page application shell (index.html)."""
    return render_template(
        "index.html",
        folders=get_active_folders(),
        folder_templates=get_active_folder_templates(),
        default_dest_parent=session_state["destination_parent"] or DEFAULT_DEST_PARENT,
    )


@app.route("/api/folders")
def get_folders():
    """Return the current destination folder list as JSON."""
    return jsonify({
        "folders": get_active_folders(),
        "templates": get_active_folder_templates(),
    })


@app.route("/api/folders", methods=["POST"])
def set_folders():
    """
    Update and persist the user-defined folder template list.

    Expected JSON body:
      ``folders`` — list of {"key": str, "label": str}
    """
    global folder_templates

    data = request.json or {}
    raw_templates = data.get("folders")
    if raw_templates is None:
        return jsonify({"error": "No folder list provided"}), 400

    try:
        normalized = normalize_folder_templates(raw_templates)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    folder_templates = normalized
    save_folder_templates(folder_templates)

    session_state["folder_templates"] = folder_templates.copy()
    active_parent = session_state["destination_parent"] or DEFAULT_DEST_PARENT
    session_state["folders"] = compute_destination_folders(active_parent, folder_templates)

    return jsonify({
        "templates": session_state["folder_templates"],
        "folders": session_state["folders"],
    })


@app.route("/api/scan", methods=["POST"])
def scan():
    """
    Recursively scan *directory* for image files and initialise a new session.

    Expected JSON body:
      ``directory``         — path to scan (required)
      ``destination_parent``— root for destination sub-folders (optional)
            ``folder_templates``  — list of key/label templates (optional)

    Returns JSON with the list of found image paths (relative to *directory*)
    and the resolved destination folder descriptors.
    """
    global folder_templates

    data = request.json or {}
    raw_dir = data.get("directory", "").strip()
    raw_dest_parent = data.get("destination_parent", "").strip() or DEFAULT_DEST_PARENT
    raw_templates = data.get("folder_templates")
    if not raw_dir:
        return jsonify({"error": "No directory provided"}), 400

    if raw_templates is not None:
        try:
            normalized = normalize_folder_templates(raw_templates)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        folder_templates = normalized
        save_folder_templates(folder_templates)

    source = expand(raw_dir)
    if not os.path.isdir(source):
        return jsonify({"error": f"Directory not found: {source}"}), 404

    # Walk the directory tree and collect all recognised image files.
    images = []
    for entry in sorted(Path(source).rglob("*")):
        if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS:
            # Store paths relative to source so they're portable across
            # systems and safe to display in the browser.
            images.append(str(entry.relative_to(source)))

    if not images:
        return jsonify({"error": "No images found in that directory"}), 404

    # Reset all session state for the new scan.
    session_state["source_dir"] = source
    session_state["images"] = images
    session_state["current_index"] = 0
    session_state["destination_parent"] = expand(raw_dest_parent)
    session_state["folder_templates"] = folder_templates.copy()
    session_state["folders"] = compute_destination_folders(raw_dest_parent, session_state["folder_templates"])
    session_state["decisions"] = {}

    return jsonify({
        "count": len(images),
        "images": images,
        "templates": session_state["folder_templates"],
        "folders": session_state["folders"],
    })


@app.route("/api/image/<int:index>")
def get_image(index: int):
    """
    Stream the image at position *index* in the current session's image list.

    The correct MIME type is inferred from the file extension so that the
    browser can render SVG, AVIF, and other non-JPEG formats correctly.
    """
    images = session_state["images"]
    source = session_state["source_dir"]
    if not images or index >= len(images):
        return jsonify({"error": "No image"}), 404

    path = os.path.join(source, images[index])
    ext = Path(path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".bmp": "image/bmp", ".webp": "image/webp",
        ".svg": "image/svg+xml", ".ico": "image/x-icon",
        ".tiff": "image/tiff", ".tif": "image/tiff",
        ".avif": "image/avif",
    }
    mime = mime_map.get(ext, "image/jpeg")
    return send_file(path, mimetype=mime)


@app.route("/api/decide", methods=["POST"])
def decide():
    """
    Record a sorting decision for the image at the given index.

    Expected JSON body:
      ``index``  — 0-based position in the image list
      ``action`` — one of ``"move"``, ``"delete"``, ``"skip"``
      ``dest``   — destination folder key (required when action is ``"move"``)

    Returns the next index and a ``done`` flag when all images are processed.
    """
    data = request.json
    index = data.get("index")
    action = data.get("action")   # "move" | "delete" | "skip"
    dest_key = data.get("dest")   # folder key, or None for non-move actions

    images = session_state["images"]
    if index is None or index >= len(images):
        return jsonify({"error": "Invalid index"}), 400

    file_path = images[index]
    active_folders = get_active_folders()

    if action == "move":
        folder = next((f for f in active_folders if f["key"] == dest_key), None)
        if not folder:
            return jsonify({"error": "Invalid folder"}), 400
        session_state["decisions"][file_path] = {
            "action": "move",
            "dest_label": folder["label"],
            "dest_path": folder["path"],
        }
    elif action == "delete":
        session_state["decisions"][file_path] = {"action": "delete"}
    elif action == "skip":
        session_state["decisions"][file_path] = {"action": "skip"}

    next_index = index + 1
    session_state["current_index"] = next_index
    done = next_index >= len(images)
    return jsonify({"next_index": next_index, "done": done})


@app.route("/api/review")
def review():
    """
    Return all recorded decisions plus any images not yet assigned a decision.

    The frontend uses this to populate the Review screen before the user
    confirms that changes should be applied.
    """
    decisions = session_state["decisions"]
    images = session_state["images"]
    # Identify images that the user navigated past without making a decision.
    undecided = [img for img in images if img not in decisions]
    return jsonify({
        "decisions": decisions,
        "undecided": undecided,
        "source_dir": session_state["source_dir"],
    })


@app.route("/api/run", methods=["POST"])
def run():
    """
    Apply all recorded decisions (move / delete) to the filesystem.

    This is the **only** route that mutates files on disk.  Files are only
    moved or deleted after the user explicitly clicks RUN on the Review screen.

    Collisions are resolved by appending a numeric suffix so existing files at
    the destination are never silently overwritten.

    Session state is cleared after a successful run so the user can start a
    fresh scan without restarting the server.
    """
    decisions = session_state["decisions"]
    source = session_state["source_dir"]
    results = {"moved": [], "deleted": [], "skipped": [], "errors": []}

    for file_path, decision in decisions.items():
        src = os.path.join(source, file_path)
        action = decision["action"]

        if action == "skip":
            results["skipped"].append(file_path)
            continue

        # Guard against files that were removed externally between scan and run.
        if not os.path.exists(src):
            results["errors"].append({"file": file_path, "reason": "Source file missing"})
            continue

        if action == "delete":
            try:
                os.remove(src)
                results["deleted"].append(file_path)
            except Exception as e:
                results["errors"].append({"file": file_path, "reason": str(e)})

        elif action == "move":
            dest_dir = decision["dest_path"]
            try:
                os.makedirs(dest_dir, exist_ok=True)
                base_name = os.path.basename(file_path)
                dest_file = os.path.join(dest_dir, base_name)
                # If a file with the same name already exists, append _1, _2, …
                if os.path.exists(dest_file):
                    base, ext = os.path.splitext(base_name)
                    counter = 1
                    while os.path.exists(dest_file):
                        dest_file = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                        counter += 1
                shutil.move(src, dest_file)
                results["moved"].append({"file": file_path, "to": decision["dest_label"]})
            except Exception as e:
                results["errors"].append({"file": file_path, "reason": str(e)})

    # Reset session so the interface returns cleanly to the setup screen.
    session_state["decisions"] = {}
    session_state["images"] = []
    session_state["source_dir"] = None
    session_state["current_index"] = 0
    session_state["destination_parent"] = None
    session_state["folder_templates"] = []
    session_state["folders"] = []

    return jsonify(results)


@app.route("/api/undo", methods=["POST"])
def undo():
    """
    Remove the decision for the most recently decided image and step back.

    This allows the user to change their mind without restarting the scan.
    Only one level of undo per call is supported; call repeatedly to step
    back further.
    """
    decisions = session_state["decisions"]
    images = session_state["images"]
    idx = session_state["current_index"]

    if idx > 0:
        prev_idx = idx - 1
        prev_file = images[prev_idx]
        # Remove whichever decision was made for the previous image (if any).
        decisions.pop(prev_file, None)
        session_state["current_index"] = prev_idx
        return jsonify({"index": prev_idx})
    return jsonify({"error": "Nothing to undo"}), 400


# ── Entry point ───────────────────────────────────────────────────────────────

def find_free_port(start: int = 5050, max_tries: int = 20) -> int:
    """
    Find a free TCP port on localhost, starting from *start*.

    Iterates up to *max_tries* consecutive ports until one is available.
    Raises ``RuntimeError`` if no free port is found within the range.
    """
    for port in range(start, start + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # connect_ex returns 0 only if the port is already in use.
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"Could not find a free port in range {start}–{start + max_tries - 1}")


if __name__ == "__main__":
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    if getattr(sys, "frozen", False):
        # ── Standalone executable mode (PyInstaller) ──────────────────────
        # Start the local Flask server in a background thread and show the UI
        # in a native desktop window (Electron-like UX) via pywebview.
        server = threading.Thread(
            target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
            daemon=True,
        )
        server.start()

        if webview is not None:
            webview.create_window("SORTR", url, width=1280, height=820)
            webview.start()
        else:
            # Fallback for environments where pywebview is unavailable.
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
            print("pywebview not available — opening default browser instead")
            server.join()
    else:
        # ── Development mode ──────────────────────────────────────────────
        print(f"SORTR v{__version__} — development server on {url}")
        app.run(debug=True, host="127.0.0.1", port=port)