"""Brain — LLM-Intelligenz-Layer.

Lädt SOUL.md als System-Kontext und stellt 4 Kern-Funktionen bereit:
  think()    → Aufgabe verstehen + Plan erstellen
  act()      → Tool ausführen + Ergebnis bewerten
  reflect()  → Aus Ergebnis lernen
  evaluate() → Output-Qualität prüfen (1-10 Score)

LLM-Kette: OpenAI → Anthropic → Keyword-Fallback
"""

import ipaddress
import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("brain")

SOUL_PATH = Path(__file__).parent / "SOUL.md"
CONFIG_PATH = Path(__file__).parent / "config.json"

_session_usage: dict = {
    "calls": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_tokens": 0,
    "cache_write_tokens": 0,
}

_PROVIDER_ALIASES = {
    "azure_foundry": "azure",
    "openai_compatible": "onprem",
    "self_hosted": "onprem",
}
_SUPPORTED_PROVIDERS = {"azure", "onprem", "openai", "anthropic", "auto"}
_AZURE_HOST_SUFFIXES = (
    ".openai.azure.com",
    ".services.ai.azure.com",
    ".cognitiveservices.azure.com",
)
_AZURE_TOKEN_SCOPE = "https://ai.azure.com/.default"
_ALLOWED_APP_ENVS = {"development", "test", "production"}
_ALLOWED_REASONING_EFFORTS = {
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
}


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def _load_soul() -> str:
    if SOUL_PATH.exists():
        return SOUL_PATH.read_text(encoding="utf-8")
    return "Du bist ein autonomer KI-Agent. Handle verantwortungsbewusst."


def _provider_for_model(model: str | None) -> str | None:
    """Return the required provider for known model families, if any."""
    normalized = (model or "").strip().lower()
    if normalized.startswith("claude"):
        return "anthropic"
    if normalized.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    return None


def _configured_provider(cfg: dict) -> str | None:
    """Resolve the provider without silently changing the trust boundary."""
    app_env = _app_env()
    if app_env is None:
        logger.error(
            "LLM-Aufruf gesperrt: APP_ENV muss development, test oder production sein"
        )
        return None

    configured_value = os.getenv("LLM_PROVIDER") or cfg.get("model_provider")
    if not configured_value and (
        os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    ):
        logger.error(
            "LLM-Aufruf gesperrt: Alt-Konfiguration erkannt; LLM_PROVIDER explizit setzen"
        )
        return None
    raw = str(configured_value or "azure")
    provider = _PROVIDER_ALIASES.get(raw.strip().lower(), raw.strip().lower())
    if provider not in _SUPPORTED_PROVIDERS:
        logger.error("Unbekannter LLM-Provider '%s' - Modellaufruf gesperrt", provider)
        return None
    if app_env == "production" and provider in {"auto", "openai", "anthropic"}:
        logger.error(
            "LLM-Provider '%s' ist im Produktionsmodus nicht freigegeben",
            provider,
        )
        return None
    return provider


def _model_for_provider(
    provider: str,
    cfg: dict,
    *,
    use_fast: bool,
    override: str | None,
) -> str | None:
    if override and provider not in {"azure", "onprem"}:
        return override

    if provider == "azure":
        env_name = (
            "AZURE_OPENAI_DEPLOYMENT_FAST"
            if use_fast
            else "AZURE_OPENAI_DEPLOYMENT_SMART"
        )
        config_name = "model_azure_fast" if use_fast else "model_azure_smart"
        return (
            os.getenv(env_name)
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or cfg.get(config_name)
            or cfg.get("model_azure")
            or cfg.get("model")
        )

    if provider == "onprem":
        env_name = "ONPREM_LLM_MODEL_FAST" if use_fast else "ONPREM_LLM_MODEL_SMART"
        config_name = "model_onprem_fast" if use_fast else "model_onprem_smart"
        return (
            os.getenv(env_name)
            or os.getenv("ONPREM_LLM_MODEL")
            or os.getenv("OPENAI_COMPATIBLE_MODEL")
            or cfg.get(config_name)
            or cfg.get("model_onprem")
        )

    if provider == "anthropic":
        default = cfg.get("model_anthropic", "claude-haiku-4-5-20251001")
        config_name = "model_anthropic_fast" if use_fast else "model_anthropic_smart"
        return cfg.get(config_name, default)

    default = cfg.get("model", "gpt-5-nano")
    config_name = "model_fast" if use_fast else "model_smart"
    return cfg.get(config_name, default)


