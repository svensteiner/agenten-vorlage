from types import SimpleNamespace

import brain


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
