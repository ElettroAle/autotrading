from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.account_references import reference_of
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import MarketOrderFeeReaderPort, ReferenceOpenerPort, SealedAddressPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.round_trip_cost import RoundTripCost


class ReadRoundTripCostUseCase:
    """In the worker: the fee the exchange applies to the account of a flow for a market order, read once at the start
    of a cycle and only with the option of the flow on (R5.5.6, ADR costo-di-andata-e-ritorno-nel-contesto-dell-agente).

    The account is opened only for the fields its reader asks. An exchange that does not give the fee, temporarily or
    for good, leaves the cost among the missing data: the agent decides without it, and the cycle goes on.
    """

    def __init__(
        self,
        accounts: SealedAddressPort,
        opener: ReferenceOpenerPort,
        readers: Mapping[str, MarketOrderFeeReaderPort],
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def execute(self, flow: Flow) -> RoundTripCost:
        if not flow.configuration.fees_for_agent:
            return RoundTripCost()
        try:
            return RoundTripCost.of_rate(self._fee_rate_of(flow.assigned_account_id))
        except FlowExchangeUnavailableError as error:
            return RoundTripCost.unread(str(error))

    def _fee_rate_of(self, account_id: UUID) -> Decimal:
        sealed = self._accounts.sealed_address(account_id)
        reader = self._readers.get(sealed.exchange)
        if reader is None:
            raise FlowExchangeUnavailableError
        return reader.market_order_fee_rate(reference_of(self._opener, sealed, reader.reference_fields()))