def _request_model_family(
    provider: str,
    selected_model: str | None,
    cfg: dict,
    *,
    use_fast: bool,
) -> str:
    """Return model capabilities separately from Azure deployment names."""
    if provider != "azure":
        return str(selected_model or "")
    env_name = (
        "AZURE_OPENAI_MODEL_FAMILY_FAST"
        if use_fast
        else "AZURE_OPENAI_MODEL_FAMILY_SMART"
    )
    config_name = (
        "model_azure_family_fast"
        if use_fast
        else "model_azure_family_smart"
    )
    return str(
        os.getenv(env_name)
        or os.getenv("AZURE_OPENAI_MODEL_FAMILY")
        or cfg.get(config_name)
        or cfg.get("model_azure_family")
        or selected_model
        or ""
    )


def _azure_reasoning_effort(cfg: dict, *, use_fast: bool) -> str | None:
    """Return an explicitly configured effort; never guess from a model name."""
    env_name = (
        "AZURE_OPENAI_REASONING_EFFORT_FAST"
        if use_fast
        else "AZURE_OPENAI_REASONING_EFFORT_SMART"
    )
    config_name = (
        "model_azure_reasoning_effort_fast"
        if use_fast
        else "model_azure_reasoning_effort_smart"
    )
    value = str(
        os.getenv(env_name)
        or os.getenv("AZURE_OPENAI_REASONING_EFFORT")
        or cfg.get(config_name)
        or cfg.get("model_azure_reasoning_effort")
        or ""
    ).strip().lower()
    if not value:
        return None
    if value not in _ALLOWED_REASONING_EFFORTS:
        raise ValueError("ungueltiger Azure reasoning effort")
    return value


def _app_env() -> str | None:
    value = os.getenv("APP_ENV", "").strip().lower()
    return value if value in _ALLOWED_APP_ENVS else None


def _is_production() -> bool:
    return _app_env() == "production"


def _is_development() -> bool:
    return _app_env() in {"development", "test"}


def _azure_base_url(endpoint: str) -> str | None:
    value = endpoint.strip().rstrip("/")
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return None
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not hostname
        or not hostname.endswith(_AZURE_HOST_SUFFIXES)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or port not in {None, 443}
        or parsed.path not in {"", "/", "/openai/v1", "/openai/v1/"}
    ):
        return None
    if value.endswith("/openai/v1"):
        return value + "/"
    return value + "/openai/v1/"


def _is_loopback_url(endpoint: str) -> bool:
    try:
        parsed = urlparse(endpoint)
    except ValueError:
        return False
    host = (parsed.hostname or "").strip().lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _azure_client(cfg: dict):
    base_url = _azure_base_url(os.getenv("AZURE_OPENAI_ENDPOINT", ""))
    if not base_url:
        logger.error(
            "Azure-LLM gesperrt: AZURE_OPENAI_ENDPOINT muss eine HTTPS-URL sein"
        )
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.error("Azure-LLM gesperrt: Python-Paket 'openai' fehlt")
        return None

    production = _is_production()
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    if api_key and not _is_development():
        logger.error("Azure-LLM gesperrt: API-Key ist nur in Entwicklung erlaubt")
        return None
    if api_key:
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=int(cfg.get("max_retries", 2)),
        )

    managed_identity = os.getenv(
        "AZURE_OPENAI_USE_MANAGED_IDENTITY",
        "true",
    ).strip().lower()
    if managed_identity not in {"1", "true", "yes", "on"}:
        logger.error(
            "Azure-LLM gesperrt: weder API-Key noch Managed Identity aktiviert"
        )
        return None

    try:
        from azure.identity import get_bearer_token_provider

        credential: Any
        if production:
            from azure.identity import ManagedIdentityCredential

            client_id = os.getenv("AZURE_CLIENT_ID", "").strip() or None
            credential = ManagedIdentityCredential(client_id=client_id)
        else:
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
    except ImportError:
        logger.error("Azure-LLM gesperrt: Python-Paket 'azure-identity' fehlt")
        return None

    token_provider = get_bearer_token_provider(credential, _AZURE_TOKEN_SCOPE)
    return OpenAI(
        api_key=token_provider,
        base_url=base_url,
        max_retries=int(cfg.get("max_retries", 2)),
    )


