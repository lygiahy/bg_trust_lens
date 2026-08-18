"""
extract.py — Content acquisition layer
======================================
Turns a public URL into clean body text (navigation, cookie banners, scripts
removed) and, crucially, REPORTS when a fetch is unreliable instead of silently
scoring a stub.

Why this matters
----------------
Modern fintech/asset-manager sites are JS-rendered single-page apps behind
Cloudflare. A plain HTTP GET with a non-browser User-Agent often returns only
the static shell (nav/title) or an anti-bot challenge, yielding a tiny word
count. Scoring that stub produces meaningless numbers (e.g. Integrity 99 from
two stray words). This layer defends against that:

  1. sends a REAL browser User-Agent (+ Accept-Language) so sites serve the
     full page rather than a reduced stub;
  2. if the static fetch still yields too little, RENDERS the page with headless
     Chromium (Playwright) so client-hydrated body content is captured;
  3. enforces a MIN_WORDS reliability threshold and returns ok=False + a reason
     so the pipeline can FLAG a failed scrape rather than score it.

Modes
-----
  fetch_page(url) -> dict   single URL: {url,text,words,method,ok,reason}
  fetch_url(url)  -> str    backward-compatible text-only wrapper
  load_corpus()             read pre-cached ./corpus/*.txt (offline/reproducible)
"""
from __future__ import annotations
import re
from pathlib import Path

_CORPUS = Path(__file__).resolve().parent.parent / "corpus"

# Below this many words a fetch is treated as FAILED (SPA shell / anti-bot stub),
# not as a genuinely sparse page. Tunable.
MIN_WORDS = 150

# A real, current browser UA. The previous "Mozilla/5.0 (BG-TrustLens)" UA was
# the likely root cause of reduced/stub responses from Cloudflare-fronted sites.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_HEADERS = {
    "User-Agent": _UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
}


def _clean(text: str) -> str:
    text = re.sub(r"\s*\n\s*", "\n", text or "")
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _wc(text: str) -> int:
    return len((text or "").split())


def _extract_html(html: str) -> str:
    """Best-effort main-content extraction from raw HTML."""
    if not html:
        return ""
    try:  # trafilatura = best-in-class boilerplate removal
        import trafilatura
        txt = trafilatura.extract(html, include_comments=False,
                                  include_tables=False, favor_precision=False)
        if txt and _wc(txt) >= 30:
            return _clean(txt)
    except Exception:
        pass
    try:  # BeautifulSoup fallback
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "form", "noscript", "svg"]):
            tag.decompose()
        return _clean(soup.get_text(" "))
    except Exception:  # last-resort regex strip
        return _clean(re.sub(r"<[^>]+>", " ", html))


def _static_html(url: str, timeout: int) -> str:
    """Plain HTTP GET with a real browser User-Agent."""
    import requests
    r = requests.get(url, timeout=timeout, headers=_HEADERS)
    r.raise_for_status()
    return r.text


def _rendered_html(url: str, timeout: int) -> str:
    """Headless-Chromium render that EXECUTES JS — required for SPA sites that
    hydrate their body client-side (Moneybox, Revolut, Trading 212, ...).

    Requires Playwright + a chromium build:
        pip install playwright && playwright install chromium
    Raises if unavailable; the caller degrades gracefully.
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox",
                                            "--disable-blink-features=AutomationControlled"])
        page = browser.new_page(user_agent=_UA, locale="en-GB",
                                viewport={"width": 1366, "height": 900})
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            page.wait_for_timeout(1800)  # let late-hydrating content settle
            html = page.content()
        finally:
            browser.close()
    return html


def fetch_page(url: str, timeout: int = 25, render: str = "auto") -> dict:
    """Fetch + extract one URL, with reliability reporting.

    Returns {url, text, words, method, ok, reason}. `ok` is False when fewer
    than MIN_WORDS were extracted, so callers FLAG the failure rather than
    scoring a stub. `render`: 'auto' (render only if static is too thin),
    'always', or 'never'.
    """
    text, method, reason = "", "none", ""

    if render != "always":
        try:
            text = _extract_html(_static_html(url, timeout))
            method = "static"
        except Exception as e:
            reason = f"static fetch failed ({type(e).__name__}: {e})"

    if _wc(text) < MIN_WORDS and render != "never":
        try:
            rendered = _extract_html(_rendered_html(url, timeout))
            if _wc(rendered) > _wc(text):
                text, method = rendered, "rendered"
        except Exception as e:
            note = f"JS render unavailable ({type(e).__name__})"
            reason = f"{reason} | {note}" if reason else note

    words = _wc(text)
    ok = words >= MIN_WORDS
    if not ok and not reason:
        reason = (f"only {words} words extracted (likely SPA shell or anti-bot "
                  f"stub); below {MIN_WORDS}-word reliability threshold")
    return {"url": url, "text": text, "words": words,
            "method": method, "ok": ok, "reason": reason}


def fetch_url(url: str, timeout: int = 25) -> str:
    """Backward-compatible: returns extracted text (may be empty on failure)."""
    return fetch_page(url, timeout)["text"]


def load_corpus(folder: Path | None = None) -> dict[str, str]:
    folder = folder or _CORPUS
    return {p.stem: p.read_text(encoding="utf-8")
            for p in sorted(folder.glob("*.txt"))}


def cache_text(provider: str, text: str, folder: Path | None = None) -> Path:
    folder = folder or _CORPUS
    folder.mkdir(exist_ok=True)
    out = folder / f"{provider}.txt"
    out.write_text(_clean(text), encoding="utf-8")
    return out
