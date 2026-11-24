"""ADR-asset-del-flusso-nel-riepilogo-dei-flussi (Bug 731): the overview of the flows of the API answers the assets of
the version in force of each flow, and the card of the dashboard shows them from that answer alone, joined by « · » or
«nessuno», never from a second reading of the flows (ADR 0116).
"""

import re
from pathlib import Path

from fastapi import FastAPI

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform

FLOWS = Path(__file__).resolve().parents[2] / "dashboard" / "src" / "features" / "flows"
OVERVIEW_QUERY = FLOWS / "api" / "get-flow-overviews.ts"
CARD = FLOWS / "components" / "flow-overview-card.tsx"
ASSETS_SCHEMA = re.compile(r"\bassets:\s*z\.array\(z\.string\(\)\)")
OTHER_READINGS = re.compile(r"api\.GET\('/flows(?!/overview)|from '\.\./api/get-flows?'")

READING_THE_FLOWS = """
import { useFlows } from '../api/get-flows';
export const FlowOverviewCard = ({ flow }) => {
  const flows = useFlows();
  return <Fact term="Asset">{flows.data?.find((one) => one.id === flow.id)?.assets.join(', ')}</Fact>;
};
"""
FROM_THE_OVERVIEW = """
const assetsOf = ({ assets }: FlowOverview): string => (assets.length === 0 ? 'nessuno' : assets.join(' · '));
export const FlowOverviewCard = ({ flow }) => <Fact term="Asset">{assetsOf(flow)}</Fact>;
"""
OVERVIEW_SCHEMA = "const flowOverviewSchema = z.object({ id: z.string(), assets: z.array(z.string()) });"


def overview_api() -> FastAPI:
    return create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(InMemoryTenantRepositoryAdapter()),
        Platform().for_tenant,
        IdentityProvider().authentication(),
    )


def violations(card: str, overview_query: str) -> list[str]:
    """What keeps the card from showing the assets of the overview alone."""
    found = []
    if not ASSETS_SCHEMA.search(overview_query):
        found.append("no assets in the schema of the overview")
    if OTHER_READINGS.search(card):
        found.append("the card reads the flows a second time")
    if 'term="Asset"' not in card:
        found.append("no row of the assets in the card")
    if "' · '" not in card or "'nessuno'" not in card:
        found.append("the assets not joined by « · » or «nessuno»")
    return found


def test_adr_asset_del_flusso_nel_riepilogo_dei_flussi_the_overview_answers_the_assets_as_a_list_of_texts() -> None:
    schema = overview_api().openapi()["components"]["schemas"]["FlowOverviewResponse"]

    assert schema["properties"]["assets"] == {"items": {"type": "string"}, "type": "array", "title": "Assets"}
    assert "assets" in schema["required"]


def test_adr_asset_del_flusso_nel_riepilogo_dei_flussi_the_card_shows_the_assets_of_the_overview_alone() -> None:
    assert violations(CARD.read_text(encoding="utf-8"), OVERVIEW_QUERY.read_text(encoding="utf-8")) == []


def test_adr_asset_del_flusso_nel_riepilogo_dei_flussi_a_card_reading_the_flows_again_is_found() -> None:
    assert violations(READING_THE_FLOWS, "const flowOverviewSchema = z.object({ id: z.string() });") == [
        "no assets in the schema of the overview",
        "the card reads the flows a second time",
        "the assets not joined by « · » or «nessuno»",
    ]
    assert violations(FROM_THE_OVERVIEW, OVERVIEW_SCHEMA) == []
