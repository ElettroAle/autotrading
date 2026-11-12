from autotrading.domain.errors import DomainError


class AccountNameRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("nome obbligatorio")


class ExchangeRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("exchange obbligatorio")


class CredentialsRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("credenziali obbligatorio")


class CredentialsOfAnotherAccountError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("le credenziali appartengono a un altro conto dell'exchange")


class OpenPositionsNeedConfirmationError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("il conto ha posizioni aperte che resteranno sull'exchange senza gestione")


class OperatingFlowsNeedConfirmationError(DomainError):
    """The flows active or paused on the account are stopped by the removal, so it waits for a confirmation (R1.1.8)."""

    status_code = 409

    def __init__(self, flows: tuple[str, ...]) -> None:
        super().__init__("il conto ha flussi attivi o in pausa che verranno fermati: " + ", ".join(flows))
        self.flows = flows


class FlowPositionsLeftOpenError(DomainError):
    """A position of a flow of the account the exchange did not close: the account is not removed (R1.1.8)."""

    status_code = 409

    def __init__(self, positions: tuple[tuple[str, str], ...]) -> None:
        listed = ", ".join(f"{asset} ({reason})" for asset, reason in positions)
        super().__init__(f"posizioni dei flussi rimaste aperte, conto non rimosso: {listed}")
        self.positions = positions
