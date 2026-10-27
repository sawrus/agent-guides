"""Minimal manifest checks without a YAML library.

test: every document has top-level `apiVersion:`, `kind:`, and `metadata:` keys.
lint: no tabs, no trailing spaces, lines at most 120 characters, files end with a newline.
"""
import sys
from pathlib import Path

MAX_LINE = 120


def documents(text):
    doc = []
    for line in text.splitlines():
        if line.strip() == '---':
            yield doc
            doc = []
        elif line.strip() and not line.lstrip().startswith('#'):
            doc.append(line)
    yield doc


def main(mode, folder):
    problems = []
    for path in sorted(Path(folder).rglob('*.y*ml')):
        text = path.read_text()
        if mode == 'test':
            for number, doc in enumerate(documents(text), 1):
                if doc:
                    keys = {line.split(':', 1)[0] for line in doc if not line.startswith((' ', '-'))}
                    missing = {'apiVersion', 'kind', 'metadata'} - keys
                    if missing:
                        problems.append(f'{path}: document {number} misses {sorted(missing)}')
        else:
            if text and not text.endswith('\n'):
                problems.append(f'{path}: no newline at end of file')
            for number, line in enumerate(text.splitlines(), 1):
                if len(line) > MAX_LINE:
                    problems.append(f'{path}:{number}: line longer than {MAX_LINE}')
                if '\t' in line or line != line.rstrip():
                    problems.append(f'{path}:{number}: tab or trailing space')
    print('\n'.join(problems) or f'{mode}: ok')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
