"""Stage 2: LLM assessment over stage-1 JSON plus short, redacted excerpts.

Providers: `litellm` (OpenAI-compatible HTTP API; key only from env AGENTIC_LLM_API_KEY) and `claude`
(`claude -p`). Results are cached by repository HEAD sha, provider and model.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request

from .common import read_text, redact, write_json

PROMPT_VERSION = 1
DEFAULT_BASE_URL = 'https://llm.dats.services/'
# The proxy expects the bare model id. `dats_ai/coding-agent-default` is the OpenCode provider/model form;
# the provider prefix is not part of the id (HTTP 403 "team not allowed to access model").
DEFAULT_LITELLM_MODEL = 'coding-agent-default'
CLAUDE_MODELS = ('haiku', 'sonnet', 'opus', 'fable')
EXCERPT_LINES = 60
EXCERPT_CHARS = 3000

SYSTEM = ('You assess one software repository for an engineering team that uses a catalog of agent workflows '
          'and rules (agent-guides). Use only the facts given. Do not invent files, services or ids. '
          'Answer with one JSON object and nothing else.')

SCHEMA = '''{
  "summary": "one or two sentences: what the repository is and does",
  "applicability": [{"id": "<guide id from candidates>", "applies": true, "confidence": 0.0, "why": "short"}],
  "missing_guides": ["<workflow or rule id from all_guide_ids that fits but is not in candidates>"],
  "risks": ["short risk statements grounded in the facts"],
  "recommendations": ["short, concrete next steps"],
  "gate": {"commands": ["checks an agent should run before finishing"], "notes": "short"}
}'''


def excerpt(repo, rel):
    text = read_text(Path(repo) / rel)
    if not text:
        return None
    lines = text.splitlines()[:EXCERPT_LINES]
    return redact('\n'.join(lines))[:EXCERPT_CHARS]


def build_prompt(record, applicability, relationships, guide_ids):
    repo = record['path']
    excerpts = {}
    for rel in ('README.md', 'README.rst', 'README', 'Makefile', '.gitlab-ci.yml'):
        text = excerpt(repo, rel)
        if text:
            excerpts[rel] = text
    facts = {k: record[k] for k in ('id', 'name', 'activity', 'metrics', 'top_level', 'agents', 'makefile', 'ci',
                                    'manifests', 'kafka_topics') if k in record}
    facts['metrics'] = dict(facts.get('metrics', {}), languages=dict(list(record['metrics']['languages'].items())[:8]))
    edges = [{k: e[k] for k in ('from', 'to', 'kind', 'confidence', 'detail')} for e in relationships
             if record['id'] in (e['from'], e['to'])][:40]
    candidates = {'rules': [r['id'] for r in applicability.get('rules', [])],
                  'workflows': [w['id'] for w in applicability.get('workflows', [])],
                  'task_routing': applicability.get('task_routing', {})}
    payload = {'repository': facts, 'relationships': edges, 'candidates': candidates,
               'all_guide_ids': guide_ids, 'excerpts': excerpts}
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    return (f'{SYSTEM}\n\nReturn JSON with this shape:\n{SCHEMA}\n\n'
            f'Repository facts (static scan, values of secrets removed):\n{body}\n')


def parse_answer(text):
    text = text.strip()
    m = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', text)
    if m:
        text = m.group(1)
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end < start:
        raise ValueError('no JSON object in answer')
    return json.loads(text[start:end + 1])


def validate(answer, guide_ids):
    known = set(guide_ids['workflows']) | set(guide_ids['rules'])
    invalid = []
    for item in answer.get('applicability') or []:
        if isinstance(item, dict) and item.get('id') not in known:
            invalid.append(item.get('id'))
    answer['applicability'] = [i for i in answer.get('applicability') or []
                               if isinstance(i, dict) and i.get('id') in known]
    missing = answer.get('missing_guides') or []
    invalid += [g for g in missing if g not in known]
    answer['missing_guides'] = [g for g in missing if g in known]
    if invalid:
        answer['invalid_ids'] = sorted({str(i) for i in invalid})
    return answer


def call_claude(prompt, model, timeout):
    exe = os.environ.get('AGENTIC_LLM_CLAUDE_BIN') or shutil.which('claude')
    if not exe:
        raise RuntimeError('claude CLI not found')
    with tempfile.TemporaryDirectory(prefix='repo-scan-llm-') as cwd:
        result = subprocess.run([exe, '-p', '--model', model, '--output-format', 'text', '--tools', '',
                                 '--no-session-persistence'], input=prompt, capture_output=True, text=True,
                                timeout=timeout, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f'claude exited {result.returncode}: {result.stderr.strip()[-300:]}')
    return result.stdout


def call_litellm(prompt, model, timeout):
    key = os.environ.get('AGENTIC_LLM_API_KEY')
    if not key:
        raise RuntimeError('AGENTIC_LLM_API_KEY is not set')
    base = os.environ.get('AGENTIC_LLM_BASE_URL', DEFAULT_BASE_URL).rstrip('/')
    url = base + ('/chat/completions' if base.endswith('/v1') else '/v1/chat/completions')
    body = json.dumps({'model': model, 'temperature': 0,
                       'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt}]})
    req = urllib.request.Request(url, data=body.encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors='replace')[:300]
        raise RuntimeError(f'HTTP {exc.code}: {redact(detail)}') from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RuntimeError(f'request failed: {exc}') from None
    try:
        return data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise RuntimeError('unexpected response shape') from None


PROVIDERS = {'claude': call_claude, 'litellm': call_litellm}


def assess(scan_dir, provider, model, select, out_dir, timeout=300, use_cache=True, log=print):
    scan_dir, out_dir = Path(scan_dir), Path(out_dir)
    repos = json.loads((scan_dir / 'repositories.json').read_text())['repositories']
    rels = json.loads((scan_dir / 'relationships.json').read_text())['edges']
    guides = json.loads((scan_dir / 'guide-applicability.json').read_text())
    guide_ids = guides['guide_ids']
    chosen = select(repos)
    cache_dir = out_dir / 'llm-cache'
    out_path = out_dir / 'llm-assessment.json'
    try:
        results = json.loads(out_path.read_text())
    except (OSError, ValueError):
        results = {'assessments': {}}
    results.update(provider=provider, model=model, prompt_version=PROMPT_VERSION)
    call = PROVIDERS[provider]
    for record in chosen:
        rid, head = record['id'], record['git'].get('head')
        slug = re.sub(r'[^A-Za-z0-9._-]+', '_', rid)
        cache = cache_dir / f'{slug}-{(head or "nohead")[:12]}-{provider}-{re.sub(r"[^A-Za-z0-9._-]+", "_", model)}-v{PROMPT_VERSION}.json'
        if use_cache and head and cache.exists():
            results['assessments'][rid] = json.loads(cache.read_text())
            log(f'cache  {rid}')
            continue
        prompt = build_prompt(record, guides['repositories'].get(rid, {}), rels, guide_ids)
        entry = {'repo': rid, 'head': head, 'provider': provider, 'model': model}
        try:
            raw = call(prompt, model, timeout)
            entry['assessment'] = validate(parse_answer(raw), guide_ids)
            entry['status'] = 'ok'
        except (RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            entry['status'] = 'error'
            entry['error'] = redact(str(exc))
        results['assessments'][rid] = entry
        if entry['status'] == 'ok' and head:
            write_json(cache, entry)
        log(f'{entry["status"]:<6} {rid}')
    write_json(out_path, results)
    return results
