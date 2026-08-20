# ROKA v0.1 Release Plan

## Command

- Mission: review ROKA-Agent as a complete release candidate and make the
  final corrections required for real use.
- Purpose: prove that intent preservation, independent review, session
  isolation, and learning control exist on live runtime paths rather than only
  in documentation.
- Completion rule: do not declare the release ready while a claimed control is
  metadata-only, prompt-only without an enforced boundary, or untested at its
  integration point.

## Release Contract

ROKA v0.1 reuses Hermes' existing Mixture of Agents, tool middleware, memory,
skills, background review, and pending-write approval store.

One user request is handled by four isolated model calls:

1. `intent_analyst` converts the ordinary user request into an immutable
   execution brief.
2. `constraint_reviewer` checks authority, constraints, assumptions, and scope.
3. `verification_reviewer` checks evidence, completion claims, and repeatability.
4. `executor` is the acting MoA aggregator and is the only role with tools.

The intent analyst runs first because the other roles must receive the exact
same brief. The two reviewers then run independently. On later tool iterations,
the brief remains fixed while reviewers can re-evaluate the updated evidence.

## Execution Brief

The brief contains:

- `brief_id`
- `task`
- `purpose`
- `constraints`
- `assumptions`
- `deviation_rule`
- `autonomy_policy`
- `review_policy`

If the intent response is malformed, ROKA creates a conservative fallback
brief and marks its source. It must never silently discard the control layer.

## Enforcement Boundaries

- Each role receives a unique `agent_session_id`; all roles share one
  `brief_id`.
- Advisor calls receive separate message copies and cannot call tools.
- The intent response is parsed and re-rendered as the canonical brief. Only
  reviewer findings are appended as private advice; advisor message histories
  and raw intent prose are never merged into the user conversation.
- Tool execution binds the active brief/session/role metadata through the
  existing Hermes tool middleware.
- The v0.1 executor cannot spawn a new delegated child because brief and
  approval-policy inheritance are not yet implemented for that child path.
- In ROKA mode, memory and skill writes require the existing approval gate even
  when the global Hermes compatibility default is off.
- Pending-write persistence fails closed. A write that was not saved to the
  pending store must not be reported as staged.
- Pending IDs are validated before filesystem access.
- Configured and actual fallback routes remain separately observable.
- Background review inherits the brief but receives its own reviewer identity.
- "Nothing to save" is a normal background-review result; learning requires
  durable evidence and must not be forced for activity's sake.

## Impacted Functions

| Existing Hermes surface | Release adjustment | Direct effect |
| --- | --- | --- |
| `hermes_cli.moa_config._clean_slot` | Preserve advisor roles and ROKA mode | Existing MoA config remains the source of model selection |
| `hermes_cli.moa_cmd.cmd_moa` and web MoA settings | Preserve fixed role slots through every save path | Reconfiguration changes models without deleting the control contract |
| `agent.moa_loop.MoAChatCompletions.create` | Compile and replicate one brief | Four-call control flow without a new engine |
| `agent.moa_loop._run_reference` | Add role-specific, brief-aware prompts | Independent reviewer behavior |
| `agent.tool_executor._run_agent_tool_execution_middleware` | Bind execution metadata | All live tool calls share one provenance path |
| `tools.write_approval.evaluate_gate` | Force approval in ROKA mode | No silent durable learning |
| `tools.write_approval.stage_write` | Merge provenance and fail closed | Pending records are auditable and real |
| `agent.background_review._run_review_in_thread` | Copy brief and allocate reviewer identity | Post-turn learning stays attributable |
| `agent.background_review` review prompts | Require evidence; allow no-op | Prevents arbitrary skill churn |

## Quality Gates

- Pure tests for execution-brief parsing, fallback, IDs, and context isolation.
- MoA integration test proving call order, exact brief replication, unique role
  identities, and acting-model guidance.
- Memory and skill staging tests proving provenance reaches the saved pending
  record through the real gate.
- Persistence-failure and invalid-ID tests for the pending store.
- Background-review prompt contract tests.
- CLI, web API, and web type/build checks for role-preserving configuration.
- Existing focused Hermes suites run through `scripts/run_tests.sh`.
- Syntax, lint, and repository status checks before commit.

## Non-Goals

- Replacing Hermes sessions, tools, memory, skills, or provider adapters.
- Giving advisory models tool access.
- Claiming bit-for-bit deterministic LLM output.
- Rebranding upstream package/import names in a way that breaks compatibility.
