# ROKA Learning Control Map

This document maps Hermes' existing automatic learning path before ROKA-Agent
changes any runtime behavior. The goal is to keep useful automatic learning,
while preventing silent changes that make repeated work produce different
results.

## Design Principle

Do not build a new learning system first.

ROKA should reuse Hermes' existing surfaces:

- `agent/background_review.py`
- `tools/memory_tool.py`
- `agent/memory_manager.py`
- `tools/skill_manager_tool.py`
- `tools/write_approval.py`
- `tools/skill_ledger.py`
- `tools/delegate_tool.py`
- `agent/subagent_lifecycle.py`

Only add a small adapter or policy layer where the existing surfaces cannot
carry the required execution-brief metadata.

## Current Hermes Flow

Hermes has three relevant learning paths.

1. Built-in memory files
   - Store: `MEMORY.md` and `USER.md`.
   - Tool: `memory`.
   - Mutating actions: `add`, `replace`, `remove`, plus batch operations.
   - Default gate: `memory.write_approval` is off, so writes commit directly.

2. External memory providers
   - Manager: `agent/memory_manager.py`.
   - Start-of-turn path: `prefetch_all(query, session_id=...)`.
   - End-of-turn path: `sync_all(user_content, assistant_content, session_id=...)`.
   - Built-in memory mirror: `notify_memory_tool_write(...)` forwards committed
     memory-tool writes to providers with provenance metadata.

3. Skill library
   - Tool: `skill_manage`.
   - Mutating actions: `create`, `edit`, `patch`, `delete`, `write_file`,
     `remove_file`.
   - Default gate: `skills.write_approval` is off, so allowed writes commit
     directly.
   - Audit: `skill_ledger` records mutations, but it is telemetry, not a gate.

## Background Review Trigger

Background review runs after a turn is complete, not before the user receives a
reply. The trigger is in `agent/turn_finalizer.py`.

It spawns only when:

- the turn produced a final response,
- the turn was not interrupted,
- `skip_background_review` is false,
- memory or skill review cadence says a review is due.

Default cadence comes from `agent/agent_init.py`:

- `memory.nudge_interval`: default `10`
- `skills.creation_nudge_interval`: default `10`

`auxiliary.background_review.enabled` controls whether the review may spawn.
The default is enabled.

## Background Review Capabilities

`agent/background_review.py` creates a forked `AIAgent`.

Important existing controls:

- The fork can route to the same model as the parent, or a configured auxiliary
  model.
- The fork is quiet and runs after the foreground response.
- The fork has a runtime whitelist limited to memory and skill management
  tools.
- Dangerous command approvals in the fork auto-deny instead of blocking.
- External memory providers are skipped for the fork to avoid leaking the review
  prompt into provider memory.
- The fork disables DB persistence so its review prompt does not become part of
  the user's real conversation.
- If a new foreground turn starts while a review is still running, Hermes tries
  to interrupt the old review.

The important ROKA finding is that Hermes already contains several isolation
protections. ROKA should tighten policy around learning writes, not replace this
machinery.

## Current Memory Write Control

`tools/memory_tool.py` calls `_apply_write_gate(...)` before mutating
`MEMORY.md` or `USER.md`.

`tools/write_approval.py` defines the gate:

- Gate off: write freely.
- Gate on, foreground memory with interactive CLI: prompt inline.
- Gate on, background/gateway/script memory: stage as pending.
- Gate on, skill writes: always stage as pending.

Pending writes are stored under:

- `<HERMES_HOME>/pending/memory/`
- `<HERMES_HOME>/pending/skills/`

ROKA should use this gate instead of inventing a new approval store.

## Current Skill Write Control

`tools/skill_manager_tool.py` already distinguishes foreground writes from
background review writes.

Existing background-review protections:

- Background review cannot mutate pinned skills.
- Background review cannot mutate external skills.
- Background review cannot mutate protected built-in, hub-installed, or bundled
  skills.
- Background review cannot mutate user-owned skills unless they are explicitly
  curator-managed.
- Background review must read the target skill file before patching or editing
  it.
- Background review deletes are routed through safer consolidation/archive
  behavior when applicable.

Existing gap for ROKA:

- If `skills.write_approval` is off, background review can still directly create
  or update curator-managed local skills.
- The prompt currently pushes the reviewer toward action: "most sessions produce
  at least one skill update."
- This is useful for fast learning, but bad for reproducibility when the update
  changes future task behavior.

## Session Separation Rule

ROKA orchestration may run multiple agents in parallel, for example:

- executor
- context reviewer
- result reviewer
- policy reviewer

This is allowed across OpenAI, DeepSeek, or mixed providers, but only under a
strict state rule.

Required identifiers:

- `brief_id`: shared by all agents working from the same execution brief.
- `agent_session_id`: unique per agent instance.
- `parent_session_id`: the originating user-facing session.
- `agent_role`: `executor`, `context_reviewer`, `result_reviewer`, or
  `policy_reviewer`.
