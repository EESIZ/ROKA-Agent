# ROKA v0.1 Final Release Review

Date: 2026-08-20

## Review Command

- Mission: perform a repository-wide pre-release review and make every final
  correction required for real use. This is not a subordinate ROKA task.
- Purpose: prove at function and runtime-flow level that the methodology is
  implemented, not represented by labels or prompts alone.
- Completion rule: do not mark the source release ready if a claimed boundary
  can silently degrade, lose its execution identity, or report work that did
  not occur.

## Verdict

**ROKA-Agent v0.1 is ready for a source release.**

The user-message-to-executor path, role isolation, live tool provenance,
approval routing, background-review behavior, configuration surfaces, and
fallback behavior are implemented and covered by focused integration and
upstream regression tests.

This verdict is not a provider-deployment certification. The local machine has
neither Codex credentials nor an OpenRouter credential, so no paid live call
across all four default providers was made. After credentials are configured,
one operator smoke turn remains required before relying on a deployment.

## Verified Runtime Path

1. A normal user message enters the existing Hermes virtual `provider=moa`
   facade.
2. `intent_analyst` runs first and produces a parsed, immutable
   `ExecutionBrief`.
3. `constraint_reviewer` and `verification_reviewer` receive independent
   message copies, unique logical session IDs, no tools, and the same brief.
4. The MoA aggregator acts as the sole executor and receives the canonical
   brief plus reviewer findings.
5. Tool middleware binds the brief, parent session, logical executor session,
   role, actual provider/model route, task ID, and tool-call ID.
6. Existing Hermes tools execute normally. New `delegate_task` spawns are
   unavailable and middleware-blocked in ROKA v0.1.
7. Built-in memory and skill mutations enter Hermes' existing approval store.
   A staged result is returned only after its pending record exists on disk.
8. Background review uses a spawn-time brief snapshot, a separate reviewer
   identity, the direct acting-model route, an evidence-gated prompt, and only
   the existing learning APIs.

## Release Blockers Resolved

| Finding | Final correction |
| --- | --- |
| Legacy context-only MoA could look like ROKA | ROKA-labelled legacy payloads fail before execution and direct callers to the virtual provider path. |
| Missing CLI/Gateway MoA config could select generic defaults | One-shot commands use the shipped `roka` default when no user block is loaded. |
| Malformed intent output could contaminate acting guidance | Raw intent prose is never acting advice; parsing either produces a canonical brief or a conservative fallback from the clean user request. |
| Brief identity could change after in-turn compression | The ID uses the live turn ID and compression-lineage root. |
| A normal outer fallback could replace four-role control with one model | Outer fallback is refused while the ROKA MoA facade is active. Role-level provider fallback remains observable. |
| Disabled or misspelled control mode could run generic/executor-only behavior | Disabled ROKA and unknown nonempty control modes fail before any model call. |
| Executor could create an unbriefed child | New delegation is removed from the executor schema and blocked again in middleware. |
| Pending writes could claim staging after disk failure | Pending persistence is atomic and fail-closed; memory/skill tools return failure if staging fails. |
| Short pending IDs and unchecked lookup could weaken storage integrity | New IDs use UUID128 hex; lookup/discard accept only bounded hexadecimal IDs. |
| Caller audit hints could relabel actual execution | Dispatch-bound brief, session, role, and route provenance are authoritative when a pending record is created. |
| Direct background-review fallback retained the old model label | Successful direct-worker fallback updates the actual ROKA provider/model provenance. |
| Background review pressured the model to invent learning | Durable evidence is required and `Nothing to save.` is a normal successful result. |
| Background review could recursively invoke ROKA MoA | It routes directly to the acting executor model with an isolated reviewer identity. |
| UI saves could delete role identity | CLI, web, and desktop editors preserve three fixed ROKA advisor roles while allowing route replacement. |
| Public Windows setup instructions were incomplete | README now documents installation from the cloned fork through `scripts/install.ps1`. |
| Production npm override lagged a patched dependency | The Nano ID 3 override was advanced to 3.3.18; the production audit now reports zero vulnerabilities. |

## Mechanical Boundary

The code mechanically enforces topology, call order, separate message objects,
logical identities, one brief per turn, tool access, delegation blocking,
provenance binding, pending persistence, and approval routing for built-in
memory/skill APIs.

The code does not mechanically prove that an LLM semantically understood the
user, that reviewer advice is true, or that the executor obeyed every sentence.
Those claims require observable tool results and tests. ROKA also remains an
agent control profile rather than a filesystem sandbox: generic terminal/file
writes, out-of-process plugins, and external provider retention need operating
system and plugin controls.

## Review Dimensions

- Security: release-ready within the declared boundary. Path traversal,
  approval fail-open behavior, recursive MoA review, provenance spoofing, and
  silent outer fallback were addressed. No credentials are present in the
  change set.
