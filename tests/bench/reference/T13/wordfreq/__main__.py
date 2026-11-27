import argparse
import sys

from wordfreq import top


def main(argv=None):
    parser = argparse.ArgumentParser(prog='wordfreq')
    parser.add_argument('file', nargs='?', help='text file; stdin when omitted')
    parser.add_argument('-n', type=int, default=10, help='how many words to print')
    args = parser.parse_args(argv)
    text = open(args.file, encoding='utf-8').read() if args.file else sys.stdin.read()
    for word, count in top(text, args.n):
        print(f'{word} {count}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
