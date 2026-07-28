import sys
from types import ModuleType

import brain
import openai


def _clear_provider_env(monkeypatch):
    for name in (
        "LLM_PROVIDER",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_USE_MANAGED_IDENTITY",
        "AZURE_OPENAI_TOKEN_SCOPE",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_FAST",
        "AZURE_OPENAI_DEPLOYMENT_SMART",
        "AZURE_OPENAI_MODEL_FAMILY",
        "AZURE_OPENAI_MODEL_FAMILY_FAST",
        "AZURE_OPENAI_MODEL_FAMILY_SMART",
        "AZURE_OPENAI_REASONING_EFFORT",
        "AZURE_OPENAI_REASONING_EFFORT_FAST",
        "AZURE_OPENAI_REASONING_EFFORT_SMART",
        "AZURE_CLIENT_ID",
        "APP_ENV",
        "DEPLOYMENT_TENANCY",
        "ONPREM_LLM_BASE_URL",
        "ONPREM_LLM_ALLOWED_HOSTS",
        "ONPREM_LLM_API_KEY",
        "ONPREM_LLM_CA_BUNDLE",
        "ONPREM_LLM_CLIENT_CERT",
        "ONPREM_LLM_CLIENT_KEY",
        "ONPREM_LLM_MODEL",
        "ONPREM_LLM_MODEL_FAST",
        "ONPREM_LLM_MODEL_SMART",
        "OPENAI_COMPATIBLE_BASE_URL",
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_COMPATIBLE_MODEL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_ENV", "test")


def test_azure_is_the_default_provider(monkeypatch):
    _clear_provider_env(monkeypatch)
    assert brain._configured_provider({}) == "azure"


def test_azure_api_key_builds_openai_compatible_client(monkeypatch):
    _clear_provider_env(monkeypatch)
    captured = {}
    sentinel = object()
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://agent.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {
            "model_provider": "azure",
            "model_azure_smart": "agent-smart",
            "max_retries": 1,
        },
    )

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(openai, "OpenAI", fake_openai)

    client, model, provider = brain._get_client(model="claude-haiku-4-5")

    assert client is sentinel
    assert model == "agent-smart"
    assert provider == "azure"
    assert captured == {
        "api_key": "test-key",
        "base_url": "https://agent.openai.azure.com/openai/v1/",
        "max_retries": 1,
    }


def test_azure_managed_identity_uses_token_provider(monkeypatch):
    _clear_provider_env(monkeypatch)
    captured = {}
    sentinel = object()
    credential = object()
    token_provider = object()
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://agent.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_USE_MANAGED_IDENTITY", "true")
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {"model_provider": "azure", "model_azure_smart": "agent-smart"},
    )

    azure_module = ModuleType("azure")
    identity_module = ModuleType("azure.identity")
    identity_module.DefaultAzureCredential = lambda: credential

    def fake_token_provider(actual_credential, scope):
        assert actual_credential is credential
        assert scope == "https://ai.azure.com/.default"
        return token_provider

    identity_module.get_bearer_token_provider = fake_token_provider
    azure_module.identity = identity_module
    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.identity", identity_module)

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(openai, "OpenAI", fake_openai)

    client, model, provider = brain._get_client()

    assert (client, model, provider) == (sentinel, "agent-smart", "azure")
    assert captured["api_key"] is token_provider
    assert captured["base_url"] == "https://agent.openai.azure.com/openai/v1/"


def test_generic_azure_deployment_env_overrides_specific_config(monkeypatch):
    _clear_provider_env(monkeypatch)
    sentinel = object()
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://agent.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "env-deployment")
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {
            "model_provider": "azure",
            "model_azure_smart": "config-deployment",
        },
    )
    monkeypatch.setattr(openai, "OpenAI", lambda **_: sentinel)

    assert brain._get_client() == (sentinel, "env-deployment", "azure")


def test_azure_rejects_non_azure_endpoint(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {"model_provider": "azure", "model_azure_smart": "agent-smart"},
    )

    assert brain._get_client() == (None, None, "fallback")


def test_invalid_endpoint_never_raises(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://[bad")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {"model_provider": "azure", "model_azure_smart": "agent-smart"},
    )

    assert brain._get_client() == (None, None, "fallback")


def test_azure_production_rejects_api_key(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://agent.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {"model_provider": "azure", "model_azure_smart": "agent-smart"},
    )

    assert brain._get_client() == (None, None, "fallback")


def test_azure_production_uses_managed_identity_only(monkeypatch):
    _clear_provider_env(monkeypatch)
    captured = {}
    sentinel = object()
    credential = object()
    token_provider = object()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AZURE_CLIENT_ID", "managed-identity-client")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://agent.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_USE_MANAGED_IDENTITY", "true")
    monkeypatch.setattr(
        brain,
        "_load_config",
        lambda: {"model_provider": "azure", "model_azure_smart": "agent-smart"},
    )

    azure_module = ModuleType("azure")
    identity_module = ModuleType("azure.identity")

    def fake_managed_identity(*, client_id):
        assert client_id == "managed-identity-client"
        return credential

    identity_module.ManagedIdentityCredential = fake_managed_identity

    def fake_token_provider(actual_credential, scope):
        assert actual_credential is credential
        assert scope == "https://ai.azure.com/.default"
        return token_provider

    identity_module.get_bearer_token_provider = fake_token_provider
    azure_module.identity = identity_module
    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.identity", identity_module)

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(openai, "OpenAI", fake_openai)

    client, model, provider = brain._get_client()

    assert (client, model, provider) == (sentinel, "agent-smart", "azure")
    assert captured["api_key"] is token_provider


