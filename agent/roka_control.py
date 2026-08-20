"""ROKA control metadata and execution-brief helpers.

The module is intentionally small. Hermes still owns model routing, sessions,
tools, and persistence; ROKA only compiles one immutable brief and carries its
identity through those existing paths.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any, Iterator, Mapping, Sequence


ROKA_CONTROL_MODE = "roka"
ROKA_ADVISOR_ROLES = (
    "intent_analyst",
    "constraint_reviewer",
    "verification_reviewer",
)

_MAX_FIELD_CHARS = 8_000
_MAX_LIST_ITEMS = 32

_BASE_CONSTRAINTS = (
    "Do not expand scope or authority beyond the user's request.",
    "Do not claim execution or verification without observable evidence.",
    "Do not bypass memory or skill approval through generic file or terminal tools.",
)

_REQUIRED_TEXT_FIELDS = (
    "task",
    "purpose",
    "deviation_rule",
    "autonomy_policy",
    "review_policy",
)

_CURRENT_EXECUTION_METADATA: contextvars.ContextVar[dict[str, Any]] = (
    contextvars.ContextVar("roka_execution_metadata", default={})
)


def _clip(value: Any, *, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return text[:_MAX_FIELD_CHARS]


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values: Sequence[Any] = [value]
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        values = []
    result: list[str] = []
    for item in values[:_MAX_LIST_ITEMS]:
        text = _clip(item)
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _message_text(message: Mapping[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, Mapping) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    return ""


def latest_user_request(messages: Sequence[Mapping[str, Any]]) -> str:
    """Return the latest real user request from an API message sequence."""
    for message in reversed(messages):
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        text = _message_text(message)
        if not text or text.startswith("[Mixture of Agents reference context]"):
            continue
        return text
    return "Complete the user's current request."


def reject_legacy_roka_execution(moa_config: Any) -> None:
    """Fail closed when ROKA is sent through the legacy context-only path.

    The old ``run_conversation(..., moa_config=...)`` contract asks reference
    models for text, synthesizes it, and then lets the already-selected main
    model act.  It cannot provide ROKA's frozen brief, role identities, or
    executor provenance.  A ROKA-labelled preset must therefore use Hermes'
    virtual ``provider=moa`` facade instead of silently receiving weaker
    behavior under the same name.
    """
    if not isinstance(moa_config, Mapping):
        return
    control_mode = str(moa_config.get("control_mode") or "").strip().lower()
    if not control_mode:
        presets = moa_config.get("presets")
        if isinstance(presets, Mapping):
            preset_name = str(
                moa_config.get("active_preset")
                or moa_config.get("default_preset")
                or ""
            ).strip()
            selected = presets.get(preset_name) if preset_name else None
            if isinstance(selected, Mapping):
                control_mode = str(
                    selected.get("control_mode") or ""
                ).strip().lower()
    if control_mode == ROKA_CONTROL_MODE:
        raise RuntimeError(
            "ROKA control requires the virtual MoA provider path "
            "(provider='moa' with a ROKA preset); the legacy moa_config "
            "context path is not an equivalent control runtime."
        )


def build_brief_id(
    messages: Sequence[Mapping[str, Any]],
    *,
    parent_session_id: str = "",
    turn_id: str = "",
) -> str:
    """Build a stable ID for one user turn, including its prior context.

    A live Hermes turn ID is authoritative because transcript compression may
    rewrite older messages during the same tool loop. Direct/test callers that
    have no turn ID retain the deterministic message-prefix fallback.
    """
    if str(turn_id or "").strip():
        canonical = json.dumps(
            {
                "parent_session_id": str(parent_session_id or ""),
                "turn_id": str(turn_id).strip(),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return "brief_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]

    last_user_index = -1
    for index, message in enumerate(messages):
        if isinstance(message, Mapping) and message.get("role") == "user":
            last_user_index = index
    turn_prefix = list(messages[: last_user_index + 1]) if last_user_index >= 0 else []
    canonical = json.dumps(
        {
            "parent_session_id": str(parent_session_id or ""),
            "turn_prefix": turn_prefix,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "brief_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def build_agent_session_id(
    brief_id: str,
    role: str,
    *,
    provider: str = "",
    model: str = "",
    index: int = 0,
) -> str:
    """Return a stable, role-specific logical session ID for one brief."""
    value = "|".join(
        (brief_id, role, str(provider or ""), str(model or ""), str(index))
    )
    return "agent_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class ExecutionBrief:
    brief_id: str
    task: str
    purpose: str
    constraints: tuple[str, ...]
    assumptions: tuple[str, ...]
    deviation_rule: str
    autonomy_policy: str
    review_policy: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["constraints"] = list(self.constraints)
        value["assumptions"] = list(self.assumptions)
        return value

    def render(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def fallback_execution_brief(
    *,
    brief_id: str,
    user_request: str,
) -> ExecutionBrief:
    """Create a conservative brief when the intent advisor cannot be parsed."""
    return ExecutionBrief(
        brief_id=brief_id,
        task=_clip(user_request, fallback="Complete the user's current request."),
        purpose=(
            "Satisfy the user's stated objective while preserving their stated "
            "priorities and authority boundaries."
        ),
        constraints=_BASE_CONSTRAINTS,
        assumptions=(
            "Unstated implementation details may be chosen conservatively and reversibly.",
        ),
        deviation_rule=(
            "Depart from the requested method only when an observed contradiction, "
            "constraint, or blocking condition requires it; report the reason."
        ),
        autonomy_policy=(
            "Proceed with reversible actions inside the stated scope; stop for missing "
            "authority or ambiguity that would materially change the outcome."
        ),
        review_policy=(
            "Check the result against the task, purpose, constraints, and observable "
            "evidence before claiming completion."
        ),
        source="fallback",
    )


def _first_json_object(text: str) -> Mapping[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text or ""):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            nested = value.get("execution_brief")
            return nested if isinstance(nested, Mapping) else value
    return None


def parse_execution_brief(
    advisor_output: str,
    *,
    brief_id: str,
    user_request: str,
) -> ExecutionBrief:
    """Parse an intent-advisor response, falling back without dropping control."""
    fallback = fallback_execution_brief(
        brief_id=brief_id,
        user_request=user_request,
    )
    raw = _first_json_object(advisor_output)
    if raw is None:
        return fallback
    if any(
        not isinstance(raw.get(field), str) or not str(raw[field]).strip()
        for field in _REQUIRED_TEXT_FIELDS
    ):
        return fallback
    if not isinstance(raw.get("constraints"), (list, tuple)):
        return fallback
    if not isinstance(raw.get("assumptions"), (list, tuple)):
        return fallback

    task = _clip(raw.get("task"), fallback=fallback.task)
    purpose = _clip(raw.get("purpose"), fallback=fallback.purpose)
    constraints = [
        item
        for item in _string_list(raw.get("constraints"))
        if item not in _BASE_CONSTRAINTS
    ]
    constraints = constraints[: _MAX_LIST_ITEMS - len(_BASE_CONSTRAINTS)]
    constraints.extend(_BASE_CONSTRAINTS)
    assumptions = _string_list(raw.get("assumptions")) or fallback.assumptions

    return ExecutionBrief(
        brief_id=brief_id,
        task=task,
        purpose=purpose,
        constraints=tuple(constraints),
        assumptions=assumptions,
        deviation_rule=_clip(
            raw.get("deviation_rule"), fallback=fallback.deviation_rule
        ),
        autonomy_policy=_clip(
            raw.get("autonomy_policy"), fallback=fallback.autonomy_policy
        ),
        review_policy=_clip(
            raw.get("review_policy"), fallback=fallback.review_policy
        ),
        source="advisor",
    )


def advisor_system_prompt(
    base_prompt: str,
    *,
    role: str = "",
    agent_session_id: str = "",
    brief_id: str = "",
    execution_brief: ExecutionBrief | None = None,
) -> str:
    """Add a bounded ROKA role contract to Hermes' reference prompt."""
    if role not in ROKA_ADVISOR_ROLES:
        return base_prompt

    identity = (
        f"\n\nROKA role: {role}\n"
        f"Execution brief ID: {brief_id or 'unassigned'}\n"
        f"Logical agent session: {agent_session_id or 'unassigned'}\n"
    )
    if role == "intent_analyst":
        return base_prompt + identity + (
            "Convert the user's ordinary request into one execution brief. Return "
            "ONLY a JSON object with these keys: task, purpose, constraints "
            "(array), assumptions (array), deviation_rule, autonomy_policy, and "
            "review_policy. Do not include markdown, user-facing prose, commands, "
            "or any text outside the JSON object. Preserve the user's actual "
            "priorities. Do not invent authority, side effects, deadlines, or "
            "requirements."
        )

    brief_text = execution_brief.render() if execution_brief is not None else "{}"
    if role == "constraint_reviewer":
        instructions = (
            "Treat the execution brief below as immutable. Identify scope expansion, "
            "conflicting constraints, unsafe assumptions, missing authority, and the "
            "specific conditions that require stopping or deviating. Give concrete "
            "guidance to the acting model; do not rewrite the brief. Always return "
            "a non-empty constraint assessment. If no breach is found, say "
            "`No constraint breach found` and name the boundaries to preserve. "
            "Flag any drift toward host OS/package installation, sudo/apt commands, "
            "Chromium/Xvfb setup, approval bypass, or changes outside the requested "
            "repository/service boundary unless the execution brief explicitly "
            "authorizes it."
        )
    else:
        instructions = (
            "Treat the execution brief below as immutable. Judge whether the current "
            "task state contains enough observable evidence for each completion claim. "
            "Call out unverified self-reports, missing tests, regressions, and causes of "
            "non-repeatable results. Give concrete checks to the acting model."
        )
    return base_prompt + identity + instructions + (f"\n\nExecution brief:\n{brief_text}")


