"""The parameters of an adapter of a source as JSON: a whole number, or an array of them for a list parameter (ADR
parametri-delle-fonti-come-liste-libere). Which parameter is a list the catalog declares, never this module.
"""

from collections.abc import Mapping

from autotrading.domain.sources.source_parameter import SourceParameterValue

type ParameterBody = int | list[int]


def parameters_of(body: Mapping[str, ParameterBody]) -> dict[str, SourceParameterValue]:
    """The parameters as the domain checks them: an array becomes a list of the flow."""
    return {key: tuple(value) if isinstance(value, list) else value for key, value in body.items()}


def parameters_body(parameters: Mapping[str, SourceParameterValue]) -> dict[str, ParameterBody]:
    return {key: list(value) if isinstance(value, tuple) else value for key, value in parameters.items()}
