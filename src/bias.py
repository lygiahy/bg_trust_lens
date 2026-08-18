"""
bias.py — Module C: credibility / bias controls (Direction B)
=============================================================
The trust engine counts positive trust cues. But every company's website is
written to look positive, so a high score can reflect promotion rather than
trustworthiness (the "Key Themes reads too positively" problem). This module
adds three *unmixed* controls that sit ALONGSIDE the Trust Index, never inside
it, so the reader can see promotion vs substance separately.

Controls
--------
- candour_density   : risk-disclosure / two-sided language per 1,000 words.
                      Grounded in two-sided message credibility (Eisend, 2006):
                      admitting the downside raises credibility.
- puffery_density   : promotional superlatives + pressure selling per 1,000 words.
- spin_index (0-100): puffery / (puffery + candour) * 100. High = one-sided.
- substantiation    : share of positive-claim sentences that carry concrete
                      evidence (a number, %, £, or a regulator: FCA/FSCS).
                      Grounded in claim-substantiation / impression-management
                      (e.g. Lyon & Montgomery, 2015 on greenwashing).
- lm_polarity       : Loughran & McDonald (2011) financial tone, (pos-neg)/(pos+neg),
                      if `pysentiment2` is installed (optional; academic cross-check).

None of these replace the Trust Index; they qualify it.
"""
from __future__ import annotations
import csv
import re
from pathlib import Path

from nltk.tokenize import sent_tokenize

_CONFIG = Path(__file__).resolve().parent.parent / "config"
_TOKEN_RE = re.compile(r"[a-z][a-z'\-]+")


def _load_bias(path: Path | None = None):
    path = path or _CONFIG / "bias_lexicon.csv"
    cand, puff = [], []
    for r in csv.DictReader(open(path, newline="")):
        (cand if r["category"] == "candour" else puff).append(r["term"].strip().lower())
    return cand, puff


_CANDOUR, _PUFFERY = _load_bias()


def _density(text: str, terms: list[str]) -> float:
    low = text.lower()
    # Denominator must match the pipeline's reported word_count (naive split);
    # _TOKEN_RE is still used below for whole-word boundary matching only.
    W = max(len(text.split()), 1)
    multi = sorted([t for t in terms if " " in t], key=len, reverse=True)
    single = {t for t in terms if " " not in t}
    hits, scratch = 0, low
    for t in multi:
        c = scratch.count(t)
        hits += c
        scratch = scratch.replace(t, " ")
    for w in _TOKEN_RE.findall(scratch):
        if w in single:
            hits += 1
    return round(hits / W * 1000, 1)


def _has_evidence(s: str) -> bool:
    return bool(re.search(r"\d", s) or re.search(r"[£$%]", s)
                or re.search(r"\b(fca|fscs|financial conduct authority|"
                             r"financial services compensation)\b", s.lower()))


def bias_controls(text: str, positive_cues: list[str]) -> dict:
    cand = _density(text, _CANDOUR)
    puff = _density(text, _PUFFERY)
    spin = round(puff / (puff + cand) * 100) if (puff + cand) > 0 else 0
    sents = sent_tokenize(text)
    claim_s = [s for s in sents if any(c in s.lower() for c in positive_cues)]
    subst = round(sum(_has_evidence(s) for s in claim_s) / max(len(claim_s), 1) * 100)
    out = {"candour_density": cand, "puffery_density": puff,
           "spin_index": spin, "substantiation_pct": subst}
    try:  # optional Loughran-McDonald cross-check
        import pysentiment2 as ps
        lm = ps.LM()
        out["lm_polarity"] = round(lm.get_score(lm.tokenize(text))["Polarity"], 2)
    except Exception:
        out["lm_polarity"] = None
    return out
