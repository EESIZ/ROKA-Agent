from types import SimpleNamespace


def test_tool_middleware_binds_roka_provenance_only_during_dispatch(monkeypatch):
    from agent import relay_tools, tool_executor
    from agent.roka_control import current_execution_metadata

    monkeypatch.setattr(
        "hermes_cli.middleware.apply_tool_request_middleware",
        lambda _name, args, **_kwargs: SimpleNamespace(payload=args, trace=[]),
    )
    monkeypatch.setattr(
        "hermes_cli.middleware.run_tool_execution_middleware",
        lambda _name, args, callback, **_kwargs: callback(args),
    )
    monkeypatch.setattr(
        "hermes_cli.plugins._dispatch_pre_tool_call_hooks",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(tool_executor, "_begin_tool_execution", lambda *_a, **_k: None)
    monkeypatch.setattr(
        relay_tools,
        "execute",
        lambda _name, args, callback, **_kwargs: (callback(args), args),
    )

    guardrails = SimpleNamespace(
        before_call=lambda _name, _args: SimpleNamespace(allows_execution=True)
    )
    agent = SimpleNamespace(
        session_id="parent-session",
        provider="moa",
        model="roka",
        _roka_control_mode="roka",
        _execution_brief_id="brief-1",
        _agent_session_id="executor-session",
        _agent_role="executor",
        _roka_model_provider="fake",
        _roka_model="executor-model",
        _tool_guardrails=guardrails,
        _turns_since_memory=1,
        _iters_since_skill=1,
        _touch_activity=lambda _label: None,
    )
    captured = {}

    outcome = tool_executor._run_agent_tool_execution_middleware(
        agent,
        function_name="terminal",
        function_args={"command": "echo ok"},
        effective_task_id="task-1",
        tool_call_id="call-1",
        execute=lambda _args: captured.update(current_execution_metadata()) or "ok",
    )

    assert outcome.result == "ok"
    assert captured["control_mode"] == "roka"
    assert captured["brief_id"] == "brief-1"
    assert captured["agent_session_id"] == "executor-session"
    assert captured["task_id"] == "task-1"
    assert captured["tool_call_id"] == "call-1"
    assert current_execution_metadata() == {}


def test_roka_tool_middleware_blocks_new_subagent_spawn(monkeypatch):
    from agent import relay_tools, tool_executor

    monkeypatch.setattr(
        "hermes_cli.middleware.apply_tool_request_middleware",
        lambda _name, args, **_kwargs: SimpleNamespace(payload=args, trace=[]),
    )
    monkeypatch.setattr(
        "hermes_cli.middleware.run_tool_execution_middleware",
        lambda _name, args, callback, **_kwargs: callback(args),
    )
    monkeypatch.setattr(
        relay_tools,
        "execute",
        lambda _name, args, callback, **_kwargs: (callback(args), args),
    )
    monkeypatch.setattr(
        tool_executor,
        "_emit_terminal_post_tool_call",
        lambda *_args, **_kwargs: None,
    )

    agent = SimpleNamespace(
        session_id="parent-session",
        _roka_control_mode="roka",
        _tool_guardrails=SimpleNamespace(
            before_call=lambda _name, _args: SimpleNamespace(allows_execution=True)
        ),
    )
    dispatched = []

    outcome = tool_executor._run_agent_tool_execution_middleware(
        agent,
        function_name="delegate_task",
        function_args={"action": "spawn", "task": "work outside the brief"},
        effective_task_id="task-1",
        tool_call_id="call-1",
        execute=lambda args: dispatched.append(args) or "unexpected",
    )

    assert dispatched == []
    assert "ROKA blocks new subagent delegation" in outcome.result
