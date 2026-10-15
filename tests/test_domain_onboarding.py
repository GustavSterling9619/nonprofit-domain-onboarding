from __future__ import annotations

import asyncio

from nonprofit_domains.domain_onboarding import DomainOnboarding, NonprofitOnboardingRequest


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    async def request(self, method: str, path: str, *, json: dict[str, object]):
        self.calls.append((method, path, json))
        if path == "/dns/domain/add":
            return {"zone_id": "zone_food_bank"}
        return {"accepted": True}


def test_onboarding_uses_returned_zone_and_requests_verification() -> None:
    client = RecordingClient()
    request = NonprofitOnboardingRequest.model_validate(
        {
            "nonprofit_id": "river-town-food-bank",
            "domain": "give.rivertown.example",
            "receipts": {"destination": "receipts.product.example"},
            "reminders": {"destination": "volunteers.product.example"},
            "reporting": {"verification_value": "campaign=river-town"},
            "webhook_url": "https://app.product.example/webhooks/infrai",
            "webhook_secret": "a-local-test-secret",
        }
    )

    result = asyncio.run(DomainOnboarding(client).start(request))  # type: ignore[arg-type]

    record_calls = [call for call in client.calls if call[1] == "/dns/record/upsert"]
    assert len(record_calls) == 3
    assert {call[2]["zone_id"] for call in record_calls} == {"zone_food_bank"}
    assert [call[2]["record_type"] for call in record_calls] == ["CNAME", "CNAME", "TXT"]
    assert client.calls[-1] == (
        "POST",
        "/dns/domain/verify",
        {"domain": "give.rivertown.example"},
    )
    assert result.state == "awaiting_verification"
    assert result.records_written == 3
