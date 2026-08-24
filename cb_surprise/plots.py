"""The one chart: does the surprise move the front end, and how wide is the
event-day move distribution a market maker has to quote against?

Left panel  — scatter of speaker-relative surprise vs event-day 2y move (bp),
              chair vs regional, with the OLS fit and its R².
Right panel — ECDF of |event-day move| by event class vs non-event days, with
              the p90 quote-width markers the quoting section reports.
"""

from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
BLUE = "#2a78d6"    # chair / presser
ORANGE = "#eb6834"  # regional / other
GRAY = "#9b9a94"    # non-event baseline


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(True, color="#e8e7e2", linewidth=0.6)
    ax.set_axisbelow(True)


def _ecdf(ax, values, color, label, offset=(8, -14)):
    a = np.sort(np.abs(np.asarray(values, float)))
    a = a[~np.isnan(a)]
    if len(a) == 0:
        return
    y = np.arange(1, len(a) + 1) / len(a)
    ax.step(a, y, where="post", color=color, linewidth=2, label=label)
    p90 = np.percentile(a, 90)
    ax.plot([p90], [0.9], "o", color=color, markersize=8, zorder=5)
    ax.annotate(f"p90 = {p90:.1f} bp", (p90, 0.9), textcoords="offset points",
                xytext=offset, fontsize=9, color=color)


def summary_chart(results: dict, out_path: str | Path, demo: bool = False) -> Path:
    ev = results["events"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2))
    fig.patch.set_facecolor(SURFACE)
    _style(ax1)
    _style(ax2)

    # --- left: surprise vs event-day move ---
    for mask, color, label in [(ev["is_chair"], BLUE, "chair / presser"),
                               (~ev["is_chair"], ORANGE, "regional / other")]:
        sub = ev[mask]
        ax1.scatter(sub["surprise"], sub["event_move_bp"], s=26, color=color,
                    alpha=0.75, linewidths=0, label=label)
    fit = results["event_day"]
    if np.isfinite(fit.get("slope", np.nan)):
        xs = np.linspace(ev["surprise"].min(), ev["surprise"].max(), 50)
        icept = ev["event_move_bp"].mean() - fit["slope"] * ev["surprise"].mean()
        ax1.plot(xs, fit["slope"] * xs + icept, color=INK, linewidth=2)
        hr = results.get("hit_rate", {})
        hr_line = (f"\nhit rate = {hr['rate']:.0%}  (p = {hr['p']:.2g})"
                   if np.isfinite(hr.get("rate", np.nan)) else "")
        ax1.annotate(f"slope = {fit['slope']:.1f} bp / unit  (t = {fit['t']:.1f})\n"
                     f"R² = {fit['r2']:.02f}   n = {fit['n']}" + hr_line,
                     xy=(0.03, 0.97), xycoords="axes fraction", va="top",
                     fontsize=10, color=INK)
    ax1.set_xlabel("surprise  (score − speaker's trailing mean)", color=INK2)
    ax1.set_ylabel("event-day 2y move (bp)", color=INK2)
    ax1.set_title("Surprise vs front-end repricing", color=INK, fontsize=11, loc="left")
    ax1.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=INK2)

    # --- right: |move| distribution by class ---
    _ecdf(ax2, ev.loc[ev["is_chair"], "event_move_bp"], BLUE, "chair / presser",
          offset=(10, -16))
    _ecdf(ax2, ev.loc[~ev["is_chair"], "event_move_bp"], ORANGE, "regional / other",
          offset=(-70, 10))
    ax2.set_xlabel("|event-day 2y move| (bp)", color=INK2)
    ax2.set_ylabel("fraction of events ≤ x", color=INK2)
    ax2.set_title("How wide do you quote? |move| ECDF and p90 widths",
                  color=INK, fontsize=11, loc="left")
    ax2.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=INK2)

    if demo:
        fig.text(0.5, 0.5, "SYNTHETIC DEMO DATA", fontsize=40, color=INK,
                 alpha=0.12, ha="center", va="center", rotation=18, weight="bold")

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return out_path
