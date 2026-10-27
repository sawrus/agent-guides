"""Docs catalog: rules, skills, and workflow steps for the docs site; examples come from `Example request:` lines."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_docs_catalog as catalog

REPO = Path(__file__).resolve().parents[2]

WORKFLOW = """---
name: fix-bug
type: workflow
trigger: /fix-bug
description: Fix a reproduced defect.
inputs:
  - bug_report
outputs: [fix, regression_test]
selection:
  general: false
  use-when: "A user reports a defect with steps to reproduce."
  avoid-when: "A live incident."
uses-skills: []
related-rules:
  - testing.md
checks:
  - make test
---

# Fix a bug

Example request: `The login form accepts an empty password; fix it and add a test.`
**Example request:** Orders API returns 500 for an empty cart.

## Steps

### 1. Reproduce

- **Do:** run the failing case
  and capture the log.
- **Done when:** a test fails for the reported reason.

### 2. Fix

**Do**: change the smallest module.
**Done when**: the test passes.

### 3. Check

- **Do:** run `make test`.
- **Done when:** it exits 0.
"""

RULE = """---
description: Test layout and naming.
paths:
  - "tests/**"
---

# Testing

- Name tests `test_<behaviour>`.
"""

MANUAL_RULE = "---\ndescription: Git hygiene.\ntrigger: manual\n---\n\n# Git\n\n- Tag releases.\n"
SKILL = '---\nname: api-design\ndescription: "Procedure to design an endpoint. Use when you add a route."\n---\n\n# API\n\n1. Read.\n'


class DocsCatalog(unittest.TestCase):
    def build(self, files, require_examples=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for rel, text in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            with patch.object(catalog, "ROOT", root), patch.object(catalog, "AREAS_DIR", root / "areas"):
                return catalog.build_catalog(validate=True, require_examples=require_examples)

    def full(self, workflow=WORKFLOW):
        return {
            "areas/software/general/AGENTS.md": "# General\n\nShared baseline.\n\n- Rules: x\n",
            "areas/software/general/workflows/fix-bug.md": workflow,
            "areas/software/general/rules/testing.md": RULE,
            "areas/software/general/rules/git.md": MANUAL_RULE,
            "areas/software/general/skills/api-design/SKILL.md": SKILL,
            # A leftover prompt file is ignored.
            "areas/software/general/prompts/fix-bug.md": "---\nworkflow: fix-bug\n---\n# Prompt: /fix-bug\n",
        }

    def test_workflow_fields_and_steps(self):
        data, problems = self.build(self.full())
        self.assertEqual(problems, [])
        self.assertEqual(data["version"], "1.4.0")
        area = data["areas"][0]
        self.assertEqual((area["group"], area["spec"], area["summary"]), ("software", "general", "Shared baseline."))
        wf = area["workflows"][0]
        self.assertEqual(wf["examples"], [
            "The login form accepts an empty password; fix it and add a test.",
            "Orders API returns 500 for an empty cart.",
        ])
        self.assertEqual(wf["use_when"], "A user reports a defect with steps to reproduce.")
        self.assertEqual(wf["avoid_when"], "A live incident.")
        self.assertEqual((wf["inputs"], wf["outputs"]), (["bug_report"], ["fix", "regression_test"]))
        self.assertEqual(wf["checks"], ["make test"])
        self.assertEqual(wf["artifacts"], [])
        self.assertEqual(wf["rule_refs"], [{"name": "testing", "path": "areas/software/general/rules/testing.md"}])
        self.assertEqual([s["title"] for s in wf["steps"]], ["Reproduce", "Fix", "Check"])
        self.assertEqual(wf["steps"][0]["do"], "run the failing case and capture the log.")
        self.assertEqual(wf["steps"][1]["done_when"], "the test passes.")
        self.assertEqual(wf["body"], "")
        for gone in ("roles", "quality_gates", "workflow_diagram", "prompt_path"):
            self.assertNotIn(gone, wf)
        self.assertEqual(data["stats"], {"rules": 2, "skills": 1, "workflows": 1, "examples": 2, "problems": 0})

    def test_rules_and_skills(self):
        data, _ = self.build(self.full())
        rules = {r["name"]: r for r in data["areas"][0]["rules"]}
        self.assertEqual(rules["testing"]["paths"], ["tests/**"])
        self.assertEqual(rules["git"]["trigger"], "manual")
        self.assertTrue(rules["testing"]["body"].startswith("- Name tests"))
        skill = data["areas"][0]["skills"][0]
        self.assertEqual(skill["name"], "api-design")
        self.assertEqual(skill["description"], "Procedure to design an endpoint. Use when you add a route.")

    def test_validation_catches_bad_steps_rules_and_refs(self):
        files = self.full(WORKFLOW.split("### 2.")[0].replace("testing.md", "nope.md"))
        files["areas/software/general/rules/bare.md"] = "---\ndescription: \n---\n\n# Bare\n"
        data, problems = self.build(files)
        text = "\n".join(problems)
        self.assertIn("1 parsed steps, needs >= 3", text)
        self.assertIn("unknown rule or skill `nope`", text)
        self.assertIn("rule missing description", text)
        self.assertIn("neither paths nor trigger", text)
        # The raw body stays available when the steps cannot be parsed.
        self.assertIn("Reproduce", data["areas"][0]["workflows"][0]["body"])

    def test_missing_example_is_a_problem_only_when_required(self):
        text = WORKFLOW.replace("Example request:", "Example:")
        _, problems = self.build(self.full(text))
        _, strict = self.build(self.full(text), require_examples=True)
        self.assertEqual(problems, [])
        self.assertEqual(len(strict), 1)
        self.assertIn("no `Example request:` line", strict[0])


class RealCatalog(unittest.TestCase):
    """The pack itself builds a complete catalog, and the site renders no empty section for it."""

    @classmethod
    def setUpClass(cls):
        cls.data, cls.problems = catalog.build_catalog(validate=True)

    def test_no_problems_and_no_empty_required_fields(self):
        self.assertEqual(self.problems, [])
        for area in self.data["areas"]:
            for rule in area["rules"]:
                self.assertTrue(rule["description"] and rule["body"], rule["path"])
                self.assertTrue(rule["paths"] or rule["trigger"] == "manual", rule["path"])
            for skill in area["skills"]:
                self.assertTrue(skill["description"] and skill["body"], skill["path"])
            for wf in area["workflows"]:
                self.assertTrue(wf["description"] and wf["use_when"], wf["workflow_path"])
                self.assertGreaterEqual(len(wf["steps"]), 3, wf["workflow_path"])
                for step in wf["steps"]:
                    self.assertTrue(step["title"] and step["do"] and step["done_when"], wf["workflow_path"])
                for ref in wf["rule_refs"] + wf["skill_refs"]:
                    self.assertTrue(ref["path"], f"{wf['workflow_path']}: {ref['name']}")

    def test_matches_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")
        schema = json.loads((REPO / "docs/catalog.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(self.data, schema)

    def test_site_renders_every_page_without_empty_sections(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        script = r"""
