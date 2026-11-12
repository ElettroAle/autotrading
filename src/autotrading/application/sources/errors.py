from autotrading.application.errors import ApplicationError


class SourceUnavailableError(ApplicationError):
    """An external source did not answer, or answered in an unexpected shape: the cycle treats it as absent."""

    status_code = 503

    def __init__(self, source: str) -> None:
        super().__init__(f"fonte non raggiungibile: {source}")
        self.source = source


class AssetRequiredError(ApplicationError):
    """A per-asset source asked without an asset: a defect of the caller, never of the user."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("la fonte va interrogata per un asset")
