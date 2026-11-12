from autotrading.domain.errors import DomainError


class InvalidScheduleError(DomainError):
    """An anchor without time zone or an interval that is not positive: a defect of whoever plans the cycles."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("pianificazione dei cicli non valida")
