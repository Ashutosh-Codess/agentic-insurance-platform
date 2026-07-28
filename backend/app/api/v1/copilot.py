"""
Two endpoints: a plain search over the knowledge base, and a streaming
chat endpoint grounded in that search.

Performance notes:
  - The RAG retriever uses sentence-transformers (pre-warmed at startup)
    so the first query is fast.
  - The Ollama LLM stream starts immediately; the browser sees the first
    tokens arrive even while the model is still generating.
  - max_tokens=400 caps generation length so the model doesn't run forever.
  - If Ollama is unreachable the endpoint returns a graceful error, not a
    500 crash.
"""
import os

import httpx
import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import OpenAI, APIConnectionError
from pydantic import BaseModel

from app.core.database import get_db  # noqa: F401  (needed for auth dep)
from app.core.security import get_current_user
from app.models.user import User
from guardrails.input_guard import apply_input_guardrail
from guardrails.output_guard import check_faithfulness
from rag.retriever import retrieve
from vector_db.collections import ALL_COLLECTIONS

router = APIRouter()

# Local Ollama server — defaults to 127.0.0.1 for local dev.
# In Docker the env var is set to http://ollama:11434/v1
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Capped so long prompts don't stall the browser for minutes.
MAX_TOKENS = int(os.getenv("COPILOT_MAX_TOKENS", "400"))

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
            http_client=httpx.Client(timeout=180),
        )
    return _client


def _load_system_prompt() -> str:
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "prompts",
        "policy_copilot.yaml",
    )

    with open(path, encoding="utf-8") as f:
        prompt = yaml.safe_load(f)

    return (
        f"{prompt['backstory']}\n\n"
        f"Goal: {prompt['goal']}\n\n"
        f"Instructions:\n{prompt['instructions']}"
    )


SYSTEM_PROMPT = _load_system_prompt()


class SearchRequest(BaseModel):
    collection: str
    query: str


class SearchResponse(BaseModel):
    results: list[dict]
    faithfulness_note: str | None = None


class AskRequest(BaseModel):
    collection: str
    question: str


@router.post("/copilot/search", response_model=SearchResponse)
def search_knowledge_base(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    if payload.collection not in ALL_COLLECTIONS:
        return SearchResponse(
            results=[],
            faithfulness_note=f"Unknown collection. Valid: {ALL_COLLECTIONS}",
        )

    results = retrieve(payload.collection, payload.query)
    return SearchResponse(results=results)


@router.post("/copilot/ask")
def ask_copilot(
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
):
    safe_question = apply_input_guardrail(payload.question)

    if payload.collection in ALL_COLLECTIONS:
        retrieved = retrieve(payload.collection, safe_question)
    else:
        retrieved = []

    context_text = "\n\n".join(r["text"] for r in retrieved)

    # Fast-path: if we have no Ollama or the collection had no docs,
    # return the raw retrieved text immediately so the user gets something.
    if not context_text:
        def no_context_stream():
            yield (
                "I couldn't find specific policy information for your question in the "
                "knowledge base. Please contact your insurance agent directly for "
                "accurate policy details regarding: " + safe_question
            )
        return StreamingResponse(no_context_stream(), media_type="text/plain")

    def stream():
        full_answer = ""

        try:
            response = get_client().chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context_text}\n\nQuestion: {safe_question}",
                    },
                ],
                stream=True,
                max_tokens=MAX_TOKENS,
            )

            for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                full_answer += delta
                yield delta

        except APIConnectionError:
            # Ollama is not running — fall back to showing the raw retrieved context
            fallback = (
                "[Copilot AI is currently offline. Here is the relevant policy information "
                "retrieved from the knowledge base:]\n\n" + context_text
            )
            full_answer = fallback
            yield fallback
            return
        except Exception as exc:
            yield f"\n\n[Error generating answer: {exc}]"
            return

        faithfulness = check_faithfulness(
            full_answer,
            [r["text"] for r in retrieved],
        )

        if not faithfulness["faithful"]:
            print(f"[copilot] low faithfulness answer flagged: {faithfulness}")

    return StreamingResponse(stream(), media_type="text/plain")