def _onprem_client(cfg: dict):
    endpoint = (
        os.getenv("ONPREM_LLM_BASE_URL")
        or os.getenv("OPENAI_COMPATIBLE_BASE_URL")
        or ""
    ).strip()
    try:
        parsed = urlparse(endpoint)
    except ValueError:
        logger.error("Kunden-LLM gesperrt: ONPREM_LLM_BASE_URL ist ungueltig")
        return None
    hostname = (parsed.hostname or "").strip().lower()
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        logger.error(
            "Kunden-LLM gesperrt: ONPREM_LLM_BASE_URL fehlt oder ist ungueltig"
        )
        return None
    loopback = _is_loopback_url(endpoint)
    if parsed.scheme != "https" and not loopback:
        logger.error("Kunden-LLM gesperrt: Remote-Endpunkte muessen HTTPS verwenden")
        return None
    if loopback and _is_production():
        logger.error("Kunden-LLM gesperrt: Loopback ist in Produktion nicht erlaubt")
        return None

    if not loopback:
        if os.getenv("DEPLOYMENT_TENANCY", "").strip().lower() != "isolated":
            logger.error(
                "Kunden-LLM gesperrt: Remote-Betrieb erfordert DEPLOYMENT_TENANCY=isolated"
            )
            return None
        allowed_hosts = {
            item.strip().lower()
            for item in os.getenv("ONPREM_LLM_ALLOWED_HOSTS", "").split(",")
            if item.strip()
        }
        if hostname not in allowed_hosts:
            logger.error(
                "Kunden-LLM gesperrt: Endpunkt steht nicht in ONPREM_LLM_ALLOWED_HOSTS"
            )
            return None
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address and (
            address.is_link_local
            or address.is_loopback
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            logger.error("Kunden-LLM gesperrt: unzulaessige Zieladresse")
            return None

    api_key = (
        os.getenv("ONPREM_LLM_API_KEY")
        or os.getenv("OPENAI_COMPATIBLE_API_KEY")
        or ""
    ).strip()
    ca_bundle = os.getenv("ONPREM_LLM_CA_BUNDLE", "").strip()
    client_cert = os.getenv("ONPREM_LLM_CLIENT_CERT", "").strip()
    client_key = os.getenv("ONPREM_LLM_CLIENT_KEY", "").strip()
    if bool(client_cert) != bool(client_key):
        logger.error("Kunden-LLM gesperrt: mTLS braucht Zertifikat und Schluessel")
        return None
    if not api_key and not loopback and not (client_cert and client_key):
        logger.error("Kunden-LLM gesperrt: Remote-Endpunkte brauchen API-Key oder mTLS")
        return None

    try:
        import httpx
        from openai import OpenAI
    except ImportError:
        logger.error("Kunden-LLM gesperrt: Python-Paket 'openai' oder 'httpx' fehlt")
        return None

    http_client = None
    if ca_bundle or client_cert:
        verify: bool | str = ca_bundle or True
        cert = (client_cert, client_key) if client_cert else None
        try:
            http_client = httpx.Client(verify=verify, cert=cert)
        except (OSError, ValueError):
            logger.error("Kunden-LLM gesperrt: TLS-Dateien sind ungueltig")
            return None

    return OpenAI(
        api_key=api_key or ("mtls-auth" if client_cert else "local-only"),
        base_url=endpoint.rstrip("/") + "/",
        max_retries=int(cfg.get("max_retries", 2)),
        http_client=http_client,
    )


def _get_client(use_fast: bool = False, model: str | None = None):
    """Return the client selected for the configured trust boundary.

    An explicit provider never falls through to another provider.
    """
    cfg = _load_config()
    configured = _configured_provider(cfg)
    if configured is None:
        return None, None, "fallback"

    providers = [configured]
    if configured == "auto":
        required_provider = _provider_for_model(model)
        providers = [required_provider] if required_provider else ["openai", "anthropic"]

    for provider in providers:
        selected_model = _model_for_provider(
            provider,
            cfg,
            use_fast=use_fast,
            override=model,
        )
        if not selected_model:
            logger.error(
                "LLM-Aufruf gesperrt: fuer Provider '%s' ist kein Modell konfiguriert",
                provider,
            )
            continue

        if provider == "azure":
            client = _azure_client(cfg)
            if client is not None:
                return client, selected_model, provider
            continue

        if provider == "onprem":
            client = _onprem_client(cfg)
            if client is not None:
                return client, selected_model, provider
            continue

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if api_key:
                try:
                    from openai import OpenAI

                    client = OpenAI(
                        api_key=api_key,
                        max_retries=int(cfg.get("max_retries", 2)),
                    )
                    return client, selected_model, provider
                except ImportError:
                    pass
            continue

        if provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            if api_key:
                try:
                    import anthropic

                    client = anthropic.Anthropic(
                        api_key=api_key,
                        max_retries=int(cfg.get("max_retries", 2)),
                    )
                    return client, selected_model, provider
                except ImportError:
                    pass

    return None, None, "fallback"


def _call_llm(system: str, user: str, temperature: float = 0.7, max_tokens: int = 1000,
              use_fast: bool = False, model: str | None = None) -> str:
    """Ruft LLM auf. Gibt Text zurück oder leeren String bei Fehler."""
    client, selected_model, provider = _get_client(use_fast=use_fast, model=model)

    if provider == "fallback" or client is None:
        logger.warning("Kein LLM verfügbar — Keyword-Fallback aktiv")
        return ""

    try:
        if provider in {"openai", "azure", "onprem"}:
            request = {
                "model": selected_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            normalized_model = _request_model_family(
                provider,
                selected_model,
                _load_config(),
                use_fast=use_fast,
            ).lower()
            if provider != "onprem" and normalized_model.startswith("gpt-5"):
                request["max_completion_tokens"] = max_tokens
                if provider == "azure":
                    effort = _azure_reasoning_effort(
                        _load_config(),
                        use_fast=use_fast,
                    )
                    if effort:
                        request["reasoning_effort"] = effort
                else:
                    request["reasoning_effort"] = (
                        "none"
                        if normalized_model.startswith("gpt-5.6")
                        else "minimal"
                    )
            else:
                request["temperature"] = temperature
                request["max_tokens"] = max_tokens
            response = client.chat.completions.create(**request)
            _session_usage["calls"] += 1
            _session_usage["input_tokens"] += getattr(response.usage, "prompt_tokens", 0)
            _session_usage["output_tokens"] += getattr(response.usage, "completion_tokens", 0)
            return response.choices[0].message.content.strip()

        elif provider == "anthropic":
            # Prompt Caching: SOUL.md als ephemeral cache (bis zu 90% Kostenersparnis)
            # Cache TTL: 5 Minuten — rentiert sich bei mehreren Calls pro Session
            response = client.messages.create(
                model=selected_model,
                max_tokens=max_tokens,
                system=[{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user}],
            )
            _session_usage["calls"] += 1
            _session_usage["input_tokens"] += getattr(response.usage, "input_tokens", 0)
            _session_usage["output_tokens"] += getattr(response.usage, "output_tokens", 0)
            _session_usage["cache_read_tokens"] += getattr(response.usage, "cache_read_input_tokens", 0)
            _session_usage["cache_write_tokens"] += getattr(response.usage, "cache_creation_input_tokens", 0)
            return response.content[0].text.strip()

    except Exception as exc:
        logger.error(
            "LLM-Fehler provider=%s type=%s status=%s request_id=%s",
            provider,
            type(exc).__name__,
            getattr(exc, "status_code", None),
            getattr(exc, "request_id", None),
        )
        return ""
    return ""


def complete(system: str, user: str, temperature: float = 0.7, max_tokens: int = 1000,
             use_fast: bool = False, model: str | None = None) -> str:
    """Public text-completion helper for orchestration layers and subagents."""
    return _call_llm(
        system,
        user,
        temperature=temperature,
        max_tokens=max_tokens,
        use_fast=use_fast,
        model=model,
    )


def _parse_json(text: str) -> dict:
    """Extrahiert JSON aus LLM-Antwort (auch wenn in Markdown-Block)."""
    # JSON-Block aus Markdown extrahieren
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


# ── Kern-Funktionen ────────────────────────────────────────────────────────

def think(task: str, context: str = "") -> dict:
    """Aufgabe verstehen, Schritte planen, Tool wählen.

    Returns:
        {
            "understood": "Was der Agent verstanden hat",
            "plan": ["Schritt 1", "Schritt 2"],
            "tool": "tool_name oder None",
            "tool_input": "Was dem Tool übergeben wird",
            "needs_human": False,
            "reasoning": "Warum dieser Plan"
        }
    """
    soul = _load_soul()
    system = f"""{soul}

Du planst eine Aufgabe. Antworte NUR mit JSON:
{{
    "understood": "Kurze Zusammenfassung was du verstanden hast",
    "plan": ["Konkreter Schritt 1", "Schritt 2", "..."],
    "tool": "tool_name oder null",
    "tool_input": "Input für das Tool oder null",
    "needs_human": false,
    "reasoning": "Warum dieser Plan"
}}"""

    user = f"Aufgabe: {task}"
    if context:
        user += f"\n\nKontext: {context}"

    result = _call_llm(system, user, temperature=0.3, max_tokens=500)
    parsed = _parse_json(result)

    if not parsed:
        # Keyword-Fallback
        return {
            "understood": task,
            "plan": ["Aufgabe direkt ausführen"],
            "tool": None,
            "tool_input": task,
            "needs_human": False,
            "reasoning": "Fallback — kein LLM verfügbar",
        }

    return parsed


def challenge(plan: dict, context: str = "") -> dict:
    """Plan adversarial hinterfragen — zweite Meinung vor dem Handeln.

    Returns:
        {
            "approved": True/False,
            "concerns": ["Bedenken 1", ...],
            "risk_level": "low | medium | high",
            "suggestion": "Alternative oder None"
        }
    """
    soul = _load_soul()
    system = f"""{soul}

Du bist ein kritischer Reviewer. Hinterfrage diesen Plan streng.
Antworte NUR mit JSON:
{{
    "approved": true,
    "concerns": [],
    "risk_level": "low",
    "suggestion": null
}}

risk_level: "low" = sicher ausführen | "medium" = mit Vorsicht | "high" = besser nicht"""

    user = f"Plan zur Überprüfung: {json.dumps(plan, ensure_ascii=False)}"
    if context:
        user += f"\n\nKontext: {context}"

    result = _call_llm(system, user, temperature=0.2, max_tokens=300)
    parsed = _parse_json(result)

    if not parsed:
        logger.warning("Challenge nicht verfügbar (kein LLM) — Plan wird ohne Review ausgeführt")
        return {
            "approved": True,
            "concerns": ["Challenge nicht verfügbar — kein LLM"],
            "risk_level": "low",
            "suggestion": None,
        }

    return parsed


def act(plan: dict, tool_result: str = "") -> dict:
    """Ergebnis eines Tool-Aufrufs bewerten + nächsten Schritt bestimmen.

    Returns:
        {
            "success": True/False,
            "next_action": "done / retry / escalate / next_tool",
            "summary": "Was passiert ist",
            "output": "Finales Ergebnis (wenn done)"
        }
    """
    soul = _load_soul()
    system = f"""{soul}

Bewerte ein Tool-Ergebnis. Antworte NUR mit JSON:
{{
    "success": true,
    "next_action": "done",
    "summary": "Was ist passiert",
    "output": "Finales Ergebnis oder null"
}}

next_action kann sein: "done" | "retry" | "escalate" | "use_different_tool"
"""

    user = f"""Plan war: {json.dumps(plan, ensure_ascii=False)}

Tool-Ergebnis: {tool_result or '(kein Ergebnis)'}

War das erfolgreich? Was ist der nächste Schritt?"""

    result = _call_llm(system, user, temperature=0.2, max_tokens=300)
    parsed = _parse_json(result)

    if not parsed:
        success = "error" not in tool_result.lower() and "fail" not in tool_result.lower()
        return {
            "success": success,
            "next_action": "done" if success else "retry",
            "summary": tool_result[:200] if tool_result else "Kein Ergebnis",
            "output": tool_result if success else None,
        }

    return parsed


def reflect(action_taken: str, result: str, expected: str = "") -> dict:
    """Aus dem Ergebnis lernen. Gibt Learning zurück.

    Returns:
        {
            "worked": True/False,
            "insight": "Was ich gelernt habe",
            "improve_next_time": "Was ich nächstes Mal anders mache"
        }
    """
    soul = _load_soul()
    system = f"""{soul}

Reflektiere über eine abgeschlossene Aktion. Antworte NUR mit JSON:
{{
    "worked": true,
    "insight": "Konkretes Learning (1 Satz)",
    "improve_next_time": "Was nächstes Mal anders machen (1 Satz oder null)"
}}"""

    user = f"""Aktion: {action_taken}
Erwartet: {expected or 'Erfolgreiche Ausführung'}
Tatsächlich: {result}"""

    result_text = _call_llm(system, user, temperature=0.4, max_tokens=200, use_fast=True)
    parsed = _parse_json(result_text)

    if not parsed:
        return {
            "worked": True,
            "insight": "Aktion wurde ausgeführt.",
            "improve_next_time": None,
        }

    return parsed


def evaluate(content: str, content_type: str = "output", criteria: str = "") -> dict:
    """Output qualitativ bewerten (1–10 Score).

    Returns:
        {
            "score": 8,
            "passes": True,
            "feedback": ["Feedback 1", "Feedback 2"],
            "improved_version": "Verbesserter Output oder None"
        }
    """
    soul = _load_soul()
    cfg = _load_config()
    threshold = cfg.get("quality_threshold", 7)

    system = f"""{soul}

Bewerte einen Output nach Qualität. Antworte NUR mit JSON:
{{
    "score": 8,
    "passes_quality": true,
    "feedback": ["Stärke 1", "Verbesserungspunkt 1"],
    "improved_version": "Verbesserter Text oder null (nur wenn score < {threshold})"
}}

Score 1-10: 1=unbrauchbar, 7=gut genug, 10=perfekt.
passes_quality = score >= {threshold}"""

    criteria_text = f"\n\nBewertungskriterien: {criteria}" if criteria else ""
    user = f"Content-Typ: {content_type}{criteria_text}\n\nZu bewerten:\n{content}"

    result = _call_llm(system, user, temperature=0.3, max_tokens=600, use_fast=True)
    parsed = _parse_json(result)

    if not parsed:
        return {
            "score": 5,
            "passes": False,
            "feedback": ["LLM nicht verfügbar — manuelle Prüfung nötig"],
            "improved_version": None,
        }

    parsed["passes"] = parsed.get("passes_quality", parsed.get("score", 0) >= threshold)
    return parsed


def proactive(state_context: str) -> list[dict]:
    """Generiert proaktive Ziele basierend auf dem Agenten-Zustand.

    Returns:
        List von {"id", "task", "priority", "reasoning"}
    """
    soul = _load_soul()
    result = _call_llm(soul, state_context, temperature=0.6, max_tokens=600)
    parsed = _parse_json(result)
    return parsed.get("goals", [])


def get_usage_stats() -> dict:
    """Token-Verbrauch der aktuellen Session."""
    s = _session_usage
    billed = s["input_tokens"] - s["cache_read_tokens"] + s["output_tokens"]
    return {
        "calls": s["calls"],
        "input_tokens": s["input_tokens"],
        "output_tokens": s["output_tokens"],
        "cache_read_tokens": s["cache_read_tokens"],
        "cache_write_tokens": s["cache_write_tokens"],
        "billed_tokens": billed,
        "cache_savings_pct": round(s["cache_read_tokens"] / max(s["input_tokens"], 1) * 100, 1),
    }


def reset_usage_stats() -> None:
    """Setzt Session-Zähler zurück (z.B. nach jedem Loop-Zyklus)."""
    _session_usage.update({
        "calls": 0, "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_write_tokens": 0,
    })
