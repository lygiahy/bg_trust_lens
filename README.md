# BG Trust Lens

A self-contained tool that scores an asset manager's and its competitors' **public web copy** on:
- **Trust signals** — Mayer, Davis & Schoorman (1995): Ability, Benevolence, Integrity, plus trust-breaker penalty → composite Trust Signal Index (0–100).
- **Readability** — Flesch–Kincaid family + finance **jargon density**.

Built for the Baillie Gifford × UCL project (Trust workstream). See `SPEC.md` for the full method and `outputs/report.html` for results.

## No-code option (recommended for BG stakeholders)

Open **`BG_Trust_Lens_dashboard.html`** in any browser — no install, no terminal.
Choose a comparison group (**Asset managers** = BG's direct rivals, or **Fintech apps** = what young
investors expect), then click **Run analysis**. Each provider gets Trust signals (MDS 1995), a **Credibility check** (Candour / Substantiation / Spin — so a high score can't just mean 'positive copy'), and Readability (incl. hard-jargon). Click **Show a worked example** to see it run instantly. Click **Load example** to see it run instantly on
cached real copy. If a site blocks fetching, use **Paste text instead**.

## Install (for the Python pipeline / live batch runs)
```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

## Run

**On the cached corpus (real fetched copy — 9 providers as of the 2026-08-05 freeze, see SPEC.md §10/§10.1):**
```bash
python src/report.py            # writes outputs/report.html + outputs/scores.csv
python src/pipeline.py          # prints the scores table
```

**Live, on the homepages in `config/providers.yaml` (needs network):**
```bash
# one-time, to render JS-heavy sites (Moneybox, Revolut, Trading 212, ...):
pip install playwright && playwright install chromium
python src/report.py --live
```
Live fetch uses a real browser User-Agent, falls back to a headless-Chromium
render when a page is JS-hydrated, and FLAGS any page that yields fewer than
`extract.MIN_WORDS` (150) words as a failed scrape (printed as a warning and
excluded from scoring) rather than scoring a stub. Without Playwright the run
still works but JS-only sites may be flagged as incomplete.

**Interactive (paste URLs or text):**
```bash
open BG_Trust_Lens_dashboard.html (the no-code tool)
```

## How to extend
- Edit `config/providers.yaml` to add URLs (3–4 per provider gives fairer composites).
- Edit `config/mds_lexicon.csv` to refine trust cues (transparent, weighted).
- Edit `config/finance_jargon.csv` to tune the novice-jargon list.

## Layout
```
config/   providers.yaml · mds_lexicon.csv · finance_jargon.csv · bias_lexicon.csv
corpus/   cached <provider>.txt (real fetched copy)
src/      extract · readability · trust_engine · bias (credibility) · coverage · pipeline · report
tests/    test_canonical.py (locks the 3- and 9-provider reference numbers)
outputs/  scores.csv · report.html · see outputs/README_outputs.md
BG_Trust_Lens_dashboard.html   no-code interactive tool
SPEC.md   full technical specification
```
Not investment advice. Public data only.
