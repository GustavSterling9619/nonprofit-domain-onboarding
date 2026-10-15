from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from .infrai_client import InfraiClient


class DonorReceipts(BaseModel):
    hostname: str = "receipts"
    destination: str = Field(description="CNAME target for receipt pages")


class VolunteerReminders(BaseModel):
    hostname: str = "volunteer"
    destination: str = Field(description="CNAME target for reminder pages")


class CampaignReporting(BaseModel):
    hostname: str = "_campaign-reporting"
    verification_value: str = Field(description="TXT value for campaign reporting")


class NonprofitOnboardingRequest(BaseModel):
    nonprofit_id: str
    domain: str
    receipts: DonorReceipts
    reminders: VolunteerReminders
    reporting: CampaignReporting
    webhook_url: HttpUrl
    webhook_secret: str = Field(min_length=16)


class OnboardingResult(BaseModel):
    nonprofit_id: str
    domain: str
    zone_id: str
    state: str
    records_written: int


class DomainOnboarding:
    def __init__(self, client: InfraiClient) -> None:
        self.client = client

    async def start(self, request: NonprofitOnboardingRequest) -> OnboardingResult:
        domain_data = await self.client.request(
            "POST",
            "/dns/domain/add",
            json={
                "domain": request.domain,
                "metadata": {"nonprofit_id": request.nonprofit_id},
            },
        )
        zone_id = domain_data["zone_id"]

        records = [
            {
                "zone_id": zone_id,
                "record_type": "CNAME",
                "name": request.receipts.hostname,
                "content": request.receipts.destination,
                "ttl": 300,
                "metadata": {"purpose": "donor_receipts"},
            },
            {
                "zone_id": zone_id,
                "record_type": "CNAME",
                "name": request.reminders.hostname,
                "content": request.reminders.destination,
                "ttl": 300,
                "metadata": {"purpose": "volunteer_reminders"},
            },
            {
                "zone_id": zone_id,
                "record_type": "TXT",
                "name": request.reporting.hostname,
                "content": request.reporting.verification_value,
                "ttl": 300,
                "metadata": {"purpose": "campaign_reporting"},
            },
        ]
        for record in records:
            await self.client.request("PUT", "/dns/record/upsert", json=record)

        await self.client.request(
            "POST",
            "/account/webhooks/register",
            json={
                "url": str(request.webhook_url),
                "events": ["dns.domain.verified"],
                "description": f"Domain verification for {request.nonprofit_id}",
                "secret": request.webhook_secret,
            },
        )
        await self.client.request(
            "POST",
            "/dns/domain/verify",
            json={"domain": request.domain},
        )
        return OnboardingResult(
            nonprofit_id=request.nonprofit_id,
            domain=request.domain,
            zone_id=zone_id,
            state="awaiting_verification",
            records_written=len(records),
        )
