# =============================================================================
# llm_provider.py — Iqra Digital Library v2
# =============================================================================
# LLMProvider
# -----------
# Unified multi-provider LLM abstraction supporting:
#   • Claude  (Anthropic)
#   • OpenAI  (GPT-4o, GPT-4.1, …)
#   • Gemini  (Google)
#   • Groq    (fast inference, free tier — llama3, mixtral, gemma)
#   • Ollama  (local, free — no API key needed)
#
# Usage
# -----
#   from llm_provider import llm          # module-level singleton
#   llm.configure("claude", "claude-sonnet-4-6")
#   response = llm.expand_query("mystery books")
#
# The provider never raises — failures return empty strings and log warnings.
# =============================================================================

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model catalogue — shown in the UI dropdown per provider
# ---------------------------------------------------------------------------
PROVIDER_MODELS: dict[str, list[str]] = {
    "claude": [
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-opus-4-7",
        "claude-opus-4-8",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-3.5-turbo",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    # Groq — fast inference, free tier, great for demos.
    # API key at: https://console.groq.com/
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    # Only models that support tool/function calling (required for the ReAct agent).
    # gemma:2b, gemma:7b, phi3 do NOT support tool calling and are excluded.
    "ollama": [
        "llama3.2",       # 2 GB  — recommended, full tool calling
        "llama3.3",       # 42 GB — high quality, tool calling
        "qwen2.5:3b",     # 1.9 GB — excellent structured output + tool calling
        "qwen2.5:7b",     # 4.7 GB — high quality, tool calling
        "qwen3:8b",       # 5.2 GB — latest Qwen3, strong reasoning
        "phi4",           # 9.1 GB — Microsoft Phi-4, strong reasoning
        "llama3.1",       # 4.7 GB — tool calling supported
        "mistral",        # 4.7 GB — tool calling supported
        "deepseek-r1:8b", # 5.2 GB — strong reasoning, tool calling
        "gemma3:4b",      # 3.3 GB — Google Gemma 3, tool calling
    ],
}

_DEFAULT_MODELS: dict[str, str] = {k: v[0] for k, v in PROVIDER_MODELS.items()}


# =============================================================================
class LLMProvider:
    """
    Wraps multiple LLM backends under one interface.
    Call configure() to authenticate, then use expand_query() / explain_match()
    or get_langchain_llm() for agent use.
    """

    def __init__(self) -> None:
        self._provider:    str  = ""
        self._model:       str  = ""
        self._client:      Any  = None
        self._ollama_host: str  = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.is_enabled:   bool = False
        self.status:       str  = "Not connected"

    def set_ollama_host(self, host: str) -> None:
        """Override the Ollama server URL.  Call before configure('ollama', ...)."""
        host = host.strip().rstrip("/")
        if host:
            self._ollama_host = host

    # ── Public: model catalogue ───────────────────────────────────────────
    @property
    def available_models(self) -> dict[str, list[str]]:
        return PROVIDER_MODELS

    def models_for(self, provider: str) -> list[str]:
        return PROVIDER_MODELS.get(provider.lower(), [])

    # ── Public: connect ───────────────────────────────────────────────────
    def configure(self, provider: str, model: str) -> str:
        """
        Attempt to connect to the given provider/model.

        Returns a human-readable status string starting with ✅ or ❌.
        Never raises.
        """
        provider = provider.lower().strip()
        if provider not in PROVIDER_MODELS:
            return f"❌ Unknown provider '{provider}'."

        try:
            if provider == "claude":
                status = self._connect_claude(model)
            elif provider == "openai":
                status = self._connect_openai(model)
            elif provider == "gemini":
                status = self._connect_gemini(model)
            elif provider == "groq":
                status = self._connect_groq(model)
            elif provider == "ollama":
                status = self._connect_ollama(model)
            else:
                status = f"❌ Provider '{provider}' not implemented."
        except Exception as exc:
            logger.warning("LLMProvider.configure error: %s", exc)
            status = f"❌ Unexpected error: {exc}"

        if status.startswith("✅"):
            self._provider  = provider
            self._model     = model
            self.is_enabled = True
        else:
            self.is_enabled = False

        self.status = status
        logger.info("LLMProvider status: %s", status)
        return status

    # ── Provider-specific connect helpers ─────────────────────────────────
    def _connect_claude(self, model: str) -> str:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return "❌ ANTHROPIC_API_KEY not set. Add it to .env"
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        client.messages.create(
            model=model, max_tokens=5,
            messages=[{"role": "user", "content": "hi"}],
        )
        self._client = client
        return f"✅ Claude ({model}) connected."

    def _connect_openai(self, model: str) -> str:
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            return "❌ OPENAI_API_KEY not set. Add it to .env"
        from openai import OpenAI
        client = OpenAI(api_key=key)
        client.models.retrieve(model)
        self._client = client
        return f"✅ OpenAI ({model}) connected."

    def _connect_gemini(self, model: str) -> str:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            return "❌ GEMINI_API_KEY not set. Add it to .env"
        import google.generativeai as genai
        genai.configure(api_key=key)
        self._client = genai.GenerativeModel(model)
        return f"✅ Gemini ({model}) connected."

    def _connect_groq(self, model: str) -> str:
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key:
            return "❌ GROQ_API_KEY not set. Add it to .env  (free key at console.groq.com)"
        try:
            from groq import Groq
            client = Groq(api_key=key)
            client.chat.completions.create(
                model=model, max_tokens=5,
                messages=[{"role": "user", "content": "hi"}],
            )
            self._client = client
            return f"✅ Groq ({model}) connected."
        except ImportError:
            return "❌ groq package not installed. Run: pip install groq"
        except Exception as exc:
            return f"❌ Groq connection failed: {exc}"

    def _connect_ollama(self, model: str) -> str:
        import requests as _requests
        host = self._ollama_host
        try:
            r = _requests.get(f"{host}/api/tags", timeout=10)
            r.raise_for_status()
        except _requests.ConnectionError:
            return (
                f"❌ Ollama server not reachable at {host}. "
                "Make sure Ollama is running (open Ollama app or run 'ollama serve')."
            )
        except _requests.Timeout:
            return f"❌ Ollama server at {host} timed out. Check the host URL."
        except Exception as exc:
            return f"❌ Could not reach Ollama at {host}: {exc}"

        # Verify the requested model is actually pulled
        pulled_names = [m.get("name", "") for m in r.json().get("models", [])]
        model_base   = model.split(":")[0]
        is_available = any(
            p == model or p.startswith(model_base + ":") or p.startswith(model_base + " ")
            for p in pulled_names
        )
        if not is_available:
            available_str = ", ".join(pulled_names) if pulled_names else "(none pulled yet)"
            return (
                f"❌ Model '{model}' not found at {host}.\n"
                f"   Pull it with:  ollama pull {model}\n"
                f"   Available:     {available_str}"
            )

        self._client = host
        return f"✅ Ollama ({model} @ {host}) connected."

    # ── Raw LLM call (never raises) ───────────────────────────────────────
    def _call(self, prompt: str, max_tokens: int = 512) -> str:
        """Single-turn prompt. Returns empty string on failure."""
        if not self.is_enabled or not self._client:
            return ""
        try:
            if self._provider == "claude":
                resp = self._client.messages.create(
                    model=self._model, max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.content[0].text.strip()

            if self._provider == "openai":
                resp = self._client.chat.completions.create(
                    model=self._model, max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message.content.strip()

            if self._provider == "gemini":
                resp = self._client.generate_content(prompt)
                return resp.text.strip()

            if self._provider == "groq":
                resp = self._client.chat.completions.create(
                    model=self._model, max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message.content.strip()

            if self._provider == "ollama":
                import requests as _requests
                r = _requests.post(
                    f"{self._client}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": max_tokens},
                    },
                    timeout=90,
                )
                return r.json().get("response", "").strip()

        except Exception as exc:
            logger.warning("LLMProvider._call error (%s): %s", self._provider, exc)
        return ""

    # ── High-level helpers ────────────────────────────────────────────────
    def expand_query(self, query: str) -> str:
        """
        Rewrite a user search query into richer terms with synonyms/themes.
        Falls back to the original query if AI is off or the call fails.
        """
        if not self.is_enabled:
            return query
        prompt = (
            "You are a library search assistant. Rewrite this book search query "
            "into richer terms with relevant synonyms and related themes. "
            "Return ONLY the improved query on a single line — no explanation.\n\n"
            f"Original query: {query}"
        )
        result = self._call(prompt, max_tokens=120)
        return result if result else query

    def explain_match(self, query: str, book: dict[str, Any]) -> str:
        """
        Generate a 2-sentence explanation of why the book matches the query.
        Returns empty string if AI is off.
        """
        if not self.is_enabled:
            return ""
        title   = book.get("title",   "")
        authors = book.get("authors", "")
        desc    = (str(book.get("description", "") or ""))[:350]
        prompt = (
            f"In exactly 2 sentences, explain why '{title}' by {authors} "
            f"is a great match for the search query: '{query}'. "
            f"Book description: {desc}"
        )
        return self._call(prompt, max_tokens=200)

    def generate_hypothetical_doc(self, query: str) -> str:
        """
        HyDE: generate a hypothetical ideal book description for the query.
        The resulting text is embedded and used as the FAISS search vector,
        often yielding richer semantic matches than embedding the raw query.
        Returns empty string when AI is off or the call fails.
        """
        if not self.is_enabled:
            return ""
        prompt = (
            "Write a 2-sentence description of an ideal book that perfectly answers "
            f"this reader's request: \"{query}\"\n"
            "Output ONLY the book description — no title, no author, no preamble."
        )
        return self._call(prompt, max_tokens=180)

    def generate_query_variants(self, query: str) -> list[str]:
        """
        Multi-query RAG: generate up to 3 alternative search queries.
        Variants are run in parallel through the retriever; results are merged
        with Reciprocal Rank Fusion to surface books missed by the raw query.
        Returns an empty list when AI is off or the call fails.
        """
        if not self.is_enabled:
            return []
        prompt = (
            "Generate exactly 3 alternative search queries for finding books about:\n"
            f'"{query}"\n\n'
            "Rules: one query per line, no numbering, no explanation, no blank lines."
        )
        raw = self._call(prompt, max_tokens=200)
        if not raw:
            return []
        return [line.strip() for line in raw.strip().splitlines() if line.strip()][:3]

    # ── LangChain integration ─────────────────────────────────────────────
    def get_langchain_llm(self) -> Any:
        """
        Return a LangChain chat model compatible with LangGraph agents.
        Returns None if AI is disabled or the required package is missing.
        """
        if not self.is_enabled:
            return None
        try:
            if self._provider == "claude":
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=self._model,
                    api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                    max_tokens=1024,
                )
            if self._provider == "openai":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=self._model,
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                )
            if self._provider == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=self._model,
                    google_api_key=os.getenv("GEMINI_API_KEY", ""),
                )
            if self._provider == "groq":
                from langchain_groq import ChatGroq
                return ChatGroq(
                    model=self._model,
                    api_key=os.getenv("GROQ_API_KEY", ""),
                )
            if self._provider == "ollama":
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=self._model,
                    base_url=str(self._client),
                )
        except ImportError as exc:
            logger.warning(
                "get_langchain_llm: missing LangChain package for %s — %s. "
                "Install langchain-%s.", self._provider, exc, self._provider,
            )
        except Exception as exc:
            logger.warning("get_langchain_llm error (%s): %s", self._provider, exc)
        return None


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
llm = LLMProvider()
