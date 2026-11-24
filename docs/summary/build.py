"""Build docs/summary.pdf. Run from the repository root: python docs/summary/build.py

Needs `pip install markdown` and Google Chrome; reuses the helpers of the Assignment 1 report.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "report"))
import build as report  # noqa: E402

report.HERE = HERE
CSS = """
@page { size: A4; margin: 10mm }
body { font: 9.5pt/1.3 Helvetica, Arial, sans-serif }
h1 { font-size: 16pt; margin: 0 } h2 { font-size: 11.5pt; margin: 6pt 0 3pt }
table { border-collapse: collapse; width: 100% } td, th { border: 1px solid #bbb; padding: 2.5pt 4pt; text-align: left }
.page { break-before: page } figure { margin: 0; text-align: center } figcaption { display: none }
pre { margin: 0 } svg { max-width: 100% !important }
#fig-c4-container svg { max-height: 75mm } #fig-c4-component-api svg { max-height: 180mm; width: 188mm }
#fig-erd-people svg, #fig-erd-content svg { width: 188mm; height: 72mm }
#fig-erd-collaboration, #fig-erd-messaging { display: inline-block; width: 49% }
#fig-erd-collaboration svg, #fig-erd-messaging svg { height: 34mm }
#fig-erd-moderation svg { width: 188mm; height: 70mm }
"""


def keys_only(body: str) -> str:
    """Leave out plain columns of the embedded ER diagrams so that they stay legible on one page."""
    return re.sub(r"^    \w+ \w+(?: +&quot;nullable&quot;)?\n", "", body, flags=re.M)


def main() -> None:
    """Render Markdown and diagrams to one PDF."""
    body = report.embed_diagrams(
        markdown.markdown((HERE / "summary.md").read_text(), extensions=["extra"])
    )
    body = keys_only(body)
    page = HERE / "summary.html"
    page.write_text(f"""<!doctype html><meta charset="utf-8"><title>Connect summary</title><style>{CSS}</style>
<script src="{report.mermaid_js().as_uri()}"></script>{body}
<script>mermaid.initialize({{startOnLoad:false, securityLevel:"loose", flowchart:{{nodeSpacing:20, rankSpacing:28}}}});
mermaid.run()</script>""")
    # Chrome prints to a temporary file because macOS protects files Chrome writes to the Desktop.
    pdf = Path(tempfile.mkdtemp()) / "summary.pdf"
    subprocess.run(
        [
            report.chrome(), "--headless=new", "--no-pdf-header-footer", "--allow-file-access-from-files",
            "--virtual-time-budget=30000", f"--print-to-pdf={pdf}", page.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    (HERE.parent / "summary.pdf").write_bytes(pdf.read_bytes())


if __name__ == "__main__":
    main()
