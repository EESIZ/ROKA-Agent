# ROKA-Agent Documentation Map

ROKA-Agent is a fork of Hermes Agent. The first ROKA work should not be a broad
rewrite. It should identify where Hermes already carries command, context,
delegation, tool, and review concepts, then adjust those existing surfaces into
a stricter command/control flow.

## Design Principle 1: Do Not Reinvent Existing Hermes Capabilities

ROKA-Agent must not build a new subsystem when Hermes already has a usable
surface. Prefer, in order:

1. configuration and policy changes
2. documentation and operating-profile changes
3. existing hook or review flow changes
4. small adapters around existing Hermes structures
5. new core runtime code only as a last resort

The goal is not to replace Hermes. The goal is to make Hermes' existing memory,
skills, delegation, review, guardrail, verification, and observability features
operate under clearer user control.

## Strategic Goal

ROKA-Agent should make Hermes execute work through explicit execution briefs:

- task: what to do
- purpose: why it matters, including higher intent
- constraints: what must not be violated
- assumptions: what the command believes to be true
- deviation rule: when the executor may depart from the brief
- autonomy policy: what to do without immediate user contact
- outcome review: how judgment is reconstructed afterward

The goal is not "make Hermes say ROKA." The goal is to make Hermes delegation,
tool use, subagent work, session recovery, and learning updates operate through
this control model.

## Existing Hermes Surfaces

### 1. Project Intent And Contributor Doctrine

Primary files:

- `AGENTS.md`
- `CONTRIBUTING.md`
- `docs/ADR.md`

Why it matters:

Hermes already has an explicit contributor intent layer. `AGENTS.md` defines
project rules such as prompt-cache stability, narrow core surface, tool
footprint discipline, and the AIAgent loop. ROKA should extend this as a
structured command doctrine rather than replacing it.

ROKA action:

- Add a short ROKA section explaining execution briefs and task control.
- Keep upstream's existing contribution rubric intact.
- Add ROKA-specific ADRs only after the first design is approved.

### 2. User-Facing Product Identity

Primary files:

- `README.md`
- `website/docs/`

Why it matters:

The README is currently Hermes product identity. Changing it too early would
make the fork look like a finished product before the command layer exists.

ROKA action:

- Delay full rebrand.
- Add a small fork notice only after the first ROKA module exists.
- Keep install instructions truthful until ROKA has its own setup path.

### 3. Context And System Prompt Construction

Primary files:

- `agent/system_prompt.py`
- `agent/prompt_builder.py`
- `agent/turn_context.py`
- `docs/micro-compaction.md`

Why it matters:

ROKA's "intent is replicated on both sides" becomes concrete here. Hermes loads
context files, skills, memory, gateway notes, and plugin context into the prompt
while preserving prompt-cache stability.

ROKA action:

- Do not inject volatile ROKA data into the cached system prompt by default.
- Treat execution briefs as turn-scoped context unless proven stable.
- Document where command context enters the prompt and how it survives
  compaction.

### 4. Delegation And Subagents

Primary files:

- `agent/delegation_context.py`
- `agent/subagent_lifecycle.py`
- `agent/turn_context.py`
- `README.md` delegation section

Why it matters:

ROKA's edge judgment model maps directly to Hermes subagents. Subagents need
task, purpose, constraints, assumptions, and deviation reporting, not just a
plain task string.

ROKA action:

- First map Hermes' existing `SubagentLaunchRequest.goal`, `context`, and
  `metadata` fields to execution-brief semantics.
- Avoid changing subagent execution until the mapping is documented.
- Only add a compatibility adapter if existing fields cannot carry the brief
  safely.

### 5. Tool Execution And Intervention Boundaries

Primary files:

- `model_tools.py`
- `toolsets.py`
- `agent/tool_executor.py`
- `agent/tool_guardrails.py`
- `tools/`
- `docs/security/network-egress-isolation.md`

Why it matters:

ROKA says central observation is allowed, but intervention should be limited to
constraint risk, assumption failure, or objective conflict. Hermes already has
tool execution, approval, guardrails, and toolset gating.

ROKA action:

- Map ROKA constraints to existing tool guardrail and approval decisions.
- Avoid adding a new core tool unless necessary.
- Prefer existing middleware, hook, guardrail, and approval surfaces.

### 6. Session Lifecycle And Disconnect Policy

Primary files:

- `docs/session-lifecycle.md`
- `gateway/session.py`
- `gateway/run.py`
- `agent/turn_context.py`
- `tools/delegate_tool.py`
- `agent/subagent_lifecycle.py`

Why it matters:

ROKA's autonomy principle needs a runtime interpretation. Hermes already
tracks sessions, resume, suspended sessions, restarts, and recovery.

ROKA also needs strict session separation for orchestration. Different
executor/reviewer/context/policy agents may run in parallel, and may use
different model providers. They must share the same execution brief, but must
not share mutable conversation history.

ROKA action:

- Define autonomy policy at the command level before changing gateway logic.
- Use session lifecycle docs to decide what "continue", "hold", "ask", and
  "abort" mean in Hermes.
- Treat restart recovery as one form of disconnected execution.
- Assign each parallel agent its own `agent_session_id`.
- Keep a shared `brief_id` across all agents working from the same execution
  brief.
- Store each agent's transcript separately and merge only summaries, evidence,
  and declared findings back into the parent orchestration state.
- Never let four agents append directly to the same server-side conversation or
  local `messages[]` chain.

### 7. After-Action Review And Learning Loop

Primary files:

- `agent/turn_summary.py`
- `agent/turn_finalizer.py`
- `agent/memory_manager.py`
- `agent/learning_graph.py`
- `docs/observability/`

Why it matters:

ROKA evaluates judgment reconstruction, not only task success. Hermes already
has summaries, memory, learning, traces, and observability surfaces.

ROKA action:

- Reuse background review, turn summary, verification evidence, and
  observability events before adding a new reviewer.
- Capture "what the agent knew then" separately from final outcome.
- Stage memory, skill, and profile changes as learning proposals before
  activation.

### 8. Learning And Profile Change Control

Primary files:

- `agent/background_review.py`
- `agent/memory_manager.py`
- `agent/skill_commands.py`
- `agent/prompt_builder.py`
- `skills/`

Why it matters:

Hermes can automatically review turns and update memory or skills. This is
useful, but it can also make repeated tasks produce different results without a
clear user-approved change.

ROKA action:

- Prefer configuration/policy changes that stage learning updates before
  activation.
- Treat automatic memory, skill, and profile changes as proposals unless a
  policy explicitly allows automatic activation.
- Record why a learning proposal exists and what behavior it may change.

## First Implementation Target

The first implementation target is not a new subsystem. It is a mapping and
policy pass over existing Hermes surfaces:

- execution brief fields mapped to `goal`, `context`, and `metadata`
- parallel agents mapped to separate child sessions sharing one `brief_id`
- learning updates staged through existing background-review paths
- constraints mapped to existing guardrails, approval, and verification hooks
- outcome review mapped to existing turn summaries and observability events

Only after this mapping fails should ROKA-Agent add a small adapter module.

## First Documentation Target

Before code integration, add:

- `docs/roka-command-layer.md`: design and runtime contract
- `docs/roka-agent-doc-map.md`: this map
- `mydocs/plans/task_002_roka_intent_schema.md`: approved implementation plan

## Non-Goals For The First Pass

- Full Hermes rebrand
- Rewriting `run_agent.py`
- Replacing Hermes memory
- Replacing Hermes skills
- Adding a new core model tool
- Creating a parallel review system when background review/hooks can be adjusted
- Changing gateway session semantics
- Changing install scripts

## Decision Rule

If a change affects prompt caching, tool schemas, session persistence, or
security approval, it requires a written implementation plan before code.
