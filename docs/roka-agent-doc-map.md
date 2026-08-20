# ROKA-Agent Documentation Map

ROKA-Agent extends Hermes instead of replacing it. This map identifies the
authoritative documents for the v0.1 source release.

## Product and Operation

| Document | Authority |
| --- | --- |
| `README.md` | User-facing purpose, runtime flow, setup, commands, defaults, guarantees, and limits. |
| `AGENTS.md` | Contributor rules and the ROKA runtime invariants future agents must preserve. |
| `ROKA-CONTENT-LICENSE.md` | Scope and terms for original ROKA non-code content. |
| `LICENSE` | MIT terms for source code and inherited Hermes-compatible changes. |

## Architecture and Review

| Document | Authority |
| --- | --- |
| `docs/roka-function-impact-map.md` | Implemented function-level call graph and downstream impact. |
| `docs/roka-learning-control-map.md` | Durable memory/skill write policy and background-review behavior. |
| `docs/roka-license-note.md` | Plain-language explanation of the dual-scope license layout. |
| `mydocs/plans/roka-v0.1-release.md` | Release mission, constraints, implementation plan, and quality gates. |
| `mydocs/working/roka-v0.1-final.md` | Test evidence, findings resolved, residual limits, and release verdict. |

## Source Ownership

ROKA-specific runtime ownership is intentionally narrow:

- `agent/roka_control.py`: brief schema, parsing, identity, and context binding.
- `agent/moa_loop.py`: orchestration order and executor control context.
- `hermes_cli/moa_config.py`: ROKA role validation.
- `hermes_cli/config_defaults.py`: default model routes.

Existing Hermes functions remain owners of their original concerns:

- `agent/tool_executor.py`: universal tool dispatch boundary.
- `agent/background_review.py`: post-turn review lifecycle.
- `tools/write_approval.py`: pending policy and persistence.
- `tools/memory_tool.py`: built-in memory mutation/replay.
- `tools/skill_manager_tool.py`: skill mutation/replay and ownership guards.
- `agent/agent_runtime_helpers.py`: live model switching.

This ownership split is the practical meaning of the project's first rule:
reuse a working Hermes surface before creating a ROKA subsystem.

## Update Rules

When runtime behavior changes:

1. Update the function impact map in the same commit.
2. Update README only for user-visible behavior or limits.
3. Record test commands and results in the current release report.
4. Keep plans historical; do not rewrite an approved plan to disguise scope
   drift.
5. Do not copy large upstream Hermes documentation into ROKA files. Link to the
   upstream source and document only fork-specific behavior.

## Upstream References

For unchanged Hermes installation, gateways, providers, plugins, tools, and
session behavior, use:

- <https://github.com/NousResearch/hermes-agent>
- <https://hermes-agent.nousresearch.com/docs/>

ROKA documents override upstream documentation only for the fork-specific
control mode described here.
