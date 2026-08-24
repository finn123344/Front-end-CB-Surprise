#!/usr/bin/env python3
"""Run the front-end repricing event study.

    python run_study.py --demo                 # synthetic data, no network
    python run_study.py --events data/events.csv   # your scored archive + free market data

Outputs: output/summary.png (the chart) and output/findings.md (the numbers).
"""

import argparse
from pathlib import Path

import pandas as pd

from cb_surprise.config import MARKET_MAP, StudyConfig
from cb_surprise.event_study import run_study
from cb_surprise.plots import summary_chart
from cb_surprise.quoting import quote_table
from cb_surprise.surprise import add_surprise

OUT = Path(__file__).resolve().parent / "output"


def load_events(path: str) -> pd.DataFrame:
    ev = pd.read_csv(path, parse_dates=["timestamp"])
    required = {"timestamp", "bank", "speaker", "role", "score"}
    missing = required - set(ev.columns)
    if missing:
        raise SystemExit(f"events file is missing columns: {sorted(missing)} "
                         "(see data/README.md for the schema)")
    return ev


def _reg_line(label: str, fit: dict) -> str:
    return (f"| {label} | {fit['n']} | {fit['slope']:.2f} | {fit['se']:.2f} | "
            f"{fit['t']:.2f} | {fit['r2']:.3f} |")


def write_findings(results: dict, qt: pd.DataFrame, path: Path, demo: bool) -> None:
    hr = results["hit_rate"]
    lines = ["# Findings", ""]
    if demo:
        lines += ["> **SYNTHETIC DEMO DATA** — these numbers exercise the pipeline; "
                  "they are not a result.", ""]
    lines += [
        f"Events with a defined surprise: **{results['n_events']}** "
        f"({int(results['events']['macro_day'].sum())} on macro-release days, "
        f"{int(results['events']['is_decision'].sum())} on scheduled decision days).",
        "",
        "## Does the surprise move the front end?",
        "",
        "| sample | n | slope (bp/unit) | HC1 se | t | R² |",
        "|---|---|---|---|---|---|",
        _reg_line("event day, all events", results["event_day"]),
        _reg_line("event day, ex macro-release days", results["event_day_clean"]),
        _reg_line("event day, speeches only ex macro", results["event_day_speeches"]),
        _reg_line("pre-window (already in the price)", results["pre_positioning"]),
        _reg_line("post-event drift", results["post_drift"]),
        "",
        f"- Hit rate (sign of move matches sign of surprise): "
        f"**{hr['rate']:.1%}** of {hr['n']} events, two-sided p = {hr['p']:.2g}.",
    ]
    if "placebo" in results:
        pb = results["placebo"]
        lines += [
            f"- Placebo ({pb['n_iter']} draws of random non-event days, same "
            f"surprises): median placebo R² = {pb['median_r2']:.4f}; fraction of "
            f"placebos beating the real R² = **{pb['p_value']:.3f}**.",
        ]
    lines += [
        "",
        "## How wide do you quote? (bp half-widths)",
        "",
        "`breakeven` is the always-informed floor E[|move|]; `w(α)` assumes a "
        "share α of uninformed flow and informed traders who only cross when "
        "the move clears your width.",
        "",
        qt.to_markdown(index=False),
        "",
        "## |move| by surprise-magnitude bucket",
        "",
    ]
    for bucket, d in results["by_magnitude"].items():
        lines.append(f"- {bucket}: n={d['n']}, mean {d['mean']:.1f} bp, "
                     f"p90 {d.get('p90', float('nan')):.1f} bp")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true", help="run on synthetic data (no network)")
    ap.add_argument("--events", default="data/events.csv", help="scored events CSV")
    ap.add_argument("--start", default="2014-01-01", help="market-data start date")
    ap.add_argument("--refresh", action="store_true", help="re-download market data")
    args = ap.parse_args()

    cfg = StudyConfig()
    if args.demo:
        from cb_surprise import demo
        events = demo.make_events()
        yields = demo.make_yields(events)
    else:
        from cb_surprise.market_data import load_yields
        events = load_events(args.events)
        series = sorted({MARKET_MAP[b] for b in events["bank"].unique() if b in MARKET_MAP})
        skipped = sorted(set(events["bank"].unique()) - set(MARKET_MAP))
        if skipped:
            print(f"note: no market-data mapping for {skipped}; those events are skipped "
                  "(extend MARKET_MAP in cb_surprise/config.py)")
        yields = load_yields(series, start=args.start, refresh=args.refresh)

    events = add_surprise(events, cfg.trailing_window, cfg.min_prior_events)
    results = run_study(events, yields, cfg)
    qt = quote_table(results)

    OUT.mkdir(exist_ok=True)
    chart = summary_chart(results, OUT / "summary.png", demo=args.demo)
    write_findings(results, qt, OUT / "findings.md", demo=args.demo)

    fit = results["event_day"]
    print(f"\nevents used: {results['n_events']}")
    print(f"event-day:  slope {fit['slope']:.2f} bp/unit (t {fit['t']:.1f}), "
          f"R² {fit['r2']:.3f}; hit rate {results['hit_rate']['rate']:.1%} "
          f"(p {results['hit_rate']['p']:.4f})")
    print(f"speeches ex-macro: R² {results['event_day_speeches']['r2']:.3f} "
          f"(t {results['event_day_speeches']['t']:.1f})  — the clean sample")
    print(f"pre-window: R² {results['pre_positioning']['r2']:.3f}  "
          f"(how much was already in the price)")
    if "placebo" in results:
        print(f"placebo:    {results['placebo']['p_value']:.3f} of random-day draws "
              f"beat the real R²")
    print("\nquote widths (bp):")
    print(qt.to_string(index=False))
    print(f"\nchart:    {chart}")
    print(f"findings: {OUT / 'findings.md'}")


if __name__ == "__main__":
    main()
