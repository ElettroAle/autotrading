from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.account_exposure import AccountExposure, AccountExposureLimit
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class AccountExposureReading:
    """What a cycle reads of the exposure of the account of its flow: with a limit, the limit and the exposure of every
    flow of the account; with the option of the flow on, the exposure of the other flows for its agent (R5.5.5).

    Without either nothing is computed, and the cycle goes as before.
    """

    limit: AccountExposureLimit | None = None
    of_account: AccountExposure = field(default_factory=AccountExposure)
    of_others: AccountExposure | None = None

    @classmethod
    def of(
        cls, flow: Flow, flows: Sequence[Flow], account: CycleAccount, percent: Decimal | None
    ) -> AccountExposureReading:
        """The positions and the balance are those of the one reading of the account at the start of the cycle."""
        limit = None if percent is None else AccountExposureLimit(percent, account.balance, account.currency)
        of_account = (
            AccountExposure() if limit is None else AccountExposure.of(account.positions, _assets_of(flow, flows))
        )
        of_others = (
            AccountExposure.of(account.positions, _assets_of(flow, flows, excluding=flow.id))
            if flow.configuration.account_exposure_for_agent
            else None
        )
        return cls(limit, of_account, of_others)


def _assets_of(flow: Flow, flows: Iterable[Flow], excluding: FlowId | None = None) -> frozenset[str]:
    """The assets of the flows of the account of the flow neither archived nor in draft, the attribution of the free
    capital (ADR capitale-libero-al-netto-del-valore-dei-flussi), but the one left out."""
    account_id = flow.assigned_account_id
    return frozenset(
        asset
        for other in flows
        if other.belongs_to(account_id) and other.status.holds_account and other.id != excluding
        for asset in other.configuration.assets
    )
