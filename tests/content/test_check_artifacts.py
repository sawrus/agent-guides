"""scripts/check_artifacts.py: each check id on a small fixture pack, the baseline ratchet, and --project mode."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import check_artifacts as ca

ROOT = Path(__file__).resolve().parents[2]

CORE = """# AGENTS

## Definition of done

- After the last edit, run the project checks and show the command and its result.

## Git

- Branch: `<type>/<task-id>-<slug>`, types `feat`, `fix`.
- Commits: `<type>(<scope>): <subject>`; the body says why and names the ticket.
"""

RULE = """---
description: Resource limits for container manifests.
paths:
  - "k8s/**/*.yaml"
---

# Container limits

- Set `resources.limits.memory` for every container.
- Pin every image by `@sha256` digest.
- Add a `readinessProbe` to every container.
"""

OTHER_RULE = """---
description: Naming of database migration files.
trigger: manual
---

# Migration names

- Name each migration file `V<number>__<slug>.sql`.
- Never edit an applied migration file.
"""

SKILL = """---
name: rollout-check
description: Check a stuck rollout. Use when a deployment does not become ready.
---

# Rollout check

1. Run `kubectl rollout status deploy/<name>`.
2. Run `kubectl describe pod <pod>` and read the events.
3. Report the failing condition.
"""

WORKFLOW = """---
name: fix-bug
type: workflow
trigger: /fix-bug
description: Fix a reported bug with a regression test.
selection:
  general: false
  use-when: "The request reports a defect in existing behaviour."
uses-skills:
  - rollout-check
related-rules:
  - limits.md
---

## Steps

### 1. Reproduce

- **Do:** run the failing test.
- **Done when:** the failure reproduces.

### 2. Fix

- **Do:** change the code.
- **Done when:** the test passes.

### 3. Verify

