# inventory

Small stock and pricing library for a shop back office.

- `inventory/pricing.py` — prices, discounts, and order totals.
- `inventory/stock.py` — stock levels, reservations, and returns.
- `inventory/legacy_report.py` — old text report kept for the accounting export.
- `inventory/cli.py` — command line entry point (`python3 -m inventory.cli`).

Run `make test` and `make lint` before every change. Record user-visible changes in `CHANGELOG.md`.
