from collections.abc import Callable, Mapping
from dataclasses import dataclass

from autotrading.domain.sources.errors import SourceParameterOutOfRangeError, UnknownSourceParameterError
from autotrading.domain.sources.source_parameter import SourceParameter


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    """What the catalog shows of a source: a per-asset source is asked for every asset of the flow, the others once."""

    name: str
    description: str
    per_asset: bool
    parameters: tuple[SourceParameter, ...]
    # A source whose silence is itself a datum says so to the agent (R1.3.7).
    silence: Callable[[Mapping[str, int]], Mapping[str, str]] | None = None

    def silence_note(self, settings: Mapping[str, int]) -> Mapping[str, str] | None:
        """What the agent reads when the source collected nothing with these settings; None when nothing at all."""
        if self.silence is None:
            return None
        return self.silence(settings)

    def settings(self, requested: Mapping[str, int]) -> dict[str, int]:
        """The parameters of a flow: the requested values checked, the catalog defaults for the others (R1.3.2)."""
        chosen = {key: self._accepted(key, value) for key, value in requested.items()}
        return {parameter.key: chosen.get(parameter.key, parameter.default) for parameter in self.parameters}

    def _accepted(self, key: str, value: int) -> int:
        parameter = next((parameter for parameter in self.parameters if parameter.key == key), None)
        if parameter is None:
            raise UnknownSourceParameterError(self.name, key)
        # A boolean is an int in Python, never a number a user meant.
        if isinstance(value, bool) or not isinstance(value, int) or not parameter.accepts(value):
            raise SourceParameterOutOfRangeError(parameter.label)
        return value
