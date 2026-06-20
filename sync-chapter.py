#!/usr/bin/env python3
"""
sync-chapter.py — build/refresh a public chapter page from the manuscript.

The manuscript ("../Building a Different Kind of Company - manuscript.md") is the
single source of truth. This script regenerates the chapter BODY (and heading,
read-time, and meta tags) on the matching HTML page. Run it after editing a
chapter.

Usage:
    python sync-chapter.py 1        # rebuild chapter 1  -> notice.html
    python sync-chapter.py 2        # build/rebuild chapter 2 -> <slug>.html
    python sync-chapter.py all      # rebuild every public chapter (1-3)

Notes:
  * Only chapters 1-3 are public pages. Chapter 4+ go out by email, so the
    script refuses higher numbers.
  * If the page already exists, only the managed regions are replaced; any
    hand edits you made to its CSS or layout are preserved.
  * A new page is created from notice.html, so it inherits the same design.
  * The filename is the slug of the chapter title (e.g. "The Number" ->
    the-number.html). Chapter 1, "Notice", maps to notice.html.
  * This does not touch index.html — flip that chapter's row from "soon" to a
    link yourself when you're ready to list it.
"""
import re, html, sys, os, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
MANUSCRIPT = os.path.join(HERE, "..", "Building a Different Kind of Company - manuscript.md")
TEMPLATE = os.path.join(HERE, "notice.html")
PUBLIC = (1, 2, 3)
WORDS_PER_MIN = 200
ORD = {1: "One", 2: "Two", 3: "Three"}


def slugify(title):
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    t = re.sub(r"[^\w\s-]", "", t).strip().lower()
    return re.sub(r"[\s_]+", "-", t)


def extract(n):
    """Return (title, body_markdown) for chapter n from the manuscript."""
    raw = open(MANUSCRIPT, encoding="utf-8").read()
    m = re.search(rf'^# {n}\.\s*(.*?)[ \t]*$\n(.*?)(?=^# {n + 1}\.|\Z)', raw, re.S | re.M)
    if not m:
        sys.exit(f"Chapter {n} not found in the manuscript.")
    return m.group(1).strip(), m.group(2)


def build_article(body_md):
    """Parse chapter markdown into the <article> HTML and a read-time (minutes)."""
    blocks, buf, in_code, code = [], [], False, []
    for ln in body_md.splitlines():
        if ln.strip() == "```":
            if not in_code:
                if buf:
                    blocks.append(("p", " ".join(x.strip() for x in buf).strip())); buf = []
                in_code, code = True, []
            else:
                blocks.append(("code", "\n".join(code))); in_code = False
            continue
        if in_code:
            code.append(ln); continue
        if ln.strip() == "---":
            if buf:
                blocks.append(("p", " ".join(x.strip() for x in buf).strip())); buf = []
            break
        if ln.strip() == "":
            if buf:
                blocks.append(("p", " ".join(x.strip() for x in buf).strip())); buf = []
        else:
            buf.append(ln)
    if buf:
        blocks.append(("p", " ".join(x.strip() for x in buf).strip()))

    esc = lambda t: html.escape(t, quote=False)   # keep ' and " literal
    parts, first = [], True
    for kind, text in blocks:
        if kind == "code":
            parts.append('<pre class="artifact">' + esc(text) + "</pre>")
        elif text:
            parts.append(('<p class="first lead">' if first else "<p>") + esc(text) + "</p>")
            first = False
    article = "<article>\n    " + "\n\n    ".join(parts) + "\n  </article>"
    words = sum(len(t.split()) for k, t in blocks if k == "p")
    return article, max(1, round(words / WORDS_PER_MIN))


def sync(n):
    if n not in PUBLIC:
        sys.exit(f"Chapter {n} is not a public page (only {PUBLIC[0]}-{PUBLIC[-1]} are).")
    title, body_md = extract(n)
    slug = slugify(title)
    page = os.path.join(HERE, f"{slug}.html")
    article, readmin = build_article(body_md)

    fresh = not os.path.exists(page)
    s = open(TEMPLATE, encoding="utf-8").read() if fresh else open(page, encoding="utf-8").read()

    # split head / body so meta swaps never touch the prose
    head, sep, rest = s.partition("</head>")

    head = re.sub(r"Chapter \d+:[^<\"]*", f"Chapter {n}: {title}", head)      # <title> + og:title
    head = re.sub(r"Chapter \d+ of", f"Chapter {n} of", head)                  # meta description
    head = re.sub(r"Chapter \d+\.", f"Chapter {n}.", head)                     # og:description
    head = re.sub(r'(content="https://read\.newworkbydesign\.com/)[\w-]+\.html(")',
                  rf"\g<1>{slug}.html\g<2>", head)                             # og:url
    s = head + sep + rest

    s = re.sub(r"<article>.*?</article>", lambda _: article, s, count=1, flags=re.S)
    s = re.sub(r"(<h1>).*?(</h1>)", rf"\g<1>{html.escape(title, quote=False)}\g<2>", s, count=1, flags=re.S)
    s = re.sub(r'(<p class="eyebrow">)Chapter [A-Za-z]+(</p>)',
               rf"\g<1>Chapter {ORD[n]}\g<2>", s, count=1)
    s = re.sub(r'(<p class="readtime">)\d+ min read(</p>)',
               rf"\g<1>{readmin} min read\g<2>", s, count=1)

    open(page, "w", encoding="utf-8").write(s)
    print(f"{'created' if fresh else 'updated'}  ch{n}  {os.path.basename(page)}  ({readmin} min read)")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1].lower()
    targets = list(PUBLIC) if arg == "all" else [int(arg)] if arg.isdigit() else sys.exit(__doc__)
    for n in targets:
        sync(n)


if __name__ == "__main__":
    main()
