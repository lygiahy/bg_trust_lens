"""
pipeline.py — orchestration
===========================
Runs the Trust Signal engine, Readability benchmarker and Direction-B credibility
controls over a set of providers, with a fixed 4-slot page universe and a coverage
gate so a score is only published when there is enough reliable evidence behind it.

Text comes from either:
  - the cached ./corpus  (default, reproducible offline demo), or
  - live URLs in config/providers.yaml  (use_live=True; needs network + renderer).
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract
import readability as rd
import trust_engine as te
import bias as bz
from coverage import SLOTS, SLOT_LABELS, slot_state, coverage_status

PROVIDER_LABELS = {
    "baillie_gifford": "Baillie Gifford", "trading_212": "Trading 212",
    "moneybox": "Moneybox", "revolut": "Revolut", "monzo": "Monzo",
    "vanguard": "Vanguard", "abrdn": "abrdn", "fidelity": "Fidelity",
    "blackrock": "BlackRock iShares", "fundsmith": "Fundsmith",
}

_POS_CUES = [c for d in ("ability", "benevolence", "integrity")
             for c, _ in te.load_lexicon()[d]]


def _wc(t: str) -> int:
    return len((t or "").split())


def _slot_urls(raw):
    """Normalise a slot spec into (urls, na)."""
    if isinstance(raw, dict):
        return [], bool(raw.get("na", False))
    if isinstance(raw, list):
        return [u for u in raw if u], False
    if isinstance(raw, str):
        return [raw], False
    return [], False


def _acquire_live(providers_yaml):
    import yaml
    cfg = yaml.safe_load(open(providers_yaml or
          Path(__file__).resolve().parent.parent / "config" / "providers.yaml"))
    providers = cfg.get("providers", {})
    texts, coverage, scrape_report = {}, {}, []

    for prov, spec in providers.items():
        label = spec.get("label", PROVIDER_LABELS.get(prov, prov))
        states, slot_meta, combined_parts = {}, {}, []

        for slot in SLOTS:
            urls, na = _slot_urls(spec.get(slot, []))
            slot_parts, words_total = [], 0
            for u in urls:
                p = extract.fetch_page(u)
                scrape_report.append({"provider": label, "slot": slot, "url": p["url"],
                                      "words": p["words"], "method": p["method"],
                                      "ok": p["ok"], "reason": p["reason"]})
                words_total += p["words"]
                if p["ok"]:
                    slot_parts.append(p["text"])
            slot_text = "\n\n".join(slot_parts)
            st = slot_state(urls, na, bool(slot_parts))
            states[slot] = st
            slot_meta[slot] = {"state": st, "words": _wc(slot_text) if slot_parts else words_total,
                               "urls": urls, "na": na}
            if slot_parts:
                combined_parts.append(slot_text)

        cov = coverage_status(states)
        cov["slots"] = slot_meta
        coverage[prov] = cov
        if cov["status"] != "Insufficient" and combined_parts:
            joined = "\n\n".join(combined_parts)
            extract.cache_text(prov, joined)
            texts[prov] = joined

    return texts, coverage, scrape_report


def run(use_live: bool = False, providers_yaml: Path | None = None) -> dict:
    if use_live:
        texts, coverage, scrape_report = _acquire_live(providers_yaml)
        failed = [r for r in scrape_report if not r["ok"] and r["words"] is not None]
        if failed:
            print(f"\n[SCRAPE WARNINGS] pages below the {extract.MIN_WORDS}-word "
                  "reliability threshold (excluded from scoring):")
            for r in failed:
                print(f"  - {r['provider']:<18} [{r['slot']:<16}] {r['words']:>5}w  {r['url']}")
            print()
        print("[COVERAGE]")
        for prov, c in coverage.items():
            label = PROVIDER_LABELS.get(prov, prov)
            print(f"  - {label:<18} {c['status']:<12} (risk {c['extraction_risk']}) — {c['note']}")
        print()
    else:
        texts, coverage, scrape_report = extract.load_corpus(), {}, []

    rows, audits = [], {}
    for prov, text in texts.items():
        t = te.score_text(text)
        r = rd.readability_scores(text)
        b = bz.bias_controls(text, _POS_CUES)
        audits[prov] = t.pop("audit")
        cov = coverage.get(prov, {})
        rows.append({
            "provider": PROVIDER_LABELS.get(prov, prov),
            "coverage_status": cov.get("status", "n/a"),
            "extraction_risk": cov.get("extraction_risk", "n/a"),
            "ability": t["ability"], "benevolence": t["benevolence"],
            "integrity": t["integrity"], "trust_signal_index": t["trust_signal_index"],
            "candour_density": b["candour_density"], "substantiation_pct": b["substantiation_pct"],
            "spin_index": b["spin_index"], "lm_polarity": b["lm_polarity"],
            "flesch_reading_ease": r["flesch_reading_ease"], "flesch_kincaid_grade": r["flesch_kincaid_grade"],
            "jargon_density": r["jargon_density"], "hard_jargon_density": r["hard_jargon_density"],
            "word_count": r["word_count"],
        })
    df = pd.DataFrame(rows).sort_values("trust_signal_index",
                                        ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
    return {"scores": df, "audits": audits, "coverage": coverage, "scrape_report": scrape_report}


if __name__ == "__main__":
    out = run(use_live="--live" in sys.argv)
    pd.set_option("display.width", 220, "display.max_columns", 20)
    if len(out["scores"]):
        print(out["scores"][["provider", "coverage_status", "extraction_risk",
                             "trust_signal_index", "spin_index", "word_count"]].to_string(index=False))
        outdir = Path(__file__).resolve().parent.parent / "outputs"
        outdir.mkdir(exist_ok=True)
        out["scores"].to_csv(outdir / "scores.csv", index=False)
        print("\nsaved -> outputs/scores.csv")
