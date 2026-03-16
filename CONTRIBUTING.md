# Contributing to SORTR

Contributions are welcome — bug reports, fixes, and small improvements.

## Reporting Bugs

Open an issue and include your OS, Python version, steps to reproduce,
and any error messages from the terminal.

## Making Changes

```bash
git clone https://github.com/your-username/sortr.git
cd sortr
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Keep pull requests focused on a single change. Make sure `python app.py` still
works before opening a PR.

## Code Style

- Python: PEP 8, 4-space indentation.
- JS/HTML: vanilla JS, `const`/`let`, stay consistent with the existing style.
