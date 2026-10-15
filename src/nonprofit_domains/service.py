from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .domain_onboarding import DomainOnboarding, NonprofitOnboardingRequest, OnboardingResult
from .infrai_client import InfraiClient, InfraiError

app = FastAPI(title="Nonprofit domain onboarding")


class VerificationEvent(BaseModel):
    event: str
    data: dict[str, Any]


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    supplied = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, supplied)


@app.exception_handler(InfraiError)
async def infrai_error_handler(_: Request, exc: InfraiError) -> JSONResponse:
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=status, content={"error": exc.code, "detail": exc.detail})


@app.post("/nonprofits/domains", response_model=OnboardingResult, status_code=202)
async def onboard_domain(request: NonprofitOnboardingRequest) -> OnboardingResult:
    api_key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(api_key)
    try:
        return await DomainOnboarding(client).start(request)
    finally:
        await client.close()


@app.post("/webhooks/infrai")
async def receive_verification(
    request: Request,
    x_infrai_signature: str = Header(alias="X-Infrai-Signature"),
) -> dict[str, str]:
    body = await request.body()
    secret = os.environ["INFRAI_WEBHOOK_SECRET"]
    if not verify_signature(body, x_infrai_signature, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = VerificationEvent.model_validate(json.loads(body))
    state = "verified" if event.event == "dns.domain.verified" else "ignored"
    return {"state": state, "domain": str(event.data.get("domain", ""))}
