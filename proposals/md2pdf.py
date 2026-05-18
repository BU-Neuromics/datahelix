"""Convert biodms2026-project-talk.md to PDF.

Strips the internal "Notes for the user" trailing section before rendering,
since that is drafting scaffolding rather than submission content.
"""

import re
import sys
from pathlib import Path

import markdown
from weasyprint import CSS, HTML

HERE = Path(__file__).parent
MD = HERE / "biodms2026-project-talk.md"
PDF = HERE / "biodms2026-project-talk.pdf"

CSS_STYLE = """
@page {
  size: letter;
  margin: 0.7in 0.75in 0.85in 0.75in;
  @bottom-center {
    content: counter(page) " of " counter(pages);
    font-family: "Helvetica", "Arial", sans-serif;
    font-size: 9pt;
    color: #555;
  }
}
html { font-size: 10pt; }
body {
  font-family: "Georgia", "Times New Roman", serif;
  line-height: 1.28;
  color: #111;
  text-align: justify;
  hyphens: auto;
}
h1 {
  font-family: "Helvetica", "Arial", sans-serif;
  font-size: 15pt;
  line-height: 1.2;
  margin: 0 0 0.25em 0;
  text-align: left;
}
h2 {
  font-family: "Helvetica", "Arial", sans-serif;
  font-size: 12pt;
  margin: 0.85em 0 0.25em 0;
  text-align: left;
  page-break-after: avoid;
}
h3 {
  font-family: "Helvetica", "Arial", sans-serif;
  font-size: 10.5pt;
  margin: 0.7em 0 0.2em 0;
  text-align: left;
  page-break-after: avoid;
}
p { margin: 0 0 0.4em 0; }
ul, ol { margin: 0 0 0.4em 1.1em; padding: 0; }
li { margin-bottom: 0.15em; }
em { font-style: italic; }
strong { font-weight: 600; }
code {
  font-family: "Menlo", "Consolas", monospace;
  font-size: 0.92em;
  background: #f4f4f4;
  padding: 1px 3px;
  border-radius: 2px;
}
table {
  border-collapse: collapse;
  margin: 0.5em 0;
  font-size: 9.5pt;
}
th, td { border: 1px solid #bbb; padding: 4px 7px; text-align: left; }
th { background: #efefef; }
hr { border: none; border-top: 1px solid #bbb; margin: 1em 0; }
.author {
  font-family: "Helvetica", "Arial", sans-serif;
  font-size: 10pt;
  color: #333;
  margin-bottom: 0.2em;
}
"""


def strip_internal_notes(md_text: str) -> str:
    # Remove everything from the "Notes for the user" section to end of file.
    return re.split(r"\n---\s*\n+### Notes for the user", md_text, maxsplit=1)[0].rstrip() + "\n"


def main() -> int:
    md_text = strip_internal_notes(MD.read_text())
    html_body = markdown.markdown(
        md_text,
        extensions=["extra", "tables", "smarty", "sane_lists"],
    )
    html_doc = f"<!doctype html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
    HTML(string=html_doc, base_url=str(HERE)).write_pdf(
        PDF, stylesheets=[CSS(string=CSS_STYLE)]
    )
    print(f"Wrote {PDF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
