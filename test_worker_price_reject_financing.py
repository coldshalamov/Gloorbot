from apps.worker.src.gloorbot_worker.slot_worker import _to_float_price


def test_rejects_monthly_payment_prices() -> None:
    assert (
        _to_float_price("$125/mo Suggested payments with 8 month special financing.")
        is None
    )
    assert _to_float_price("$167 per month Suggested payments.") is None
    assert (
        _to_float_price("Buy Now, Pay Later $85.61 with 12 monthly payments.") is None
    )


def test_thousand_dollar_prices_do_not_concatenate_reviews() -> None:
    # The historic bug only surfaced once we crossed $999.99, because any
    # fallback text pollution (reviews) combined with a "cents rescue" heuristic
    # could manufacture a huge was_price.

    # Crossing the 4-digit dollar frontier should be safe.
    assert _to_float_price("$999.99") == 999.99
    assert _to_float_price("$1,000.00") == 1000.00

    # Normal thousand-dollar cases
    assert _to_float_price("$1,149.00") == 1149.00

    # Lowe's sometimes produces extra trailing digits after the cents in text blobs.
    # We should safely salvage the real price from the prefix.
    assert _to_float_price("$1,149.003756") == 1149.00

    # If reviews are adjacent but separated by whitespace, we must not fuse digits.
    assert _to_float_price("$1149 3756") == 1149.00

    # If digits truly glue into a long run (no separators), refuse to guess.
    assert _to_float_price("$1149003756") is None

    # Still allow the legitimate no-dot cents-appended form.
    assert _to_float_price("$114900") == 1149.00


def test_high_ticket_sanity_rejects_manufactured_was_prices() -> None:
    from apps.worker.src.gloorbot_worker.slot_worker import _deal_from_product

    # Simulate a "manufactured" was_price (price digits + review digits), which tends to
    # only happen once we cross the $1,000 frontier.
    p = {
        "store_id": "0000",
        "store_name": "Test Store",
        "url": "https://www.lowes.com/pd/TEST/1",
        "title": "Test",
        "price": "$900.00",
        "was_price": "$1200300",  # parses to 12003.00 via cents heuristic
        "image_url": None,
    }
    assert _deal_from_product(p, "https://example.com/cat") is None


if __name__ == "__main__":
    test_rejects_monthly_payment_prices()
    test_thousand_dollar_prices_do_not_concatenate_reviews()