def test_onprem_loopback_allows_http_without_secret(monkeypatch):
    _clear_provider_env(monkeypatch)
    captured = {}
    sentinel = object()
    monkeypatch.setenv("LLM_PROVIDER", "onprem")
    monkeypatch.setenv("ONPREM_LLM_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("ONPREM_LLM_MODEL", "local-controller")
    monkeypatch.setattr(brain, "_load_config", lambda: {})

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(openai, "OpenAI", fake_openai)

    client, model, provider = brain._get_client()

    assert (client, model, provider) == (sentinel, "local-controller", "onprem")
    assert captured["base_url"] == "http://127.0.0.1:8000/v1/"
    assert captured["api_key"] == "local-only"


def test_onprem_remote_https_requires_isolation_and_allowlist(monkeypatch):
    _clear_provider_env(monkeypatch)
    captured = {}
    sentinel = object()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LLM_PROVIDER", "onprem")
    monkeypatch.setenv("DEPLOYMENT_TENANCY", "isolated")
    monkeypatch.setenv("ONPREM_LLM_BASE_URL", "https://llm.customer.example/v1")
    monkeypatch.setenv("ONPREM_LLM_ALLOWED_HOSTS", "llm.customer.example")
    monkeypatch.setenv("ONPREM_LLM_API_KEY", "customer-secret")
    monkeypatch.setenv("ONPREM_LLM_MODEL", "local-controller")
    monkeypatch.setattr(brain, "_load_config", lambda: {})

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(openai, "OpenAI", fake_openai)

    client, model, provider = brain._get_client()

    assert (client, model, provider) == (sentinel, "local-controller", "onprem")
    assert captured["base_url"] == "https://llm.customer.example/v1/"
    assert captured["api_key"] == "customer-secret"


def test_onprem_remote_is_blocked_in_shared_deployment(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "onprem")
    monkeypatch.setenv("DEPLOYMENT_TENANCY", "shared")
    monkeypatch.setenv("ONPREM_LLM_BASE_URL", "https://llm.customer.example/v1")
    monkeypatch.setenv("ONPREM_LLM_ALLOWED_HOSTS", "llm.customer.example")
    monkeypatch.setenv("ONPREM_LLM_API_KEY", "customer-secret")
    monkeypatch.setenv("ONPREM_LLM_MODEL", "local-controller")
    monkeypatch.setattr(brain, "_load_config", lambda: {})

    assert brain._get_client() == (None, None, "fallback")


def test_onprem_rejects_cloud_metadata_address(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "onprem")
    monkeypatch.setenv("DEPLOYMENT_TENANCY", "isolated")
    monkeypatch.setenv("ONPREM_LLM_BASE_URL", "https://169.254.169.254/v1")
    monkeypatch.setenv("ONPREM_LLM_ALLOWED_HOSTS", "169.254.169.254")
    monkeypatch.setenv("ONPREM_LLM_API_KEY", "customer-secret")
    monkeypatch.setenv("ONPREM_LLM_MODEL", "local-controller")
    monkeypatch.setattr(brain, "_load_config", lambda: {})

    assert brain._get_client() == (None, None, "fallback")


def test_onprem_remote_http_fails_closed_without_public_fallback(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "onprem")
    monkeypatch.setenv("ONPREM_LLM_BASE_URL", "http://10.0.0.5:8000/v1")
    monkeypatch.setenv("ONPREM_LLM_MODEL", "local-controller")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(brain, "_load_config", lambda: {})

    assert brain._get_client() == (None, None, "fallback")


def test_onprem_remote_https_requires_its_own_secret(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "onprem")
    monkeypatch.setenv("ONPREM_LLM_BASE_URL", "https://llm.customer.example/v1")
    monkeypatch.setenv("ONPREM_LLM_MODEL", "local-controller")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(brain, "_load_config", lambda: {})

    assert brain._get_client() == (None, None, "fallback")


def test_unknown_provider_fails_closed(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(brain, "_load_config", lambda: {})

    assert brain._get_client() == (None, None, "fallback")


def test_missing_app_env_fails_closed(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.delenv("APP_ENV")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(brain, "_load_config", lambda: {"model": "gpt-4.1-mini"})

    assert brain._get_client() == (None, None, "fallback")


def test_legacy_key_without_provider_requires_explicit_migration(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(brain, "_load_config", lambda: {"model": "gpt-4.1-mini"})

    assert brain._get_client() == (None, None, "fallback")


def test_production_blocks_legacy_public_provider(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setattr(brain, "_load_config", lambda: {"model": "gpt-4.1-mini"})

    assert brain._get_client() == (None, None, "fallback")
