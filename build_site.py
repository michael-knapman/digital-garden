#!/usr/bin/env python3
"""
build_site.py - Manual build step for michael.nekoweb.org

Run this BEFORE `git push` (the github workflow deploys public/ as-is):

    python3 build_site.py

What it does
------------
* Scans every *.html file under public/, including subfolders, so the
  git structure and the webpage structure stay in sync.
* Builds a hierarchical sitemap from the folder structure. A page named
  <section>.html is treated as the landing page for the sibling folder
  <section>/, so pages inside engineering/ are shown as children of
  engineering.html, e.g.:

      Home (index.html)
      Cool stuff! (cool_stuff.html)
      Engineering landing page (engineering.html)
        Codecs (engineering/codecs.html)

* Excludes special folders from the sitemap:
  - media/    - assets only (images, music), never webpages
  - unlisted/ - secret pages you reach by typing the URL or exploring the
                site; they still get the sidebar, just no link to them.
  The 404 page (not_found.html) is also left out of the sitemap.
* Injects a fixed left-hand sidebar into every page (except inside media/).
  The sidebar shows the sitemap, a sticker linking to nekoweb.org and a
  copyright notice. The page or section you are currently on is
  highlighted. Links are written relative to each page's own folder, so
  pages in subfolders get "../index.html" and so on.
  On phones (max-width 600px) the sidebar turns into a full-width top bar
  so the content gets the whole viewport.

The script is idempotent: re-running it replaces any previously injected
sidebar instead of duplicating it, so it is safe to run after every edit.
If you add, rename or remove a page, just run the build again.

The injected markup is pure HTML + CSS. No JavaScript is used anywhere.
"""

import pathlib
import posixpath
import re
import sys
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

HOME_LABEL = "Home"
HOMEPAGE_FILE = "index.html"
NOT_FOUND_FILE = "not_found.html"

