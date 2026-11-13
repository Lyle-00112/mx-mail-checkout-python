from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from infrai_client import InfraiClient


@dataclass(frozen=True)
class CheckoutRequest:
    order_id: str
    customer_email: str
    item: str
    quantity: int


@dataclass(frozen=True)
class Receipt:
    order_id: str
    fulfillment_status: str
    customer_update: str


def configure_mail(client: InfraiClient, domain: str, mx_host: str) -> dict[str, Any]:
    """Take the domain response's zone_id before changing its MX record."""
    domain_result = client.get_domain(domain)
    domain_data = domain_result.data or {}
    zone_id = domain_data.get("zone_id")
    if not zone_id:
        domain_result = client.add_domain(domain)
        zone_id = (domain_result.data or {}).get("zone_id")
    if not zone_id:
        raise ValueError("domain response did not include zone_id")
    record = client.upsert_record(zone_id, "@", mx_host, 10)
    verification = client.verify_domain(domain)
    outbound = client.email_domains()
    return {"zone_id": zone_id, "record": record.data, "verification": verification.data,
            "outbound_domains": outbound.data}


def checkout(request: CheckoutRequest, client: InfraiClient) -> Receipt:
    if request.quantity < 1:
        raise ValueError("quantity must be positive")
    return Receipt(request.order_id, "queued", f"Order {request.order_id} is queued for fulfillment")


def main() -> None:
    request = CheckoutRequest("order-1007", "buyer@example.com", "webhook handbook", 1)
    receipt = checkout(request, InfraiClient())
    print(f"{receipt.order_id}: {receipt.fulfillment_status}; {receipt.customer_update}")


if __name__ == "__main__":
    main()
