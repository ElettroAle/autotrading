from decimal import Decimal

from autotrading.domain.errors import DomainError


class InvalidLeverageError(DomainError):
    def __init__(self, leverage: int) -> None:
        super().__init__("leva non valida")
        self.leverage = leverage


class LeverageAboveMaximumError(DomainError):
    def __init__(self, coin: str, maximum: int) -> None:
        super().__init__(f"leva oltre il massimo dell'exchange per {coin}: {maximum}")
        self.coin = coin
        self.maximum = maximum


class OrderSizeBelowStepError(DomainError):
    def __init__(self, coin: str, step: Decimal) -> None:
        super().__init__(f"valore sotto la dimensione minima dell'exchange per {coin}: {step}")
        self.coin = coin
        self.step = step


class InvalidSlippageError(DomainError):
    def __init__(self, fraction: Decimal) -> None:
        super().__init__("scostamento massimo di prezzo non valido")
        self.fraction = fraction


class InvalidMarketError(DomainError):
    def __init__(self, coin: str) -> None:
        super().__init__(f"metadati dell'exchange non validi per {coin}")
        self.coin = coin


class EmptyExecutionError(DomainError):
    def __init__(self) -> None:
        super().__init__("esecuzione senza dimensione eseguita")


class TradingAccessRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("accesso al conto obbligatorio")
