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


def write_findings(results: dict, qt: pd.DataFrame, path: Path, demo: bool) -> None:
    fit, pre, post = results["event_day"], results["pre_positioning"], results["post_drift"]
    lines = ["# Findings", ""]
    if demo:
        lines += ["> **SYNTHETIC DEMO DATA** — these numbers exercise the pipeline; "
                  "they are not a result.", ""]
    lines += [
        f"- Events with a defined surprise: **{results['n_events']}**",
        f"- Event-day repricing vs surprise: slope **{fit['slope']:.1f} bp/unit**, "
        f"**R² = {fit['r2']:.3f}** (n = {fit['n']})",
        f"- Pre-positioning (move over the 5 prior days vs eventual surprise): "
        f"slope {pre['slope']:.1f} bp/unit, R² = {pre['r2']:.3f}",
        f"- Post-event drift vs surprise: slope {post['slope']:.1f} bp/unit, "
        f"R² = {post['r2']:.3f}",
        "",
        "## Distribution of |event-day move| and quote widths (bp)",
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
    print(f"event-day:  slope {fit['slope']:.2f} bp/unit surprise, R² {fit['r2']:.3f}")
    print(f"pre-window: R² {results['pre_positioning']['r2']:.3f}  "
          f"(how much was already in the price)")
    print("\nquote widths (bp):")
    print(qt.to_string(index=False))
    print(f"\nchart:    {chart}")
    print(f"findings: {OUT / 'findings.md'}")


if __name__ == "__main__":
    main()
