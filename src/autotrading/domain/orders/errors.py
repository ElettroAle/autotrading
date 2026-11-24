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


class ManualOpeningNotAllowedError(DomainError):
    """Only the procedure of verification and the flows open positions; a user can only close them (R0.3.2)."""

    status_code = 403

    def __init__(self) -> None:
        super().__init__("apertura manuale non consentita")


class CycleOrderClosesFlowError(DomainError):
    """An order of a cycle carries its flow in the link to the cycle: it never closes a flow outside of it."""

    def __init__(self) -> None:
        super().__init__("un ordine del ciclo non chiude un flusso fuori dal ciclo")


class SimulatedOrderRefusedError(DomainError):
    """An order the simulated exchange refuses, as the real exchange refuses it: the adapter answers it with the error of
    the contract of the port (R6.3.2)."""


class OrderBelowMinimumValueError(SimulatedOrderRefusedError):
    def __init__(self, coin: str, minimum: Decimal) -> None:
        super().__init__(f"valore dell'ordine sotto il minimo dell'exchange per {coin}: {minimum}")
        self.coin = coin
        self.minimum = minimum


class OrderSizeOffStepError(SimulatedOrderRefusedError):
    def __init__(self, coin: str, step: Decimal) -> None:
        super().__init__(f"dimensione dell'ordine non multipla del passo dell'exchange per {coin}: {step}")
        self.coin = coin
        self.step = step


class InsufficientMarginError(SimulatedOrderRefusedError):
    def __init__(self, coin: str) -> None:
        super().__init__(f"margine insufficiente per l'ordine su {coin}")
        self.coin = coin


class ReduceOnlyWithoutPositionError(SimulatedOrderRefusedError):
    def __init__(self, coin: str) -> None:
        super().__init__(f"nessuna posizione da ridurre su {coin}")
        self.coin = coin


class UnknownSimulatedProtectionError(SimulatedOrderRefusedError):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"protezione {order_id} non in attesa: eseguita o cancellata")
        self.order_id = order_id
