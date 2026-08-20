import json
from types import SimpleNamespace

import pytest

from agent.roka_control import (
    advisor_system_prompt,
    bind_execution_metadata,
    build_agent_session_id,
    build_brief_id,
    current_execution_metadata,
    parse_execution_brief,
    reject_legacy_roka_execution,
    update_execution_route_for_agent,
)


def test_parse_execution_brief_preserves_intent_and_adds_control_constraints():
    output = json.dumps(
        {
            "task": "Ship the release candidate",
            "purpose": "Prove the control flow works in real use",
            "constraints": ["Do not publish unverified claims."],
            "assumptions": ["The repository is the release source."],
            "deviation_rule": "Report any required scope change.",
            "autonomy_policy": "Proceed with reversible repository edits.",
            "review_policy": "Require test evidence before completion.",
        }
    )

    brief = parse_execution_brief(
        output,
        brief_id="brief_test",
        user_request="Prepare this project for release.",
    )

    assert brief.source == "advisor"
    assert brief.task == "Ship the release candidate"
    assert "Do not publish unverified claims." in brief.constraints
    assert any("scope or authority" in item for item in brief.constraints)
    assert any("observable evidence" in item for item in brief.constraints)
    assert any("bypass memory or skill approval" in item for item in brief.constraints)


def test_required_constraints_survive_a_full_advisor_constraint_list():
    output = json.dumps(
        {
            "task": "Run the bounded task",
            "purpose": "Keep mandatory controls",
            "constraints": [f"user constraint {index}" for index in range(32)],
            "assumptions": ["The input is available."],
            "deviation_rule": "Report any deviation.",
            "autonomy_policy": "Proceed only in scope.",
            "review_policy": "Require evidence.",
        }
    )

    brief = parse_execution_brief(
        output,
        brief_id="brief_full_constraints",
        user_request="Run the bounded task.",
    )

    assert len(brief.constraints) == 32
    assert any("scope or authority" in item for item in brief.constraints)
    assert any("observable evidence" in item for item in brief.constraints)
    assert any("bypass memory or skill approval" in item for item in brief.constraints)


def test_malformed_intent_output_fails_to_a_conservative_brief():
    brief = parse_execution_brief(
        "not valid json",
        brief_id="brief_fallback",
        user_request="Fix the reported defect.",
    )

    assert brief.source == "fallback"
    assert brief.task == "Fix the reported defect."
    assert "observable evidence" in " ".join(brief.constraints)


def test_shape_only_intent_json_is_not_reported_as_advisor_success():
    brief = parse_execution_brief(
        "{}",
        brief_id="brief_empty",
        user_request="Keep the user's real request.",
    )

    assert brief.source == "fallback"
    assert brief.task == "Keep the user's real request."


def test_advisor_prompts_preserve_operational_guardrails():
    brief = parse_execution_brief(
        json.dumps(
            {
                "task": "Keep the runtime bounded",
                "purpose": "Prevent fake advisor success",
                "constraints": ["Do not modify host services."],
                "assumptions": ["Repository edits are allowed."],
                "deviation_rule": "Report changed premises.",
                "autonomy_policy": "Proceed in repo only.",
                "review_policy": "Require observable evidence.",
            }
        ),
        brief_id="brief_prompt",
        user_request="Keep the runtime bounded.",
    )

    intent_prompt = advisor_system_prompt(
        "base",
        role="intent_analyst",
        brief_id=brief.brief_id,
        agent_session_id="intent-session",
    )
    constraint_prompt = advisor_system_prompt(
        "base",
        role="constraint_reviewer",
        brief_id=brief.brief_id,
        agent_session_id="constraint-session",
        execution_brief=brief,
    )

    assert "ONLY a JSON object" in intent_prompt
    assert "Do not include markdown, user-facing prose" in intent_prompt
    assert "No constraint breach found" in constraint_prompt
    assert "sudo/apt" in constraint_prompt
    assert "Chromium/Xvfb" in constraint_prompt
    assert "approval bypass" in constraint_prompt


def test_turn_and_role_session_ids_are_stable_but_isolated():
    first = [{"role": "user", "content": "Do the task."}]
    same_turn = first + [
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "tool", "content": "evidence", "tool_call_id": "call-1"},
    ]
    next_turn = same_turn + [{"role": "user", "content": "Now verify it."}]

    first_id = build_brief_id(first, parent_session_id="parent")
    assert build_brief_id(same_turn, parent_session_id="parent") == first_id
    assert build_brief_id(next_turn, parent_session_id="parent") != first_id

    ids = {
        build_agent_session_id(first_id, role, provider="test", model="model")
        for role in (
            "intent_analyst",
            "constraint_reviewer",
            "verification_reviewer",
            "executor",
        )
    }
    assert len(ids) == 4


def test_live_turn_id_keeps_brief_stable_across_transcript_compression():
    before_compression = [
        {"role": "user", "content": "Old context"},
        {"role": "assistant", "content": "Old answer"},
        {"role": "user", "content": "Do the current task."},
    ]
    after_compression = [
        {"role": "system", "content": "Compressed prior conversation"},
        {"role": "user", "content": "Do the current task."},
    ]

    before_id = build_brief_id(
        before_compression,
        parent_session_id="parent",
        turn_id="turn-1",
    )
    assert build_brief_id(
        after_compression,
        parent_session_id="parent",
        turn_id="turn-1",
    ) == before_id
    assert build_brief_id(
        after_compression,
        parent_session_id="parent",
        turn_id="turn-2",
    ) != before_id


