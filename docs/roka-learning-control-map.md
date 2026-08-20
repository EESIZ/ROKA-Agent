# ROKA Learning Control Map

ROKA keeps Hermes' existing memory, skill, background-review, ledger, and
pending-approval systems. It changes when a durable write is allowed and what
evidence travels with it.

## Policy

Durable learning is a proposal, not proof that the task succeeded.

In active ROKA mode, for Hermes' built-in curated learning APIs:

- reads remain normal Hermes behavior;
- `memory` and `skill_manage` mutations enter the existing approval decision;
- foreground memory may commit only after an available inline approval;
- all other ROKA memory writes stage to `pending/memory`;
- every ROKA skill mutation stages to `pending/skills`;
- background review must have durable, reusable evidence before proposing a
  write;
- `Nothing to save.` is a successful review result;
- staging failure is a failed tool call, never a fake success.
- staged responses say `saved: false` and `requires_approval: true`, and
  background notifications expose the pending ID.

Outside ROKA mode, existing `memory.write_approval` and
`skills.write_approval` settings retain their upstream behavior.

## Existing Hermes Paths Reused

| Data | Read path | Mutation path | ROKA control point |
| --- | --- | --- | --- |
| Built-in memory | `MemoryStore`, `memory(action="view")` | `memory_tool` add/replace/remove/batch | `_apply_write_gate`, `_apply_batch_write_gate` |
| External memory | `MemoryManager.prefetch_all(...)` | `notify_memory_tool_write(...)`, end-turn sync | Common metadata from `build_memory_write_metadata(...)`; provider-specific retention remains governed by that plugin/config, and review forks skip providers. |
| Skills | `skills_list`, `skill_view` | `skill_manage` create/edit/patch/delete/file actions | `_apply_skill_write_gate(...)` and inherited ownership/read-before-write guards. |
| Audit | pending list/diff and skill ledger | approval replay | Metadata is audit-only and excluded from replay payloads. |

## Provenance Record

Pending ROKA records may contain:

```json
{
  "control_mode": "roka",
  "brief_id": "brief_...",
  "parent_session_id": "session_...",
  "agent_session_id": "agent_...",
  "agent_role": "executor|background_reviewer",
  "model_provider": "provider",
  "model": "model-id",
  "task_id": "task_...",
  "tool_call_id": "call_...",
  "risk_class": "approval_required",
  "learning_origin": "assistant_tool|background_review"
}
```

The record's `payload` remains the exact existing Hermes replay input.
Approving an old or new record therefore invokes the same memory or skill
function, with the established gate-bypass mechanism.

## Background Review

ROKA preserves Hermes protections:

- quiet fork with a memory/skills-only runtime whitelist;
- dangerous command auto-denial;
- no external-memory prefetch or sync;
- no session DB persistence;
- protected, bundled, external, pinned, and user-owned skill guards;
- read-before-write requirements;
- foreground-turn cancellation of stale reviews.

ROKA adds:

- a spawn-time execution-brief snapshot;
- a unique `background_reviewer` logical session ID;
- direct routing to the real executor model rather than recursive MoA;
- evidence-gated prompts;
- mandatory approval routing through bound ROKA metadata.

## Risk Decisions

ROKA v0.1 intentionally uses one conservative durable-write risk class:
`approval_required`.

This avoids pretending that an LLM can reliably self-classify a behavioral
change as low risk. Future auto-allow classes require an independently
verifiable classifier, evidence references, and explicit user policy. Until
then, telemetry/read counters may follow existing Hermes behavior, while
memory and skill content changes require approval.

## Security and Correctness Properties

- Pending IDs cannot contain path separators or traversal components.
- New pending IDs use all 128 UUID bits instead of an eight-hex-character
  prefix.
- Pending files are written to a temporary path and atomically replaced.
- A failed atomic write raises `PendingWritePersistenceError`.
- Memory and skill callers convert that exception to a visible failed result.
- Bound metadata uses `contextvars`, so concurrent tool worker contexts do not
  overwrite one another.
- Dispatch-bound brief, role, session, and route metadata override conflicting
  caller-supplied audit hints when a pending record is created.
- Context binding resets after dispatch, preventing provenance from leaking to
  unrelated calls.

## Known Limits

- Approval verifies user consent, not factual correctness.
- Background evidence is still interpreted by an LLM.
- The gate covers the built-in `memory` and `skill_manage` APIs, not arbitrary
  foreground terminal/file writes or an external memory provider's own
  conversation-retention policy. ROKA forbids API bypass in the execution
  brief but is not a filesystem sandbox.
- The current pending CLI does not render every provenance field in its compact
  list view; the JSON record contains them.
- ROKA does not stop a third-party plugin that bypasses both Hermes tool
  middleware and the memory/skill APIs. Such a plugin is outside this control
  boundary and should be reviewed separately.
