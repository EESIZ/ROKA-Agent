from types import SimpleNamespace

from agent import background_review


def _roka_parent():
    return SimpleNamespace(
        session_id="parent-session",
        provider="moa",
        model="roka",
        base_url="",
        api_key="",
        api_mode="",
        auth_mode="",
        request_overrides={},
        max_tokens=None,
        acp_command=None,
        acp_args=[],
        _credential_pool=None,
        _roka_control_mode="roka",
        _execution_brief_id="brief-original",
        _execution_brief={"brief_id": "brief-original", "task": "Original task"},
        _roka_model_provider="openrouter",
        _roka_model="executor-model",
        _current_main_runtime=lambda: {
            "provider": "moa",
            "model": "roka",
            "base_url": "",
            "api_key": "",
            "api_mode": "",
        },
    )


def test_background_review_captures_brief_at_spawn_time(monkeypatch):
    parent = _roka_parent()
    captured = {}

    def record_call(agent, messages, prompt, task_cfg):
        captured.update(
            agent=agent,
            messages=messages,
            prompt=prompt,
            task_cfg=task_cfg,
        )

    monkeypatch.setattr(background_review, "_run_review_in_thread", record_call)
    target, prompt = background_review.spawn_background_review_thread(
        parent,
        [{"role": "user", "content": "Original task"}],
        review_memory=True,
        task_cfg={},
    )

    parent._execution_brief_id = "brief-next-turn"
    parent._execution_brief = {
        "brief_id": "brief-next-turn",
        "task": "Different task",
    }
    target()

    snapshot = captured["task_cfg"]["_roka_control_snapshot"]
    assert snapshot["brief_id"] == "brief-original"
    assert snapshot["execution_brief"]["task"] == "Original task"
    assert "Original task" in prompt
    assert "Different task" not in prompt


def test_background_review_routes_to_direct_executor_model(monkeypatch):
    parent = _roka_parent()
    calls = []

    def resolve_runtime_provider(**kwargs):
        calls.append(kwargs)
        return {
            "provider": "openrouter",
            "model": "executor-model",
            "api_key": "resolved-key",
            "base_url": "https://example.invalid/v1",
            "api_mode": "chat_completions",
        }

    monkeypatch.setattr(
        "hermes_cli.runtime_provider.resolve_runtime_provider",
        resolve_runtime_provider,
    )
    task_cfg = {
        "provider": "moa",
        "model": "recursive-review-preset",
        "_roka_control_snapshot": {
            "control_mode": "roka",
            "model_provider": "openrouter",
            "model": "executor-model",
        }
    }

    runtime = background_review._resolve_review_runtime(parent, task_cfg)

    assert calls[0]["requested"] == "openrouter"
    assert runtime["provider"] == "openrouter"
    assert runtime["model"] == "executor-model"
    assert runtime["routed"] is True


def test_background_review_fails_instead_of_recursing_without_direct_route():
    parent = _roka_parent()
    task_cfg = {
        "provider": "moa",
        "model": "recursive-review-preset",
        "_roka_control_snapshot": {
            "control_mode": "roka",
            "model_provider": "moa",
            "model": "roka",
        },
    }

    try:
        background_review._resolve_review_runtime(parent, task_cfg)
    except RuntimeError as exc:
        assert "concrete direct executor route" in str(exc)
    else:
        raise AssertionError("ROKA review must not recursively enter MoA")


def test_staged_background_learning_is_reported_as_pending_approval():
    review_messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-memory",
                    "function": {
                        "name": "memory",
                        "arguments": '{"action":"add","target":"memory",'
                        '"content":"candidate"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call-memory",
            "content": (
                '{"success":true,"saved":false,"staged":true,'
                '"requires_approval":true,"pending_id":"abc123",'
                '"message":"Staged for approval."}'
            ),
        },
    ]

    actions = background_review.summarize_background_review_actions(
        review_messages,
        [],
        notification_mode="on",
    )

    assert actions == ["Memory proposal pending approval (abc123)"]
