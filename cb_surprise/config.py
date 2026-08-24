"""Configuration: bank -> market-data mapping and study parameters."""

from dataclasses import dataclass, field


@dataclass
class StudyConfig:
    # Surprise definition
    trailing_window: int = 8      # events in the speaker's trailing mean
    min_prior_events: int = 3     # speaker events required before a surprise is defined

    # Event-study windows (business days relative to event day t)
    pre_window: int = 5           # pre-positioning window [t-5, t-1]
    post_window: int = 1          # optional drift check [t, t+1]

    # Local-market close hour (24h). Events time-stamped after the close are
    # assigned to the next business day's yield change.
    market_close_hour: dict = field(default_factory=lambda: {
        "FED": 16,   # 4pm New York
        "ECB": 17,   # ~5:15pm CET Bund futures pit close proxy
        "BOE": 16,
    })

    # Quote-width percentiles reported for the market-maker section
    width_percentiles: tuple = (50, 75, 90, 95)


# Which free 2y-yield series proxies the front end for each bank.
# Extend this map (and market_data.FETCHERS) to cover more of the 11 banks:
# any daily 2y government yield or short-rate-futures-implied yield works.
MARKET_MAP = {
    "FED": "US2Y",   # FRED DGS2, daily constant-maturity 2y Treasury
    "ECB": "EA2Y",   # ECB Data Portal, euro-area AAA 2y spot yield
}

# Roles treated as "chair" for the chair-vs-regional split.
CHAIR_ROLES = {"chair", "president", "governor_head"}

# Event types that sit on a scheduled decision day, where the presser move is
# confounded with the statement/decision move. Speeches are the clean sample.
DECISION_EVENT_TYPES = {"presser", "statement", "decision"}
