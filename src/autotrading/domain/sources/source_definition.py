from collections.abc import Callable, Mapping
from dataclasses import dataclass

from autotrading.domain.sources.errors import UnknownSourceParameterError
from autotrading.domain.sources.source_list_parameter import DeclaredParameter
from autotrading.domain.sources.source_parameter import SourceParameterValue


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    """What the catalog shows of a source: a per-asset source is asked for every asset of the flow, the others once."""

    name: str
    description: str
    per_asset: bool
    parameters: tuple[DeclaredParameter, ...]
    # A source whose silence is itself a datum says so to the agent (R1.3.7).
    silence: Callable[[Mapping[str, SourceParameterValue]], Mapping[str, str]] | None = None

    def silence_note(self, settings: Mapping[str, SourceParameterValue]) -> Mapping[str, str] | None:
        """What the agent reads when the source collected nothing with these settings; None when nothing at all."""
        if self.silence is None:
            return None
        return self.silence(settings)

    def settings(
        self, requested: Mapping[str, SourceParameterValue], adapter_parameters: tuple[DeclaredParameter, ...] = ()
    ) -> dict[str, SourceParameterValue]:
        """The parameters of a flow: the requested values checked, the catalog defaults for the others (R1.3.2).

        The parameters of the source hold for every adapter; the adapter may add its own (R4.1.1).
        """
        parameters = (*self.parameters, *adapter_parameters)
        chosen = {key: self._accepted(parameters, key, value) for key, value in requested.items()}
        return {parameter.key: chosen.get(parameter.key, parameter.default) for parameter in parameters}

    def _accepted(
        self, parameters: tuple[DeclaredParameter, ...], key: str, value: SourceParameterValue
    ) -> SourceParameterValue:
        parameter = next((parameter for parameter in parameters if parameter.key == key), None)
        if parameter is None:
            raise UnknownSourceParameterError(self.name, key)
        return parameter.accepted(value)
