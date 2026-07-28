from types import SimpleNamespace

import brain
import pytest


class _Completions:
    def __init__(self):
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=2, completion_tokens=1),
        )


def _client():
    completions = _Completions()
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_gpt5_nano_request_uses_current_token_limit_and_minimal_reasoning(monkeypatch):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "gpt-5-nano", "openai"),
    )

    assert brain.complete("system", "user", max_tokens=123) == "ok"

    assert completions.request["max_completion_tokens"] == 123
    assert completions.request["reasoning_effort"] == "minimal"
    assert "max_tokens" not in completions.request
    assert "temperature" not in completions.request


def test_gpt56_request_disables_reasoning_for_routine_low_cost_work(monkeypatch):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "gpt-5.6-luna", "openai"),
    )

    assert brain.complete("system", "user", max_tokens=50) == "ok"

    assert completions.request["max_completion_tokens"] == 50
    assert completions.request["reasoning_effort"] == "none"


def test_legacy_chat_model_keeps_supported_sampling_parameters(monkeypatch):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "gpt-4o-mini", "openai"),
    )

    assert brain.complete("system", "user", temperature=0.2, max_tokens=77) == "ok"

    assert completions.request["max_tokens"] == 77
    assert completions.request["temperature"] == 0.2
    assert "max_completion_tokens" not in completions.request


def test_azure_uses_the_openai_compatible_request_path(monkeypatch):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "gpt-4.1-mini", "azure"),
    )

    assert brain.complete("system", "user", max_tokens=77) == "ok"

    assert completions.request["model"] == "gpt-4.1-mini"
    assert completions.request["max_tokens"] == 77


def test_azure_uses_explicit_model_family_not_deployment_name(monkeypatch):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "agent-smart", "azure"),
    )
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {
            "model_azure_family_smart": "gpt-5.6",
            "model_azure_reasoning_effort_smart": "none",
        },
    )

    assert brain.complete("system", "user", max_tokens=77) == "ok"

    assert completions.request["model"] == "agent-smart"
    assert completions.request["max_completion_tokens"] == 77
    assert completions.request["reasoning_effort"] == "none"
    assert "temperature" not in completions.request


@pytest.mark.parametrize("family", ["gpt-5.1", "gpt-5-pro"])
def test_azure_does_not_guess_reasoning_effort(monkeypatch, family):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "agent-reasoning", "azure"),
    )
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {"model_azure_family_smart": family},
    )

    assert brain.complete("system", "user", max_tokens=77) == "ok"

    assert completions.request["max_completion_tokens"] == 77
    assert "reasoning_effort" not in completions.request


def test_azure_gpt5_pro_accepts_explicit_high_effort(monkeypatch):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "agent-pro", "azure"),
    )
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {
            "model_azure_family_smart": "gpt-5-pro",
            "model_azure_reasoning_effort_smart": "high",
        },
    )

    assert brain.complete("system", "user", max_tokens=77) == "ok"

    assert completions.request["reasoning_effort"] == "high"


def test_onprem_does_not_receive_openai_reasoning_parameters(monkeypatch):
    client, completions = _client()
    monkeypatch.setattr(
        brain,
        "_get_client",
        lambda **_: (client, "gpt-5-local", "onprem"),
    )

    assert brain.complete("system", "user", max_tokens=77) == "ok"

    assert completions.request["max_tokens"] == 77
    assert "reasoning_effort" not in completions.request
