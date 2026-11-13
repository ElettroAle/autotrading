from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from autotrading.domain.agent.errors import InvalidModelDefinitionError, ParameterOutOfRangeError

# The parameters the platform knows, with the label the reasons of a refusal use (R1.4.2).
PARAMETER_LABELS = {
    "temperature": "temperatura",
    "max_tokens": "limite di lunghezza della risposta",
    "reasoning_effort": "livello di ragionamento",
}

type ParameterValue = Decimal | str


def label_of(key: str) -> str:
    return PARAMETER_LABELS[key]


def _require_known(key: str) -> None:
    if key not in PARAMETER_LABELS:
        raise InvalidModelDefinitionError(key)


@dataclass(frozen=True, slots=True)
class RangeParameter:
    """A number between a minimum and a maximum, whole when the model takes only whole numbers."""

    key: str
    minimum: Decimal
    maximum: Decimal
    default: Decimal
    whole: bool = False

    def __post_init__(self) -> None:
        _require_known(self.key)
        if not self.minimum <= self.default <= self.maximum or not self._fits_kind(self.default):
            raise InvalidModelDefinitionError(self.key)

    @property
    def label(self) -> str:
        return label_of(self.key)

    def value_of(self, requested: object) -> ParameterValue:
        number = self._number(requested)
        if not self.minimum <= number <= self.maximum or not self._fits_kind(number):
            raise ParameterOutOfRangeError(self.label)
        return number

    def _number(self, requested: object) -> Decimal:
        # A boolean is an int in Python, never a number a user meant.
        if isinstance(requested, bool) or not isinstance(requested, int | float | Decimal | str):
            raise ParameterOutOfRangeError(self.label)
        try:
            number = Decimal(str(requested))
        except InvalidOperation as error:
            raise ParameterOutOfRangeError(self.label) from error
        if not number.is_finite():
            raise ParameterOutOfRangeError(self.label)
        return number

    def _fits_kind(self, number: Decimal) -> bool:
        return not self.whole or number == number.to_integral_value()


@dataclass(frozen=True, slots=True)
class ChoiceParameter:
    """One value out of a fixed list."""

    key: str
    choices: tuple[str, ...]
    default: str

    def __post_init__(self) -> None:
        _require_known(self.key)
        if self.default not in self.choices:
            raise InvalidModelDefinitionError(self.key)

    @property
    def label(self) -> str:
        return label_of(self.key)

    def value_of(self, requested: object) -> ParameterValue:
        if not isinstance(requested, str) or requested not in self.choices:
            raise ParameterOutOfRangeError(self.label)
        return requested


type ModelParameter = RangeParameter | ChoiceParameter
