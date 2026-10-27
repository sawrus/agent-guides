---
name: code-review-workflow
type: workflow
trigger: /code-review-workflow
description: Review a merge request or diff against its requirements and the review regulation, with evidence per finding.
inputs:
  - merge_request_or_diff
  - requirements
outputs:
  - review_findings
  - verdict
selection:
  general: false
  use-when: "The request asks to review an existing pull request, merge request or diff and give review comments."
  avoid-when: "The request asks to write or change code."
uses-skills: []
related-rules:
  - code-style-guide.md
  - docs-layout.md
  - git-workflow-guide.md
checks: []
---

# Review a change

Example request: `/code-review-workflow MR !87 "Add rate limiting to the public API"`

## Steps

### 1. Collect the change and its requirements

- **Do:** get the diff against the merge base (`git diff origin/main...HEAD`, `glab mr diff`, `gh pr diff`).
  Collect requirements from the linked ticket, the feature page under `docs/`, and the description.
- **Done when:** you have the full diff and a numbered list of requirements, or a note that none exist.

### 2. Check gates and scope

- **Do:** read the CI result of the last commit. Run the project checks locally when CI is not available.
  Compare changed paths with the requirements and mark unrelated edits.
- **Done when:** gate status is known for build, tests, lint, and security scan, with a link or command output.

### 3. Review the diff

- **Do:** check each requirement (`met`, `partial`, `missing`). Look for wrong behaviour, missing tests for
  changed behaviour, broken contracts (API, schema, config, CLI), unsafe migrations, secrets, unbounded remote
  calls, and changed code without a matching docs page. Do not report what a linter or formatter enforces.
- **Done when:** every finding has a severity (`blocker`, `major`, `minor`, `info`), a file and line, and a fix.

### 4. Give the verdict

- **Do:** answer in the review thread or the chat, not in a file: a status table of requirements, findings by
  severity, and the verdict (`changes_requested`, `approve_with_comments`, `approve`). Do not merge.
- **Done when:** the verdict follows the findings: any `missing` requirement or open `blocker`/`major` gives
  `changes_requested`.
