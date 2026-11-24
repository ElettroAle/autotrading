from collections.abc import Callable


class FakeCycleNoticesAdapter:
    """Every release of the notices of a cycle, with what the cycle had done by then as the test reads it."""

    def __init__(self, done: Callable[[], object] = lambda: None) -> None:
        self._done = done
        self.releases: list[object] = []

    def release(self) -> None:
        self.releases.append(self._done())
