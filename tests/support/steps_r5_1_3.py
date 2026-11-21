"""R5.1.3: the social sentiment, the mentions and the interactions of the last 24 hours and the most relevant posts of
the most influential creators of every asset of the flow enter the context of the cycle; the adapter is activatable
only with the key of the tenant, and a provider that does not answer is an absent source. On the cycle the worker
composes and on the use cases of the API, with the fake adapters (ADR fonte-social-con-adapter-lunarcrush).
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import timedelta

import pytest
from pytest_bdd import given, then, when

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.ports import AdapterRequest
from autotrading.application.sources.remove_source_credentials import RemoveSourceCredentialsCommand
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, AdapterSelection, SourceSelection
from autotrading.domain.sources.social_snapshot import SocialPost, SocialSnapshot
from tests.fakes.social import API_KEY, FakeSocialAdapter, SocialAsked
from tests.support.flow_cycles import FlowCycles, at
from tests.support.lifecycle_steps import Lifecycle, modify
from tests.support.source_keys import configure_paid
from tests.support.steps import quoted

USER = "anna"
SOCIAL = "social"
TYPED_KEY = "K-LUNAR-SEGRETA"
DEFAULT_POSTS = 5
# Seven posts published, the most relevant first: only the first five, the default of the adapter, reach the agent.
POSTS = tuple(
    SocialPost(f"creatore{index}", at("09:00") - timedelta(minutes=index), f"messaggio {index} su BTC")
    for index in range(1, 8)
)
SNAPSHOT = SocialSnapshot(68, 157841, 136486672, POSTS)


@dataclass
class SocialCycles:
    """The cycles of the flow of anna, with the social provider the platform offers."""

    cycles: FlowCycles = field(default_factory=FlowCycles)
    lifecycle: Lifecycle = field(default_factory=Lifecycle)
    flow: str = ""
    provider: FakeSocialAdapter | None = None

    def adapter(self) -> FakeSocialAdapter:
        assert self.provider is not None
        return self.provider

    def social_entries(self, asset: str | None = None) -> list[dict[str, str]]:
        return self.cycles.sources_in_context(SOCIAL, asset)


@pytest.fixture
def social() -> SocialCycles:
    return SocialCycles()


def selected(adapter: str) -> Callable[[FlowConfiguration], FlowConfiguration]:
    def change(configuration: FlowConfiguration) -> FlowConfiguration:
        selection = SourceSelection(SOCIAL, (AdapterSelection(adapter, DEFAULT_WEIGHT, {}),))
        return replace(configuration, sources=(selection,))

    return change


# Given


@given(
    quoted('che il flusso "{flow}" ha l\'asset "{asset}" e la fonte "{source}" con l\'adapter "{adapter}" configurato')
)
def flow_with_social_source(social: SocialCycles, flow: str, asset: str, source: str, adapter: str) -> None:
    assert source == SOCIAL
    cycles = social.cycles
    social.provider = FakeSocialAdapter(adapter, published={asset: SNAPSHOT})
    cycles.socials[adapter] = social.provider
    cycles.platform.source_systems = cycles.systems()
    cycles.add_flow(USER, flow, assets=(asset,))
    configure_paid(cycles, USER, adapter, TYPED_KEY)
    cycles.reconfigure(flow, selected(adapter))
    social.flow = flow


@given(quoted('che "{user}" non ha configurato l\'adapter "{adapter}"'))
def adapter_not_configured(social: SocialCycles, user: str, adapter: str) -> None:
    use_cases = social.cycles.platform.use_cases_of(user)
    use_cases.remove_source_credentials.execute(RemoveSourceCredentialsCommand(adapter))
    [summary] = [each for each in use_cases.list_source_credentials.execute() if each.adapter == adapter]
    assert not summary.configured


@given(quoted("che {adapter} non risponde"))
def provider_unreachable(social: SocialCycles, adapter: str) -> None:
    assert adapter == social.adapter().name
    social.adapter().reachable = False


# When


@when(quoted('parte il ciclo di "{flow}"'))
def cycle_starts(social: SocialCycles, flow: str) -> None:
    social.cycles.run(flow)


@when(quoted('"{user}" prova ad attivare la fonte "{source}" nel flusso "{flow}"'))
def tries_to_activate(social: SocialCycles, user: str, source: str, flow: str) -> None:
    request = SourceRequest(source, (AdapterRequest(social.adapter().name, None),))
    modify(social.cycles.platform, social.lifecycle, user, flow, sources=(request,))


# Then


@then(
    quoted(
        'il contesto contiene per "{asset}" sentiment social, volume di menzioni e interazioni, e fino a {count} '
        "messaggi con autore, data e testo"
    )
)
def social_in_context(social: SocialCycles, asset: str, count: str) -> None:
    figures, *posts = social.social_entries(asset)
    assert figures == {"sentiment_percento": "68", "menzioni_24h": "157841", "interazioni_24h": "136486672"}
    assert len(posts) == int(count) == DEFAULT_POSTS
    assert posts == [
        {"autore": post.author, "data_ora": post.at.isoformat(), "testo": post.text} for post in POSTS[:DEFAULT_POSTS]
    ]
    # The number of posts is the default of the adapter, read with the key of anna.
    assert social.adapter().asked == [SocialAsked(asset, DEFAULT_POSTS, {API_KEY.name: TYPED_KEY})]


@then(quoted('l\'attivazione è rifiutata con il motivo "{reason}"'))
def activation_refused(social: SocialCycles, reason: str) -> None:
    assert str(social.lifecycle.error) == reason


@then(quoted('la fonte "{source}" è assente nel contesto e il ciclo prosegue'))
def absent_and_cycle_goes_on(social: SocialCycles, source: str) -> None:
    record = social.cycles.last_record(social.flow)
    [absent] = record.absent_sources
    assert (absent.source, absent.adapter) == (source, social.adapter().name)
    assert social.cycles.context()["dati_mancanti"] == [f"{absent.label}: {absent.reason}"]
    assert social.social_entries() == []
    assert CycleStep.AGENT_DECISION in record.steps
    assert record.outcome is CycleOutcome.COMPLETED
