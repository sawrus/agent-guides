"""Languages and line counts: `scc` when it is on PATH, else a built-in counter over tracked files."""
import json
from pathlib import Path
import shutil
import subprocess

from .common import read_text

LANGUAGES = {
    '.py': 'Python', '.pyi': 'Python', '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin',
    '.scala': 'Scala', '.js': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript', '.jsx': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript', '.vue': 'Vue', '.svelte': 'Svelte', '.rb': 'Ruby', '.php': 'PHP',
    '.cs': 'C#', '.c': 'C', '.h': 'C', '.cpp': 'C++', '.hpp': 'C++', '.cc': 'C++', '.swift': 'Swift',
    '.sh': 'Shell', '.bash': 'Shell', '.sql': 'SQL', '.tf': 'Terraform', '.hcl': 'HCL', '.proto': 'Protocol Buffers',
    '.yml': 'YAML', '.yaml': 'YAML', '.json': 'JSON', '.toml': 'TOML', '.md': 'Markdown', '.rst': 'Markdown',
    '.html': 'HTML', '.css': 'CSS', '.scss': 'CSS', '.ipynb': 'Jupyter', '.lua': 'Lua', '.groovy': 'Groovy',
    '.tpl': 'Go Template', '.j2': 'Jinja', '.jinja': 'Jinja', '.avsc': 'Avro',
}
NAMES = {'Dockerfile': 'Dockerfile', 'Makefile': 'Makefile', 'Jenkinsfile': 'Groovy'}
# Languages that do not count as code for the junk rule.
NOT_CODE = {'Markdown', 'JSON', 'YAML', 'TOML', 'Jupyter', 'Avro', 'Plain Text', 'CSV', 'License', 'gitignore',
            'Unknown'}
# Configuration languages: a repository of CI templates or GitOps manifests is not junk.
CONFIG = {'YAML', 'JSON', 'TOML'}


def language_of(rel):
    name = Path(rel).name
    if name in NAMES or name.startswith('Dockerfile'):
        return NAMES.get(name, 'Dockerfile')
    return LANGUAGES.get(Path(rel).suffix.lower())


def builtin_counts(repo, files):
    langs = {}
    for rel in files:
        lang = language_of(rel)
        if not lang:
            continue
        text = read_text(Path(repo) / rel, limit=2 * 1024 * 1024)
        if text is None:
            continue
        code = sum(1 for line in text.splitlines() if line.strip())
        entry = langs.setdefault(lang, {'files': 0, 'code': 0})
        entry['files'] += 1
        entry['code'] += code
    return langs


def scc_counts(repo):
    try:
        out = subprocess.run(['scc', '--format', 'json', '--no-cocomo', str(repo)], capture_output=True, text=True,
                             timeout=300, check=True).stdout
        data = json.loads(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return {item['Name']: {'files': item.get('Count', 0), 'code': item.get('Code', 0)} for item in data
            if isinstance(item, dict) and 'Name' in item}


def count(repo, files, use_scc=None):
    if use_scc is None:
        use_scc = shutil.which('scc') is not None
    langs = scc_counts(repo) if use_scc else None
    tool = 'scc' if langs is not None else 'builtin'
    if langs is None:
        langs = builtin_counts(repo, files)
    langs = dict(sorted(langs.items(), key=lambda kv: -kv[1]['code']))
    code = sum(v['code'] for k, v in langs.items() if k not in NOT_CODE)
    config = sum(v['code'] for k, v in langs.items() if k in CONFIG)
    return {'tool': tool, 'languages': langs, 'code_lines': code, 'config_lines': config, 'files': len(files)}
