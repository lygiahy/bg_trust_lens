"""
tests/test_canonical.py — hard-locks the reproducible offline results.

Two independent frozen sets, per SPEC.md §10:
  1. The original 3-provider canonical corpus (Baillie Gifford, Moneybox,
     Trading 212) — cached since the project's inception, never touched by a
     live run.
  2. The 2026-08-05 9-provider live freeze — the original 3 plus 6 more
     providers whose text was captured live on 2026-08-05 and frozen into
     corpus/ as plain text (see SPEC.md §10 and outputs/README_outputs.md).
     BlackRock iShares is deliberately absent: its live fetch failed the
     coverage gate that day (anti-bot blocking on ishares.com) and no
     reliable text exists to cache. It is asserted absent here rather than
     silently ignored, so a future successful scrape is a visible diff, not
     invisible scope creep.

Both run pipeline.run(use_live=False) against whatever is cached in corpus/
and filter to the providers each set locks — so set 1 stays valid even as
more providers are added to corpus/ over time.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pipeline  # noqa: E402

TOL = 0.15  # absolute tolerance: scoring functions round internally to 1-2dp


@pytest.fixture(scope="module")
def offline_scores():
    df = pipeline.run(use_live=False)["scores"]
    return df.set_index("provider")


def test_three_provider_canonical(offline_scores):
    """Locks the original cached corpus (SPEC.md §10), untouched by any live run.
    Values re-frozen 2026-08-05 after fixing the word-count normalization bug in
    trust_engine.py/bias.py (see SPEC.md changelog note under §10)."""
    expected = {
        "Moneybox":        dict(trust_signal_index=90.2, spin_index=17, word_count=283),
        "Baillie Gifford": dict(trust_signal_index=74.8, spin_index=67, word_count=272),
        "Trading 212":     dict(trust_signal_index=32.9, spin_index=60, word_count=158),
    }
    for provider, exp in expected.items():
        assert provider in offline_scores.index, f"{provider} missing from offline corpus"
        row = offline_scores.loc[provider]
        assert row["trust_signal_index"] == pytest.approx(exp["trust_signal_index"], abs=TOL)
        assert row["spin_index"] == pytest.approx(exp["spin_index"], abs=TOL)
        assert int(row["word_count"]) == exp["word_count"]


def test_nine_provider_freeze_2026_08_05(offline_scores):
    """Locks the 2026-08-05 live-capture freeze: the 3 canonical + 6 live-fetched
    providers merged into corpus/ that day. See SPEC.md §10 for the frozen table
    and outputs/fetch_log_2026-08-05.txt for the scrape evidence."""
    expected = {
        "Moneybox":        dict(trust_signal_index=90.2, word_count=283),
        "Fidelity":        dict(trust_signal_index=76.3, word_count=1590),
        "Baillie Gifford": dict(trust_signal_index=74.8, word_count=272),
        "Revolut":         dict(trust_signal_index=72.7, word_count=2897),
        "Monzo":           dict(trust_signal_index=58.4, word_count=2601),
        "Fundsmith":       dict(trust_signal_index=53.5, word_count=2308),
        "Vanguard":        dict(trust_signal_index=49.4, word_count=7497),
        "abrdn":           dict(trust_signal_index=46.2, word_count=1593),
        "Trading 212":     dict(trust_signal_index=32.9, word_count=158),
    }
    assert set(offline_scores.index) == set(expected), (
        "Cached provider set has drifted from the 2026-08-05 freeze — "
        "if you added/removed a provider's corpus text, update this test deliberately."
    )
    for provider, exp in expected.items():
        row = offline_scores.loc[provider]
        assert row["trust_signal_index"] == pytest.approx(exp["trust_signal_index"], abs=TOL)
        assert int(row["word_count"]) == exp["word_count"]


def test_blackrock_excluded_pending_reliable_scrape(offline_scores):
    """Documents the known gap: BlackRock iShares has no cached text as of the
    2026-08-05 freeze because ishares.com failed the coverage gate on every
    live attempt that day. Flip this test (and add blackrock.txt to corpus/)
    once a scrape actually clears MIN_WORDS."""
    assert "BlackRock iShares" not in offline_scores.index