# Folders that are never listed in the sidebar sitemap.
EXCLUDE_FROM_SITEMAP = {"media", "unlisted"}
# Folders whose pages do not even get a sidebar injected (pure assets).
EXCLUDE_FROM_INJECTION = {"media"}

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
.sidebar-nav ul ul {
    padding-left: 14px;
}
.sidebar-nav li {
    margin: 4px 0;
}
.sidebar-nav li.group > span {
    display: block;
    padding: 4px 8px;
    font-size: 12px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #8a8375;
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
/* Mobile: the sidebar becomes a full-width top bar so the content gets
   the whole viewport. It sits in normal flow (scrolls away as you read)
   and scrolls internally if the sitemap outgrows the capped height. */
@media (max-width: 600px) {
    body {
        margin-left: 0;
    }
    aside.sidebar {
        position: static;
        width: 100%;
        height: auto;
        max-height: 32vh;
        overflow-y: auto;
        box-sizing: border-box;
        padding: 8px 10px 10px;
        border-right: none;
        border-bottom: 1px solid #d8d2c6;
    }
    .sidebar-nav ul {
        padding-left: 0;
    }
    .sidebar-nav ul ul {
        padding-left: 12px;
    }
    .sidebar-nav li {
        margin: 2px 0;
    }
    .sidebar-nav a {
        padding: 3px 6px;
        font-size: 13px;
    }
    .sidebar-foot {
        margin-top: 8px;
        padding-top: 8px;
    }
}
"""


@dataclass
class PageNode:
    """A clickable page in the sitemap."""

    rel_path: str  # posix path relative to PUBLIC, e.g. "engineering/codecs.html"
    label: str
    children: list = field(default_factory=list)


@dataclass
class GroupNode:
    """A non-clickable section heading, used when a folder has no landing page."""

    label: str
    children: list = field(default_factory=list)


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


def parent_dir(rel_path):
    """Parent directory of a posix rel path, "" for the root folder."""
    return posixpath.dirname(rel_path)


def stem(rel_path):
    """File stem, e.g. "engineering/codecs.html" -> "codecs"."""
    return posixpath.splitext(posixpath.basename(rel_path))[0]


def rel_href(cur_dir, target_rel_path):
    """Relative href from a page in cur_dir to a sitemap target."""
    if not cur_dir:
        return target_rel_path
    up = "../" * len(cur_dir.split("/"))
    return up + target_rel_path


class Sitemap:
    """Builds and holds the hierarchical sitemap for the whole site."""

    def __init__(self):
        self.pages = {}       # rel_path -> PageNode
        self.pages_in_dir = {}  # dir -> [rel_path, ...]
        self.all_dirs = set()   # every directory that contains a page below it

        self._scan_pages()
        self._index_dirs()
        self.root = self._build_tree("")

    def _is_excluded(self, rel_path):
        parts = rel_path.split("/")[:-1]
        return any(part in EXCLUDE_FROM_SITEMAP for part in parts)

    def _scan_pages(self):
        for path in sorted(PUBLIC.rglob("*.html")):
            rel = path.relative_to(PUBLIC).as_posix()
            if self._is_excluded(rel):
                continue
            if path.name == NOT_FOUND_FILE:
                continue
            label = (HOME_LABEL if rel == HOMEPAGE_FILE
                     else extract_title(path.read_text(encoding="utf-8"), path.name))
            self.pages[rel] = PageNode(rel, label)

    def _index_dirs(self):
        for rel in self.pages:
            d = parent_dir(rel)
            self.pages_in_dir.setdefault(d, []).append(rel)
            self.all_dirs.add(d)  # when rel's parent == "" we add "" directly
            while d:
                d = parent_dir(d)
                self.all_dirs.add(d)

    def _child_dirs_with_pages(self, cur_dir):
        """Immediate sub-folders of cur_dir that contain pages somewhere below."""
        found = set()
        prefix = f"{cur_dir}/" if cur_dir else ""
        for rel in self.pages:
            if rel.startswith(prefix):
                rest = rel[len(prefix):]
                if "/" in rest:
                    found.add(rest.split("/", 1)[0])
        return found

    def _build_tree(self, cur_dir):
        children = []
        my_pages = self.pages_in_dir.get(cur_dir, [])
        my_pages = sorted(my_pages, key=lambda rel: (rel != HOMEPAGE_FILE, stem(rel)))
        for rel in my_pages:
            node = self.pages[rel]
            section = stem(rel) if not cur_dir else posixpath.join(cur_dir, stem(rel))
            if section in self.all_dirs:
                node.children = self._build_tree(section)
            children.append(node)

        for sub in sorted(self._child_dirs_with_pages(cur_dir)):
            section = sub if not cur_dir else posixpath.join(cur_dir, sub)
            landing = f"{sub}.html" if not cur_dir else posixpath.join(cur_dir, sub + ".html")
            if landing not in self.pages:
                group = GroupNode(sub)
                group.children = self._build_tree(section)
                children.append(group)
        return children


def strip_block(text, start_token, end_token):
    """Remove a previously injected block (idempotency).

    The blocks this script writes own the single newline on each side, so
    both are consumed here and re-added on injection. Without that, blank
    lines would creep into the file on every run.
    """
    pattern = re.compile(
        r"\n?<!--\s*" + re.escape(start_token) + r"\s*-->.*?"
        r"<!--\s*" + re.escape(end_token) + r"\s*-->\n?",
        re.DOTALL,
    )
    return pattern.sub("", text)


def normalize_marker_spacing(html):
    """Normalize blank lines next to the injected blocks.

    Guarantees deterministic spacing at the block boundaries (the CSS marker
    sits on its own line, one blank line separates the sidebar footer from
    the page content) and cleans up blank-line runs left over from older
    build_site versions. This is idempotent: on already-clean files it is a
    no-op.
    """
    # CSS block: exactly one newline before the opening marker.
    html = re.sub(r"\n*(<!--\s*BEGINSIDEBAR:CSS\s*-->)", r"\n\1", html)
    # Sidebar block: exactly one blank line after the closing marker.
    html = re.sub(
        r"(<!--\s*ENDSIDEBAR\s*-->)(\n*)", r"\1\n\n", html
    )
    return html


def render_nav(nodes, cur_dir, current_rel, depth=0):
    """Render the nested <ul> sitemap. Handles page and group nodes."""
    out = []
    pad = "    " * (depth + 2)
    for node in nodes:
        if isinstance(node, PageNode):
            href = rel_href(cur_dir, node.rel_path)
            is_current = node.rel_path == current_rel
            extra = ' class="current" aria-current="page"' if is_current else ""
            out.append(
                f"{pad}<li><a href=\"{href}\"{extra}>"
                f"{escape_html(node.label)}</a></li>"
            )
            if node.children:
                out.append(f"{pad}<ul>")
                out.extend(render_nav(node.children, cur_dir, current_rel, depth + 1))
                out.append(f"{pad}</ul>")
        else:  # GroupNode
            out.append(
                f"{pad}<li class=\"group\"><span>"
                f"{escape_html(node.label)}</span></li>"
            )
            if node.children:
                out.append(f"{pad}<ul>")
                out.extend(render_nav(node.children, cur_dir, current_rel, depth + 1))
                out.append(f"{pad}</ul>")
    return out


def build_sidebar(sitemap, current_rel):
    cur_dir = parent_dir(current_rel)
    nav_lines = render_nav(sitemap.root, cur_dir, current_rel)
    nav = "\n".join(nav_lines)
    return (
        f"\n<!-- {SIDEBAR_MARKER_START} -->\n"
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
        f"<!-- {SIDEBAR_MARKER_END} -->\n"
    )


def build_css_block():
    return (
        f"<!-- {CSS_MARKER_START} -->\n"
        f"<style id=\"sidebar-css\">{SIDEBAR_CSS}</style>\n"
        f"<!-- {CSS_MARKER_END} -->\n"
    )


def inject_into_page(html, current_rel, sitemap):
    html = strip_block(html, CSS_MARKER_START, CSS_MARKER_END)
    html = strip_block(html, SIDEBAR_MARKER_START, SIDEBAR_MARKER_END)

    css_block = build_css_block()
    if "</head>" in html:
        html = html.replace("</head>", css_block + "</head>", 1)
    else:
        html = css_block + html

    sidebar = build_sidebar(sitemap, current_rel)
    match = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    if match:
        html = html[: match.end()] + sidebar + html[match.end():]
    else:
        html = sidebar + html
    return normalize_marker_spacing(html)


def print_tree(nodes, indent=""):
    for node in nodes:
        if isinstance(node, PageNode):
            print(f"{indent}{node.rel_path}  ({node.label})")
            print_tree(node.children, indent + "  ")
        else:
            print(f"{indent}{node.label}/  (group)")
            print_tree(node.children, indent + "  ")


def main():
    sitemap = Sitemap()

    html_files = [p for p in sorted(PUBLIC.rglob("*.html"))
                  if not any(part in EXCLUDE_FROM_INJECTION
                             for part in p.relative_to(PUBLIC).parts[:-1])]
    if not html_files:
        print(f"No HTML files found under {PUBLIC}", file=sys.stderr)
        return 1

    print("Build step: sitemap:")
    print_tree(sitemap.root)

    for path in html_files:
        current_rel = path.relative_to(PUBLIC).as_posix()
        html = path.read_text(encoding="utf-8")
        updated = inject_into_page(html, current_rel, sitemap)
        if updated != html:
            path.write_text(updated, encoding="utf-8")
            print(f"  updated {path.name} ({current_rel})")
        else:
            print(f"  unchanged {path.name} ({current_rel})")

    print("Done. You can now git add, git commit, and git push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())