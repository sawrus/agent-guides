"""Prices are Decimal amounts in the shop currency, rounded to cents half-up."""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal('0.01')


def to_money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def apply_discount(price, percent):
    """Price after a percentage discount.

    Example: apply_discount('19.99', 15) -> Decimal('16.99').
    """
    if not 0 <= percent <= 100:
        raise ValueError('percent must be between 0 and 100')
    price = to_money(price)
    discount = to_money(price * percent / 100)
    return to_money(price - discount)


def order_total(lines, percent=0):
    """Sum of quantity * unit price over (sku, quantity, unit_price) lines, then the discount."""
    subtotal = sum((to_money(unit) * quantity for _, quantity, unit in lines), Decimal('0'))
    return apply_discount(subtotal, percent)
