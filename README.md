# InsuraMind AI

Autonomous multi-agent insurance operations platform, built per the
architecture doc: FastAPI + PostgreSQL backend, CrewAI + PydanticAI
agents, Chroma vector search, vanilla JS frontend, Docker Compose.

## Two calls I made on things the spec left ambiguous

1. **Chroma, not Pinecone.** The doc listed both interchangeably. Pinecone
   is a managed cloud service - using it would send policy/medical
   embeddings to a third party, which contradicts the doc's own reasoning
   for using local open-weight LLMs (no third-party data transmission).
   See `docs/architecture.md` for the full reasoning.
2. **Ollama, serving Llama 3 by default.** The doc named three model
   options without saying how any of them get served. Change
   `OLLAMA_MODEL` in `.env` to use Qwen 2.5 or DeepSeek instead - both
   run on Ollama the same way.

## Running it

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres, Ollama, and the backend. First run: pull a model
into Ollama (it doesn't ship with one):

```bash
docker compose exec ollama ollama pull llama3
```

Then open `frontend/index.html` directly in a browser, or serve it with
any static file server (`python -m http.server` from inside `frontend/`).

API docs: `http://localhost:8000/docs`

## What was actually verified, and how

I don't have package-registry or Docker access in the environment that
built this - here's exactly what was and wasn't tested:

| Component | Verified how |
|---|---|
| Every Python file across the whole repo | `python -m py_compile`, zero warnings |
| All four `guardrails/` modules | **Actually executed**, 17 real test assertions, all passing |
| `risk_service.py` | **Actually executed** against a stand-in customer object, all 3 cases pass |
| Frontend JS (all 6 files) | `node --check` - zero syntax errors |
| `docker-compose.yml`, `docs/api_specs.openapi.yaml` | Parsed with PyYAML - valid |
| FastAPI routers, SQLAlchemy models, Alembic migration | Syntax-verified only - FastAPI/SQLAlchemy aren't installable in this sandbox |
| `agents/` (CrewAI crews, PydanticAI agents) | Syntax-verified only - CrewAI/PydanticAI aren't installable here either, and even if they were, they need a running Ollama to actually produce output |

**Two real bugs were caught and fixed** by actually running the tests
rather than just writing them:
- `output_guard.py`'s faithfulness check was scoring a completely
  unrelated answer as "faithful" because common words like "policy" and
  "covers" were inflating the overlap score. Fixed with a stopword filter
  and a corrected threshold, re-verified against the real token overlap
  numbers.
- `risk_service.py` imported the SQLAlchemy `Customer` model just for a
  type hint, making the pure scoring logic impossible to unit test
  without a full SQLAlchemy install. Fixed with a `TYPE_CHECKING` guard.

Both are documented in `docs/architecture.md` and in the code itself.

## Directory structure

Matches the original spec's tree exactly - see `docs/architecture.md`
for why `agents/`, `guardrails/`, `rag/`, and `vector_db/` (siblings of
`backend/` in the tree) get mounted into the backend container rather
than living inside it.

```
insuramind-ai/
├── frontend/       HTML/CSS/vanilla JS - pages/, components/, assets/
├── backend/        FastAPI app - api/, core/, models/, schemas/, services/
├── agents/         CrewAI crews + PydanticAI agents + tools + orchestrator
├── guardrails/      input/output/execution/agent safety checks
├── rag/            chunking, embeddings, retrieval
├── vector_db/      Chroma client, collection definitions, indexer
├── prompts/        the four agent system prompts (YAML)
├── database/       init.sql + Faker synthetic data generator
├── data/           raw/ (per-collection source docs) + processed/
├── docs/           architecture.md, api_specs.openapi.yaml
├── tests/          unit/, integration/, agent_tests/, guardrail_tests/
└── docker-compose.yml
```

## Populating the knowledge base

Four sample `.txt` files are included (one per collection, clearly marked
SAMPLE) so `python -m vector_db.indexer` has something to index on first
run. Replace them with real policy wording, medical guidelines, repair
cost data, and regulatory text before relying on the copilot or the
adjudication crew for anything real.

```bash
docker compose exec backend python -m vector_db.indexer
```

## Generating synthetic test data

```bash
docker compose exec backend python database/seeds/generate_seed_data.py --customers 50
```

Creates synthetic customers (Faker), each with 1-2 policies and some
claims, for local testing. Every seeded user's password is
`password123`.

## Known gaps (see docs/architecture.md for the full list)

- `agents/pydantic_agents/policy_recommender.py` and `kyc_verifier.py`
  have working service-layer functions
  (`agent_service.get_policy_recommendation`,
  `agent_service.verify_customer_kyc`) but no API route calls them yet.
- The AI analysis endpoint (`POST /claims/{id}/run-analysis`) has to be
  triggered manually by an agent - nothing auto-runs it on document
  upload. That's a reasonable next step, not done here since the spec
  didn't specify which trigger it should be.

## Running the tests

```bash
# these run with zero dependencies beyond the standard library:
pytest tests/guardrail_tests/

# these need the full stack:
pip install -r backend/requirements.txt
pytest tests/unit/ tests/integration/ tests/agent_tests/
```

If something breaks on your machine, it's most likely a dependency
version mismatch I couldn't verify locally (CrewAI, PydanticAI, and
TensorFlow all move fast) - send me the exact error and I'll fix it.
