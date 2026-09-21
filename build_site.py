#!/usr/bin/env python3
"""
build_site.py - Manual build step for michael.nekoweb.org

Run this BEFORE `git push` (the github workflow deploys public/ as-is):

    python3 build_site.py

What it does
------------
* Scans every *.html file in public/.
* Builds a sitemap from those pages: index.html becomes "Home" and is listed
  first; every other page follows, labelled with its <title> tag.
  not_found.html (the 404 page) is excluded from the sitemap.
* Injects a fixed left-hand sidebar into every page. The sidebar shows the
  sitemap, a sticker linking to nekoweb.org and a copyright notice.
  The page you are currently on is highlighted.

The script is idempotent: re-running it replaces any previously injected
sidebar instead of duplicating it, so it is safe to run after every edit.
If you add, rename or remove a page, just run the build again.

The injected markup is pure HTML + CSS. No JavaScript is used anywhere.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

HOME_LABEL = "Home"
HOMEPAGE_FILE = "index.html"
EXCLUDE_FROM_SITEMAP = {"not_found.html"}

CSS_MARKER_START = "BEGINSIDEBAR:CSS"
CSS_MARKER_END = "ENDSIDEBAR:CSS"
SIDEBAR_MARKER_START = "BEGINSIDEBAR"
SIDEBAR_MARKER_END = "ENDSIDEBAR"

STICKER = (
    '<a href="https://nekoweb.org/">'
    '<img src="https://nekoweb.org/assets/buttons/button5.gif" alt="Nekoweb">'
    "</a>"
)
COPYRIGHT = "Copyright © 2026 Michael Knapman. All Rights Reserved."

SIDEBAR_CSS = """
/* Injected by build_site.py - do not edit by hand, re-run the build instead. */
:root {
    --sidebar-width: 260px;
}
body {
    margin-left: var(--sidebar-width);
}
aside.sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--sidebar-width);
    box-sizing: border-box;
    overflow-y: auto;
    padding: 16px 14px;
    background-color: #f3f0ea;
    border-right: 1px solid #d8d2c6;
    font-family: sans-serif;
    font-size: 14px;
    z-index: 1000;
}
.sidebar-nav ul {
    list-style: none;
    margin: 0;
    padding: 0;
}
.sidebar-nav li {
    margin: 4px 0;
}
.sidebar-nav a {
    display: block;
    padding: 4px 8px;
    color: #224a77;
    text-decoration: none;
    border-radius: 4px;
}
.sidebar-nav a:hover,
.sidebar-nav a:focus {
    background-color: #e3dccb;
}
.sidebar-nav a.current {
    background-color: #d9d2c2;
    font-weight: bold;
    color: #17375c;
}
.sidebar-foot {
    margin-top: 24px;
    border-top: 1px solid #d8d2c6;
    padding-top: 12px;
    text-align: center;
}
.sidebar-foot p {
    margin: 8px 0 0;
    font-size: 12px;
    color: #6b6559;
}
@media (max-width: 600px) {
    :root {
        --sidebar-width: min(220px, 70vw);
    }
}
"""


def escape_html(text):
    """Escape a page title so it is safe inside HTML markup."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def extract_title(html, filename):
    match = re.search(r"<title[^>]*>([^<]*)</title>", html, re.IGNORECASE)
    if match and match.group(1).strip():
        return match.group(1).strip()
    return filename.removesuffix(".html")


def build_sitemap():
    """Return an ordered list of (filename, label) for the sidebar."""
    pages = []
    for path in sorted(PUBLIC.glob("*.html")):
        if path.name in EXCLUDE_FROM_SITEMAP:
            continue
        label = extract_title(path.read_text(encoding="utf-8"), path.name)
        pages.append((path.name, label))

    # index.html first as "Home", everything else keeps alphabetical order.
    pages.sort(key=lambda item: (item[0] != HOMEPAGE_FILE, item[0]))
    return [(name, HOME_LABEL if name == HOMEPAGE_FILE else label)
            for name, label in pages]


def strip_block(text, start_token, end_token):
    """Remove a previously injected block (idempotency).

    Matches the canonical markers this script writes:
        <!-- BEGINSIDEBAR:CSS --> ... <!-- ENDSIDEBAR:CSS -->
    """
    pattern = re.compile(
        r"<!--\s*" + re.escape(start_token) + r"\s*-->.*?"
        r"<!--\s*" + re.escape(end_token) + r"\s*-->",
        re.DOTALL,
    )
    return pattern.sub("", text)


def build_sidebar(current_filename, sitemap):
    links = []
    for filename, label in sitemap:
        is_current = filename == current_filename
        extra = ' class="current" aria-current="page"' if is_current else ""
        links.append(
            f"            <li><a href=\"{filename}\"{extra}>"
            f"{escape_html(label)}</a></li>"
        )
    nav = "\n".join(links)
    return (
        f"<!-- {SIDEBAR_MARKER_START} -->\n"
        f'<aside class="sidebar">\n'
        f"    <nav class=\"sidebar-nav\" aria-label=\"Sitemap\">\n"
        f"        <ul>\n"
        f"{nav}\n"
        f"        </ul>\n"
        f"    </nav>\n"
        f"    <div class=\"sidebar-foot\">\n"
        f"        {STICKER}\n"
        f"        <p>{escape_html(COPYRIGHT)}</p>\n"
        f"    </div>\n"
        f"</aside>\n"
        f"<!-- {SIDEBAR_MARKER_END} -->"
    )


def build_css_block():
    return (
        f"<!-- {CSS_MARKER_START} -->\n"
        f"<style id=\"sidebar-css\">{SIDEBAR_CSS}</style>\n"
        f"<!-- {CSS_MARKER_END} -->"
    )


def inject_into_page(html, current_filename, sitemap):
    html = strip_block(html, CSS_MARKER_START, CSS_MARKER_END)
    html = strip_block(html, SIDEBAR_MARKER_START, SIDEBAR_MARKER_END)

    css_block = build_css_block()
    if "</head>" in html:
        html = html.replace("</head>", css_block + "\n</head>", 1)
    else:
        html = css_block + "\n" + html

    sidebar = build_sidebar(current_filename, sitemap)
    match = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    if match:
        html = html[: match.end()] + "\n" + sidebar + html[match.end():]
    else:
        html = sidebar + "\n" + html

    return html


def main():
    html_files = sorted(PUBLIC.glob("*.html"))
    if not html_files:
        print(f"No HTML files found in {PUBLIC}", file=sys.stderr)
        return 1

    sitemap = build_sitemap()
    print("Build step: sitemap generated")
    for filename, label in sitemap:
        print(f"  - {filename}  ({label})")

    for path in html_files:
        html = path.read_text(encoding="utf-8")
        updated = inject_into_page(html, path.name, sitemap)
        if updated != html:
            path.write_text(updated, encoding="utf-8")
        print(f"  injected sidebar into {path.name}")

    print("Done building. You can now git add, git commit, and git push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())