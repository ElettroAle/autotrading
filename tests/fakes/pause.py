"""A pause that never waits: it records how long the use case asked to wait, in order."""

from dataclasses import dataclass, field
from datetime import timedelta

from tests.fakes.cycles import FakeClockAdapter


@dataclass
class FakePauseAdapter:
    """Realises the pause port without waiting, keeping every pause asked for; with a clock, each pause moves it on by
    the seconds asked, as if they had passed."""

    pauses: list[float] = field(default_factory=list)
    clock: FakeClockAdapter | None = None

    def pause(self, seconds: float) -> None:
        self.pauses.append(seconds)
        if self.clock is not None:
            self.clock.current += timedelta(seconds=seconds)
