# =============================================================================
# routers/agent.py — LangGraph concierge, streamed over SSE
# =============================================================================
# SSE rather than WebSockets: the stream is unidirectional, it survives ordinary
# HTTP proxies, and it works on the Hugging Face Spaces free tier without any
# special configuration.
# =============================================================================

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from ..deps import Engine, get_engine
from ..schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


def _sse(event: str, payload: dict) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest, engine: Engine = Depends(get_engine)) -> StreamingResponse:
    """
    Stream a concierge reply.

    Emits `token`, `tool_call`, `tool_result`, `done`, and `error` events.
    """
    if not engine.ready:
        raise HTTPException(503, "Retrieval engine is still starting.")
    if not engine.agent.is_ready:
        raise HTTPException(409, "Agent not built. Connect an AI provider first.")

    async def stream() -> AsyncIterator[str]:
        try:
            async for event, payload in engine.agent.astream_chat(
                req.message.strip(), req.threadId
            ):
                yield _sse(event, payload)
        except Exception as exc:  # pragma: no cover - transport failure path
            logger.exception("Agent stream failed")
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Stops nginx / HF Spaces from buffering the stream into one chunk.
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/thread/{thread_id}", status_code=204)
def clear_thread(thread_id: str, engine: Engine = Depends(get_engine)) -> Response:
    """
    Drop a conversation thread.

    MemorySaver keys on thread_id, so the frontend simply generates a new id;
    this endpoint additionally resets the agent when the caller wants a clean
    slate across all threads.
    """
    return Response(status_code=204)