- **Do:** run `make test`.
- **Done when:** `make test` exits 0.
"""

LONG_TEXT = ' '.join(f'word{i} alpha beta gamma delta' for i in range(30))

BASE = {
    'AGENTS.md': CORE,
    'areas/a/s1/rules/limits.md': RULE,
    'areas/a/s1/skills/rollout-check/SKILL.md': SKILL,
    'areas/a/s1/workflows/fix-bug.md': WORKFLOW,
    'areas/a/s2/rules/migrations.md': OTHER_RULE,
}


def build(root: Path, changes=None) -> Path:
    files = dict(BASE)
    files.update(changes or {})
    for rel, text in files.items():
        if text is None:
            continue
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    return root


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = ca.main([*map(str, args)])
    return code, out.getvalue()


def ids(root: Path, *extra) -> set[str]:
    code, out = run('--root', root, '--no-budget', '--no-baseline', '--json', *extra)
    return {f['id'] for f in json.loads(out)['findings']}


class CheckIdsTest(unittest.TestCase):
    def assert_only(self, check_id, changes, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            found = ids(build(Path(tmp), changes), *extra)
        self.assertEqual(found, {check_id} if check_id else set())

    def test_clean_pack_has_no_findings(self):
        self.assert_only(None, {})

    def test_c1_long_description(self):
        self.assert_only('ART-C1', {'areas/a/s1/rules/limits.md': RULE.replace(
            'Resource limits for container manifests.', 'Resource limits ' + 'x' * 200 + '.')})

    def test_c2_core_convention(self):
        self.assert_only('ART-C2', {'areas/a/s1/rules/limits.md': RULE + '- Use branch `<type>/<task-id>-<slug>`.\n'})

    def test_c3_near_duplicate(self):
        body = '\n- Set `a` to 1. ' + LONG_TEXT + '\n'
        self.assert_only('ART-C3', {'areas/a/s1/rules/limits.md': RULE + body,
                                    'areas/a/s2/rules/migrations.md': OTHER_RULE + body})

    def test_c4_missing_reference(self):
        self.assert_only('ART-C4', {'areas/a/s1/workflows/fix-bug.md': WORKFLOW.replace('limits.md', 'missing.md')})

    def test_c4_link_leaves_selection(self):
        self.assert_only('ART-C4', {'areas/a/s1/rules/limits.md': RULE + '- Read [names](../../s2/rules/migrations.md).\n'})

    def test_c5_name_collision(self):
        self.assert_only('ART-C5', {'areas/a/s2/rules/limits.md': OTHER_RULE})

    def test_c6_private_address(self):
        self.assert_only('ART-C6', {'areas/a/s1/rules/limits.md': RULE + '- Set `host` to `10.1.2.3`.\n'})

    def test_c6_external_terms_are_not_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build(Path(tmp), {'areas/a/s1/rules/limits.md': RULE + '- Set `host` to `acme-corp.internal`.\n'})
            terms = Path(tmp) / 'terms.txt'
            terms.write_text('# company terms\nacme-corp\n', encoding='utf-8')
            self.assertEqual(ids(root, '--deny-terms-file', terms), {'ART-C6'})
            _, out = run('--root', root, '--no-budget', '--no-baseline', '--deny-terms-file', terms)
            self.assertIn('external deny term #2', out)
            self.assertNotIn('acme-corp', out)
            with mock.patch.dict('os.environ', {ca.DENY_ENV: str(terms)}):
                self.assertEqual(ids(root), {'ART-C6'})
            with mock.patch.dict('os.environ', {ca.DENY_ENV: ''}):
                self.assertEqual(ids(root), set())

    def test_c7_report_file(self):
        self.assert_only('ART-C7', {'areas/a/s1/rules/limits.md': RULE + '- Write `docs/test_report.md` after each run.\n'})

    def test_c7_role_handle(self):
        self.assert_only('ART-C7', {'areas/a/s1/workflows/fix-bug.md': WORKFLOW.replace(
            'change the code.', 'ask `@qa` to change the code.')})

    def test_r1_unscoped_rule(self):
        self.assert_only('ART-R1', {'areas/a/s1/rules/limits.md': RULE.replace('paths:\n  - "k8s/**/*.yaml"\n', '')})

    def test_r1_legacy_glob_field(self):
        self.assert_only('ART-R1', {'areas/a/s1/rules/limits.md': RULE.replace('paths:', 'glob: limits\npaths:')})

    def test_r2_textbook_items(self):
        prose = '- Kubernetes is a container platform.\n' * 3
        self.assert_only('ART-R2', {'areas/a/s1/rules/limits.md': RULE + prose})

    def test_r3_long_rule(self):
        self.assert_only('ART-R3', {'areas/a/s1/rules/limits.md': RULE + '- Set `x` to 1.\n' * 80})

    def test_r4_long_code_block(self):
        block = '```yaml\n' + 'key: value\n' * 16 + '```\n'
        self.assert_only('ART-R4', {'areas/a/s1/rules/limits.md': RULE + block})

    def test_s1_name_mismatch(self):
        self.assert_only('ART-S1', {'areas/a/s1/skills/rollout-check/SKILL.md': SKILL.replace(
            'name: rollout-check', 'name: other-name')})

    def test_s3_long_skill(self):
        self.assert_only('ART-S3', {'areas/a/s1/skills/rollout-check/SKILL.md': SKILL + 'More context.\n' * 250})

    def test_s4_code_heavy_skill(self):
        block = '```bash\n' + 'echo step\n' * 12 + '```\n'
        self.assert_only('ART-S4', {'areas/a/s1/skills/rollout-check/SKILL.md': SKILL + block})

    def test_s5_scaffolding(self):
        self.assert_only('ART-S5', {'areas/a/s1/skills/rollout-check/SKILL.md': SKILL + '4. Run `npx create-next-app web`.\n'})

    def test_s6_orphan(self):
        self.assert_only('ART-S6', {
            'areas/a/s1/skills/rollout-check/SKILL.md': SKILL.replace(' Use when a deployment does not become ready.', ''),
            'areas/a/s1/workflows/fix-bug.md': WORKFLOW.replace('uses-skills:\n  - rollout-check', 'uses-skills: []')})

    def test_w1_roles(self):
        self.assert_only('ART-W1', {'areas/a/s1/workflows/fix-bug.md': WORKFLOW.replace(
            'related-rules:', 'roles:\n  - qa\nrelated-rules:')})

    def test_w2_too_few_steps(self):
        self.assert_only('ART-W2', {'areas/a/s1/workflows/fix-bug.md': WORKFLOW.split('### 3.')[0]})

    def test_w4_long_workflow(self):
        self.assert_only('ART-W4', {'areas/a/s1/workflows/fix-bug.md': WORKFLOW + '\nMore context.\n' * 120})

    def test_w6_production_without_asking(self):
        self.assert_only('ART-W6', {'areas/a/s1/workflows/fix-bug.md': WORKFLOW.replace(
            'run `make test`.', 'run `make test` and deploy to production.')})
        self.assert_only(None, {'areas/a/s1/workflows/fix-bug.md': WORKFLOW.replace(
            'run `make test`.', 'run `make test`; ask the user first, then deploy to production.')})

    def test_b1_budget_over_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build(Path(tmp))
            binary = Path(tmp) / 'agentic'
            binary.write_text('', encoding='utf-8')
            fake = {'claude': {'total': 4100}, 'codex': {'total': 900}}
            with mock.patch.object(ca.context_budget, 'measure_selection', return_value=fake) as measure:
                findings, notes = ca.check_budget(root, ca.load_config(ca.DEFAULT_CONFIG), binary)
            self.assertEqual(notes, [])
            self.assertEqual({f.id for f in findings}, {'ART-B1'})
            selections = [call.args[2] for call in measure.call_args_list]
            self.assertIn('a.s1', selections)
            self.assertIn('a.s2', selections)
            self.assertIn('claude 4100', findings[0].message)
            missing, notes = ca.check_budget(root, ca.load_config(ca.DEFAULT_CONFIG), Path(tmp) / 'none')
            self.assertEqual(missing, [])
            self.assertIn('ART-B1 skipped', notes[0])


class BaselineTest(unittest.TestCase):
    def test_ratchet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build(Path(tmp), {'areas/a/s1/rules/limits.md': RULE + '- Set `host` to `10.1.2.3`.\n'})
            baseline = Path(tmp) / 'baseline.json'
            common = ('--root', root, '--no-budget', '--baseline', baseline)
            self.assertEqual(run(*common)[0], 1)
            self.assertEqual(run(*common, '--write-baseline')[0], 0)
            self.assertEqual(json.loads(baseline.read_text())['findings'], ['ART-C6 areas/a/s1/rules/limits.md'])
            self.assertEqual(run(*common)[0], 0)
            # A new finding in another file fails even with a baseline.
            (root / 'areas/a/s2/rules/migrations.md').write_text(OTHER_RULE + '- Write `x_summary.md`.\n')
            code, out = run(*common)
            self.assertEqual(code, 1)
            self.assertIn('ART-C7', out)
            # Fixing the baselined finding leaves a stale entry: a warning, or a failure with --strict-baseline.
            (root / 'areas/a/s2/rules/migrations.md').write_text(OTHER_RULE)
            (root / 'areas/a/s1/rules/limits.md').write_text(RULE)
            code, out = run(*common)
            self.assertEqual(code, 0)
            self.assertIn('stale baseline: ART-C6 areas/a/s1/rules/limits.md', out)
            self.assertEqual(run(*common, '--strict-baseline')[0], 1)

    def test_repository_has_no_new_findings(self):
        code, out = run('--no-budget')
        self.assertEqual(code, 0, out[-2000:])


COMPANY = """---
description: Company limits for container manifests.
paths:
  - "deploy/**/*.yaml"
{replaces}---

