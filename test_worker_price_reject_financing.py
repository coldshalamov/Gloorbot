from apps.worker.src.gloorbot_worker.slot_worker import _to_float_price


def test_rejects_monthly_payment_prices() -> None:
    assert _to_float_price("$125/mo Suggested payments with 8 month special financing.") is None
    assert _to_float_price("$167 per month Suggested payments.") is None
    assert _to_float_price("Buy Now, Pay Later $85.61 with 12 monthly payments.") is None


if __name__ == "__main__":
    test_rejects_monthly_payment_prices()

