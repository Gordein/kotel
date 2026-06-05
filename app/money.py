from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def parse_amount(value) -> Decimal:
    d = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    if d <= 0:
        raise ValueError("amount must be > 0")
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
