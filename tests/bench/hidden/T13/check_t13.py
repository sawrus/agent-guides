"""T13 grader: a new `wordfreq` project has a spec, a glossary, an ADR, tests, and working code.

Usage: check_t13.py <project>. Exit 0 when every item holds; otherwise print the failed items and exit 1.
Items: a spec (SPEC.md, docs/spec*.md, or docs/*spec*), GLOSSARY.md (root or docs/), at least one ADR file
(docs/adr/, docs/decisions/, or adr/), at least 3 test functions, and `python3 -m wordfreq` behaviour:
lower-cased `\\w+` words, count descending then word ascending, `-n`, FILE or stdin.
`make test` and `make lint` are graded by the harness (`suite` and `lint` checks).
"""
import subprocess
import sys
from pathlib import Path

SAMPLE = 'The cat and the dog. The END, and the Cat!\n'
TOP3 = 'the 4\nand 2\ncat 2\n'


def found(project, patterns):
    return any(p.is_file() and p.stat().st_size > 40 for pattern in patterns for p in project.glob(pattern))


def run(project, args, stdin=None):
    return subprocess.run([sys.executable, '-m', 'wordfreq', *args], cwd=project, input=stdin, capture_output=True,
                          text=True, timeout=30, env={'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(project)})


def check(project):
    failed = []
    if not found(project, ['SPEC.md', 'docs/spec*.md', 'docs/*spec*', 'docs/*/spec*.md', 'spec*.md']):
        failed.append('spec')
    if not found(project, ['GLOSSARY.md', 'docs/GLOSSARY.md', 'docs/glossary.md', 'glossary.md']):
        failed.append('glossary')
    if not found(project, ['docs/adr/*.md', 'docs/decisions/*.md', 'adr/*.md', 'docs/adrs/*.md']):
        failed.append('adr')
    tests = sum(path.read_text(errors='replace').count('def test_') for path in (project / 'tests').rglob('*.py')) \
        if (project / 'tests').is_dir() else 0
    if tests < 3:
        failed.append(f'tests ({tests} < 3)')
    try:
        by_stdin = run(project, ['-n', '3'], SAMPLE)
        sample = project / 'sample.txt'
        sample.write_text(SAMPLE)
        by_file = run(project, ['-n', '3', str(sample)])
        sample.unlink()
        if by_stdin.returncode or by_stdin.stdout != TOP3:
            failed.append(f'stdin output {by_stdin.stdout!r} {by_stdin.stderr[-200:]!r}')
        if by_file.returncode or by_file.stdout != TOP3:
            failed.append(f'file output {by_file.stdout!r}')
    except (OSError, subprocess.SubprocessError) as error:
        failed.append(f'run: {error}')
    return failed


if __name__ == '__main__':
    problems = check(Path(sys.argv[1]))
    print('\n'.join(problems) or 'T13: ok')
    raise SystemExit(1 if problems else 0)
