"""Build docs/report/Connect_Report.pdf from report.md, the ADRs and the Mermaid diagram sources.

Usage (from the repository root):
    pip install markdown
    python docs/report/build.py

Needs Google Chrome (or Chromium) for headless PDF printing. Mermaid is downloaded
once into docs/report/.vendor/ (git-ignored).
"""

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE / "report.md"
OUT_HTML = HERE / "report.html"
OUT_PDF = HERE / "Connect_Report.pdf"
VENDOR = HERE / ".vendor"
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"

CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
]


def include_files(text: str) -> str:
    """Replace <!-- include: path --> with the file, demoting its headings by two levels."""

    def repl(m: re.Match) -> str:
        body = (HERE / m.group(1)).read_text()
        return re.sub(r"^(#{1,4}) ", lambda h: "#" * (len(h.group(1)) + 2) + " ", body, flags=re.M)

    return re.sub(r"<!--\s*include:\s*(\S+)\s*-->", repl, text)


def embed_diagrams(body_html: str) -> str:
    """Turn <img src="...mmd"> into a Mermaid figure built from the diagram source file."""

    def repl(m: re.Match) -> str:
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        src = (HERE / html.unescape(attrs["src"])).resolve()
        name = src.stem
        code = html.escape(src.read_text())
        caption = attrs.get("alt", name)
        cls = "diagram landscape" if attrs.get("title") == "landscape" else "diagram"
        return (
            f'<figure class="{cls}" id="fig-{name}">'
            f'<pre class="mermaid">{code}</pre>'
            f"<figcaption>{caption} <span class=\"src\">(source: docs/diagrams/{src.name})</span></figcaption>"
            f"</figure>"
        )

    body_html = re.sub(r"<p>\s*(<img [^>]*src=\"[^\"]+\.mmd\"[^>]*>)\s*</p>", r"\1", body_html)
    return re.sub(r"<img [^>]*src=\"[^\"]+\.mmd\"[^>]*/?>", repl, body_html)


def mermaid_js() -> Path:
    VENDOR.mkdir(exist_ok=True)
    path = VENDOR / "mermaid.min.js"
    if not path.exists():
        print("Downloading Mermaid ...")
        urllib.request.urlretrieve(MERMAID_URL, path)
    return path


def chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    sys.exit("Chrome/Chromium not found; set the CHROME environment variable.")


def main() -> None:
    text = include_files(SRC.read_text())
    md = markdown.Markdown(
        extensions=["extra", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "1-2", "title": "Contents"}},
    )
    body = embed_diagrams(md.convert(text))
    # Keep requirement IDs (FR-COM-1, NFR-10, US-3, ...) on one line in table cells.
    body = re.sub(r"<td>((?:[A-Z]{1,5}-){1,2}[A-Z0-9]{1,4})</td>", r'<td class="id">\1</td>', body)
    css = (HERE / "report.css").read_text()
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Connect — AI1220 Assignment 1 report</title>
<style>{css}</style>
<script src="{mermaid_js().relative_to(HERE)}"></script>
</head><body>
{body}
<script>
mermaid.initialize({{
  startOnLoad: false, theme: "default", securityLevel: "loose",
  fontFamily: "Helvetica, Arial, sans-serif",
  flowchart: {{ htmlLabels: true, curve: "basis", nodeSpacing: 30, rankSpacing: 45 }},
  sequence: {{ mirrorActors: false, useMaxWidth: true, wrap: false }},
  er: {{ useMaxWidth: true }}
}});
mermaid.run().then(() => {{ document.body.dataset.ready = "1"; }});
</script>
</body></html>"""
    OUT_HTML.write_text(page)

    # Chrome prints to a temp file first; copying it ourselves avoids macOS
    # protected-folder attributes that can make Chrome-written files unreadable.
    tmp_pdf = Path(tempfile.mkdtemp()) / "Connect_Report.pdf"
    subprocess.run(
        [
            chrome(),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--allow-file-access-from-files",
            "--virtual-time-budget=30000",
            f"--print-to-pdf={tmp_pdf}",
            OUT_HTML.as_uri(),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    OUT_PDF.unlink(missing_ok=True)
    OUT_PDF.write_bytes(tmp_pdf.read_bytes())
    print(f"Wrote {OUT_PDF.relative_to(HERE.parents[1])}")


if __name__ == "__main__":
    main()
