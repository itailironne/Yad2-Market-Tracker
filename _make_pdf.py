"""Generate README.pdf from README.md using xhtml2pdf (pure Python)."""
import os
import markdown2
from xhtml2pdf import pisa

DIR = os.path.dirname(os.path.abspath(__file__))
md_path  = os.path.join(DIR, "README.md")
pdf_path = os.path.join(DIR, "README.pdf")

# If the existing PDF is locked, write to a sibling file
try:
    open(pdf_path, "ab").close()
except PermissionError:
    pdf_path = os.path.join(DIR, "README_new.pdf")
    print("README.pdf is locked — writing to README_new.pdf instead.")

with open(md_path, encoding="utf-8") as f:
    md = f.read()

html_body = markdown2.markdown(md, extras=[
    "fenced-code-blocks", "tables", "header-ids", "code-friendly", "strike"
])

style = """
@page { size: A4; margin: 22mm 18mm 20mm 18mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.5; color: #0f172a; }
h1 { font-size: 22pt; font-weight: bold; color: #0f172a; margin: 0 0 8pt; border-bottom: 2pt solid #2563eb; padding-bottom: 6pt; }
h2 { font-size: 15pt; font-weight: bold; color: #1e293b; margin-top: 18pt; margin-bottom: 6pt; border-bottom: 1pt solid #cbd5e1; padding-bottom: 4pt; }
h3 { font-size: 12pt; font-weight: bold; color: #1e40af; margin-top: 14pt; margin-bottom: 4pt; }
p  { margin: 5pt 0; }
hr { border: 0; border-top: 1pt solid #e2e8f0; margin: 12pt 0; }
code { background-color: #f1f5f9; padding: 1pt 4pt; font-family: 'Courier New', monospace; font-size: 9pt; color: #1e40af; }
pre  { background-color: #1e293b; color: #f1f5f9; padding: 10pt 12pt; font-family: 'Courier New', monospace; font-size: 9pt; line-height: 1.4; }
pre code { background: none; color: #f1f5f9; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9pt; }
th { background-color: #f1f5f9; color: #0f172a; font-weight: bold; padding: 6pt 8pt; text-align: left; border: 1pt solid #cbd5e1; }
td { padding: 5pt 8pt; border: 1pt solid #e2e8f0; vertical-align: top; }
ul, ol { padding-left: 16pt; margin: 4pt 0; }
li { margin: 2pt 0; }
strong, b { font-weight: bold; color: #0f172a; }
a { color: #2563eb; text-decoration: none; }
"""

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{style}</style></head>
<body>{html_body}</body></html>"""

with open(pdf_path, "wb") as f:
    err = pisa.CreatePDF(html, dest=f, encoding="utf-8")

if err.err:
    print("PDF generation FAILED")
else:
    print(f"wrote {pdf_path}")