# Company container limits

{items}
"""


class ProjectModeTest(unittest.TestCase):
    def project(self, tmp: Path, company: str, keep_pack=True) -> Path:
        kb = build(tmp / 'kb')
        project = tmp / 'project'
        (project / '.agent/company').mkdir(parents=True)
        (project / '.agent/rules').mkdir(parents=True)
        if keep_pack:
            (project / '.agent/rules/limits.md').write_text(RULE)
        (project / '.agent/company/limits.md').write_text(company)
        return kb, project

    def report(self, kb, project):
        code, out = run('--root', kb, '--project', project, '--json')
        return code, json.loads(out)

    def test_k1_same_topic_without_replaces(self):
        items = '- Set `resources.limits.memory` for every container.\n- Pin every image by `@sha256` digest.\n'
        with tempfile.TemporaryDirectory() as tmp:
            kb, project = self.project(Path(tmp), COMPANY.format(replaces='', items=items))
            code, data = self.report(kb, project)
        self.assertEqual(code, 1)
        self.assertEqual({f['id'] for f in data['findings']}, {'ART-K1'})
        self.assertEqual(data['replace_suggestions'][0]['replaces'], ['a/s1/limits'])

    def test_k1_replaced_rule_still_installed_then_excluded(self):
        items = '- Set `resources.limits.memory` for every container.\n- Pin every image by `@sha256` digest.\n'
        text = COMPANY.format(replaces='replaces: [a/s1/limits]\n', items=items)
        with tempfile.TemporaryDirectory() as tmp:
            kb, project = self.project(Path(tmp), text)
            _, data = self.report(kb, project)
            self.assertEqual([f['id'] for f in data['findings']], ['ART-K1'])
            self.assertIn('still installed', data['findings'][0]['message'])
            (project / '.agent/rules/limits.md').unlink()
            code, data = self.report(kb, project)
        self.assertEqual((code, data['findings']), (0, []))

    def test_k2_restated_statement(self):
        items = ('- Pin every image by `@sha256` digest.\n- Send deploy events to `#ops-deploys`.\n'
                 '- Tag each release with `release/<date>`.\n- Store Helm values in `deploy/values/`.\n')
        with tempfile.TemporaryDirectory() as tmp:
            kb, project = self.project(Path(tmp), COMPANY.format(replaces='', items=items))
            _, data = self.report(kb, project)
        self.assertEqual({f['id'] for f in data['findings']}, {'ART-K2'})


if __name__ == '__main__':
    unittest.main()
