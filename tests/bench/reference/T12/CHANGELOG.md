# Changelog

## Unreleased

- Add `loyalty_price(price, orders_count)`.
  Assumptions: "regular customer" means completed orders; 2% off per 5 orders; cap 20%; new customers pay full price.
  Acceptance criteria: 0 orders gives the list price; the price never rises with more orders; result is in cents.

## 0.3.0

- Add stock returns (`restock_returned`).

## 0.2.0

- Add order totals with discounts.