def apply_execution_brief_to_agent(
    agent: Any,
    brief: ExecutionBrief,
    *,
    provider: str,
    model: str,
    parent_session_id: str = "",
) -> None:
    """Attach turn-scoped ROKA identity to the existing Hermes agent object."""
    if agent is None:
        return
    agent._roka_control_mode = ROKA_CONTROL_MODE
    agent._execution_brief = brief.to_dict()
    agent._execution_brief_id = brief.brief_id
    agent._agent_role = "executor"
    agent._roka_parent_session_id = str(
        parent_session_id or getattr(agent, "session_id", "") or ""
    )
    agent._agent_session_id = build_agent_session_id(
        brief.brief_id,
        "executor",
        provider=provider,
        model=model,
    )
    agent._roka_model_provider = provider
    agent._roka_model = model


def update_execution_route_for_agent(
    agent: Any,
    *,
    provider: str,
    model: str,
) -> None:
    """Record the route that actually served a ROKA acting-model call."""
    if agent is None or getattr(agent, "_roka_control_mode", "") != ROKA_CONTROL_MODE:
        return
    agent._roka_model_provider = str(provider or "")
    agent._roka_model = str(model or "")


def clear_execution_brief_from_agent(agent: Any) -> None:
    """Remove turn-scoped ROKA state when an agent leaves the control mode."""
    if agent is None:
        return
    agent._roka_control_mode = ""
    agent._execution_brief = {}
    agent._execution_brief_id = ""
    agent._agent_role = ""
    agent._agent_session_id = ""
    agent._roka_parent_session_id = ""
    agent._roka_model_provider = ""
    agent._roka_model = ""


