from autotrading.domain.errors import DomainError


class FlowNameRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("nome del flusso obbligatorio")


class ModelRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("modello obbligatorio")


class CycleIntervalOutOfRangeError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("intervallo di ciclo fuori da 1-1440 minuti")


class AssetsRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("almeno un asset è obbligatorio")


class MaxLeverageRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("la leva massima è obbligatoria")


class ExposureLimitRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("almeno un limite di esposizione è obbligatorio")


class InvalidRiskLimitError(DomainError):
    status_code = 422

    def __init__(self, label: str) -> None:
        super().__init__(f"limite di rischio non valido: {label}")
        self.label = label


class SourceWeightOutOfRangeError(DomainError):
    status_code = 422

    def __init__(self, source: str) -> None:
        super().__init__(f"peso fuori da 1-10: {source}")
        self.source = source


class RepeatedSourceError(DomainError):
    status_code = 422

    def __init__(self, source: str) -> None:
        super().__init__(f"fonte ripetuta: {source}")
        self.source = source


class AllocatedCapitalNotPositiveError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("il capitale allocato deve essere positivo")


class CapitalAboveFreeCapitalError(DomainError):
    status_code = 422

    def __init__(self, free_capital: str) -> None:
        super().__init__(f"capitale allocato oltre il capitale libero: {free_capital}")
        self.free_capital = free_capital
