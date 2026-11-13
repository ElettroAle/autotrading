from typing import Any

import httpx
import httpx2

PROBLEM_MEMBERS = {"type", "title", "status", "requestId", "traceId"}


def reason_of(response: httpx.Response | httpx2.Response) -> dict[str, Any]:
    """What a Problem Details answer says about the failure, without the members every problem carries."""
    problem: dict[str, Any] = response.json()
    return {name: value for name, value in problem.items() if name not in PROBLEM_MEMBERS}
