from dataclasses import dataclass

from fastapi import FastAPI


@dataclass(frozen=True, slots=True)
class HealthReport:
    version: str
    environment: str


def create_api(health: HealthReport) -> FastAPI:
    api = FastAPI(title="AutoTrading")

    @api.get("/health")
    def read_health() -> dict[str, str]:
        return {"version": health.version, "environment": health.environment}

    return api
