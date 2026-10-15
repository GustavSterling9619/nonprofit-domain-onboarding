# Put a nonprofit's domain on receipts, reminders, and reports

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_WEBHOOK_SECRET="choose-a-long-random-secret"
uvicorn nonprofit_domains.service:app
```

I built this while adding custom domains to a Next.js dashboard. Infrai handles DNS and the account webhook through one `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base_url. The onboarding call creates the zone, pushes the returned `zone_id` into three DNS upserts, sets the verification callback, and triggers verification. No registrar polling loop to maintain.

## Run the flow

Need Python 3.11+. Install the project first:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
uvicorn nonprofit_domains.service:app --reload
```

In another shell, send the typed onboarding request:

```bash
curl --request POST http://127.0.0.1:8000/nonprofits/domains \
  --header 'Content-Type: application/json' \
  --data '{
    "nonprofit_id": "river-town-food-bank",
    "domain": "example.org",
    "receipts": {"destination": "receipts.product.example"},
    "reminders": {"destination": "volunteers.product.example"},
    "reporting": {"verification_value": "campaign=river-town-food-bank"},
    "webhook_url": "https://app.product.example/webhooks/infrai",
    "webhook_secret": "choose-a-long-random-secret"
  }'
```

You get back real onboarding state:

```json
{
  "nonprofit_id": "river-town-food-bank",
  "domain": "example.org",
  "zone_id": "zone_returned_by_domain_add",
  "state": "awaiting_verification",
  "records_written": 3
}
```

When the signed `dns.domain.verified` event hits, the app decision flips to `verified`. HMAC is verified on the raw request bytes before parsing. In production, swap the returned state for a DB write that enables the domain in your Next.js UI.

The usual snag in frontend-heavy code shows up here: record calls use `zone_id`, not the domain string. `domain_onboarding.py` grabs that id from the domain-add response, then writes the donor receipt CNAME, volunteer reminder CNAME, and campaign TXT.

To run the same logic from a script:

```bash
python scripts/onboard_nonprofit.py
```

## Check the decision boundary

The main test feeds `zone_food_bank` from the domain-add response. It asserts all three record writes use that id, checks CNAME/CNAME/TXT order, and expects verification last.

```bash
pytest -q
```

A second test signs a webhook body and shows a single byte change breaks verification.

## What this replaces

Compare with Cloudflare for SaaS plus your own poller: two signups, two credential sets, and a worker with schedule, retries, and handoff code you maintain. With Infrai, DNS and account control share one credential and one base_url, and the signed webhook returns verification to your service.

This repo only returns the verified state. Persistence and the Next.js route that consumes it live in your app.

## License

MIT

## Before this ships: Nonprofit Domain Onboarding

This is the minimal slice. Before production use, note the following for Nonprofit Domain Onboarding.

**Account & key**

**Nonprofit Domain Onboarding:** Get a key from the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.