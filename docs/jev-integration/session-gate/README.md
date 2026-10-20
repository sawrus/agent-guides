# JEV session gate (1.5.0, hardened in 1.6.0)

## Problem

A review of three real `service_x` sessions (Claude Code, Codex, OpenCode) for
the request «разработай калькулятор питон простой» found:

- **Too many calls.** The three sessions made 25 paid JEV calls. Every user
  message, including «да верно написал ты» and «как отработал JEV», opened a new
  task and sent a new workflow question.
- **Wrong task binding.** After such a follow-up, spawns were recorded under the
  follow-up with `workflow: null`. The review packets of the Claude and OpenCode
  runs described the follow-up, not the calculator task.
- **Wrong fallback model in Claude.** The install had Codex and Claude, so
  `model-defaults.json` held Codex ids. Claude found no alias role default, and
  low-confidence spawns (team-lead, developer, qa) inherited the coordinator's opus.
- **Threshold too high for models.** At 0.9, six of seven OpenCode model answers
  fell back, including `fast` at 0.87 and 0.88.
- **Empty fields.** `usage.cost_usd` and observation `requested_model` were
  `null` in every record. The budget ledger booked a fixed $0.02 guess per call.
- **No manual control.** JEV could be turned off only for the whole project.
- **Expensive blackbox.** Runs took up to 20 minutes per host.

## Requirements and acceptance criteria

| ID | Requirement | Acceptance |
| --- | --- | --- |
| SG-1 | The first root prompt of a session decides whether JEV is used. A selected workflow keeps JEV on; `native`, low confidence or an error turns it off for the session; `clarify` leaves the session undecided. | `test_native_first_prompt_turns_the_session_off_but_keeps_role_defaults`, `test_clarify_and_low_confidence_gate_the_session` |
| SG-2 | Later prompts make no workflow call and keep the task. A prompt that names a workflow starts a new task without a call. | `test_follow_up_prompts_continue_the_task_without_a_call` |
| SG-3 | In an off session, prompts, permissions and spawns make no JEV call. Spawns still get the role default. | `test_native_first_prompt_turns_the_session_off_but_keeps_role_defaults` |
| SG-4 | `/jev off`, `/jev on`, `/jev status` switch JEV per session with no JEV call; Claude Code and Codex block the prompt. `/jev on` restarts workflow selection. | `test_manual_switch_needs_no_call_and_on_restarts_workflow_selection`, `test_switch_prompt_is_blocked_before_the_model` |
| SG-5 | The default model threshold is 0.6; workflow and permission stay 0.9. | `Thresholds.test_threshold_range_and_default` |
| SG-6 | Below the model threshold, Claude spawns use the Claude profile role default, also in an install with Codex. | `test_combined_install_uses_the_claude_host_defaults`, `claude_only_defaults_use_profile_aliases_and_combined_install_keeps_codex` |
| SG-7 | Records keep `input_tokens` and `output_tokens`; `cost_usd`, `requested_model` and the budget ledger are removed. | `test_observation_has_no_requested_model_and_usage_has_no_price` |
| SG-8 | The blackbox sends at most three prompts per host within 8 minutes and fails when a follow-up sends a JEV request. | `test_verify_counts_calls_and_rejects_a_paid_follow_up` |

## Decisions

- **Codex encrypted assignments:** without prepared metadata, keep the role default without a call (`assignment_unavailable`). Since 1.6.0 use [open-assignment preselection](../epic/preselection.md) before transport encryption; profile preservation can leave application unconfirmed.
- **Session state lives in the existing context file**
  (`.agentic/jev/context-<hash>.json`): `jev` (`on`/`off`) and `off_reason`
  (`manual`, `native_request`, `low_confidence`, …). No new hook event is needed.
- **Codex switch spelling.** Codex has no project slash commands, so the hook also
  accepts the bare `jev off|on|status`. Only a prompt that consists of the switch
  alone matches.

## Operational notes

- Reinstall the project (`agentic install …` or the TUI) to get the new runtime,
  `hosts.claude` in `model-defaults.json` and the `jev.md` commands.
- Codex asks for a new `/hooks` trust review only when hook definitions change;
  this release changes the runtime files, not the hook entries.
- Remove `AGENTIC_JEV_BUDGET_FILE` from local scripts; the runtime ignores it now.
- To compare sessions, read `jev_calls` and `jev_input_tokens` in blackbox
  `results.json`, or count records with `result.usage` in `.agentic/jev/`.

## Explicit task boundary (1.6.0)

Use existing `jev on` or `/jev on`, then send the new task. The switch clears original_prompt, task_id, workflow and approved_decisions and rotates task_generation. The next prompt chooses its workflow again. Permission caches and prepared decisions from the old generation cannot be reused, even when prompt/tool IDs repeat. An explicit workflow restart also clears old approval history. Ordinary confirmations/follow-ups keep the task without a workflow call. Automatic goal-change recognition remains a separate capability.
