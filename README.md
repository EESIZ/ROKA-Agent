# ROKA-Agent

ROKA-Agent is an experimental fork of Hermes Agent for intent-preserving agent
control.

The project starts from one working rule:

> Put observation near the center, put judgment near the edge, and copy intent
> into both sides.

For LLM agents, that means a user should not have to micromanage every step, and
the agent should not silently rewrite its own behavior after every task. ROKA is
the control layer between those failures. It makes the work brief explicit,
keeps agent sessions separated, records where learning came from, and routes
durable memory or skill changes through reviewable gates.

ROKA does not try to replace Hermes. The first design rule is: do not rebuild
what Hermes already has. Reuse Hermes sessions, tools, memory, skills,
delegation, background review, approval gates, and ledgers. Add the smallest
policy or metadata layer needed to make them more controllable.

## Current Status

This repository is at the first ROKA milestone.

Implemented:

- ROKA project documentation and Hermes function impact maps.
- Audit-only provenance metadata for staged memory and skill writes.
- Session and role metadata fields for learning-related writes.
- A regression test proving pending write payload replay remains unchanged.

Not implemented yet:

- Full execution-brief renderer.
- Multi-agent reviewer orchestration.
- Risk-classified background review prompts.
- ROKA-specific installer or release package.

This is intentional. ROKA starts with traceability before changing behavior.

## Why ROKA Exists

Hermes already has a powerful learning loop. It can remember useful facts,
create and update skills, delegate work, run background review, and carry state
across sessions.

That power creates a control problem:

- The same user request can produce different results after silent skill or
  memory updates.
- Background learning can improve future work, but it can also mutate the
  agent's behavior without a clear audit path.
- Parallel agents can be useful only if their histories, roles, assumptions,
  and outputs remain separated.
- A user cannot manually write a perfect structured brief for every task.

ROKA treats those as command and control problems, not prompt-style problems.

The goal is to make agent work reproducible enough to inspect:

- What was the task?
- Why was it done?
- What constraints mattered?
- Which model and agent role made the judgment?
- Which session produced the proposed memory or skill change?
- What evidence justified the change?
- Was the change approved, staged, or rejected?

## Core Model

ROKA uses Hermes terminology where possible.

| ROKA concept | Hermes surface |
| --- | --- |
| Execution brief | Turn-scoped task, context, constraints, and metadata |
| Agent session | Existing Hermes session or subagent session |
| Role separation | Executor, reviewer, policy reviewer, context reviewer |
| Learning proposal | Memory or skill write routed through existing gates |
| Provenance | Metadata attached to pending records and memory mirrors |
| Review loop | Background review, approval commands, and skill ledger |

The execution brief is the center of the system. It should eventually carry:

- `task`: what to do
- `purpose`: why it matters
- `constraints`: what must not be violated
- `assumptions`: what the agent believes to be true
- `deviation_rule`: when the agent may depart from the brief
- `autonomy_policy`: what to do without immediate user contact
- `review_policy`: how the result and learning should be checked

The first runtime patch does not add the full brief yet. It prepares the audit
path that the brief will use.

## What Changed In Milestone 1

### Pending Write Metadata

`tools.write_approval.stage_write(...)` now accepts optional audit metadata.

The metadata is stored on pending records, but it is not part of the replay
payload. That matters because old and new pending writes must approve in the
same way.

### Memory Write Provenance

`agent.background_review.build_memory_write_metadata(...)` now records optional
ROKA fields:

- `brief_id`
- `agent_session_id`
- `agent_role`
- `model_provider`
- `model`
- `risk_class`
- `evidence_refs`

These fields make learning proposals inspectable without changing the memory
tool's core behavior.

### Skill Write Provenance

`tools.skill_manager_tool.skill_manage(...)` now threads task/session metadata
into staged skill writes through the existing skill write gate.

ROKA does not create a new skill mutation path. It reuses Hermes' existing gate.

## Repository Guide

ROKA-specific files:

- [docs/roka-agent-doc-map.md](docs/roka-agent-doc-map.md)
- [docs/roka-function-impact-map.md](docs/roka-function-impact-map.md)
- [docs/roka-learning-control-map.md](docs/roka-learning-control-map.md)
- [docs/roka-license-note.md](docs/roka-license-note.md)

