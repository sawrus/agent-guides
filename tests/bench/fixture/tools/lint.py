"""Minimal project lint: every file compiles, lines are at most 100 characters, no tabs or trailing spaces."""
import sys
from pathlib import Path

MAX_LINE = 100


def main(folders):
    problems = []
    for path in sorted(p for folder in folders for p in Path(folder).rglob('*.py')):
        text = path.read_text()
        try:
            compile(text, str(path), 'exec')
        except SyntaxError as error:
            problems.append(f'{path}:{error.lineno}: {error.msg}')
        for number, line in enumerate(text.splitlines(), 1):
            if len(line) > MAX_LINE:
                problems.append(f'{path}:{number}: line longer than {MAX_LINE}')
            if '\t' in line or line != line.rstrip():
                problems.append(f'{path}:{number}: tab or trailing space')
    print('\n'.join(problems) or 'lint: ok')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
