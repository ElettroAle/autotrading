from dataclasses import dataclass

from autotrading.application.sources.list_source_offers import ListSourceOffersUseCase
from autotrading.application.sources.source_offer import SourceOffer
from autotrading.domain.sources.errors import SourceNotAvailableError


@dataclass(frozen=True, slots=True)
class GetSourceCommand:
    name: str


class GetSourceUseCase:
    """One source of the catalog with its adapters, as the tenant may activate them (R1.3.1, R4.1.1, R4.1.2)."""

    def __init__(self, offers: ListSourceOffersUseCase) -> None:
        self._offers = offers

    def execute(self, command: GetSourceCommand) -> SourceOffer:
        offer = next((offer for offer in self._offers.execute() if offer.source.name == command.name), None)
        if offer is None:
            raise SourceNotAvailableError(command.name)
        return offer