First milestone code paths:

- [tools/write_approval.py](tools/write_approval.py)
- [agent/background_review.py](agent/background_review.py)
- [tools/skill_manager_tool.py](tools/skill_manager_tool.py)
- [tests/tools/test_write_approval.py](tests/tools/test_write_approval.py)

Upstream Hermes surfaces ROKA should prefer before adding new systems:

- `agent/turn_context.py`
- `agent/turn_finalizer.py`
- `agent/background_review.py`
- `agent/subagent_lifecycle.py`
- `tools/delegate_tool.py`
- `tools/memory_tool.py`
- `tools/write_approval.py`
- `tools/skill_manager_tool.py`
- `tools/skill_ledger.py`

## Development

Clone the repository:

```bash
git clone git@github.com:EESIZ/ROKA-Agent.git
cd ROKA-Agent
```

Run the focused milestone test:

```bash
uv run --with pytest python -m pytest tests/tools/test_write_approval.py -q
```

Run a syntax check for the first milestone files:

```bash
python -B -m py_compile \
  tools/write_approval.py \
  agent/background_review.py \
  tools/skill_manager_tool.py \
  tests/tools/test_write_approval.py
```

For general Hermes installation, provider setup, CLI usage, gateway setup, and
upstream feature documentation, use the upstream Hermes docs:

- https://hermes-agent.nousresearch.com/docs/
- https://github.com/NousResearch/hermes-agent

ROKA does not yet ship a separate installer.

## Design Rules

### 1. Do Not Rebuild Hermes

If Hermes already has a usable surface, use it first.

Preferred order:

1. configuration and policy
2. documentation and operating profile
3. existing hook or review flow
4. small adapter around existing Hermes structures
5. new core runtime code only as a last resort

### 2. Metadata Before Behavior

Before changing how an agent learns, record enough metadata to explain why a
learning proposal exists.

The current metadata is audit-only. It must not be required to replay a pending
write.

### 3. Separate Sessions

Parallel agents may share the same brief, but they must not share one mutable
conversation history.

Required identifiers:

- shared `brief_id`
- unique `agent_session_id`
- original `parent_session_id`
- explicit `agent_role`
- recorded `model_provider` and `model`

### 4. Learning Is A Proposal

Memory and skill updates should be classified by risk before becoming durable.

Low-risk learning may eventually auto-commit when normal Hermes policy allows
it. Behavior-changing skill edits should be staged for review.

### 5. Shorter Commands Are The Health Signal

As ROKA matures, the user should need less manual briefing, not more. If every
task requires a long hand-written control packet, the system has failed to
internalize intent.

## Roadmap

### Phase 1: Traceability

- Keep the function maps current.
- Add metadata to pending memory and skill writes.
- Prove old pending replay behavior remains compatible.

Status: implemented.

### Phase 2: Execution Briefs

- Define a structured execution brief object.
- Render the brief into existing Hermes turn context.
- Preserve prompt-cache behavior.
- Store `brief_id` without forcing a new session model.

### Phase 3: Learning Policy

- Add risk classification to background review prompts.
- Normalize "nothing to save" as a valid review result.
- Prefer staged skill changes for behavior-affecting updates.
- Improve pending summaries so users can approve or reject quickly.

### Phase 4: Multi-Agent Review

- Use existing Hermes delegation and subagent lifecycle surfaces.
- Run executor and reviewer agents in separate sessions.
- Merge only structured findings, evidence, and approved learning proposals.
- Record model/provider/role for each agent.

### Phase 5: ROKA Operating Profile

- Provide a recommended config profile.
- Document when to enable memory and skill write approval.
- Add examples for deterministic task execution and review.

## License And Attribution

ROKA-Agent is a fork of Hermes Agent.

Inherited Hermes Agent source code remains under the upstream MIT license. See
[LICENSE](LICENSE) and the upstream project:

- https://github.com/NousResearch/hermes-agent

ROKA-specific methodology documents, diagrams, project language, and brand
materials are tracked separately in
[docs/roka-license-note.md](docs/roka-license-note.md) until the project owner
chooses a formal content license.

## Project Principle

The agent should not become obedient by being watched harder.

It should become reliable because the user's intent has been copied into the
places where judgment happens.
