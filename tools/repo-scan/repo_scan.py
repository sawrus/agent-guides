#!/usr/bin/env python3
"""repo-scan entry point. See tools/repo-scan/README.md.

  python3 tools/repo-scan/repo_scan.py scan ROOT... --out DIR
  python3 tools/repo-scan/repo_scan.py gate-propose --in DIR
  python3 tools/repo-scan/repo_scan.py gate-verify REPO...
  python3 tools/repo-scan/repo_scan.py llm --in DIR --provider claude --model haiku
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reposcan.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
