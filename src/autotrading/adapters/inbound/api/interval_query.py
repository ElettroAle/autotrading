from datetime import datetime
from typing import Annotated

from fastapi import Query

# ADR periodo-al-minuto: the interval of every reading with a period is two instants read to the minute.
_INSTANT = "istante ISO 8601 letto al minuto; senza fuso vale UTC, una data sola vale la mezzanotte UTC"

IntervalStart = Annotated[datetime | None, Query(alias="from", description=f"inizio dell'intervallo, {_INSTANT}")]
IntervalEnd = Annotated[
    datetime | None, Query(alias="to", description=f"fine dell'intervallo, minuto compreso, {_INSTANT}")
]
