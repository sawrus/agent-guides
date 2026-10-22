"""Parcel shipping cost by weight."""
from decimal import Decimal, ROUND_CEILING

BASE_FEE = Decimal('4.90')
RATE_PER_KG = Decimal('1.20')
INCLUDED_KG = 1


def shipping_cost(weight_kg):
    """Return the cost in Decimal.

    The base fee covers the first kilogram; every started kilogram above it adds RATE_PER_KG.
    """
    weight = Decimal(str(weight_kg))
    if weight <= 0:
        raise ValueError('weight must be positive')
    extra_kg = max(started_kilograms(weight) - INCLUDED_KG, 0)
    return BASE_FEE + RATE_PER_KG * extra_kg


def started_kilograms(weight):
    return int(weight.to_integral_value(rounding=ROUND_CEILING))
