"""R&D fixtures for the hook questions, built with the runtime builders in questions.py (no drift).

Families:
- workflow_routing: 12 RU/EN requests against the software.backend + software.general catalog.
  The original failing request type is held out: no case names it.
- model_tier: 8 subagent assignments against Claude-style tiers.

`expected` is a list of acceptable labels; analyze.py counts a run as agreed when the choice is in it.
"""

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "extensions/codex/hooks/jev/questions.py"
CATALOG_DIRS = ("areas/software/backend/workflows", "areas/software/general/workflows")
INSTALLED_AREAS = ["software.backend", "software.general"]
GENERAL = "develop-feature"  # the general workflow since the content cleanup (was development-cycle-workflow)
EMPTY_REPOSITORY = {"is_git": True, "source_files": 0, "top_languages": [], "has_makefile": False,
                    "has_ci": False, "only_agent_guidance": True, "truncated": False}
SERVICE_REPOSITORY = {"is_git": True, "source_files": 184, "top_languages": ["python", "sql"], "has_makefile": True,
                      "has_ci": True, "only_agent_guidance": False, "truncated": False}
CLAUDE_CANDIDATES = [{"tier": "fast", "model": "haiku", "relative_cost": 1},
                     {"tier": "balanced", "model": "sonnet", "relative_cost": 2},
                     {"tier": "frontier", "model": "opus", "relative_cost": 3}]
ROLE_DEFAULTS = {"developer": "sonnet", "qa": "sonnet", "analyst": "sonnet", "team-lead": "opus"}
ROLE_DESCRIPTIONS = {
    "developer": "Implementation, bug fixes, tests and code delivery after scope and architecture are approved.",
    "qa": "Quality verification, test strategy, defect classification and go or no-go recommendations.",
    "analyst": "Requirements, scenarios, API and data contracts, testable acceptance criteria.",
    "team-lead": "Technical strategy, architecture decisions, code review and technical sign-off.",
}
WORKFLOW_CASES = (
    ("wf_ru_small_program", "Разработай конвертер валют.", EMPTY_REPOSITORY, [GENERAL]),
    ("wf_en_small_program", "Build a small command-line todo app.", EMPTY_REPOSITORY, [GENERAL]),
    ("wf_ru_script", "Напиши скрипт, который переименовывает фотографии по дате съёмки.", EMPTY_REPOSITORY, [GENERAL]),
    ("wf_ru_endpoint", "Добавь эндпоинт GET /orders/{id} с авторизацией и тестами.", SERVICE_REPOSITORY, [GENERAL]),
    ("wf_en_bugfix", "Fix the 500 error when posting an empty cart; the stack trace is attached.", SERVICE_REPOSITORY, ["debug-issue", GENERAL]),
    ("wf_en_migration", "Add a nullable archived_at column to the orders table with a safe migration.", SERVICE_REPOSITORY, ["add-migration"]),
    ("wf_en_refactor", "Split the payment module into smaller units without changing its behaviour.", SERVICE_REPOSITORY, ["refactor-module"]),
    ("wf_en_review", "Review pull request 42 and leave comments.", SERVICE_REPOSITORY, ["code-review-workflow"]),
    ("wf_en_setup", "Initialize this new repository with linting, CI and a README; no product features yet.", EMPTY_REPOSITORY, [GENERAL]),
    ("wf_ru_question", "Что делает модуль routing.py?", SERVICE_REPOSITORY, ["native"]),
    ("wf_en_explain", "Explain the difference between expand and contract migrations.", SERVICE_REPOSITORY, ["native"]),
    ("wf_ru_vague", "Сделай лучше.", SERVICE_REPOSITORY, ["clarify"]),
)
MODEL_CASES = (
    ("tier_typo", "developer", "Fix one spelling mistake in a README heading.", ["fast"]),
    ("tier_pagination", "developer", "Add pagination to the existing list endpoint following the repository pattern, with tests.", ["balanced"]),
    ("tier_architecture", "team-lead", "Design cross-tenant authorization and a zero-downtime migration for ambiguous legacy identity boundaries.", ["frontier"]),
    ("tier_run_checks", "qa", "Run make test on the current tree and report the exit code and the failing test names.", ["fast"]),
    ("tier_vague", "developer", "Do the thing we discussed.", ["clarify"]),
    ("tier_small_program", "developer", "Implement a currency converter CLI with three commands, input validation and unit tests in an empty repository.", ["fast", "balanced"]),
    ("tier_checklist", "analyst", "Copy the acceptance criteria already written in the ticket into a numbered checklist.", ["fast"]),
    ("tier_ru_sessions", "developer", "Перенеси хранение сессий из памяти процесса в Redis с переносом активных сессий без простоя.", ["frontier", "balanced"]),
)


def load_runtime(name):
    """A hook runtime module by path (no sys.path change), e.g. `questions` or the `api` client."""
    spec = importlib.util.spec_from_file_location("jev_" + name, RUNTIME.with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_questions():
    return load_runtime("questions")


def catalog(questions):
    paths = sorted(path for folder in CATALOG_DIRS for path in (ROOT / folder).glob("*.md"))
    return [w for w in (questions.parse_workflow(path, ROOT) for path in paths) if w]


def workflow_cases(questions):
    workflows = catalog(questions)
    manifest = {"settings": {"specializations": INSTALLED_AREAS}}
    cases = []
    with tempfile.TemporaryDirectory() as empty:
        for name, prompt, repository, expected in WORKFLOW_CASES:
            request = questions.workflow_request(prompt, workflows, Path(empty), manifest)
            # A fixed snapshot keeps the fixture reproducible; the builder computes it from disk at runtime.
            request["state"]["repository"] = dict(repository)
            cases.append({"id": name, "family": "workflow_routing", **request, "expected": expected})
    return cases


def model_cases(questions):
    workflow = {"id": GENERAL, "roles": ["product-owner", "team-lead", "developer", "qa"]}
    cases = []
    for name, role, assignment, expected in MODEL_CASES:
        default = ROLE_DEFAULTS[role]
        role_ctx = {"role": role, "role_description": ROLE_DESCRIPTIONS[role], "assignment": assignment,
                    "role_default": {"model": default, "tier": next(c["tier"] for c in CLAUDE_CANDIDATES if c["model"] == default)}}
        request = questions.model_request(role_ctx, CLAUDE_CANDIDATES, workflow, "Deliver the change requested in the ticket.")
        cases.append({"id": name, "family": "model_tier", **request, "expected": expected})
    return cases


def fixtures():
    questions = load_questions()
    return workflow_cases(questions) + model_cases(questions)
