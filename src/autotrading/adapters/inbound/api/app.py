from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request, Response

ENVIRONMENT_HEADER = "X-Autotrading-Environment"


@dataclass(frozen=True, slots=True)
class HealthReport:
    version: str
    environment: str


def create_api(health: HealthReport) -> FastAPI:
    api = FastAPI(title="AutoTrading")

    # A middleware covers every answer, errors included, so no response can leave without the environment (R0.1.4).
    @api.middleware("http")
    async def declare_environment(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers[ENVIRONMENT_HEADER] = health.environment
        return response

    @api.get("/health")
    def read_health() -> dict[str, str]:
        return {"version": health.version, "environment": health.environment}

    return api
