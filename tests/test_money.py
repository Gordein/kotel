from decimal import Decimal

import pytest

from app.money import format_amount, parse_amount, split_equal


def test_parse_rounds_to_grosze():
    assert parse_amount("33.335") == Decimal("33.34")
    assert parse_amount(5.5) == Decimal("5.50")


def test_parse_rejects_non_positive():
    with pytest.raises(ValueError):
        parse_amount("0")
    with pytest.raises(ValueError):
        parse_amount("-3")


def test_split_equal_distributes_remainder():
    shares = split_equal(Decimal("100.00"), 3)
    assert shares == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert sum(shares) == Decimal("100.00")


def test_split_equal_clean():
    assert split_equal(Decimal("90.00"), 3) == [Decimal("30.00")] * 3


def test_format_amount():
    assert format_amount(Decimal("5.5")) == "5.50"


def test_parse_rejects_empty_and_junk():
    with pytest.raises(ValueError):
        parse_amount("")
    with pytest.raises(ValueError):
        parse_amount("abc")
    with pytest.raises(ValueError):
        parse_amount("   ")


def test_parse_accepts_comma():
    assert parse_amount("20,50") == Decimal("20.50")
    assert parse_amount(" 1 234,5 ") == Decimal("1234.50")
