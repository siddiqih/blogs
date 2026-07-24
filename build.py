#!/usr/bin/env python3
"""Render posts/*.md into a self-contained static site in site/.

No framework — one template, Medium-like typography, dark-mode aware,
mobile-first. Run `python3 build.py` (needs `pip install markdown`) and
commit the site/ output; Cloudflare Pages serves it with no build step.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
POSTS = ROOT / "posts"
SITE = ROOT / "site"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<style>
:root {{ --bg:#ffffff; --fg:#1a1a1a; --muted:#6b6b6b; --accent:#0f62fe; --code:#f4f4f4; --border:#e6e6e6; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#121212; --fg:#e8e8e8; --muted:#9a9a9a; --accent:#78a9ff; --code:#1e1e1e; --border:#2a2a2a; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg);
  font-family:Georgia,'Times New Roman',serif; font-size:1.125rem; line-height:1.75; }}
header.site {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  border-bottom:1px solid var(--border); padding:14px 20px; }}
header.site a {{ color:var(--fg); text-decoration:none; font-weight:700; letter-spacing:.02em; }}
header.site span {{ color:var(--muted); font-weight:400; }}
main {{ max-width:680px; margin:0 auto; padding:32px 20px 80px; }}
h1 {{ font-size:2rem; line-height:1.25; margin:0 0 .4em; }}
h2 {{ font-size:1.45rem; margin-top:2em; line-height:1.3; }}
h3 {{ font-size:1.15rem; margin-top:1.6em; }}
p, li {{ letter-spacing:.003em; }}
a {{ color:var(--accent); }}
blockquote {{ margin:1.5em 0; padding-left:1em; border-left:3px solid var(--fg);
  font-style:italic; color:var(--muted); }}
hr {{ border:none; border-top:1px solid var(--border); margin:2.5em 0; }}
code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.85em;
  background:var(--code); padding:.15em .35em; border-radius:4px; }}
pre {{ background:var(--code); border:1px solid var(--border); border-radius:8px;
  padding:16px; overflow-x:auto; line-height:1.5; }}
pre code {{ background:none; padding:0; font-size:.8em; }}
table {{ border-collapse:collapse; width:100%; font-size:.9em;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
th, td {{ border:1px solid var(--border); padding:8px 12px; text-align:left; }}
th {{ background:var(--code); }}
.byline {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  color:var(--muted); font-size:.9rem; margin-bottom:2.5em; }}
.card {{ display:block; border:1px solid var(--border); border-radius:12px;
  padding:20px 24px; margin:16px 0; text-decoration:none; color:var(--fg); }}
.card:hover {{ border-color:var(--accent); }}
.card h2 {{ margin:0 0 .3em; font-size:1.3rem; }}
.card p {{ margin:0; color:var(--muted); font-size:1rem; }}
footer {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  color:var(--muted); font-size:.85rem; text-align:center; padding:24px;
  border-top:1px solid var(--border); }}
</style>
</head>
<body>
<header class="site"><a href="index.html">Engineering Notes</a> <span>· MarketingOrchestration.io</span></header>
<main>
{body}
</main>
<footer>© 2026 Hassan Siddiqi · MarketingOrchestration.io · <a href="https://github.com/siddiqih/blogs">source</a></footer>
</body>
</html>
"""

BYLINE = '<p class="byline">Hassan Siddiqi · July 2026 · Field notes from building Helix</p>'


def first_paragraph(md_text: str) -> str:
    for line in md_text.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "*", ">", "-", "!", "```")):
            return re.sub(r"[*_`\[\]]", "", line)[:180]
    return ""


def render(md_text: str) -> str:
    # Cross-links between posts: .md → .html
    md_text = re.sub(r"\(([\w\-]+)\.md\)", r"(\1.html)", md_text)
    return markdown.markdown(md_text, extensions=["tables", "fenced_code"])


def main() -> None:
    SITE.mkdir(exist_ok=True)
    entries = []
    for path in sorted(POSTS.glob("*.md")):
        text = path.read_text()
        title = next(
            (ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")),
            path.stem,
        )
        desc = first_paragraph(text.split("\n", 1)[1] if "\n" in text else "")
        body = BYLINE + render(text)
        out = SITE / f"{path.stem}.html"
        out.write_text(PAGE.format(title=title, description=desc, body=body))
        entries.append((title, desc, out.name))
        print(f"built {out.name}")

    cards = "\n".join(
        f'<a class="card" href="{name}"><h2>{title}</h2><p>{desc}</p></a>'
        for title, desc, name in entries
    )
    index_body = (
        "<h1>Engineering Notes</h1>"
        '<p class="byline">Building an AI-first CRM/CDP with a fleet of AI coding '
        "agents — what worked, what broke, and the systems that keep it honest.</p>"
        + cards
    )
    (SITE / "index.html").write_text(
        PAGE.format(
            title="Engineering Notes — MarketingOrchestration.io",
            description="Field notes from building Helix with a fleet of AI coding agents.",
            body=index_body,
        )
    )
    print(f"built index.html ({len(entries)} posts)")


if __name__ == "__main__":
    main()
