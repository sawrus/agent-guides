"""Command line entry point: python3 -m inventory.cli total SKU:QTY:PRICE ... [--discount N]"""
import argparse

from inventory.pricing import order_total, split_payment


def parse_line(raw):
    sku, quantity, price = raw.split(':')
    return sku, int(quantity), price


def main(argv=None):
    parser = argparse.ArgumentParser(prog='inventory')
    commands = parser.add_subparsers(dest='command', required=True)
    total = commands.add_parser('total', help='order total')
    total.add_argument('lines', nargs='+', help='SKU:QTY:PRICE')
    total.add_argument('--discount', type=int, default=0)
    split = commands.add_parser('split', help='split a payment into equal parts')
    split.add_argument('total')
    split.add_argument('parts', type=int)
    args = parser.parse_args(argv)
    if args.command == 'split':
        for part in split_payment(args.total, args.parts):
            print(part)
        return 0
    print(order_total([parse_line(raw) for raw in args.lines], args.discount))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
