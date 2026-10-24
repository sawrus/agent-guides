# inventory

Small stock and pricing library for a shop back office.

- `inventory/pricing.py` — prices, discounts, and order totals.
- `inventory/tax.py` — sales tax.
- `inventory/orders.py` — orders and invoices.
- `inventory/stock.py` — stock levels, reservations, and returns.
- `inventory/legacy_report.py` — old text report kept for the accounting export.
- `inventory/cli.py` — command line entry point (`python3 -m inventory.cli`).

Shop invoice rules: the discount applies to the order subtotal, tax applies to the amount after the
discount, and every amount is rounded to cents half-up.

Run `make test` and `make lint` before every change. Record user-visible changes in `CHANGELOG.md`.
