from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from autotrading.domain.agent.errors import InvalidModelDefinitionError, ParameterOutOfRangeError


@dataclass(frozen=True, slots=True)
class OfferedParameter:
    """What the platform says of a parameter of a model it offers: the label the reasons of a refusal use (R1.4.2) and
    the description its info button shows, the same for every model that admits it (R5.5.7, ADR
    descrizioni-dei-parametri-di-fonti-e-modelli). The range or the choices are of the model, so the description
    points to the field for them.
    """

    label: str
    description: str


# The parameters the platform offers: one list, the only place of their labels and descriptions.
OFFERED_PARAMETERS = {
    "temperature": OfferedParameter(
        "temperatura",
        "Quanto variano le risposte del modello: più bassa, risposte più ripetibili; più alta, più varie. Un numero "
        "nell'intervallo che il modello ammette. Vuoto: il valore predefinito del modello, mostrato nel campo.",
    ),
    "max_tokens": OfferedParameter(
        "limite di lunghezza della risposta",
        "Lunghezza massima della risposta del modello, in token: una risposta più lunga si interrompe. Un intero "
        "nell'intervallo che il modello ammette. Vuoto: il valore predefinito del modello, mostrato nel campo.",
    ),
    "reasoning_effort": OfferedParameter(
        "livello di ragionamento",
        "Quanto ragiona il modello prima di rispondere: più ragionamento dà risposte più meditate, più lente e più "
        "costose. Uno dei livelli che il modello ammette. Vuoto: il livello predefinito del modello.",
    ),
}

type ParameterValue = Decimal | str


def is_offered(key: str) -> bool:
    return key in OFFERED_PARAMETERS


def label_of(key: str) -> str:
    return OFFERED_PARAMETERS[key].label


def description_of(key: str) -> str:
    return OFFERED_PARAMETERS[key].description


def _require_known(key: str) -> None:
    if not is_offered(key):
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

    @property
    def description(self) -> str:
        return description_of(self.key)

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

    @property
    def description(self) -> str:
        return description_of(self.key)

    def value_of(self, requested: object) -> ParameterValue:
        if not isinstance(requested, str) or requested not in self.choices:
            raise ParameterOutOfRangeError(self.label)
        return requested


type ModelParameter = RangeParameter | ChoiceParameter
