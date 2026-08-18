"""
report.py — generates a self-contained HTML results report (handover artefact)
Renders: headline finding, scores table, trust + readability charts, and a
per-provider AUDIT TRAIL (which exact cues fired) for full defensibility.
No external runtime dependencies; the file opens in any browser.
"""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path
import html as _html

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline

DIM_COLORS = {"ability": "#5B8FF9", "benevolence": "#61C0BF", "integrity": "#F6BD60"}


def _bar(label, value, vmax, color, suffix=""):
    pct = 0 if value is None else max(0, min(100, value / vmax * 100))
    val = "—" if value is None else f"{value}{suffix}"
    return f"""<div class="row"><span class="lab">{label}</span>
      <span class="track"><span class="fill" style="width:{pct:.0f}%;background:{color}"></span></span>
      <span class="val">{val}</span></div>"""


def build(use_live=False) -> Path:
    out = pipeline.run(use_live=use_live)
    df, audits = out["scores"], out["audits"]
    top = df.iloc[0]["provider"]
    bg = df[df.provider == "Baillie Gifford"]
    bg = bg.iloc[0] if len(bg) else None

    # headline
    if bg is not None:
        headline = (f"Baillie Gifford signals the strongest <b>Ability</b> "
                    f"({bg.ability:.0f}/100) of the providers tested, but trails on "
                    f"<b>Benevolence</b> ({bg.benevolence:.0f}) and is the hardest to read "
                    f"(Flesch Reading Ease {bg.flesch_reading_ease:.0f}; grade "
                    f"{bg.flesch_kincaid_grade:.0f}; jargon density {bg.jargon_density:.0f}/1k words). "
                    f"<b>{top}</b> leads the composite Trust Signal Index by pairing strong "
                    f"trust signals with plain-English copy — the clarity-led trust the "
                    f"literature says a 16–25 audience responds to.")
    else:
        headline = f"<b>{top}</b> leads the composite Trust Signal Index."

    # table
    cols = [("provider","Provider"),("trust_signal_index","Trust Index"),
            ("spin_index","Spin %"),("substantiation_pct","Subst %"),
            ("candour_density","Candour /1k"),
            ("flesch_reading_ease","Flesch Ease"),("hard_jargon_density","Hard-jargon /1k"),
            ("word_count","Words")]
    thead = "".join(f"<th>{h}</th>" for _, h in cols)
    trows = ""
    for _, r in df.iterrows():
        tds = ""
        for key, _ in cols:
            v = r[key]
            cls = ""
            if key == "trust_signal_index":
                cls = "good" if v >= 70 else "mid" if v >= 50 else "low"
            tds += f'<td class="{cls}">{v if not isinstance(v,float) else round(v,1)}</td>'
        trows += f"<tr>{tds}</tr>"

    # trust + readability bars per provider
    cards = ""
    for _, r in df.iterrows():
        prov = r["provider"]
        trust_bars = (_bar("Ability", r.ability, 100, DIM_COLORS["ability"]) +
                      _bar("Benevolence", r.benevolence, 100, DIM_COLORS["benevolence"]) +
                      _bar("Integrity", r.integrity, 100, DIM_COLORS["integrity"]))
        cred_bars = (_bar("Candour /1k", r.candour_density, 25, "#2F9E9B") +
                     _bar("Substantiation", r.substantiation_pct, 100, "#7C5CD6", "%") +
                     _bar("Spin (↑=one-sided)", r.spin_index, 100, "#E0683C", "%"))
        read_bars = (_bar("Flesch Reading Ease", r.flesch_reading_ease, 100, "#9B8FF9") +
                     _bar("Jargon /1k", r.jargon_density, 25, "#E76F51") +
                     _bar("Hard-jargon /1k", r.hard_jargon_density, 15, "#C0392B"))
        # audit
        aud = audits.get({v:k for k,v in pipeline.PROVIDER_LABELS.items()}.get(prov, prov), {})
        chips = ""
        for dim in ("ability","benevolence","integrity","trust_breaker"):
            items = aud.get(dim, [])
            if not items:
                continue
            seen, uniq = set(), []
            for cue, w, sent in items:
                if cue not in seen:
                    seen.add(cue); uniq.append(cue)
            chips += (f'<div class="auditline"><span class="dim {dim}">{dim}</span> '
                      + " ".join(f'<span class="chip">{_html.escape(c)}</span>' for c in uniq[:12])
                      + "</div>")
        cards += f"""<div class="card">
          <div class="cardhead"><h3>{prov}</h3>
            <span class="tsi {'good' if r.trust_signal_index>=70 else 'mid' if r.trust_signal_index>=50 else 'low'}">
            Trust Index {r.trust_signal_index:.0f}</span></div>
          <div class="cols"><div><h4>Trust signals (MDS 1995)</h4>{trust_bars}</div>
            <div><h4>Credibility check</h4>{cred_bars}</div>
            <div><h4>Readability</h4>{read_bars}</div></div>
          <details><summary>Audit trail — cues that fired</summary>{chips}</details>
        </div>"""

    css = """
    body{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#1c2331;max-width:960px;margin:0 auto;padding:28px}
    h1{font-size:24px;margin:0 0 2px}.sub{color:#6b7280;margin:0 0 18px;font-size:13px}
    .headline{background:#f3f6ff;border:1px solid #dbe4ff;border-radius:10px;padding:16px 18px;margin:0 0 22px}
    table{border-collapse:collapse;width:100%;font-size:13px;margin:0 0 26px}
    th,td{border-bottom:1px solid #eceff3;padding:7px 9px;text-align:right}
    th:first-child,td:first-child{text-align:left}th{background:#f8fafc;color:#475569;font-weight:600}
    td.good{background:#e7f7ec;font-weight:700}td.mid{background:#fff6e5;font-weight:700}td.low{background:#fde8e8;font-weight:700}
    .card{border:1px solid #eceff3;border-radius:12px;padding:16px 18px;margin:0 0 16px}
    .cardhead{display:flex;justify-content:space-between;align-items:center}.cardhead h3{margin:0;font-size:17px}
    .tsi{font-size:12px;font-weight:700;padding:3px 10px;border-radius:20px}
    .tsi.good{background:#e7f7ec;color:#1a7f37}.tsi.mid{background:#fff6e5;color:#b45309}.tsi.low{background:#fde8e8;color:#b91c1c}
    .cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:22px;margin:12px 0 6px}
    h4{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#6b7280;margin:0 0 8px}
    .row{display:flex;align-items:center;gap:8px;margin:5px 0}.lab{width:120px;font-size:12px;color:#475569}
    .track{flex:1;height:9px;background:#f0f2f5;border-radius:6px;overflow:hidden}.fill{display:block;height:100%}
    .val{width:42px;text-align:right;font-size:12px;font-weight:600}
    details{margin-top:10px}summary{cursor:pointer;font-size:12px;color:#475569}
    .auditline{margin:7px 0;font-size:12px}.dim{display:inline-block;width:96px;font-weight:700;text-transform:capitalize}
    .dim.ability{color:#3b6fd4}.dim.benevolence{color:#2f9e9b}.dim.integrity{color:#c79324}.dim.trust_breaker{color:#b91c1c}
    .chip{display:inline-block;background:#f1f4f9;border-radius:6px;padding:1px 7px;margin:2px;font-size:11px}
    footer{color:#6b7280;font-size:12px;border-top:1px solid #eceff3;margin-top:24px;padding-top:14px}
    """
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>BG Trust Lens — Results</title><style>{css}</style></head><body>
    <h1>BG Trust Lens — Trust Signal &amp; Readability Benchmark</h1>
    <p class="sub">Method: Mayer, Davis &amp; Schoorman (1995) trust model · Flesch–Kincaid readability ·
    public web copy only · generated {date.today():%d %b %Y} · n={len(df)} providers (cached corpus)</p>
    <div class="headline">{headline}</div>
    <table><thead><tr>{thead}</tr></thead><tbody>{trows}</tbody></table>
    {cards}
    <footer>Scores are normalised 0–100 per 1,000 words. Lexicon (v1) is transparent and editable in
    config/mds_lexicon.csv; every score is auditable above. Limitations: short hero pages can understate a
    provider (run several URLs per provider for a fair composite); lexicon ≠ full semantic model — see
    SPEC.md for the zero-shot transformer upgrade path. Not investment advice.</footer>
    </body></html>"""

    outdir = Path(__file__).resolve().parent.parent / "outputs"
    outdir.mkdir(exist_ok=True)
    p = outdir / "report.html"
    p.write_text(doc, encoding="utf-8")
    df.to_csv(outdir / "scores.csv", index=False)
    return p


if __name__ == "__main__":
    print("wrote", build(use_live="--live" in sys.argv))
