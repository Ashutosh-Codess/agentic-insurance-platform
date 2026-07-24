# Insurance Platform (Final-Year-Project Scope)

A complete rebuild using ONLY the stack you specified: FastAPI + SQLAlchemy
+ PostgreSQL + JWT auth + vanilla JS frontends + OpenCV/TensorFlow/NumPy/
Pandas for AI. No LangGraph, no Celery/Redis, no repository pattern, no
CQRS -- one straightforward layer of routers -> services -> models.

## What was actually verified, and how

I don't have package-registry or Docker access in the environment that
built this, so here's exactly what was and wasn't tested, and how:

| Component | Verified how |
|---|---|
| Every Python file | `python -m py_compile`, zero warnings |
| `fraud_service.assess_fraud` | **Actually executed** with real pandas/numpy in this environment -- confirmed correct signal detection and scoring |
| `utils/ocr.py` (document quality) | **Actually executed** with real OpenCV (cv2 4.13 was available) against synthetic sharp/blurry/dark test images -- all three paths (legible, needs-review, missing-file) confirmed correct |
| `utils/classification.py` rule fallback | Logic verified; full execution blocked here only by a missing `tensorflow` import at module load (tensorflow itself isn't available in this sandbox) -- will run in Docker, where it installs normally |
| Damage-detection edge-density algorithm | **Actually executed** the core OpenCV Canny-edge-density logic standalone -- confirmed a noisy/damaged-looking image scores higher than a smooth one, as designed |
| `scripts/generate_training_dataset.py` | **Actually executed end-to-end, unmodified** -- Faker itself isn't installable in this sandbox (no registry access), so I ran the exact script against a minimal local stand-in exposing just `Faker.name()`, which is the only Faker feature it uses. Produced the real 5,000-row `datasets/synthetic_claims.csv` included in this zip; confirmed realistic claim_class distribution (~45%/25%/30%) and ~4.3% fraud rate |
| `scripts/train_classifier.py` preprocessing | The normalization, feature extraction, and train/test split logic was **actually run** against the real generated CSV (confirmed no NaNs, correct shapes, correct label mapping) -- only the `model.fit(...)` call itself is untested here, since TensorFlow isn't installable in this sandbox either |
| Frontend JS (`api.js`, `auth.js`, `dashboard.js`, `claim.js`, both portals) | `node --check` on all 8 files -- zero syntax errors |
| `docker-compose.yml` | Parsed with PyYAML -- valid |

What that means in practice: the parts of this project that are pure
Python logic (fraud detection, document quality, damage heuristics, the
synthetic dataset's statistics) are not just "should work" -- they were
run, with real inputs, and produced correct output. The parts gated on
TensorFlow/Faker specifically need `pip install -r requirements.txt`
(which needs your machine's normal internet access) before they can run,
but nothing about their code changed after `py_compile` passed clean.

## Why the schema looks simpler than the original build

Per your brief ("no unnecessary abstraction"), this rebuild deliberately:
- Merges Customer + CustomerProfile into `User` itself (profile columns
  just sit unused on agent/admin rows)
- Drops the premium-schedule table -- a policy carries `premium_amount` +
  `next_due_date` directly
- Drops the AgentRun/FraudFlag/Decision table split -- every AI module's
  output for a claim lives in one `claims.ai_analysis` JSONB column
- Has no task queue -- `POST /claims/{id}/process` runs the whole AI
  pipeline synchronously, in one function, in `services/claim_service.py`

Every one of those is flagged with a comment at the point it matters in
the code, not just here.

## The AI modules, honestly described

- **OCR** -- there is no character-level text extraction. Full OCR needs a
  trained text-recognition model or an external engine (Tesseract), which
  falls outside "OpenCV + TensorFlow only." What's implemented instead is
  a genuinely useful **document quality check** (blur detection via
  Laplacian variance, brightness check) that flags illegible uploads for
  manual review -- a real, common OpenCV technique, not a placeholder.
- **Damage Detection** -- defaults to a real OpenCV Canny-edge-density
  heuristic (more edge texture ≈ more visible damage). A trained CNN
  (`models/damage_model.h5`) is picked up automatically if you train and
  drop one in -- see `app/utils/vision_model.py`.
- **Claim Classification** -- defaults to threshold rules; picks up
  `models/claim_classifier.h5` automatically once trained (see
  `scripts/train_classifier.py`).
- **Fraud Detection** -- a weighted sum of named, explainable signals
  computed with pandas/numpy (duplicate recent amount, near-waiting-period
  filing, claim frequency, statistical z-score outlier). No black box.
- **Recommendation Engine** -- deterministic scoring over the product
  catalog using pandas, based on profile data (risk factors, dependents,
  assets, income).

None of these pretend to be more accurate than they are. Comments at each
decision point say exactly what's heuristic vs. trained.

## The Faker-generated dataset

`scripts/generate_training_dataset.py` generates a synthetic CSV of
historical claims for **offline model training only**. A pre-generated
5,000-row sample is already included at `datasets/synthetic_claims.csv` --
I ran the script itself (unmodified) to produce it, so you don't have to
run anything before trying `train_classifier.py`. Regenerate it anytime
with fresh/more rows:

```bash
cd backend
python scripts/generate_training_dataset.py --rows 5000   # overwrites datasets/synthetic_claims.csv
python scripts/train_classifier.py                        # trains + saves models/claim_classifier.h5
```

This is completely separate from the live app database. `seed.py` still
only ever creates the Admin, the Agent, and the placeholder catalog --
Faker is never imported by the running FastAPI app, only by this
standalone script. Once `models/claim_classifier.h5` exists, the live
classification module picks it up automatically on the next claim
processed -- no code change.

## Running everything

```bash
cp backend/.env.example backend/.env   # edit JWT_SECRET_KEY and seed passwords
docker compose up --build
```

| Service | URL |
|---|---|
| Customer Portal | http://localhost:5173 |
| Agent Portal | http://localhost:5174 |
| API + Swagger docs | http://localhost:8000/docs |

Log in as the seeded agent (`SEED_AGENT_EMAIL` / `SEED_AGENT_PASSWORD` in
`.env`). Register a new account at the Customer Portal -- this is the
only way a customer exists, per your original requirement.

## Project tree

```
backend/
  app/
    main.py
    core/            config.py, security.py (JWT + get_current_user + require_role)
    db/               database.py
    models/           user.py, policy.py, claim.py, document.py
    schemas/          user.py, policy.py, claim.py
    routers/          auth.py, customers.py, agents.py, claims.py, products.py
    services/         auth_service.py, claim_service.py, fraud_service.py, recommendation_service.py
    utils/            ocr.py, damage_detection.py, classification.py, copilot.py,
                       vision_model.py, file_storage.py, report_writer.py
  scripts/            generate_training_dataset.py, train_classifier.py
  uploads/            uploaded KYC + claim documents (runtime)
  reports/            per-claim AI analysis reports (runtime, JSON)
  datasets/           Faker-generated training CSV (runtime, offline only)
  models/             trained .h5 weights, once you train them (gitignored)
  alembic/
frontend/
  customer/           index.html, css/, js/{api,auth,dashboard,claim}.js
  agent/              index.html, css/, js/{api,auth,dashboard,claim}.js
docker-compose.yml
```

## Verifying the "no fake live data" rule yourself

```bash
docker compose exec postgres psql -U insurance -d insurance -c "SELECT email, role FROM users;"
# should show exactly the seeded admin + agent -- nothing else until you use the app
```

If something breaks on your machine, it's most likely a dependency
version mismatch I couldn't verify locally (TensorFlow/OpenCV builds are
platform-sensitive) -- send me the exact error and I'll fix it.
