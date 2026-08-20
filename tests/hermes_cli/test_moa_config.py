import pytest
from types import SimpleNamespace

from agent.errors import MoAPresetNotFoundError
from hermes_cli.moa_config import (
    DEFAULT_MOA_AGGREGATOR,
    DEFAULT_MOA_PRESET_NAME,
    DEFAULT_MOA_REFERENCE_MODELS,
    build_moa_turn_prompt,
    decode_moa_turn,
    exact_moa_preset_name,
    normalize_moa_config,
    resolve_moa_preset,
    set_active_moa_preset,
)


def test_moa_slot_picker_excludes_unconfigured_providers(monkeypatch):
    from hermes_cli import moa_cmd

    captured = {}
    monkeypatch.setattr(moa_cmd, "load_picker_context", lambda: object())

    def fake_build(_context, **kwargs):
        captured.update(kwargs)
        return {
            "providers": [
                {"slug": "moa", "models": ["default"]},
                {"slug": "opencode-go", "models": ["deepseek-v4-pro"]},
            ]
        }

    monkeypatch.setattr(moa_cmd, "build_models_payload", fake_build)

    assert [row["slug"] for row in moa_cmd._model_options()] == ["opencode-go"]
    assert captured["include_unconfigured"] is False


def _enabled_refs(refs):
    return [{**slot, "enabled": True} for slot in refs]


def test_normalize_moa_config_uses_default_named_preset():
    cfg = normalize_moa_config({})

    assert cfg["default_preset"] == DEFAULT_MOA_PRESET_NAME
    assert list(cfg["presets"]) == [DEFAULT_MOA_PRESET_NAME]
    assert cfg["reference_models"] == _enabled_refs(DEFAULT_MOA_REFERENCE_MODELS)
    assert cfg["aggregator"] == DEFAULT_MOA_AGGREGATOR








def test_exact_preset_matching_skips_disabled_presets():
    """A disabled preset must not match the implicit bare-name switch path.

    Regression for #55187: with ``enabled: false`` presets, a plain model
    switch whose name collides with a preset key (e.g. ``default``) silently
    pivoted the session onto the MoA virtual provider. The per-preset
    ``enabled`` opt-out must gate this implicit match.
    """
    config = {
        "presets": {
            "default": {"enabled": False},
            "klo": {"enabled": False},
        },
    }
    assert exact_moa_preset_name(config, "default") is None
    assert exact_moa_preset_name(config, "klo") is None






def test_resolve_missing_moa_preset_has_actionable_error():
    cfg = {
        "default_preset": "日常对话-高峰",
        "presets": {"日常对话-高峰": {}, "日常对话-非高峰": {}},
    }

    with pytest.raises(MoAPresetNotFoundError) as exc_info:
        resolve_moa_preset(cfg, "日常对话-高峰期")

    message = str(exc_info.value)
    assert "日常对话-高峰期" in message
    assert "日常对话-高峰" in message
    assert "日常对话-非高峰" in message
    assert "hermes moa list" in message


def test_missing_moa_preset_is_non_retryable():
    from agent.error_classifier import FailoverReason, classify_api_error

    result = classify_api_error(
        MoAPresetNotFoundError("MoA preset 'old' was not found"),
        provider="moa",
        model="old",
    )

    assert result.reason == FailoverReason.model_not_found
    assert result.retryable is False
    assert result.should_fallback is False








def _preset(**extra):
    base = {
        "reference_models": [{"provider": "openrouter", "model": "anthropic/claude-opus-4.8"}],
        "aggregator": {"provider": "openrouter", "model": "anthropic/claude-opus-4.8"},
    }
    base.update(extra)
    return {"default_preset": "p", "presets": {"p": base}}






# ── validate_moa_payload (write-boundary validation, #64156) ─────────────────
#
# normalize_moa_config is deliberately tolerant at READ time (hand-edited
# configs degrade to defaults). validate_moa_payload is the strict WRITE-time
# counterpart: it must flag exactly the payloads normalize would silently
# repair, so API save paths reject them instead of corrupting user config.


def _valid_preset_payload():
    return {
        "reference_models": [{"provider": "openrouter", "model": "deepseek/deepseek-v4-pro"}],
        "aggregator": {"provider": "openrouter", "model": "anthropic/claude-opus-4.8"},
    }




def test_validate_moa_payload_agrees_with_clean_slot():
    """Contract: a payload validate accepts must survive normalize UNCHANGED in
    its slots — validate and _clean_slot can never disagree (else a payload
    could pass validation and still be swapped for defaults)."""
    from hermes_cli.moa_config import validate_moa_payload

    payload = {"presets": {"p": _valid_preset_payload()}}
    assert validate_moa_payload(payload) == []

    cfg = normalize_moa_config(payload)
    # Slots survive with only the canonical enabled=True default added — no
    # provider/model swap, no defaults substitution.
    assert cfg["presets"]["p"]["reference_models"] == _enabled_refs(payload["presets"]["p"]["reference_models"])
    assert cfg["presets"]["p"]["aggregator"] == payload["presets"]["p"]["aggregator"]


