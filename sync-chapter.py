#!/usr/bin/env python3
"""
sync-chapter.py — build/refresh a public chapter page from the manuscript.

The manuscript ("../Building a Different Kind of Company - manuscript.md") is the
single source of truth. This script regenerates, on the matching HTML page: the
chapter BODY, heading, read-time and meta tags; the masthead GLYPH; and the
endcard PROMPT. Run it after editing a chapter.

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
  * The masthead glyph is pulled from ../05-design/glyphs/chNN-*.svg (the design
    single source of truth). If that file is missing, the existing glyph on the
    page is left untouched.
  * The endcard "Tell me" prompt is per-chapter; edit the PROMPTS table below.
  * This does not touch index.html — flip that chapter's row from "soon" to a
    link yourself when you're ready to list it.
"""
import re, html, sys, os, glob, unicodedata
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
MANUSCRIPT = os.path.join(HERE, "..", "Building a Different Kind of Company - manuscript.md")
TEMPLATE = os.path.join(HERE, "notice.html")
GLYPH_DIR = os.path.join(HERE, "..", "05-design", "glyphs")
PUBLIC = (1, 2, 3)
WORDS_PER_MIN = 150  # tuned to the book's actual readers: dense prose + non-native readers run well under the 200-265 web average
ORD = {1: "One", 2: "Two", 3: "Three"}

# Endcard "Tell me" prompt, per chapter: (question, plain-text mail subject).
# The lead-in "One thing I want to know before you go:" is constant; vary the question.
PROMPTS = {
    1: ("whose side are you on, the founder's or the company's?",
        "Whose side I'm on"),
    2: ("Jonas's mother worked forty years without expecting the job to love her back. "
        "Was that a disease, or just adulthood?",
        "Disease or adulthood"),
    3: ("Eighty million euros to walk away from the thing you built. Would you take it?",
        "Eighty million"),  # DRAFT prompt — revise before ch3 goes public
}


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


def glyph_svg(n):
    """The full masthead <svg> for chapter n, inner shapes pulled from
    ../05-design/glyphs/chNN-*.svg. Returns None if no glyph file exists, so the
    caller can leave the page's existing glyph alone."""
    hits = sorted(glob.glob(os.path.join(GLYPH_DIR, f"ch{n:02d}-*.svg")))
    if not hits:
        return None
    m = re.search(r"<svg[^>]*>(.*)</svg>", open(hits[0], encoding="utf-8").read(), re.S)
    if not m:
        return None
    inner = "\n".join("      " + ln.strip() for ln in m.group(1).splitlines() if ln.strip())
    # Standard wrapper: linecap+linejoin round so both dot-and-line and bracket glyphs render cleanly.
    return ('<svg class="glyph" viewBox="0 0 100 100" fill="none" stroke="currentColor" '
            'stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">\n'
            f"{inner}\n    </svg>")


def reply_html(n):
    """The endcard reply paragraph for chapter n, or None if no prompt is defined
    (in which case the page's existing prompt is left alone)."""
    if n not in PROMPTS:
        return None
    q, subject = PROMPTS[n]
    return ('<p class="reply">One thing I want to know before you go: '
            f'{q} <a href="mailto:manuel@newworkbydesign.com?subject={quote(subject)}">Tell me.</a></p>')


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

    glyph = glyph_svg(n)                                                       # masthead mark
    if glyph:
        s = re.sub(r'<svg class="glyph".*?</svg>', lambda _: glyph, s, count=1, flags=re.S)
    else:
        print(f"  note: no glyph file for ch{n} in 05-design/glyphs — kept the existing mark")

    reply = reply_html(n)                                                      # endcard prompt
    if reply:
        s = re.sub(r'<p class="reply">.*?</p>', lambda _: reply, s, count=1, flags=re.S)
    else:
        print(f"  note: no prompt defined for ch{n} in PROMPTS — kept the existing prompt")

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
