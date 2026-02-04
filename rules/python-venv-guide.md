---
trigger: glob
glob: python-venv-guide
globs: *.py
description: enforce Python 3, virtual environments, and Poetry for dependency management
---

# Python Venv & Poetry Rule

**Rules:**

- Use Python 3 in a project-specific venv (`.venv_projectname`).
- Activate venv before running code/tests.
- Initialize project structure with `src/` directory and place all code files inside it.
- Install and manage all dependencies via Poetry (`poetry add/install/update`).
- Commit `pyproject.toml` and `poetry.lock`.
- Ignore `.venv_projectname/` in Git.

**Violations:**

- Running code outside venv.
- Installing packages globally.
- Not using Poetry for dependency management.
