"""Each new case no flow explains reaches the user with the name of the account (R1.6.2, ADR 0088)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.flows.notify_unattributable import NotifyUnattributableUseCase
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.notifier import FakeNotifierAdapter
from tests.support.worker import TENANT, Worker

DETECTED_AT = datetime(2026, 11, 13, tzinfo=UTC)


def an_item(account_id: UUID, kind: UnattributableKind, asset: str | None, amount: str) -> UnattributableItem:
    return UnattributableItem(account_id, kind, "ref", asset, Decimal(amount), DETECTED_AT)


def notices_of(worker: Worker, notifier: FakeNotifierAdapter) -> NotifyUnattributableUseCase:
    return NotifyUnattributableUseCase(InMemoryAccountRepositoryAdapter(worker.store, TENANT), notifier, "USDC")


def test_each_case_is_told_with_the_name_of_the_account() -> None:
    worker, notifier = Worker(), FakeNotifierAdapter()
    account = worker.saved_account()
    name, account_id = account.name.value, account.id.value

    notices_of(worker, notifier).execute(
        [
            an_item(account_id, UnattributableKind.POSITION, "BTC", "0.1"),
            an_item(account_id, UnattributableKind.FILL, "ETH", "2"),
            an_item(account_id, UnattributableKind.BALANCE_CHANGE, None, "-15"),
        ]
    )

    assert notifier.notifications == [
        Notification.unattributable_position(name, "BTC"),
        Notification.unattributable_fill(name, "ETH"),
        Notification.unattributable_movement(name, Amount(Decimal(-15), "USDC")),
    ]


def test_no_case_tells_nothing() -> None:
    notifier = FakeNotifierAdapter()

    notices_of(Worker(), notifier).execute([])

    assert notifier.notifications == []


def test_an_account_of_another_tenant_is_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        notices_of(worker, FakeNotifierAdapter()).execute(
            [an_item(theirs.id.value, UnattributableKind.POSITION, "BTC", "1")]
        )
