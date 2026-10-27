---
description: Role layout, idempotency, inventory, and test requirements for Ansible playbooks and roles.
paths:
  - "**/playbooks/**"
  - "**/roles/**"
  - "**/inventory/**"
  - "**/group_vars/**"
  - "**/host_vars/**"
  - "ansible.cfg"
  - "**/requirements.yml"
---

# Ansible standards

- Keep each role in `roles/<name>/` with `tasks/main.yml`, `defaults/main.yml`, `handlers/main.yml`, and `meta/main.yml`.
- Put every overridable variable with a safe default in `defaults/main.yml`; put internal constants in `vars/main.yml`.
- Use fully qualified module names (`ansible.builtin.apt`, `ansible.builtin.template`).
- Write idempotent tasks: use `state:` modules instead of `command` or `shell`; add `creates:`, `removes:`, or `changed_when:` when `command` is unavoidable.
- Trigger service restarts through `notify:` handlers, not through unconditional restart tasks.
- Set `validate:` on `template` and `copy` tasks for config files that have a checker (`sshd -t -f %s`, `visudo -cf %s`).
- Name every task and play with `name:`.
- Keep one inventory directory per environment (`inventory/staging/`, `inventory/production/`); never mix hosts of two environments in one file.
- Use RFC 5737 addresses (`192.0.2.10`) or host names in examples; never commit real internal host addresses to a public repository.
- Pin collections and roles with exact versions in `requirements.yml`.
- Run `ansible-lint` and `ansible-playbook --syntax-check` in CI on every change.
- Test roles with `molecule test` and require a second converge run to report `changed=0`.
- Run every production playbook with `--check --diff` first and review the output before the real run.
