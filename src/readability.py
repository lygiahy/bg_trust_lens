"""
readability.py — Module B: Readability Benchmarker
==================================================
Quantifies how hard a provider's public copy is to read for a financial
novice (the project's 16-25 target reader). Pairs a battery of established
readability formulae with a domain-specific *jargon density* measure.

Why this matters for the project
--------------------------------
The Trust workstream's literature synthesis identifies "excessive jargon" and
"hidden complexity" as primary TRUST BREAKERS, and "clear, simple explanations"
as a primary TRUST SIGNAL. Readability formulae and jargon density turn that
qualitative finding into a measurable, comparable score across providers.

Metrics produced (all standard, peer-reviewed formulae via `textstat`)
----------------------------------------------------------------------
- flesch_reading_ease   : 0-100, higher = easier (90-100 ~ Grade 5; 30-50 ~ college)
- flesch_kincaid_grade  : US school-grade reading level required
- gunning_fog           : years of formal education needed to understand on first read
- smog_index            : grade level, estimated from polysyllable count
- dale_chall            : difficulty vs a list of words familiar to 4th graders
- avg_sentence_length   : words per sentence
- pct_complex_words     : share of words with >=3 syllables
- jargon_density        : finance-jargon terms per 1,000 words (domain-specific)
"""
from __future__ import annotations
import csv
import re
from pathlib import Path
import textstat

_CONFIG = Path(__file__).resolve().parent.parent / "config"


def load_jargon(path: Path | None = None) -> dict[str, int]:
    """Returns {term: hard} where hard=1 marks novice-blocking technical terms."""
    path = path or _CONFIG / "finance_jargon.csv"
    with open(path, newline="") as f:
        return {row["term"].strip().lower(): int(row.get("hard", 0))
                for row in csv.DictReader(f)}


_JARGON = load_jargon()
_WORD_RE = re.compile(r"[a-z][a-z'\-]+")


def jargon_density(text: str, jargon: dict[str, int] | None = None) -> dict:
    """Finance-jargon hits per 1,000 words, plus a separate HARD-jargon density
    for novice-blocking terms. Multiword terms counted first so 'fixed income'
    is not double counted as 'income'."""
    jargon = jargon or _JARGON
    lower = text.lower()
    # Denominator matches readability_scores()'s own word_count (naive split);
    # _WORD_RE below is for whole-word boundary matching only, not counting.
    n_words = max(len(text.split()), 1)
    multi = sorted([t for t in jargon if " " in t], key=len, reverse=True)
    single = {t for t in jargon if " " not in t}
    hits = hard = 0
    found = {}
    scratch = lower
    for term in multi:
        c = scratch.count(term)
        if c:
            hits += c
            hard += c * jargon[term]
            found[term] = found.get(term, 0) + c
            scratch = scratch.replace(term, " ")
    for w in _WORD_RE.findall(scratch):
        if w in single:
            hits += 1
            hard += jargon[w]
            found[w] = found.get(w, 0) + 1
    return {
        "jargon_density": round(hits / n_words * 1000, 2),
        "hard_jargon_density": round(hard / n_words * 1000, 2),
        "jargon_hits": hits,
        "jargon_terms": dict(sorted(found.items(), key=lambda kv: -kv[1])),
    }


def readability_scores(text: str) -> dict:
    text = (text or "").strip()
    if len(text.split()) < 20:
        return {k: None for k in (
            "flesch_reading_ease", "flesch_kincaid_grade", "gunning_fog",
            "smog_index", "dale_chall", "avg_sentence_length",
            "pct_complex_words", "word_count")}
    words = text.split()
    n = len(words)
    out = {
        "flesch_reading_ease": round(textstat.flesch_reading_ease(text), 1),
        "flesch_kincaid_grade": round(textstat.flesch_kincaid_grade(text), 1),
        "gunning_fog": round(textstat.gunning_fog(text), 1),
        "smog_index": round(textstat.smog_index(text), 1),
        "dale_chall": round(textstat.dale_chall_readability_score(text), 1),
        "avg_sentence_length": round(textstat.words_per_sentence(text), 1),
        "pct_complex_words": round(textstat.difficult_words(text) / n * 100, 1),
        "word_count": n,
    }
    out.update(jargon_density(text))
    return out


if __name__ == "__main__":
    import sys
    print(readability_scores(Path(sys.argv[1]).read_text()))
