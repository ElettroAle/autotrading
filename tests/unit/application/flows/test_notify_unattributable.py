"""Each new position or execution no flow explains reaches the user with the name of the account; a change of the
balance within the threshold is only recorded (R1.6.2, ADR 0088, ADR 0092, ADR variazioni-sotto-soglia-senza-notifica).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.flows.notify_unattributable import NotifyUnattributableUseCase, UnattributableNotices
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.unattributable_notices import FakeUnattributableAssetNoticeAdapter
from tests.support.worker import TENANT, Worker

DETECTED_AT = datetime(2026, 11, 13, tzinfo=UTC)


def an_item(account_id: UUID, kind: UnattributableKind, asset: str | None, amount: str) -> UnattributableItem:
    return UnattributableItem(account_id, kind, "ref", asset, Decimal(amount), DETECTED_AT)


class Notices:
    def __init__(self, worker: Worker) -> None:
        self.positions = FakeUnattributableAssetNoticeAdapter()
        self.fills = FakeUnattributableAssetNoticeAdapter()
        self.use_case = NotifyUnattributableUseCase(
            InMemoryAccountRepositoryAdapter(worker.store, TENANT),
            UnattributableNotices(self.positions, self.fills),
        )


def test_each_position_and_execution_is_told_by_its_kind_with_the_name_of_the_account() -> None:
    worker = Worker()
    account = worker.saved_account()
    notices, name, account_id = Notices(worker), account.name.value, account.id.value

    notices.use_case.execute(
        [
            an_item(account_id, UnattributableKind.POSITION, "BTC", "0.1"),
            an_item(account_id, UnattributableKind.FILL, "ETH", "2"),
        ]
    )

    assert (notices.positions.told, notices.fills.told) == ([(name, "BTC")], [(name, "ETH")])


def test_a_change_of_the_balance_is_not_told() -> None:
    worker = Worker()
    account_id = worker.saved_account().id.value
    notices = Notices(worker)

    notices.use_case.execute(
        [
            an_item(account_id, UnattributableKind.BALANCE_CHANGE, None, "-0.03"),
            an_item(account_id, UnattributableKind.BALANCE_CHANGE, None, "0.02"),
        ]
    )

    assert (notices.positions.told, notices.fills.told) == ([], [])


def test_no_case_tells_nothing() -> None:
    notices = Notices(Worker())

    notices.use_case.execute([])

    assert (notices.positions.told, notices.fills.told) == ([], [])


def test_an_account_of_another_tenant_is_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        Notices(worker).use_case.execute([an_item(theirs.id.value, UnattributableKind.POSITION, "BTC", "1")])
