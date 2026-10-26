"""Customer orders and their invoices."""
from decimal import Decimal

from inventory.pricing import apply_discount, to_money
from inventory.tax import tax_amount


class Order:
    def __init__(self):
        self.lines = []

    def add(self, sku, quantity, unit_price):
        if quantity <= 0:
            raise ValueError('quantity must be positive')
        self.lines.append((sku, quantity, unit_price))

    def subtotal(self):
        return to_money(sum((to_money(unit) * qty for _, qty, unit in self.lines), Decimal('0')))

    def invoice(self, discount_percent=0, tax_percent=0):
        """Invoice amounts as a dict: subtotal, discounted, tax, total."""
        subtotal = self.subtotal()
        discounted = apply_discount(subtotal, discount_percent)
        tax = tax_amount(subtotal, tax_percent)
        return {'subtotal': subtotal, 'discounted': discounted, 'tax': tax,
                'total': discounted + tax}
