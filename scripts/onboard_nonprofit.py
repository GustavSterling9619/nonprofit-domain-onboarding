from __future__ import annotations

import asyncio
import os

from nonprofit_domains.domain_onboarding import DomainOnboarding, NonprofitOnboardingRequest
from nonprofit_domains.infrai_client import InfraiClient


async def main() -> None:
    request = NonprofitOnboardingRequest.model_validate(
        {
            "nonprofit_id": "river-town-food-bank",
            "domain": "example.org",
            "receipts": {"destination": "receipts.product.example"},
            "reminders": {"destination": "volunteers.product.example"},
            "reporting": {"verification_value": "campaign=river-town-food-bank"},
            "webhook_url": "https://app.product.example/webhooks/infrai",
            "webhook_secret": os.environ["INFRAI_WEBHOOK_SECRET"],
        }
    )
    client = InfraiClient(os.environ["INFRAI_API_KEY"])
    try:
        result = await DomainOnboarding(client).start(request)
        print(result.model_dump_json(indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
