"""
trust_engine.py — Module A: Trust Signal NLP Scoring Engine
===========================================================
Operationalises Mayer, Davis & Schoorman's (1995) model of trustworthiness as
a computable score over a provider's public-facing copy. The model decomposes
perceived trustworthiness into three antecedents:

    Ability     — skills/competencies enabling influence within a domain
    Benevolence — desire to do good for the trustor beyond a profit motive
    Integrity   — adherence to a set of principles the trustor finds acceptable

Method (v1 — transparent lexicon model)
---------------------------------------
1. Sentence-tokenise the text (NLTK punkt).
2. For each MDS dimension, match a curated, citable lexicon of cues
   (config/mds_lexicon.csv). Multiword cues are matched before unigrams.
3. Apply a 3-token NEGATION window:
     - a negated positive cue is discounted to 0 ("not transparent")
     - a negated trust-breaker hype cue earns a small INTEGRITY credit
       ("returns are NOT guaranteed" is an honest disclosure, not hype)
4. Normalise weighted hits per 1,000 words so long pages don't inflate, then
   squash to a 0-100 index per dimension via a saturating transform.
5. Composite Trust Signal Index = mean(Ability, Benevolence, Integrity)
   minus a penalty for trust-breaker density.

Every score ships with an AUDIT TRAIL (which cues fired, in which sentence),
so any number is defensible line-by-line — the key property for a viva and
the property a black-box LLM classifier cannot offer.

Upgrade path (documented in SPEC.md): the `score_dimension` interface is model
-agnostic. A zero-shot NLI transformer (e.g. facebook/bart-large-mnli) or
sentence-embedding similarity to MDS anchor statements can be swapped in
without changing the pipeline, when run in an environment with model access.
"""
from __future__ import annotations
import csv
import math
import re
from collections import defaultdict
from pathlib import Path

from nltk.tokenize import sent_tokenize

_CONFIG = Path(__file__).resolve().parent.parent / "config"
_NEGATIONS = {"not", "no", "never", "without", "isn't", "aren't", "won't",
              "don't", "doesn't", "cannot", "can't", "neither", "nor"}
_DIMENSIONS = ("ability", "benevolence", "integrity")
_TOKEN_RE = re.compile(r"[a-z][a-z'\-]+")


def load_lexicon(path: Path | None = None) -> dict:
    path = path or _CONFIG / "mds_lexicon.csv"
    lex: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            lex[row["dimension"]].append((row["cue"].strip().lower(),
                                          float(row["weight"])))
    # match longer cues first to avoid partial double counts
    for d in lex:
        lex[d].sort(key=lambda cw: len(cw[0]), reverse=True)
    return lex


_LEXICON = load_lexicon()


def _negated(sentence_tokens: list[str], cue_start_idx: int) -> bool:
    window = sentence_tokens[max(0, cue_start_idx - 3):cue_start_idx]
    return any(t in _NEGATIONS for t in window)


def _saturate(per_k: float, k: float = 0.18) -> float:
    """Map a non-negative rate to 0-100 with diminishing returns.
    k tuned so a 'rich' page (~12 weighted cues / 1k words) lands near ~80."""
    return round(100 * (1 - math.exp(-k * per_k)), 1)


def score_text(text: str, lexicon: dict | None = None) -> dict:
    lexicon = lexicon or _LEXICON
    sentences = sent_tokenize(text)
    # Denominator for "per 1k words" must match the word_count the rest of the
    # pipeline reports (extract.py/readability.py use a naive whitespace split).
    # _TOKEN_RE below is for cue-boundary matching only, not for counting.
    n_words = max(len((text or "").split()), 1)

    weighted = {d: 0.0 for d in _DIMENSIONS}
    breaker_w = 0.0
    audit = {d: [] for d in (*_DIMENSIONS, "trust_breaker")}

    for sent in sentences:
        low = sent.lower()
        consumed = low
        # positive dimensions
        for dim in _DIMENSIONS:
            for cue, w in lexicon[dim]:
                if cue in consumed:
                    # Find + window against `consumed`, not `low`: once a longer
                    # overlapping cue has replaced its span with " ", a shorter
                    # cue's remaining occurrence may sit at a different position
                    # than its first (already-consumed) occurrence in `low`.
                    pos = consumed.find(cue)
                    pre = _TOKEN_RE.findall(consumed[:pos])
                    if _negated(pre, len(pre)):
                        continue  # discount negated positive cue
                    weighted[dim] += w
                    audit[dim].append((cue, round(w, 2), sent.strip()[:160]))
                    consumed = consumed.replace(cue, " ")
        # trust breakers (with negation -> integrity credit)
        # own consumption tracker: some breaker cues are substrings of others
        # (e.g. "guaranteed" inside "guaranteed returns") and would otherwise
        # double-fire on the same span once the longer cue has already matched.
        breaker_consumed = low
        for cue, w in lexicon["trust_breaker"]:
            if cue in breaker_consumed:
                pos = breaker_consumed.find(cue)
                pre = _TOKEN_RE.findall(breaker_consumed[:pos])
                if _negated(pre, len(pre)):
                    weighted["integrity"] += 0.5 * w
                    audit["integrity"].append(
                        (f"(negated) {cue}", round(0.5 * w, 2), sent.strip()[:160]))
                else:
                    breaker_w += w
                    audit["trust_breaker"].append((cue, round(w, 2), sent.strip()[:160]))
                breaker_consumed = breaker_consumed.replace(cue, " ")

    per_k = {d: weighted[d] / n_words * 1000 for d in _DIMENSIONS}
    breaker_per_k = breaker_w / n_words * 1000
    idx = {d: _saturate(per_k[d]) for d in _DIMENSIONS}
    breaker_penalty = round(min(_saturate(breaker_per_k), 40), 1)  # cap penalty
    composite = round(max(0.0,
                          sum(idx.values()) / 3 - 0.5 * breaker_penalty), 1)

    return {
        "ability": idx["ability"],
        "benevolence": idx["benevolence"],
        "integrity": idx["integrity"],
        "trust_breaker_penalty": breaker_penalty,
        "trust_signal_index": composite,
        "weighted_cues_per_1k": {d: round(per_k[d], 2) for d in _DIMENSIONS},
        "word_count": n_words,
        "audit": audit,
    }


if __name__ == "__main__":
    import sys, json
    r = score_text(Path(sys.argv[1]).read_text())
    r.pop("audit")
    print(json.dumps(r, indent=2))
