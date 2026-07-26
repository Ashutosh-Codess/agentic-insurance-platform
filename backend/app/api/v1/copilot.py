"""
Two endpoints: a plain search over the knowledge base, and a streaming
chat endpoint grounded in that search.
"""
import os

import httpx
import yaml
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel

from guardrails.input_guard import apply_input_guardrail
from guardrails.output_guard import check_faithfulness
from rag.retriever import retrieve
from vector_db.collections import ALL_COLLECTIONS

router = APIRouter()

# Local Ollama server
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
            http_client=httpx.Client(timeout=300),
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
def search_knowledge_base(payload: SearchRequest):
    if payload.collection not in ALL_COLLECTIONS:
        return SearchResponse(
            results=[],
            faithfulness_note=f"Unknown collection. Valid: {ALL_COLLECTIONS}",
        )

    results = retrieve(payload.collection, payload.query)

    return SearchResponse(results=results)


@router.post("/copilot/ask")
def ask_copilot(payload: AskRequest):
    safe_question = apply_input_guardrail(payload.question)

    if payload.collection in ALL_COLLECTIONS:
        retrieved = retrieve(payload.collection, safe_question)
    else:
        retrieved = []

    context_text = "\n\n".join(r["text"] for r in retrieved)

    def stream():
        full_answer = ""

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
        )

        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            full_answer += delta
            yield delta

        faithfulness = check_faithfulness(
            full_answer,
            [r["text"] for r in retrieved],
        )

        if not faithfulness["faithful"]:
            print(f"[copilot] low faithfulness answer flagged: {faithfulness}")

    return StreamingResponse(stream(), media_type="text/plain")