const app = require(process.argv[1]);
const cat = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const docs = app.buildDocs(cat);
const byPath = new Map(docs.map((d) => [d.path, d.id]));
const bad = [];
for (const d of [...docs, null]) {
  const md = d ? app.renderDocMarkdown(d, byPath) : app.homeMarkdown(cat);
  const id = d ? d.id : 'home';
  if (/^- —$|: —$|_No examples_|\bundefined\b|\(null\)|\[object Object\]/m.test(md)) bad.push(`${id}: empty value`);
  const lines = md.split('\n');
  lines.forEach((line, i) => {
    if (!/^#{1,3} /.test(line)) return;
    const next = lines.slice(i + 1).find((l) => l.trim());
    if (!next || /^#{1,3} /.test(next) && next.split(' ')[0].length <= line.split(' ')[0].length || next === '---') {
      bad.push(`${id}: empty section ${line}`);
    }
  });
  if (d && d.kind === 'workflow' && !/^### 1\. /m.test(md)) bad.push(`${id}: no steps`);
  if (d && !md.includes(d.data.description)) bad.push(`${id}: no description`);
}
for (const d of docs.filter((x) => x.kind === 'workflow')) {
  for (const ref of [...d.data.rule_refs, ...d.data.skill_refs]) {
    if (!byPath.has(ref.path)) bad.push(`${d.id}: ref ${ref.name} has no page`);
  }
}
console.log(JSON.stringify({ docs: docs.length, bad }));
"""
        out = subprocess.run(
            [node, "-e", script, str(REPO / "docs/site/app.js")],
            input=json.dumps(self.data), capture_output=True, text=True, check=True,
        )
        result = json.loads(out.stdout)
        stats = self.data["stats"]
        self.assertEqual(result["docs"], stats["rules"] + stats["skills"] + stats["workflows"])
        self.assertEqual(result["bad"], [])


if __name__ == "__main__":
    unittest.main()
