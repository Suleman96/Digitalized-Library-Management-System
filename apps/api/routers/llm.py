# =============================================================================
# routers/llm.py — AI provider configuration
# =============================================================================

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from ..core.llm_provider import PROVIDER_MODELS
from ..deps import Engine, get_engine
from ..schemas import ConnectRequest, LLMStatus, ProviderInfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["llm"])

# Which env var holds each provider's key. Ollama runs locally and needs none.
_KEY_ENV = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq":   "GROQ_API_KEY",
    "ollama": "",
}


def _status_of(engine: Engine, message: str = "") -> LLMStatus:
    llm = engine.llm
    return LLMStatus(
        connected=llm.is_enabled,
        provider=llm._provider or None,
        model=llm._model or None,
        message=message or llm.status,
        capabilities={
            # What the UI should let the user switch on.
            "queryExpansion": llm.is_enabled,
            "hyde":           llm.is_enabled,
            "multiQuery":     llm.is_enabled,
            "explain":        llm.is_enabled,
            "rerank":         True,   # cross-encoder is local, no LLM needed
            "agent":          engine.agent.is_ready if engine.agent else False,
        },
    )


@router.get("/providers", response_model=list[ProviderInfo])
def providers() -> list[ProviderInfo]:
    """Available providers and their models, with key availability."""
    out: list[ProviderInfo] = []
    for provider, models in PROVIDER_MODELS.items():
        env_var = _KEY_ENV.get(provider, "")
        out.append(ProviderInfo(
            provider=provider,
            models=models,
            requiresKey=bool(env_var),
            keyConfigured=bool(os.getenv(env_var, "").strip()) if env_var else True,
        ))
    return out


@router.get("/status", response_model=LLMStatus)
def status(engine: Engine = Depends(get_engine)) -> LLMStatus:
    """Current connection state."""
    return _status_of(engine)


@router.post("/connect", response_model=LLMStatus)
def connect(req: ConnectRequest, engine: Engine = Depends(get_engine)) -> LLMStatus:
    """
    Connect an AI provider and rebuild the agent.

    `apiKey` lets a public visitor supply their own credentials for a session
    rather than spending the deployment's keys.
    """
    provider = req.provider.strip().lower()
    if provider not in PROVIDER_MODELS:
        raise HTTPException(422, f"Unknown provider '{req.provider}'.")
    if req.model not in PROVIDER_MODELS[provider]:
        raise HTTPException(422, f"Model '{req.model}' is not available for {provider}.")

    if req.ollamaHost:
        engine.llm.set_ollama_host(req.ollamaHost)

    # Bring-your-own-key: scoped to this process, never persisted to disk.
    restore: tuple[str, str | None] | None = None
    env_var = _KEY_ENV.get(provider, "")
    if req.apiKey and env_var:
        restore = (env_var, os.environ.get(env_var))
        os.environ[env_var] = req.apiKey.strip()

    try:
        message = engine.llm.configure(provider, req.model)
    finally:
        if restore and not engine.llm.is_enabled:
            var, previous = restore
            if previous is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = previous

    if engine.llm.is_enabled:
        engine.agent.reset()
        engine.agent.build()

    return _status_of(engine, message)
