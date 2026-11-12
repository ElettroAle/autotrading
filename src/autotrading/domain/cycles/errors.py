from autotrading.domain.errors import DomainError


class InvalidScheduleError(DomainError):
    """An anchor without time zone or an interval that is not positive: a defect of whoever plans the cycles."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("pianificazione dei cicli non valida")


class InvalidCallCostError(DomainError):
    """Negative tokens or a negative cost: a defect of whoever reads the usage of the model."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("costo della chiamata al modello non valido")


class InvalidPageNumberError(DomainError):
    def __init__(self) -> None:
        super().__init__("numero di pagina non valido: le pagine partono da 1")
