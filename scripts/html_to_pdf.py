#!/usr/bin/env python
"""
html_to_pdf.py — render the docs/ HTML documents to PDF.

Uses headless Chrome rather than a Python PDF library so the output is the
*same* rendering engine the documents were designed against: the CSS custom
properties, grid layout, and the `@media print` block in each file all apply
exactly as they do in the browser.

Usage
-----
    python scripts/html_to_pdf.py                 # render every doc
    python scripts/html_to_pdf.py rag-assessment  # render one

Requires Chrome or Edge on PATH or at a standard install location.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Documents that carry a print stylesheet and are worth having as PDFs.
RENDERABLE = ["rag-assessment", "migration-v3"]

_BROWSER_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]


def find_browser() -> Path:
    for candidate in _BROWSER_CANDIDATES:
        if candidate.exists():
            return candidate
    raise SystemExit(
        "No Chrome or Edge installation found.\n"
        "Install one, or add its path to _BROWSER_CANDIDATES in this script."
    )


def render(browser: Path, name: str) -> Path:
    source = DOCS / f"{name}.html"
    if not source.exists():
        raise SystemExit(f"Not found: {source}")

    target = DOCS / f"{name}.pdf"
    subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            # Give webfonts and layout time to settle before the snapshot.
            "--virtual-time-budget=8000",
            f"--print-to-pdf={target}",
            source.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    return target


def main() -> None:
    names = sys.argv[1:] or RENDERABLE
    browser = find_browser()
    print(f"Rendering with {browser.name}\n")

    for name in names:
        target = render(browser, name)
        size_kb = target.stat().st_size / 1024
        print(f"  {name}.html -> docs/{target.name}  ({size_kb:,.0f} KB)")

    print("\nDone.")


if __name__ == "__main__":
    main()
