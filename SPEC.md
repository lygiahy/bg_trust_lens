# BG Trust Lens — Technical Specification

**Workstream:** Trust (Hy) · **Module:** Stream 2 (NLP on public content)
**Status:** v1.3 — fixed page universe + coverage gate + ABI-consistent instrument dashboard; engine validated on a real 3-provider corpus with Python↔JS numeric parity, extended to a 9-provider live-capture freeze dated 2026-08-05 (§10.1; BlackRock excluded pending a reliable scrape)
**One-line:** *Input = a provider's public pages, labelled by role → Output = Trust Signal scores (Mayer, Davis & Schoorman, 1995) with credibility controls, readability, a coverage label and a line-by-line audit trail.*

---

## 1. Why this exists (link to assessment)

The team's marketing strategy already sits at distinction level; what is missing for 85+ is the **"Science in Marketing Science"** Colin Fu has asked for — applied computation, not description. This tool operationalises an academic framework (Mayer, Davis & Schoorman, 1995) as a measurement instrument and runs it on real data.

It serves three assessment needs at once:

- **A1 Section 3 (Hy's individual contribution):** opens with a quantitative method and a finding, not a literature summary — a classifier scoring providers on the three MDS trust dimensions, with credibility controls and readability, run across a fixed page universe.
- **A1 Section 7 (Implementation):** a concrete, reusable artefact BG can re-run each quarter — the "lasting value" Colin wants. Code + audit in Appendix C.
- **A2 (Hy's positioning):** self-owned, defensible evidence supporting the **Challenger** position — the instrument that makes partner-mediated trust risk visible and manageable.

**Design constraint that became an advantage:** the tool uses **public data only** (no BG internal Looker/CRM, no dependence on BG data staff). BG can re-run it without piping confidential data into a student tool — a cleaner handover and a fairer test of the team's own technical capability.

---

## 2. Scope — two benchmark panels

- **Peer panel (asset managers):** Baillie Gifford + Vanguard, abrdn, Fidelity, BlackRock iShares, Fundsmith. Answers *"among direct competitors, where does BG stand?"* (the scope BG's Oliver Kitchen asked for).
- **Expectation panel (fintech):** Trading 212, Moneybox, Revolut, Monzo. Answers *"what clarity and trust standard have young investors already learned to expect?"* — the entry points where the literature says trust is first formed.

Both panels are needed because the 16–25 audience does not benchmark BG against other asset managers; it benchmarks BG against the apps it already uses. The registry is extensible to any provider (§3); public consumer copy only, no login or gated content.

### 2.1 Provider selection and audience comparability (caveat)

The four-slot page universe (homepage, fund/product, about/philosophy, guidance/support) enforces like-for-like comparison by **functional role** rather than by page title, so every provider is scored on the same kinds of page. One provider departs from this on **audience**, and the departure is disclosed rather than hidden. abrdn's UK asset-management site (aberdeeninvestments.com) addresses professional and institutional investors and intermediaries; it publishes no direct retail-investor section equivalent to the individual-investor pages of Baillie Gifford, Vanguard or Fidelity, because abrdn reaches retail clients through a separate platform brand (interactive investor) rather than through the asset-management site itself. abrdn's four slots are therefore populated from its professional-investor pages.

This was retained deliberately rather than dropped. Removing abrdn would lose a major active UK peer and weaken the benchmark, and the page-role comparison still holds: each abrdn slot is the correct functional page, only addressed to a different reader. abrdn's Trust Signal and readability scores should accordingly be read as the signals it sends to a **professional** audience, and treated as **indicative** rather than strictly equivalent to peers' retail copy; the coverage label and this note flag that explicitly.

The audience gap is itself informative. That several traditional managers — abrdn most starkly, but Baillie Gifford too, which states it offers "no online service for individual investors" — present limited or no retail-facing transactional content indicates that they reach 16–25 investors largely **through** third-party platforms. The first trust-forming touchpoint is thus delegated to intermediaries the manager does not control, which is the partner-mediated trust exposure this workstream sets out to make visible. The caveat is therefore not only a limitation of the abrdn data point but corroborating evidence for the report's central argument.

---

## 3. Page universe and coverage gate (evidence architecture)

### 3.1 Four functional slots, defined by role
A single page is not a fair basis for comparison: different providers put different content on different pages. Every provider is therefore scored across the same **four page types, defined by what the page does for a young investor**, not by its title:

| Slot | Investor question it answers | Grounding |
|---|---|---|
| **Homepage** | first impression, the overall promise | first trust-forming touchpoint |
| **Fund / product** | where does my money go, what does it cost, how has it done | survey Q15 (what young investors check); Ability + Integrity + Substantiation |
| **About / philosophy** | who runs my money, do they care about me | survey Q15 (who they are / trustworthiness); Benevolence + Ability |
| **Guidance / support** | do they help me understand this in plain English | survey Q9 (education need); Readability + Integrity |

Regulatory/risk copy is not a fifth slot: FCA/FSCS and risk language lives inside fund/product and support pages and is captured by the Integrity dimension and the candour control. The design matches the page-type matrix BG's client contact originally suggested.

### 3.2 Three states per slot; the labeller asserts, the engine never guesses
Each slot is in exactly one state:

| State | Meaning | Effect |
|---|---|---|
| `filled_reliable` | URL(s) given; fetched text ≥ 150 words | counted as evidence |
| `attempted_failed` | URL(s) given; fetch below threshold (JS app / anti-bot) | counted as missing; flagged |
| `not_applicable` | the human labeller asserts the provider has no such page type | **removed from the coverage denominator** — a minimal provider is not penalised for a page it was never meant to have |
| `not_provided` | no URL given | counted as missing |

Distinguishing *structurally absent* from *scrape failed* is what keeps the comparison fair to minimal, app-first providers.

### 3.3 Coverage gate
A score is only published with a label stating how much evidence sits behind it:

- **Reliable** (extraction risk Low) — homepage captured **and** enough supporting slots reliable (homepage + 2 others, scaled down when slots are N/A).
- **Partial** (Medium) — at least two reliable page types, or a single-page score; the note names exactly what is missing. A missing homepage is always flagged.
- **Insufficient** (High) — nothing captured reliably; **no Trust Index is shown** rather than a misleading one.

**The homepage is the preferred anchor but is deliberately not mandatory.** Several fintech homepages are unscrapeable single-page apps while their fund, about and help-centre pages scrape cleanly; requiring the homepage would re-break exactly the providers the tool exists to monitor. Its absence is therefore flagged, never fatal.

### 3.4 Generic by construction
The gate and the scorer read only slot states and text — never provider names. Adding provider #11 is one block in `config/providers.yaml` (or the **+ add another provider** row in the dashboard); the same acquisition, gate and scoring apply with no code change. Unverified URLs are safe by design: a wrong or dead URL surfaces as `attempted_failed`, never as a silent zero.

---

## 4. Acquisition ladder

Live fetching escalates only as far as needed, and reports what it did:

1. **Static fetch** with a realistic browser User-Agent; extraction via `trafilatura` (primary) with a BeautifulSoup fallback.
2. **Headless rendering** (Playwright Chromium) when the static pass yields under **150 words** — the threshold that separates real copy from an app shell.
3. **Flag and exclude** — anything still below threshold is marked `SCRAPE_FAILED` with the word count and reason, excluded from scoring, and shown in the run log.

The single-file dashboard cannot run a headless browser, so it approximates the ladder with a chain of CORS-friendly fetch routes (a server-side rendering proxy first), keeps the **best** result per URL, and applies the same 150-word gate. Per-slot outcomes appear in the run log and as the evidence strip on each score card.

---

## 5. Input / output contract

| | |
|---|---|
| **Input** | `config/providers.yaml` — per provider, four slots each holding one or more URLs or `{na: true}`; OR the dashboard matrix (same schema, editable in-browser); OR raw pasted copy; OR cached `corpus/*.txt`. |
| **Output** | `outputs/scores.csv` (one row per provider) · `outputs/report.html` (charts + audit trail) · the interactive single-file dashboard `BG_Trust_Lens_dashboard.html`. |

Per-provider row schema: `provider, coverage_status, extraction_risk, ability, benevolence, integrity, trust_signal_index, candour_density, substantiation_pct, spin_index, lm_polarity, flesch_reading_ease, flesch_kincaid_grade, jargon_density, hard_jargon_density, word_count`. The dashboard CSV export carries the same trust/credibility/readability fields plus `Coverage` and `ExtractionRisk`.

---

## 6. Module A — Trust Signal NLP engine

### 6.1 Construct operationalisation (MDS 1995)
Mayer, Davis & Schoorman decompose perceived trustworthiness into three antecedents. Each is mapped to observable text cues:

- **Ability** — competence within the domain: *expertise, track record, research, investment team, founded 1908, actively managed*.
- **Benevolence** — wanting to do good for the trustor beyond profit: *help you, your goals, plain English, education, beginners, tailored, on your behalf*.
- **Integrity** — adherence to acceptable principles: *transparent, capital at risk, FCA/FSCS, fees, past performance is not a reliable guide, where your money goes*.

A negative **trust-breaker** set operationalises the project's own literature on trust breakers: hype, overpromising and pressure selling (*guaranteed returns, get rich, act now, risk-free*).

The full lexicon — **133 weighted cues: 39 ability, 35 benevolence, 42 integrity, 17 trust-breaker** — lives in `config/mds_lexicon.csv`, transparent and editable, not hidden in code. The lexicon and the Direction-B controls are **theory-grounded operationalisations built for this project**; the readability formulas and the Loughran–McDonald dictionary are published instruments used as published. The code and report keep that distinction explicit.

### 6.2 Scoring procedure
1. Sentence-tokenise (NLTK punkt). 2. Match cues (multiword before unigram). 3. **Negation window (3 tokens):** a negated positive cue is discounted ("*not* transparent"); a negated hype cue earns a small integrity credit ("returns are *not* guaranteed" is honest disclosure). 4. Normalise weighted hits **per 1,000 words** so long pages don't inflate. 5. Squash to 0–100 with a saturating transform `100·(1−e^(−k·rate))`, `k = 0.18`. 6. **Trust Signal Index** = mean(Ability, Benevolence, Integrity) − ½ · trust-breaker penalty (penalty capped at 40).

### 6.3 Audit trail (the defensibility property)
Every score ships with the exact cues that fired ("words behind the score" on each dashboard card; audit table in `report.html`). A number is defensible line-by-line — *"why does BG score 89 on Ability? These competence cues, in these sentences"* — a property a black-box LLM classifier cannot offer.

### 6.4 Validity and reliability
- **Content validity:** cues derive directly from the MDS construct definitions and the team's literature synthesis.
- **Reliability:** deterministic and fully reproducible; no model randomness; re-running yields identical scores.
- **Cross-implementation parity:** the dashboard is a JavaScript port of the Python engine. On the cached corpus the two produce **identical values on every trust, credibility and jargon metric**. The only permitted divergence is Flesch/Flesch–Kincaid, where both implement the published formulas but use different syllable estimators (`textstat`/pyphen in Python vs a compact heuristic in JS). **Citable readability values are the Python `textstat` ones;** the dashboard footer discloses the approximation. Ranking is unaffected.
- **Threats:** (a) a bag-of-cues misses deep semantics; (b) short pages understate a provider — mitigated by the four-slot universe and the coverage gate rather than by ad-hoc URL stacking; (c) cue weights are expert-set, not learned — exposed for scrutiny and sensitivity-testable.

### 6.5 Upgrade path (documented, not required for v1)
`trust_engine.score_text` is model-agnostic. Drop-in replacements without touching the pipeline: zero-shot NLI (classify each sentence against the three MDS hypotheses; aggregate entailment) or embedding similarity to MDS anchor statements. Report convergent validity against the lexicon model.

---

## 7. Module B — Readability benchmarker

Turns the qualitative finding *"jargon and complexity are trust breakers; clarity is a trust signal"* into numbers. Computes (via `textstat`): Flesch Reading Ease, Flesch–Kincaid Grade, Gunning Fog, SMOG, Dale–Chall, average sentence length, % complex words, plus a domain-specific **jargon density** (55 finance terms per 1,000 words, defined relative to a 16–25 novice; `config/finance_jargon.csv`) and a **hard-jargon density** (the 29 novice-blocking terms: OEIC, drawdown, KIID…).

Interpretation bands (Flesch Reading Ease): 70–100 easy (≈ school grade ≤7) · 50–70 fairly difficult · <50 difficult (college+). Copy scoring <50 raises an accessibility/trust flag for a first-time investor.

**Jargon density is validated, not assumed.** On the test corpus it is not redundant with Flesch (Trading 212 is the decisive counter-example — syntactically easy yet the most jargon-dense), so it captures a distinct *terminology* barrier. Hard-jargon sharpens this: Moneybox carries jargon but zero hard-jargon; BG and Trading 212 carry the blocking kind. An *unexplained-jargon* ratio was tested and dropped from v1 as unreliable on short copy; flagged for a v2 LLM check. *The corpus is small, so correlations are illustrative.*

**Module separation is a display rule, not just a computation rule.** Readability is never mixed into the Trust Index, and the dashboard renders it under an explicit divider ("separate module — not in the Trust Index") in the score cards, the benchmark matrix and the competitor profile, so the instrument cannot be misread as a four-dimension trust model.

---

## 8. Module C — Credibility controls (Direction B)

The trust engine counts positive cues, but every company website is written to read positively. Module C adds controls that sit **alongside** the Trust Index, never inside it, so promotion and substance stay visible separately:

- **Candour density** — risk-disclosure / two-sided language per 1,000 words (19-term candour list). Two-sided message credibility: Eisend (2006).
- **Substantiation %** — share of positive-claim sentences carrying concrete evidence (number, %, £, FCA/FSCS). Claim substantiation / impression management: Lyon & Montgomery (2015).
- **Spin index (0–100)** — puffery ÷ (puffery + candour), from a 31-term puffery/urgency list. High = one-sided promotion.
- **LM polarity** (optional, Python build) — Loughran & McDonald (2011) financial tone as an academic cross-check; LM's negative list is 10-K-oriented and under-detects retail risk language, hence the domain candour list.

---

## 9. The dashboard as instrument

A single self-contained HTML file (no install, no server) that ports the engine to JavaScript with verified numeric parity (§6.4). Display rules follow the methodology:

- **Construct labels are the framework's labels.** Every trust score is displayed as **Ability / Benevolence / Integrity** — the MDS construct names — with plain-English glosses as secondary text. No renamed or invented dimensions appear anywhere in the interface.
- **Calibrated gauges.** Every metric renders on a tick-marked scale (25/50/75) with the **current run's median** as a reference tick, so each value carries instant peer context.
- **Evidence strip.** Each provider card and run-log line shows the four slots (HOME · FUND · ABOUT · GUIDE) coloured by state, making the coverage architecture visible per provider.
- **Coverage badge + note** (Reliable / Partial / Insufficient) on every card, in the summary table and in the CSV export; Insufficient providers are reported but not scored.
- **Regulator-reference flag (REG).** Surfaces whether the copy **names** its regulator or compensation scheme (FCA/FSCS cues already captured in the Integrity audit trail). Display-only: no new scoring, no new data.
- **Engine readout** (cue count computed from the loaded lexicon at runtime) and the two scoring formulas shown in "How the scores work".
- Views: Analyse (matrix input → cards + summary), Peer Benchmarking (trust-score chart, signal matrix with the readability row below a labelled divider, comparative snippets on the highest-variance dimension), Competitor Profile (delta vs BG, signal mix, peer bars, evidence snippets), Word List (the full lexicon, searchable), CSV export.

---

## 10. Validated result (canonical corpus)

Reproducible reference run on the cached 3-provider corpus (`corpus/*.txt`, committed as plain text). Values are Python `textstat` outputs; the JS dashboard matches on every non-Flesch metric (§6.4).

> **Changelog, 2026-08-05:** `trust_engine.py` and `bias.py` normalized their "per 1,000 words" rates against a regex-token word count that silently excluded numbers/£/%/tickers, while the reported `word_count` (and the `MIN_WORDS` coverage gate) used a plain whitespace split — two different denominators inside one pipeline. Fixed by making every normalizer use the same whitespace-split count `word_count` already reports. All numbers below and in §10.1 are the corrected, re-frozen values; the fix left `spin_index`/`substantiation_pct` unchanged (their word-count denominator cancels out algebraically) but shifted every other density metric, most visibly for number-dense pages (see Vanguard in §10.1).
>
> **Changelog, 2026-08-06:** two further fixes in `trust_engine.py::score_text` (and mirrored in the JS dashboard's `scoreTrust`/`wordCount`), neither changing any number below — both are narrow edge cases that don't trigger in the current 9-provider corpus, verified by re-running the full offline pipeline before/after: (1) the negation-window lookup searched cue position in the original sentence text instead of the running "already-matched" text, which could misjudge negation for a cue that is a substring of an already-consumed longer cue; (2) trust-breaker cues weren't deduplicated against overlapping cues in their own lexicon (e.g. "guaranteed" inside "guaranteed returns"), risking double-counting the same phrase as two breaker hits — now consumed the same way the positive-dimension cues already were. The JS dashboard's `wordCount()` was also switched from a regex-token count to the same whitespace-split convention as the Python fix above, for genuine cross-language parity (see §10 footnote below on a separate, larger parity gap this surfaced).

| Provider | Trust Index | Ability | Benevolence | Integrity | Spin % | Subst % | Candour /1k | Flesch | Hard-jargon /1k |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Moneybox *(fintech)* | **90.2** | 75.3 | 95.8 | 99.6 | 17 | 11 | 17.7 | 71.8 (easy) | 0.0 |
| Baillie Gifford | **74.8** | 88.7 | 54.8 | 80.9 | **67** | 20 | 3.7 | 44.3 (difficult) | 7.35 |
| Trading 212 *(fintech)* | **32.9** | 0.0 | 0.0 | 98.7 | 60 | 0 | 12.7 | 65.8 (easy) | 6.33 |

**Headline finding:** BG shows the strongest **Ability** signals of the corpus but its copy is the most **one-sided** (spin 67) and the **hardest to read** (Flesch 44.3, grade ≈ 11), with the most novice-blocking jargon. The credibility controls confirm the client's instinct — every site reads positively, but candour, substantiation and spin separate genuine trust signals from polish. *(Trading 212's zeros on Ability/Benevolence and 0% substantiation reflect a short cached homepage — exactly the single-page understatement the four-slot universe and coverage gate exist to fix in live runs.)*

Live multi-provider results depend on what each run captures; they are therefore always published **with** their coverage label and evidence strip rather than as bare numbers.

> **Resolved, 2026-08-06 — sentence-tokenizer parity gap (opened earlier the same day).** Root cause was confirmed to be `splitSentences`: JS split on every `.`/`!`/`?` naively, while Python sentence-splits with NLTK's trained `punkt` model, which by default treats *any* period-final token as a sentence break **unless** it matches punkt's own trained abbreviation list (extracted directly from the shipped model: 155 entries — country/company/title abbreviations, month names, etc. — not hand-guessed). Ported that same list and default-break rule into `splitSentences`. Real punkt can still flip a matched abbreviation back to a break using a 20k-entry per-word learned table (whether that *specific following word* has ever been seen capitalised mid-sentence) — not ported, as it's WSJ-trained and not worth the file size for a self-contained dashboard. A naive proxy for it ("next word capitalised ⇒ new sentence") was tried and measured **worse** on this project's real corpus (total abs. scoring error 22.6 vs 5.2 across all 9 providers, on rules that otherwise matched) — financial copy constantly follows abbreviations like "U.K."/"U.S." with capitalised product names ("U.K. Equity Index Fund"), which isn't a new sentence. Final rule: abbreviation match ⇒ never a break. Verified against NLTK directly (not assumed): sentence counts match exactly on 8 of 9 cached providers; full downstream scores (ability/benevolence/integrity/Trust Index/candour/substantiation/spin/jargon/hard-jargon/word count) match **exactly** on 7 of 9 providers (including Vanguard, previously the worst case — `ability` 95.9→66.9, now bang on), with only Revolut (`integrity` off by 0.9) and Monzo (`substantiation_pct` off by 3) showing any residual gap. Re-verify this note if `config/mds_lexicon.csv` or the provider corpus changes materially, since the error figures above are measured against the current 9-provider freeze specifically, not a general guarantee.

### 10.1 9-provider live freeze — frozen 2026-08-05 (re-frozen same day after the word-count fix above)

A second reproducible reference, alongside (not replacing) the 3-provider table above. On 2026-08-05, 6 additional providers were fetched live (`report.py`'s live acquisition path — real-browser UA, headless-Chromium render fallback for JS-hydrated pages, coverage gate) and their extracted text frozen into `corpus/*.txt` as plain text, exactly like the original 3. `pipeline.run(use_live=False)` on this 9-provider corpus is deterministic from this point forward; the numbers below are locked by `tests/test_canonical.py::test_nine_provider_freeze_2026_08_05`.

| Provider | Trust Index | Ability | Benevolence | Integrity | Spin % | Subst % | Candour /1k | Flesch | Hard-jargon /1k | Words |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Moneybox *(fintech)* | **90.2** | 75.3 | 95.8 | 99.6 | 17 | 11 | 17.7 | 71.8 | 0.0 | 283 |
| Fidelity | **76.3** | 81.1 | 77.8 | 93.4 | 28 | 31 | 5.0 | 37.6 | 1.26 | 1,590 |
| Baillie Gifford | **74.8** | 88.7 | 54.8 | 80.9 | 67 | 20 | 3.7 | 44.3 | 7.35 | 272 |
| Revolut *(fintech)* | **72.7** | 65.4 | 62.5 | 90.1 | 26 | 38 | 4.8 | 45.9 | 2.76 | 2,897 |
| Monzo *(fintech)* | **58.4** | 31.7 | 83.5 | 59.9 | 87 | 42 | 0.4 | 57.8 | 22.30 | 2,601 |
| Fundsmith | **53.5** | 72.2 | 13.1 | 75.2 | 35 | 41 | 1.7 | 38.1 | 9.10 | 2,308 |
| Vanguard | **49.4** | 66.9 | 57.3 | 27.7 | 4 | 44 | 16.4 | 78.6 | 2.13 | 7,497 |
| abrdn | **46.2** | 94.6 | 23.8 | 20.2 | 0 | 8 | 2.5 | 53.3 | 0.0 | 1,593 |
| Trading 212 *(fintech)* | **32.9** | 0.0 | 0.0 | 98.7 | 60 | 0 | 12.7 | 65.8 | 6.33 | 158 |

**Vanguard moved from 5th to 8th of 9 after the word-count fix** (Trust Index 70.3 → 49.4, hard-jargon 4.23 → 2.13/1k). Its fund-listing page is dense with tickers/percentages/ISINs that the old regex-token denominator silently excluded, undercounting its true word count by roughly half (3,780 vs the reported 7,497) — every "per 1k" rate was correspondingly inflated. This is very likely what the pre-fix reconciliation below flagged as an "unexplained" swing; it is now understood, not open.

**BlackRock iShares is deliberately absent.** Every live attempt against `ishares.com` on 2026-08-05 failed the coverage gate (0–126 words per slot, below the 150-word `MIN_WORDS` reliability threshold, even after the headless-Chromium render fallback) — consistent with Cloudflare/anti-bot blocking rather than a genuinely thin page. Per project policy, a failed scrape is flagged (`outputs/fetch_log_2026-08-05.txt`) and excluded from scoring rather than published as a stub; it is not merged into `corpus/` and is asserted absent in `tests/test_canonical.py::test_blackrock_excluded_pending_reliable_scrape`. Trading 212 and Baillie Gifford's rows above are the untouched original 3-provider canonical text — their live fetch attempts that day did not clear the coverage gate either (Trading 212) or were simply not needed (Baillie Gifford's canonical text was already reliable), so neither was refreshed.

**Caution — same-day reconciliation flagged a real discrepancy, not just fetch noise.** An earlier live capture on 2026-08-05 (21:36, `outputs/benchmark_live_10providers.csv`, not reproducible — its underlying text was not preserved, and predates the word-count fix above) scored all 10 providers, including a working BlackRock (41.6) and Trading 212 (83.9). Diffing that run against the frozen one above shows word counts differing by 1.7–2.8× across all 6 overlapping providers (e.g. abrdn 4,481 → 1,593 words, Vanguard 4,087 → 7,497 words), driving Trust Index deltas of up to ~26 points (abrdn 71.9 → 46.2) — well outside normal fetch-to-fetch noise. abrdn's swing is explained by a coverage regression (homepage extraction failed on the second attempt); Vanguard's swing is now explained by the word-count fix above. **The table above, not the 21:36 capture, is the citable reference** — it is the only one of the two backed by inspectable cached text (§11's "corpus cached as plain text the marker can open" principle).

---

## 11. Reproducibility, ethics, conduct

- Public data only; no personal data; no gated content. Aligns with the ethics approval and the no-fabricated-data rule.
- Deterministic and version-controlled; corpus cached as plain text the marker can open; scrape log records URL, word count, method and reason for every fetch.
- AI category **Assistive**: Hy authors the method, lexicon and interpretation; AI assistance documented per UCL guidance.

## 12. Roadmap

1. Full live run across the 10-provider registry; publish scores with coverage labels. 2. Sensitivity analysis on cue weights. 3. Zero-shot transformer layer; report convergent validity. 4. Optional: extend trust scoring to social copy (BG Prize TikTok captions/transcripts). 5. Quarterly re-run protocol for BG handover.

## 13. References

Eisend, M. (2006) 'Two-sided advertising: A meta-analysis', *International Journal of Research in Marketing*, 23(2), pp. 187–198.
Flesch, R. (1948) 'A new readability yardstick', *Journal of Applied Psychology*, 32(3), pp. 221–233.
Kincaid, J.P., Fishburne, R.P., Rogers, R.L. and Chissom, B.S. (1975) *Derivation of new readability formulas for Navy enlisted personnel*. Research Branch Report 8-75. Memphis: Naval Air Station.
Loughran, T. and McDonald, B. (2011) 'When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks', *Journal of Finance*, 66(1), pp. 35–65.
Lyon, T.P. and Montgomery, A.W. (2015) 'The means and end of greenwash', *Organization & Environment*, 28(2), pp. 223–249.
Mayer, R.C., Davis, J.H. and Schoorman, F.D. (1995) 'An integrative model of organizational trust', *Academy of Management Review*, 20(3), pp. 709–734.