def test_execution_metadata_binding_is_nested_and_resets():
    assert current_execution_metadata() == {}
    with bind_execution_metadata({"brief_id": "brief-1", "agent_role": "executor"}):
        assert current_execution_metadata()["brief_id"] == "brief-1"
        with bind_execution_metadata({"tool_call_id": "call-1"}):
            assert current_execution_metadata() == {
                "brief_id": "brief-1",
                "agent_role": "executor",
                "tool_call_id": "call-1",
            }
        assert "tool_call_id" not in current_execution_metadata()
    assert current_execution_metadata() == {}


def test_successful_moa_to_moa_model_switch_clears_previous_brief(monkeypatch):
    from agent import agent_runtime_helpers as helpers

    monkeypatch.setattr(
        "hermes_cli.providers.determine_api_mode",
        lambda *_args, **_kwargs: "chat_completions",
    )
    monkeypatch.setattr(
        "agent.moa_loop.build_moa_facade",
        lambda _agent, preset: SimpleNamespace(preset=preset),
    )
    monkeypatch.setattr(
        helpers,
        "sync_credential_pool_entry_id",
        lambda _agent: None,
    )
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {},
    )
    monkeypatch.setattr(
        "hermes_cli.config.get_compatible_custom_providers",
        lambda _config: [],
    )
    monkeypatch.setattr(
        "hermes_cli.config.get_custom_provider_context_length",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "hermes_constants.resolve_reasoning_config",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "agent.chat_completion_helpers._reset_stale_streak",
        lambda _agent: None,
    )

    agent = SimpleNamespace(
        model="roka",
        provider="moa",
        requested_provider="moa",
        base_url="moa://local",
        api_mode="chat_completions",
        api_key="moa-virtual-provider",
        client=object(),
        _client_kwargs={},
        _credential_pool=object(),
        _credential_pool_entry_id=None,
        _config_context_length=None,
        _transport_cache={},
        _ensure_lmstudio_runtime_loaded=lambda _intent: None,
        _lmstudio_load_was_unverified=lambda _runtime: False,
        _effective_lmstudio_context_length=lambda intent, _runtime: intent,
        _anthropic_prompt_cache_policy=lambda **_kwargs: (False, False),
        context_compressor=None,
        reasoning_config=None,
        _cached_system_prompt="cached",
        _primary_runtime={},
        _fallback_activated=False,
        _fallback_index=0,
        _fallback_chain=[],
        _fallback_model=None,
        _session_db=None,
        session_id="parent-session",
        _roka_control_mode="roka",
        _execution_brief={"brief_id": "brief-old"},
        _execution_brief_id="brief-old",
        _agent_role="executor",
        _agent_session_id="agent-old",
        _roka_model_provider="openrouter",
        _roka_model="executor-model",
    )

    helpers.switch_model(
        agent,
        "generic",
        "moa",
        api_key="moa-virtual-provider",
        base_url="moa://local",
    )

    assert agent.model == "generic"
    assert agent._roka_control_mode == ""
    assert agent._execution_brief == {}
    assert agent._execution_brief_id == ""


def test_legacy_context_path_rejects_roka_instead_of_simulating_control():
    with pytest.raises(RuntimeError, match="virtual MoA provider"):
        reject_legacy_roka_execution(
            {
                "control_mode": "roka",
                "reference_models": [],
                "aggregator": {},
            }
        )

    reject_legacy_roka_execution({"reference_models": [], "aggregator": {}})

    with pytest.raises(RuntimeError, match="virtual MoA provider"):
        reject_legacy_roka_execution(
            {
                "default_preset": "roka",
                "presets": {
                    "roka": {"control_mode": "roka"},
                    "generic": {},
                },
            }
        )


def test_roka_blocks_outer_fallback_that_would_drop_the_control_facade():
    from agent.chat_completion_helpers import try_activate_fallback

    agent = SimpleNamespace(
        _roka_control_mode="roka",
        provider="moa",
        model="roka",
        _fallback_index=0,
        _fallback_chain=[{"provider": "openrouter", "model": "fallback"}],
    )

    assert try_activate_fallback(agent) is False
    assert agent.provider == "moa"
    assert agent._fallback_index == 0


def test_actual_route_update_only_changes_active_roka_provenance():
    roka_agent = SimpleNamespace(
        _roka_control_mode="roka",
        _roka_model_provider="configured",
        _roka_model="configured-model",
    )
    generic_agent = SimpleNamespace(
        _roka_control_mode="",
        _roka_model_provider="configured",
        _roka_model="configured-model",
    )

    update_execution_route_for_agent(
        roka_agent,
        provider="actual",
        model="actual-model",
    )
    update_execution_route_for_agent(
        generic_agent,
        provider="ignored",
        model="ignored-model",
    )

    assert roka_agent._roka_model_provider == "actual"
    assert roka_agent._roka_model == "actual-model"
    assert generic_agent._roka_model_provider == "configured"
    assert generic_agent._roka_model == "configured-model"
