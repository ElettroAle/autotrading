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


class CapitalAboveAvailableCapitalError(DomainError):
    status_code = 422

    def __init__(self, available: str) -> None:
        super().__init__(f"capitale allocato oltre il capitale disponibile: {available}")
        self.available = available


class CapitalBelowFlowMinimumError(DomainError):
    status_code = 422

    def __init__(self, minimum: str) -> None:
        super().__init__(f"capitale allocato sotto il minimo del flusso: {minimum}")
        self.minimum = minimum


class FlowCommandNotAllowedError(DomainError):
    status_code = 409

    def __init__(self, command: str, status: str) -> None:
        super().__init__(f"comando {command} non ammesso per un flusso {status}")
        self.command = command
        self.status = status


class ArchiveOnlyStoppedError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("si archivia solo un flusso fermo")


class ArchivedFlowNotModifiableError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("un flusso archiviato non si modifica")


class FlowAssignmentMissingError(DomainError):
    """Only a draft lacks account, allocated capital or assets: any other flow trades with them (ADR 0124)."""

    status_code = 409

    def __init__(self, missing: tuple[str, ...]) -> None:
        listed = missing[0] if len(missing) == 1 else ", ".join(missing[:-1]) + " e " + missing[-1]
        super().__init__(f"{listed} {'mancante' if len(missing) == 1 else 'mancanti'}")
        self.missing = missing


class FlowNotDraftError(DomainError):
    """Account, capital and assets of a flow already out of draft change only through their own commands."""

    status_code = 409

    def __init__(self) -> None:
        super().__init__("conto, capitale e asset si assegnano solo a un flusso in bozza")


class AccountNotChangeableError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("il conto di un flusso non si cambia")


class AssetsAssignedToOtherFlowError(DomainError):
    """Two flows of one account never share an asset: each position stays attributable to one flow (R1.1.2)."""

    status_code = 409

    def __init__(self, flow: str, assets: tuple[str, ...]) -> None:
        super().__init__(f"asset già assegnati al flusso {flow} sullo stesso conto: " + ", ".join(assets))
        self.flow = flow
        self.assets = assets


class InvalidClosedPositionError(DomainError):
    """A closed position the exchange cannot have shown: a defect of whoever reads it."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("posizione chiusa non valida")


class SourceNotSelectedError(DomainError):
    """A source the configuration of the cycle does not select: the cycle goes on without it (R1.2.5)."""

    status_code = 404

    def __init__(self, source: str) -> None:
        super().__init__(f"fonte non attiva nel flusso: {source}")
        self.source = source


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


class InvalidStatisticsPeriodError(DomainError):
    """A period of the statistics the user cannot have meant (R2.2.6)."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"periodo non valido: {reason}")
        self.reason = reason


class UnknownStatisticsPeriodError(InvalidStatisticsPeriodError):
    def __init__(self, periods: tuple[str, ...]) -> None:
        super().__init__("scegliere tra " + ", ".join(periods))


class DaysOutsideRangeError(InvalidStatisticsPeriodError):
    def __init__(self) -> None:
        super().__init__("i giorni valgono solo per un intervallo")


class RangeDaysRequiredError(InvalidStatisticsPeriodError):
    def __init__(self) -> None:
        super().__init__("un intervallo ha il giorno iniziale e il giorno finale")


class RangeEndingBeforeStartError(InvalidStatisticsPeriodError):
    def __init__(self) -> None:
        super().__init__("il giorno iniziale è successivo al giorno finale")
