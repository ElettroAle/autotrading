from enum import StrEnum


class FlowStatus(StrEnum):
    """Only an active flow runs cycles; an archived one is final (R1.1.4-R1.1.6)."""

    STOPPED = "fermo"
    ACTIVE = "attivo"
    PAUSED = "in pausa"
    ARCHIVED = "archiviato"

    @property
    def not_stopped(self) -> bool:
        """Active or paused: the flow still counts on its key and its positions (R1.4.1)."""
        return self in {FlowStatus.ACTIVE, FlowStatus.PAUSED}
