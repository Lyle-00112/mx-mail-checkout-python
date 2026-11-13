import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from checkout_service import CheckoutRequest, checkout


def test_checkout_queues_fulfillment_and_customer_update():
    request = CheckoutRequest("order-42", "dev@example.com", "typed client", 2)
    result = checkout(request, client=None)
    assert result.order_id == "order-42"
    assert result.fulfillment_status == "queued"
    assert "order-42" in result.customer_update
