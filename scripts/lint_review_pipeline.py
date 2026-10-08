#!/usr/bin/env python3
"""Validate post-task review contracts without invoking agents or MCP providers."""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = {
    'software/general/development-cycle-workflow': ['product-owner', 'pm', 'team-lead', 'developer', 'qa'],
    'software/backend/develop-feature': ['product-owner', 'pm', 'team-lead', 'developer', 'qa', 'designer'],
    'software/backend/develop-epic': ['product-owner', 'pm', 'team-lead', 'developer', 'qa'],
    'software/full-stack/develop-feature-fullstack': ['team-lead', 'developer', 'qa'],
    'software/full-stack/feature-implementation-flow': ['pm', 'team-lead', 'designer', 'developer', 'qa'],
    'software/full-stack/backend-project-full-cycle': ['pm', 'team-lead', 'developer', 'qa'],
}
AGENTS = ('instruction_reviewer', 'memory_curator')
ENVIRONMENTS = ('claude', 'codex', 'opencode', 'gemini')


def section(text: str, heading: str) -> str:
    match = re.search(rf'^## {re.escape(heading)}\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    return match.group(1) if match else ''


def workflow_issues(text: str, expected_roles: list[str]) -> list[str]:
    issues = []
    front = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    metadata = front.group(1) if front else ''
    roles = re.search(r'^roles:\n((?:  - .+\n)+)', metadata, re.M)
    actual = re.findall(r'^  - (.+)$', roles.group(1), re.M) if roles else []
    if actual != expected_roles:
        issues.append('SDLC role matrix changed')
    initiator = re.search(r'^  initiator: (.+)$', metadata, re.M)
    owner = initiator.group(1) if initiator else ''
    hook = section(text, 'Post-task review')
    if text.count('## Post-task review\n') != 1:
        issues.append('expected exactly one second-level Post-task review hook')
    if owner not in actual or f'`@{owner}` (`execution.initiator`)' not in hook:
        issues.append('hook coordinator must be execution.initiator in roles')
    for token in ('REVIEW_PIPELINE.md', *AGENTS, 'top-level task once',
                  'nested workflows/increments', 'fix/retest loops',
                  'failed/deferred delivery', 'do not block successful delivery',
                  'retry automatically', 'separate requested task', 'summary.md'):
        if token not in hook:
            issues.append(f'hook missing contract: {token}')
    for heading in re.findall(r'^### (.+)$', text, re.M):
        if any(agent in heading for agent in AGENTS) or 'Post-task review' in heading:
            issues.append('specialists must not be SDLC steps')
    return issues


def profile_body(path: Path) -> str:
    text = path.read_text()
    if path.suffix == '.toml':
        data = tomllib.loads(text)
        if data.get('sandbox_mode') != 'read-only':
            raise ValueError('Codex specialist must use read-only sandbox')
        return data['developer_instructions'].strip()
    return text.split('---', 2)[2].strip()


def validate(root: Path = ROOT) -> list[str]:
    issues = []
    for key, roles in WORKFLOWS.items():
        area, name = key.rsplit('/', 1)
        path = root / 'areas' / area / 'workflows' / f'{name}.md'
        issues.extend(f'{path.relative_to(root)}: {issue}' for issue in workflow_issues(path.read_text(), roles))
    for agent in AGENTS:
        reference = None
        for environment in ENVIRONMENTS:
            suffix = 'toml' if environment == 'codex' else 'md'
            path = root / 'extensions' / environment / 'agents' / f'{agent}.{suffix}'
            try:
                body = profile_body(path)
            except (ValueError, KeyError, IndexError) as error:
                issues.append(f'{path.relative_to(root)}: {error}')
                continue
            if reference is None:
                reference = body
            elif body != reference:
                issues.append(f'{path.relative_to(root)}: specialist behavior differs across environments')
            for token in ('read-only', 'at most five', '500 words', 'not measured', 'separate requested', 'orchestrator'):
                if token not in body:
                    issues.append(f'{path.relative_to(root)}: missing boundary: {token}')
    curator = profile_body(root / 'extensions/claude/agents/memory_curator.md')
    for token in ('canonical home', 'at most two', '`limit: 3`', 'Do not scan all docs', 'memory-write or delete', 'unavailable'):
        if token not in curator:
            issues.append(f'memory_curator: missing docs/memory boundary: {token}')
    protocol = (root / 'REVIEW_PIPELINE.md').read_text()
    for token in ('once per completed top-level task', 'failed/deferred delivery',
                  'Do not retry automatically', 'not measured', 'unavailable',
                  'failed', 'summary.md', 'separate', 'current task context'):
        if token not in protocol:
            issues.append(f'REVIEW_PIPELINE.md: missing lifecycle contract: {token}')
    for path in (root / 'docs/review-pipeline/examples').glob('*.md'):
        if len(path.read_text().split()) > 500:
            issues.append(f'{path.relative_to(root)}: example exceeds 500 words')
    return issues


def main() -> int:
    issues = validate()
    if issues:
        print('\n'.join(issues))
        return 1
    print('Post-task review contracts pass across six workflows and four environments.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
