"""
coverage.py — page-universe definition + coverage gate
======================================================
Generic over any provider: the gate reads only the per-slot STATE, never the
provider name, so a brand-new provider BG adds later is classified the same way.

Page universe (4 functional slots, defined by ROLE not by page title):
  homepage          first impression
  fund_product      "where does my money go, what does it cost, how has it done"
  about_philosophy  "who manages my money, do they care about me"
  guidance_support  "do they help me understand this in plain English"

Per-slot state (the labeller asserts N/A; the engine never guesses it):
  filled_reliable   has URL(s); fetched text >= MIN_WORDS
  attempted_failed  has URL(s); fetched text < MIN_WORDS (SPA / anti-bot)
  not_provided      no URL given, and not marked N/A
  not_applicable    labeller marked "this provider has no such page type"
                    -> removed from the coverage denominator

Coverage status (operational meaning):
  Insufficient  homepage itself not reliable -> no trustworthy base -> suppress TSI
  Reliable      homepage + enough supporting slots captured
  Partial       homepage captured, but supporting evidence is thin -> show TSI, flag it
"""
from __future__ import annotations

SLOTS = ["homepage", "fund_product", "about_philosophy", "guidance_support"]
SLOT_LABELS = {
    "homepage": "Homepage",
    "fund_product": "Fund / product",
    "about_philosophy": "About / philosophy",
    "guidance_support": "Guidance / support",
}


def slot_state(urls: list[str], na: bool, ok: bool) -> str:
    if na:
        return "not_applicable"
    if not urls:
        return "not_provided"
    return "filled_reliable" if ok else "attempted_failed"


def coverage_status(states: dict[str, str]) -> dict:
    """states: {slot: state}. Returns {status, extraction_risk, reliable_n,
    applicable_n, missing, homepage_missing, note}.

    Design note: the homepage is the preferred anchor and its absence is always
    flagged, but it is NOT mandatory. Several fintech homepages are unscrapeable
    SPAs while their fund/about/help pages scrape cleanly; requiring the homepage
    would re-break exactly the providers this tool exists to monitor. So a score
    is published whenever enough reliable evidence exists across the universe.
    """
    home = states.get("homepage", "not_provided")
    home_ok = home == "filled_reliable"
    home_na = home == "not_applicable"
    home_missing = (not home_ok) and (not home_na)

    applicable = [k for k, v in states.items() if v != "not_applicable"]
    reliable = [k for k, v in states.items() if v == "filled_reliable"]
    failed = [k for k, v in states.items()
              if v in ("attempted_failed", "not_provided")]
    reliable_n, applicable_n = len(reliable), len(applicable)

    if reliable_n == 0:
        return {"status": "Insufficient", "extraction_risk": "High",
                "reliable_n": 0, "applicable_n": applicable_n, "missing": failed,
                "homepage_missing": home_missing,
                "note": "No page could be captured reliably, so no Trust Index is shown."}

    need = min(3, applicable_n)  # homepage + 2 of the others, scaled by what applies
    if home_ok and reliable_n >= need:
        status, risk = "Reliable", "Low"
        note = "Homepage plus enough supporting pages captured."
    elif reliable_n >= 2:
        status, risk = "Partial", "Medium"
        if home_missing:
            note = ("Homepage page was not captured (likely an unscrapeable app/SPA); "
                    f"score rests on {reliable_n} other page type(s).")
        else:
            miss = ", ".join(SLOT_LABELS[s] for s in failed) or "some page types"
            note = (f"Captured {reliable_n} of {applicable_n} page types; "
                    f"{miss} missing or incomplete, so evidence is thinner.")
    else:  # exactly one reliable page
        status, risk = "Partial", "Medium"
        only = reliable[0]
        note = (f"Scored on a single page ({SLOT_LABELS.get(only, only)}) only; "
                "treat the score as indicative, not robust.")
    return {"status": status, "extraction_risk": risk,
            "reliable_n": reliable_n, "applicable_n": applicable_n,
            "missing": failed, "homepage_missing": home_missing, "note": note}
