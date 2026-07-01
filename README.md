# Ask the Company: chapter site (read.newworkbydesign.com)

Static site for the public chapters, served by GitHub Pages.
(Signup stays on Kit at book.newworkbydesign.com; this domain is just for reading.)

## Files
- `index.html`: book home (cover, pitch, chapter list, signup CTA)
- `notice.html`: Chapter 1, "Notice"
- `cover.png`, `social-share.png`: artwork + social/OG image
- `signup/index.html`: redirect to the Kit signup
- `404.html`, `CNAME` (read.newworkbydesign.com)

## One-time setup
1. Create a **public** GitHub repo (e.g. `ask-the-company`).
2. Upload everything here to the repo **root** (keep `CNAME`).
3. Settings → Pages → Deploy from branch → `main` / root.
4. Once DNS resolves, tick **Enforce HTTPS**.
5. DNS at your registrar: add `CNAME`  host `read`  value `<your-username>.github.io`
   (book stays as-is on Kit.)

## Live URLs
- Home: https://read.newworkbydesign.com/
- Chapter 1: https://read.newworkbydesign.com/notice.html   ← [CHAPTER_1_URL]
- Signup (Kit): https://book.newworkbydesign.com/signup  (set the Kit landing page to this) or https://book.newworkbydesign.com/signup
