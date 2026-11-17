"""A pause that never waits: it records how long the use case asked to wait, in order."""

from dataclasses import dataclass, field


@dataclass
class FakePauseAdapter:
    """Realises the pause port without waiting, keeping every pause asked for."""

    pauses: list[float] = field(default_factory=list)

    def pause(self, seconds: float) -> None:
        self.pauses.append(seconds)
