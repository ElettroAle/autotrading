from enum import StrEnum


class FlowStatus(StrEnum):
    """Only an active flow runs cycles; an archived one is final (R1.1.4-R1.1.6).

    A draft has only the strategy: it runs no cycle until account, capital and assets are assigned and it starts
    (ADR 0124).
    """

    DRAFT = "bozza"
    STOPPED = "fermo"
    ACTIVE = "attivo"
    PAUSED = "in pausa"
    ARCHIVED = "archiviato"

    @property
    def not_stopped(self) -> bool:
        """Active or paused: the flow still counts on its key and its positions (R1.4.1)."""
        return self in {FlowStatus.ACTIVE, FlowStatus.PAUSED}

    @property
    def runs_cycles(self) -> bool:
        return self is FlowStatus.ACTIVE

    @property
    def holds_account(self) -> bool:
        """Neither draft nor archived: the capital and the assets of the flow are taken on its account (ADR 0124)."""
        return self in {FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED}
