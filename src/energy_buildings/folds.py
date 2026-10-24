"""Chronological rolling-origin fold construction."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class Fold:
    name: str
    train_end: str
    test_start: str
    test_end: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def monthly_rolling_folds(
    timestamps: pd.Series,
    first_test_month: str = "2021-07",
    last_test_month: str = "2021-11",
) -> list[Fold]:
    """Use all prior observations for training and one calendar month for testing."""
    values = pd.to_datetime(timestamps, utc=True)
    first = pd.Period(first_test_month, freq="M")
    last = pd.Period(last_test_month, freq="M")
    folds = []
    for period in pd.period_range(first, last, freq="M"):
        test_start = period.start_time.tz_localize("UTC")
        test_end = (period + 1).start_time.tz_localize("UTC")
        train_end = test_start
        in_test = values.ge(test_start) & values.lt(test_end)
        if values.lt(train_end).sum() == 0 or in_test.sum() == 0:
            continue
        folds.append(
            Fold(
                name=str(period),
                train_end=train_end.isoformat(),
                test_start=test_start.isoformat(),
                test_end=test_end.isoformat(),
            )
        )
    return folds
