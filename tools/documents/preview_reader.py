#!/usr/bin/env python3
"""Local Markdown review; approximation of GitHub, not a publication renderer."""

from __future__ import annotations

import argparse
import html
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]
MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable("table")
STYLE = """
body{margin:0;background:#f6f8fa;color:#1f2328;font:16px/1.6 system-ui,sans-serif}
nav{padding:12px 24px;background:#101214;color:#fff}nav a{color:#fff;margin-right:20px}
main{box-sizing:border-box;max-width:1012px;margin:24px auto;padding:36px;background:white;border:1px solid #d1d9e0}
h1,h2,h3{line-height:1.25}h1,h2{border-bottom:1px solid #d1d9e0;padding-bottom:12px}
a{color:#0969da}img{max-width:100%;height:auto}table{display:block;overflow-x:auto;border-collapse:collapse}
th,td{border:1px solid #d1d9e0;padding:8px 12px;text-align:left}tr:nth-child(even){background:#f6f8fa}
code{background:#f1f3f5;padding:2px 4px;overflow-wrap:anywhere}pre{overflow:auto;padding:16px;background:#f6f8fa}
p,li,td{overflow-wrap:break-word}small{color:#59636e}@media(max-width:650px){main{margin:0;padding:18px}nav{padding:12px}}
"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        relative = unquote(urlsplit(self.path).path).lstrip("/") or "README.md"
        target = (ROOT / relative).resolve()
        if not target.is_relative_to(ROOT) or any(
            part.startswith(".") for part in Path(relative).parts
        ):
            self.send_error(404)
            return
        if target.is_dir():
            self.send_response(302)
            self.send_header("Location", "/" + str(target.relative_to(ROOT)) + "/README.md")
            self.end_headers()
            return
        if target.suffix.lower() == ".md" and target.is_file():
            rendered = MARKDOWN.render(target.read_text())
            anchors = {}

            def heading(match):
                level, body = match.groups()
                text = html.unescape(re.sub(r"<[^>]+>", "", body)).lower()
                slug = re.sub(r"[^\w\- ]", "", text).replace(" ", "-")
                count = anchors.get(slug, 0)
                anchors[slug] = count + 1
                suffix = f"-{count}" if count else ""
                return f'<h{level} id="{html.escape(slug + suffix)}">{body}</h{level}>'

            rendered = re.sub(r"<h([1-6])>(.*?)</h[1-6]>", heading, rendered)
            content = (
                f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f"<title>{html.escape(target.stem)} — local review</title><style>{STYLE}</style>"
                '<nav><a href="/README.md">README</a><a href="/docs/wiki/Home.md">Company</a>'
                '<a href="/docs/wiki/Library.md">Library</a><a href="/docs/finance/READER_EXERCISES.md">Finance exercises</a></nav>'
                f"<main><small>LOCAL DRAFT REVIEW · {html.escape(relative)} · GitHub-like preview, not exact GitHub rendering</small>{rendered}</main></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif target.suffix.lower() in {".png", ".svg", ".jpg", ".jpeg", ".pdf", ".xlsx"}:
            super().do_GET()
        else:
            self.send_error(404, "Open non-document assets through the repository or package guide")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"Reader review: http://127.0.0.1:{args.port}/README.md", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
