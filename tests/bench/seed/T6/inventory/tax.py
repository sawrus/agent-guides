"""Sales tax on money amounts."""
from decimal import Decimal

from inventory.pricing import to_money


def tax_amount(amount, percent):
    """Tax on an amount, rounded to cents half-up."""
    if percent < 0:
        raise ValueError('percent must not be negative')
    return to_money(to_money(amount) * Decimal(percent) / 100)