- `model_provider` and `model`: recorded for reproducibility.

Rules:

- All agents receive the same immutable execution-brief snapshot.
- Each agent keeps its own conversation history.
- No two agents append to the same `messages[]`, `conversation`, or response
  chain.
- Shared context is read-only during the run.
- Learning writes from child agents must include `brief_id`, `agent_session_id`,
  `parent_session_id`, and `agent_role`.
- The orchestrator merges only structured summaries, findings, tool evidence,
  and approved learning updates.

This rule matters especially for stateless providers such as DeepSeek, where
the orchestrator must carry each agent's `messages[]` history explicitly.

## Risk Classification

### Auto-Allow

These can commit automatically when the normal Hermes gate allows them:

- Memory entries that record explicit user preferences or stable user facts.
- Memory entries that record project facts already present in repo documents.
- Non-behavioral telemetry and audit entries.
- Skill usage counters, view counters, and append-only mutation ledger entries.
- External memory prefetch or recall that does not mutate state.

### Approval Or Proposal Required

These should stage through existing pending mechanisms or become a visible
learning proposal:

- New skill creation by background review.
- Any background-review skill patch that changes future workflow, formatting,
  tool choice, or default behavior.
- User-profile memory changes inferred indirectly rather than explicitly stated.
- Memory entries that introduce durable constraints such as "always", "never",
  "do not use", or "prefer X over Y."
- Learning writes generated by non-executor reviewer agents.
- Any learning write from a run whose execution brief had a constraint
  violation, unresolved failure, or low-confidence result.
- Any update that would affect reproducibility of a repeated task.

### Forbid

These should not be committed automatically:

- Learning from unresolved failures presented as a reliable workflow.
- Negative durable claims about tools, providers, or environments when the
  failure may be transient.
- Cross-session writes where the `agent_session_id` or `brief_id` is missing.
- Writes that mix two agents' transcripts as if they were one agent's judgment.
- Background-review edits to protected, pinned, bundled, hub, external, or
  user-owned skills.
- Any child-agent attempt to change global profile/config without foreground
  user approval.

## Execution Brief Metadata

ROKA does not need a new memory format first. It needs stronger provenance on
existing writes.

Minimum metadata to attach to memory and skill write paths:

```json
{
  "brief_id": "brief_...",
  "parent_session_id": "session_...",
  "agent_session_id": "session_...",
  "agent_role": "executor",
  "model_provider": "openai",
  "model": "gpt-5",
  "learning_origin": "foreground|background_review|child_agent",
  "risk_class": "auto_allow|approval_required|forbidden",
  "evidence_refs": ["tool_call_id_or_trace_ref"]
}
```

For the first implementation pass, this metadata can be additive:

- extend `build_memory_write_metadata(...)`,
- pass matching metadata through `skill_manage(...)` payloads if staged,
- record metadata in pending write records,
- surface it in pending review UI or CLI output later.

## ROKA Adjustment Points

First-pass changes should be small.

1. Policy config
   - Add a ROKA profile that sets `skills.write_approval: true`.
   - Consider setting `memory.write_approval: true` only for background or
     inferred profile writes, if Hermes supports origin-specific policy later.

2. Background review prompt
   - Replace the aggressive default of "most sessions produce at least one skill
     update" with a reproducibility-aware instruction.
   - Keep "Nothing to save" as a normal, acceptable result.
   - Require risk classification before calling `memory` or `skill_manage`.

3. Metadata propagation
   - Reuse `build_memory_write_metadata(...)` for memory.
   - Add execution-brief metadata to skill pending records.
   - Include `agent_role` and `agent_session_id` for child agents.

4. Orchestration contract
   - Use Hermes `delegate_task` isolated contexts for child agents.
   - Map execution brief fields into `goal`, `context`, and `metadata`.
   - Never share mutable conversation history between parallel agents.

See `docs/roka-function-impact-map.md` before implementing any of these
changes. Runtime work should start only after the touched Hermes functions and
downstream effects are identified.

## First Implementation Recommendation

Do not start by rewriting background review.

Start with:

1. Add a ROKA operating profile/document that recommends:
   - `skills.write_approval: true`
   - background review enabled
   - memory enabled according to user preference

2. Patch background-review prompts to classify learning risk before writing.

3. Extend pending-write records with execution-brief/session metadata.

4. Add tests around:
   - background review skill write stages when approval is on,
   - staged record includes `brief_id` and `agent_session_id`,
   - four parallel agents never share one mutable history chain,
   - child-agent learning writes require approval unless explicitly auto-allowed.

## Open Decisions

- Should ROKA force `skills.write_approval: true` in its profile, or only
  recommend it?
- Should memory writes be origin-sensitive, allowing foreground explicit saves
  but staging background inferred saves?
- Should reviewer agents be allowed to write memory directly, or only emit
  learning proposals for the orchestrator?
- Should DeepSeek-style stateless `messages[]` session management become the
  common lowest-level abstraction for all providers?
