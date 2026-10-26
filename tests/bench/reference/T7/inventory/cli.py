"""Command line entry point: python3 -m inventory.cli total|reserve ..."""
import argparse
import sys

from inventory.pricing import order_total
from inventory.stock import OutOfStock, Stock


def parse_line(raw):
    sku, quantity, price = raw.split(':')
    return sku, int(quantity), price


def parse_pair(raw):
    sku, quantity = raw.split(':')
    return sku, int(quantity)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='inventory')
    commands = parser.add_subparsers(dest='command', required=True)
    total = commands.add_parser('total', help='order total')
    total.add_argument('lines', nargs='+', help='SKU:QTY:PRICE')
    total.add_argument('--discount', type=int, default=0)
    reserve = commands.add_parser('reserve', help='reserve several lines at once')
    reserve.add_argument('--stock', required=True, help='SKU:QTY,SKU:QTY')
    reserve.add_argument('lines', nargs='+', help='SKU:QTY')
    args = parser.parse_args(argv)
    if args.command == 'reserve':
        stock = Stock(dict(parse_pair(raw) for raw in args.stock.split(',')))
        try:
            remaining = stock.reserve_many([parse_pair(raw) for raw in args.lines])
        except OutOfStock as error:
            print(f'out of stock: {error}', file=sys.stderr)
            return 2
        for sku in sorted(remaining):
            print(sku, remaining[sku])
        return 0
    print(order_total([parse_line(raw) for raw in args.lines], args.discount))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
