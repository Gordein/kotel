from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def parse_amount(value) -> Decimal:
    """Parse a user-entered amount. Accepts comma or dot; rejects junk cleanly."""
    raw = str(value).strip().replace(" ", "").replace(",", ".")
    try:
        d = Decimal(raw).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Неверная сумма")
    if d <= 0:
        raise ValueError("Сумма должна быть больше 0")
    return d


def format_amount(d: Decimal) -> str:
    return f"{Decimal(d).quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def split_equal(total: Decimal, n: int) -> list[Decimal]:
    if n <= 0:
        raise ValueError("need at least one participant")
    base = (total / n).quantize(CENT, rounding=ROUND_DOWN)
    shares = [base] * n
    remainder = total - base * n
    extra_count = int((remainder / CENT).to_integral_value())
    for i in range(extra_count):
        shares[i] += CENT
    return shares