- Correctness: release-ready on focused paths. A synthetic full `AIAgent` turn
  proves user input, all four roles, a real Hermes tool dispatch, stable brief
  identity, actual route attribution, and context cleanup in one flow.
- Performance: acceptable with an explicit cost. Intent runs once; the two
  reviewers run in parallel and refresh after changed tool evidence. Their
  output is capped at 900 tokens in the shipped preset. This deliberately adds
  latency and provider spend relative to one-model Hermes.
- Maintainability: the fork adds one small core module and modifies existing
  Hermes ownership points. Function maps, contributor invariants, focused
  tests, and generic-MoA regression groups cover the new contract.

## Focused Release Evidence

All Python behavior tests below used the repository's canonical
`scripts/run_tests.sh` runner, not direct pytest invocation.

| Gate | Result |
| --- | --- |
| ROKA integrated release group, 11 files | 179 passed, 8 skipped, 0 failed |
| Existing MoA neighbor group, 18 files | 98 passed, 0 failed |
| Existing background-review neighbor group, 6 files | 44 passed, 0 failed |
| Existing provider-fallback group, 5 files | 55 passed, 0 failed |
| Ruff over every changed Python file | Passed |
| Web TypeScript check | Passed |
| Web Vitest | 36 files, 275 tests passed |
| Web ESLint | 0 errors, 26 pre-existing warnings |
| Web production build | Passed |
| Desktop renderer/electron/E2E TypeScript checks | Passed |
| Desktop changed settings test | 1 file, 21 tests passed |
| Desktop ESLint | 0 errors, 134 pre-existing warnings; no warning in changed files |
| Desktop production build and artifact assertion | Passed |
| Root production dependency audit | 0 vulnerabilities |
| Editable-install module import | `agent.roka_control` resolved from this checkout |
| Repository whitespace check | Passed |

The CLI/Gateway test group includes real one-shot command routing checks. An
additional focused platform run covered Telegram, Discord, and Slack dispatch.

## Broad Baseline Results

The complete upstream Python suite was also attempted on native Windows:

- 3,066 files discovered
- 32,530 tests passed
- 704 tests failed
- 575 tests skipped
- 2,108.1 seconds

The failures cluster around upstream POSIX-only assumptions and unavailable
optional runtimes: `termios`, `geteuid`, `chown`, SIGKILL, symlink privilege,
POSIX paths and modes, `/tmp`, bash/WSL conversion, missing `acp`/native
`anthropic`, CRLF expectations, and load-related file timeouts. One guardrail
test compares `/approved/path` with Windows' normalized path. The web-server
file passed 161 tests and skipped 4 internally but exceeded the outer 300-second
per-file timeout under full-suite load.

No focused ROKA, MoA, approval, background-review, or fallback regression
remained after classification and reruns.

The full desktop Vitest suite was also attempted. It was stopped after
repeated pre-existing Windows/jsdom failures and open handles prevented a clean
termination. The failures included POSIX file-mode/worktree assumptions,
macOS helper staging, SSH control sockets, unavailable jsdom canvas behavior,
React `act()` environment warnings, and unrelated UI timeouts. The changed
settings test, full type checks, lint, and production build were therefore used
as the release gates for this fork-specific change.

## Distribution Check

Hermes intentionally rejects ordinary wheel and sdist builds in `setup.py`.
`python -m build` reached that guard and returned the documented instruction to
use the shell installer, Docker, Nix, or an editable source install. This fork
keeps that upstream distribution policy. The editable environment imports the
new ROKA module successfully, and the desktop production artifact builds.

## Deployment Prerequisite

The four shipped routes resolve to the intended local catalog entries:

- `openai-codex:gpt-5.5`
- `openrouter:deepseek/deepseek-v4-pro`
- `openrouter:google/gemini-3-pro-preview`
- `openrouter:anthropic/claude-opus-4.8`

Local credential inspection exposed no secret values. It found no stored Codex
credential and no OpenRouter credential, so a live four-model smoke test was
not possible. The first deployment must run `hermes auth`, configure
OpenRouter, start `hermes chat --provider moa --model roka`, and verify one turn
shows all three advisor labels, one executor route, a stable brief ID through a
tool iteration, and a staged learning proposal when a controlled memory write
is requested.

## Residual Limits

- Natural-language output is stochastic; ROKA constrains process and evidence,
  not byte-for-byte answers.
- A conservative fallback brief preserves control after intent-model failure,
  but it is less semantically rich than a valid intent analysis.
- Loud degraded mode permits execution when an advisor is unavailable; it does
  not falsely claim the role succeeded.
- Provider APIs are usually stateless. Logical sessions mean isolated message
  histories and audit IDs, not provider-side stored sessions.
- The approval boundary covers built-in `memory` and `skill_manage` mutations,
  not arbitrary writes by hostile plugins or shell commands.
- Third-party provider availability and retention policy remain outside the
  repository's control.

Within those explicit boundaries, no known release-blocking defect remains.
