"""Money helpers.

Never use floating point for money. All amounts are `Decimal` and stored in
PostgreSQL NUMERIC columns. This module centralises rounding and fee maths so
the rules stay consistent everywhere.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0.00")


def to_decimal(value: Any) -> Decimal:  # type: ignore[name-defined]
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_fee(amount: Decimal, fee_fraction: Decimal) -> Decimal:
    return quantize(to_decimal(amount) * fee_fraction)


def net_after_fee(gross: Decimal, fee_fraction: Decimal) -> Decimal:
    gross = to_decimal(gross)
    return quantize(gross - calculate_fee(gross, fee_fraction))


def format_amount(amount: Decimal, currency: str = "UGX") -> str:
    value = to_decimal(amount)
    return f"{currency} {value:,.2f}"
