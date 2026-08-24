# Does central-bank talk move the front end?

![ci](https://github.com/finn123344/Front-end-CB-Surprise/actions/workflows/ci.yml/badge.svg)

**TL;DR** *(numbers below are from the watermarked synthetic demo until the
study runs on the real archive — replace them from `output/findings.md`)*

- A speaker-relative hawkish/dovish surprise moves the 2y the right way
  **~62% of the time**, but explains little of the event-day variance
  (R² ≈ 0.09 all events, ≈ 0.02 for speeches off macro days) — most of the
  message is already in the price before it is spoken.
- The result survives the obvious attacks: macro-release days excluded,
  decision-day confound split out, and **0/500 placebo draws** on random
  dates match the real fit.
- The trading answer: quoting into a chair presser needs a wider two-way
  price than a regional speech — break-even and mixture widths per event
  class are in the quote table.

![summary chart](output/summary.png)

*Chart from the synthetic demo (`--demo`), watermarked as such; it exists so
the pipeline is runnable and reviewable without the private event archive.*

## The surprise definition (the part that needs the archive)

Every presser and speech in a timestamped archive covering eleven central banks
carries a hawkishness score. The **surprise is the deviation of a speaker's
score from that speaker's own trailing mean** (last 8 scored events, computed
strictly from prior events — no lookahead; see `tests/test_surprise.py`), not
from zero. A hawk sounding hawkish is not news; a hawk sounding *more* hawkish
than usual is. This speaker-relative baseline is the computation you cannot do
without the archive.

## Method

- **Market data (free):** daily 2y yields — US from FRED (`DGS2`), euro area
  from the ECB Data Portal (AAA 2y spot), both keyless, cached locally. The
  bank → market map in `cb_surprise/config.py` is extensible to the other banks.
- **Windows:** with free daily data the finest honest window is close-to-close.
  Event-day move = the close-to-close change containing the event (events after
  the local close roll to the next trading day). Pre-positioning = the move over
  the 5 prior days; post-drift = the next day.
- **Cuts:** OLS of the event-day move on the surprise (slope in bp per surprise
  unit, HC1 t-stat, R²); the same regression on the pre-window (how much was
  already in the price); |move| distributions bucketed by surprise-magnitude
  tercile and by speaker — chair/president vs regional.
- **Reported object:** the full distribution of absolute moves, not just the
  mean. The distribution is what a trader can actually use.

## Robustness (what an interviewer would attack first)

- **Same-day macro releases.** A speech on a payrolls day inherits the data
  move in a daily window. Events on major-release days are flagged
  (deterministic first-Friday NFP rule + `data/macro_releases.csv` for CPI
  and euro-area releases) and the regression is reported with and without them.
- **Decision-day confound.** A presser shares its day with the rate decision
  and statement, so decision-day events are reported separately; **speeches
  are the clean identification** and get their own regression row.
- **Placebo.** Keep the surprises, pair each with a random non-event day's
  move from the same market, 500 times. The placebo R² distribution is what
  noise looks like; the real fit is judged against it, not against zero.
- **Hit rate.** Sign agreement between surprise and move, with a binomial
  p-value — robust to the fat tails that make daily R² fragile.

## The honest result

Run on real data, the expected finding is a **null-ish one**: most
communication is already in the price by the time it is spoken, the event-day
R² is low, and pre-positioning explains a comparable or larger share. That is
the finding worth publishing — a low R² reported straight is more credible
than a suspiciously good fit, and it is what the data should show if markets
are doing their job. Numbers land in `output/findings.md` after each run.

## The market-maker's version

Given the empirical distribution of 2y moves around an event, two widths per
event class:

- **Always-informed floor:** every fill is informed and trades regardless —
  break-even half-width = E[|move|].
- **Mixture width w(α):** a share α of flow is uninformed and pays the width;
  informed traders only cross when the move clears it. Break-even solves
  α·w = (1−α)·E[(|move|−w)⁺] on the empirical distribution. As α → 0 the
  width blows out toward the worst observed move — a desk with no uninformed
  flow shouldn't be quoting into a presser at all, which is itself the answer.

So "how much wider do you quote a chair presser than a regional speech?" has a
number at any stated α, defensible from the ECDF in the chart's right panel.

## Run it

```bash
pip install -r requirements.txt

python run_study.py --demo                  # synthetic data, no network, no archive
python run_study.py --events data/events.csv  # scored archive (schema: data/README.md)

python -m pytest tests/                     # no-lookahead + inference + quoting tests
```

## Limitations, and what intraday data would add

Daily data cannot separate the press-conference move from the rate-decision
move on the same day (hence the speech-only sample), or measure the *speed*
of repricing. With intraday futures (SOFR/€STR or fed funds), the design
upgrades directly: a ±30-minute window around the timestamp isolates the
communication from everything else in the day, the decision-day confound
disappears (statement at t, presser at t+30), and "how fast" becomes
measurable in minutes — same surprise definition, same regressions, tighter
identification. Scores are one analyst's labels, so the surprise inherits
their noise; the trailing-mean baseline removes the speaker's level but not
slow drift in the scoring scale.

## Roadmap (needs a machine with market-data network access)

- Verify the FRED / ECB fetchers live and commit the cached CSVs so a fresh
  clone reproduces without hitting the endpoints.
- Populate `data/macro_releases.csv` from the BLS and Eurostat calendars
  (the NFP first-Friday rule is already built in).
- Add one true policy-path proxy — the Bank of England publishes free daily
  OIS forward curves — to show the beta on the 1y-forward point rather than
  a duration-contaminated 2y.