def test_roka_preset_validation_and_normalization_preserve_role_contract():
    from hermes_cli.moa_config import validate_moa_payload

    preset = {
        "control_mode": "roka",
        "reference_models": [
            {"provider": "fake", "model": "intent", "advisor_role": "intent_analyst"},
            {
                "provider": "fake",
                "model": "constraints",
                "advisor_role": "constraint_reviewer",
            },
            {
                "provider": "fake",
                "model": "verification",
                "advisor_role": "verification_reviewer",
            },
        ],
        "aggregator": {"provider": "fake", "model": "executor"},
    }
    payload = {"default_preset": "roka", "presets": {"roka": preset}}

    assert validate_moa_payload(payload) == []
    normalized_config = normalize_moa_config(payload)
    assert normalized_config["control_mode"] == "roka"
    normalized = normalized_config["presets"]["roka"]
    assert normalized["control_mode"] == "roka"
    assert [
        slot["advisor_role"] for slot in normalized["reference_models"]
    ] == [
        "intent_analyst",
        "constraint_reviewer",
        "verification_reviewer",
    ]


def test_shipped_roka_default_is_a_valid_four_route_control_preset():
    from hermes_cli.config_defaults import DEFAULT_CONFIG
    from hermes_cli.moa_config import validate_moa_payload

    moa = DEFAULT_CONFIG["moa"]
    assert moa["default_preset"] == "roka"
    assert validate_moa_payload(moa) == []
    roka = normalize_moa_config(moa)["presets"]["roka"]
    assert roka["control_mode"] == "roka"
    assert len(roka["reference_models"]) == 3
    assert roka["aggregator"]["provider"] != "moa"


def test_roka_preset_rejects_duplicate_or_missing_advisor_roles():
    from hermes_cli.moa_config import validate_moa_payload

    payload = {
        "presets": {
            "broken": {
                "control_mode": "roka",
                "reference_models": [
                    {
                        "provider": "fake",
                        "model": "one",
                        "advisor_role": "intent_analyst",
                    },
                    {
                        "provider": "fake",
                        "model": "two",
                        "advisor_role": "constraint_reviewer",
                    },
                    {
                        "provider": "fake",
                        "model": "three",
                        "advisor_role": "constraint_reviewer",
                    },
                ],
                "aggregator": {"provider": "fake", "model": "executor"},
            }
        }
    }

    problems = validate_moa_payload(payload)
    assert any("exactly three enabled references with unique roles" in item for item in problems)


def test_cli_reconfigure_preserves_fixed_roka_role_slots(monkeypatch):
    from hermes_cli import moa_cmd

    config = {
        "moa": {
            "default_preset": "roka",
            "presets": {
                "roka": {
                    "control_mode": "roka",
                    "reference_models": [
                        {
                            "provider": "old",
                            "model": "intent",
                            "advisor_role": "intent_analyst",
                        },
                        {
                            "provider": "old",
                            "model": "constraints",
                            "advisor_role": "constraint_reviewer",
                        },
                        {
                            "provider": "old",
                            "model": "verification",
                            "advisor_role": "verification_reviewer",
                        },
                    ],
                    "aggregator": {"provider": "old", "model": "executor"},
                }
            },
        }
    }
    selections = iter(
        [
            {"provider": "new", "model": "intent-2"},
            {"provider": "new", "model": "constraints-2"},
            {"provider": "new", "model": "verification-2"},
            {"provider": "new", "model": "executor-2"},
        ]
    )
    saved = {}
    monkeypatch.setattr(moa_cmd, "load_config", lambda: config)
    monkeypatch.setattr(moa_cmd, "_pick_slot", lambda _current=None: next(selections))
    monkeypatch.setattr(moa_cmd, "save_config", lambda cfg: saved.update(cfg))
    monkeypatch.setattr(moa_cmd, "_print_config", lambda _cfg: None)

    moa_cmd.cmd_moa(SimpleNamespace(moa_command="configure", name="roka"))

    preset = saved["moa"]["presets"]["roka"]
    assert preset["control_mode"] == "roka"
    assert [slot["advisor_role"] for slot in preset["reference_models"]] == [
        "intent_analyst",
        "constraint_reviewer",
        "verification_reviewer",
    ]
    assert all(slot["enabled"] for slot in preset["reference_models"])


# ── Per-slot max_tokens ────────────────────────────────────────────────────






# --- fanout cadence normalization (every_n) ---








# --- privacy_filter normalization ---


