from datetime import datetime

from sqlalchemy import ColumnElement, true

from autotrading.domain.flows.statistics_period import TimeWindow


def within(instant: ColumnElement[datetime], window: TimeWindow) -> ColumnElement[bool]:
    """The rows whose instant falls in the window: from its start included to its end excluded."""
    condition: ColumnElement[bool] = true()
    if window.since is not None:
        condition = condition & (instant >= window.since)
    if window.until is not None:
        condition = condition & (instant < window.until)
    return condition