def execution_metadata_for_agent(
    agent: Any,
    *,
    task_id: str = "",
    tool_call_id: str = "",
) -> dict[str, Any]:
    """Build audit-only metadata for an existing Hermes tool call."""
    if agent is None:
        return {}
    mode = str(getattr(agent, "_roka_control_mode", "") or "")
    brief_id = str(
        getattr(agent, "_execution_brief_id", "")
        or getattr(agent, "_brief_id", "")
        or ""
    )
    metadata = {
        "control_mode": mode,
        "brief_id": brief_id,
        "parent_session_id": str(
            getattr(agent, "_roka_parent_session_id", "")
            or getattr(agent, "_parent_session_id", "")
            or getattr(agent, "session_id", "")
            or ""
        ),
        "agent_session_id": str(
            getattr(agent, "_agent_session_id", "")
            or getattr(agent, "session_id", "")
            or ""
        ),
        "agent_role": str(getattr(agent, "_agent_role", "") or ""),
        "model_provider": str(
            getattr(agent, "_roka_model_provider", "")
            or getattr(agent, "provider", "")
            or ""
        ),
        "model": str(
            getattr(agent, "_roka_model", "")
            or getattr(agent, "model", "")
            or ""
        ),
        "task_id": str(task_id or ""),
        "tool_call_id": str(tool_call_id or ""),
    }
    return {key: value for key, value in metadata.items() if value not in (None, "")}


def current_execution_metadata() -> dict[str, Any]:
    return dict(_CURRENT_EXECUTION_METADATA.get() or {})


def is_roka_execution_active() -> bool:
    """Return whether the current tool call is bound to ROKA control."""
    return current_execution_metadata().get("control_mode") == ROKA_CONTROL_MODE


@contextmanager
def bind_execution_metadata(metadata: Mapping[str, Any] | None) -> Iterator[None]:
    """Bind provenance for nested tool calls without changing tool schemas."""
    merged = current_execution_metadata()
    if metadata:
        merged.update(
            key_value
            for key_value in metadata.items()
            if key_value[1] not in (None, "")
        )
    token = _CURRENT_EXECUTION_METADATA.set(merged)
    try:
        yield
    finally:
        _CURRENT_EXECUTION_METADATA.reset(token)
