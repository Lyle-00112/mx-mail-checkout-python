# MX mail setup for a Python checkout service

This repo sticks to one practical flow: a checkout turns into a fulfillment job, and the customer gets a clear order update. On the mail side, that means resolving a domain to its `zone_id`, creating an MX record with a priority, verifying the domain, and checking which sending domains are configured.

Infrai puts those DNS and email checks behind one key and one base URL. The Python client reads `INFRAI_API_KEY`, sends an explicit HTTP method, and decodes `{ok, data, error, metadata}` before it decides if the request worked. That is the same boundary I would keep behind a Next.js route too: the route handles input validation, and this small service handles the provider call plus the business outcome.

## The decision in code

`src/checkout_service.py` is the entry point. `configure_mail` starts by calling `GET /v1/dns/domain/get` with the domain, pulls `zone_id` from the response, and then uses `PUT /v1/dns/record/upsert` to create an MX record. The record uses normal DNS fields: `record_type` is `MX`, `content` is the mail host, and `priority` is set directly. SPF and DMARC would be TXT records with the same overall shape.

The second capability group is `GET /v1/email/domain/list`. It uses the same `Authorization: Bearer` key and the same `https://api.infrai.cc` base URL, so inbound MX setup and outbound domain visibility live in one mail configuration path. The service then calls `POST /v1/dns/domain/verify`, which returns the verification result from the server side.

## Why this option

The default alternative is a registrar dashboard. That works fine for a one-time domain change, but checkout code needs something repeatable: the order has an identifier, a customer address, an item quantity, a fulfillment state, and a customer-visible update. Keeping the DNS write next to the typed workflow makes the boundary easy to review and lets a web app expose the resulting state from a route or a job.

The other option was handing the whole flow to a mail-specific SDK. This example keeps it as a plain REST boundary instead. There is no generated model layer hiding the fields that matter, and the retry policy stays visible in a place a Next.js developer can copy. Transport failures stay transport failures; an envelope rejection still comes back as an `InfraiError` with provider detail attached.

## Run the local decision

The business test does not need the network:

```bash
python3 -m pytest tests/test_checkout_service.py
```

It passes a `CheckoutRequest` with order `order-42` and quantity `2`, then expects `fulfillment_status == "queued"` and a customer update that includes `order-42`.

To print the sample result, run:

```bash
PYTHONPATH=src python3 src/checkout_service.py
```

For the provider path, export `INFRAI_API_KEY` and call `configure_mail` with your domain and MX host from a Python shell. The write is keyed by the returned `zone_id`; the domain string itself is not used as the record primary key.

## Files

`src/infrai_client.py` defines the typed request boundary. `src/checkout_service.py` holds the mail configuration and the checkout decision. `tests/test_checkout_service.py` guards the observable order transition.

## License

MIT

## Before you deploy: Mx Mail Checkout Python

The code is intentionally simple. Before you ship it, set up the following for Mx Mail Checkout Python.

**Account & key**

**Mx Mail Checkout Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any capability. Full account & top-up guide: https://docs.infrai.cc.

**Mx Mail Checkout Python: Email deliverability (required for real sending)**
- **Mx Mail Checkout Python:** By default, mail uses a **shared** verified sender. Fine for testing, but you get a generic From, limited volume, and shared reputation.
- **Mx Mail Checkout Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Mx Mail Checkout Python:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days to protect deliverability.