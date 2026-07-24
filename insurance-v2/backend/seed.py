"""
Seed script for the LIVE application database.

Creates EXACTLY:
    - one Super Admin
    - one Insurance Agent
    - a small placeholder product catalog (one product per category)

Nothing else. No customers, policies, or claims are ever seeded here --
every one of those must come from real use of the application.

This is DIFFERENT from `scripts/generate_training_dataset.py`, which uses
Faker to generate a synthetic CSV dataset for offline model TRAINING --
that dataset never touches this database and is not loaded by this
script. See that file's docstring for why the two are kept separate.

Usage:
    python seed.py
"""
from app.core.config import settings
from app.core.security import hash_password
from app.db.database import Base, SessionLocal, engine
from app.models.policy import Product
from app.models.user import User

Base.metadata.create_all(bind=engine)  # convenience for first-run local dev; alembic is the real path

PLACEHOLDER_CATALOG = [
    {
        "name": "Health Shield Basic",
        "category": "health",
        "description": "Entry-level hospitalization cover. PLACEHOLDER catalog entry.",
        "base_premium": 8000,
        "waiting_period_days": 30,
        "eligibility_rules": {"min_age": 18, "max_age": 65},
        "coverage_rules": {"covered_claim_types": ["health"], "coverage_percentage": 80, "deductible": 5000},
    },
    {
        "name": "LifeSecure Term Plan",
        "category": "life",
        "description": "Term life cover. PLACEHOLDER catalog entry.",
        "base_premium": 6000,
        "waiting_period_days": 90,
        "eligibility_rules": {"min_age": 21, "max_age": 60},
        "coverage_rules": {"covered_claim_types": ["life"], "coverage_percentage": 100, "deductible": 0},
    },
    {
        "name": "MotorGuard Comprehensive",
        "category": "motor",
        "description": "Comprehensive motor insurance. PLACEHOLDER catalog entry.",
        "base_premium": 4500,
        "waiting_period_days": 0,
        "eligibility_rules": {"min_age": 18},
        "coverage_rules": {"covered_claim_types": ["motor"], "coverage_percentage": 90, "deductible": 2000},
    },
    {
        "name": "TravelEase International",
        "category": "travel",
        "description": "International travel insurance. PLACEHOLDER catalog entry.",
        "base_premium": 1500,
        "waiting_period_days": 0,
        "eligibility_rules": {"min_age": 1, "max_age": 75},
        "coverage_rules": {"covered_claim_types": ["travel"], "coverage_percentage": 100, "deductible": 1000},
    },
    {
        "name": "HomeSafe Standard",
        "category": "home",
        "description": "Home structure and contents insurance. PLACEHOLDER catalog entry.",
        "base_premium": 3000,
        "waiting_period_days": 15,
        "eligibility_rules": {},
        "coverage_rules": {"covered_claim_types": ["home"], "coverage_percentage": 85, "deductible": 3000},
    },
    {
        "name": "BizProtect SME",
        "category": "business",
        "description": "Small/medium business liability and property cover. PLACEHOLDER catalog entry.",
        "base_premium": 15000,
        "waiting_period_days": 30,
        "eligibility_rules": {},
        "coverage_rules": {"covered_claim_types": ["business"], "coverage_percentage": 80, "deductible": 10000},
    },
]


def _create_if_missing(db, email: str, password: str, role: str) -> None:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"[seed] {role} account already exists ({email}) -- skipping")
        return
    user = User(email=email, hashed_password=hash_password(password), role=role, is_active=True)
    db.add(user)
    db.commit()
    print(f"[seed] created {role} account: {email}")


def _seed_catalog(db) -> None:
    if db.query(Product).count() > 0:
        print("[seed] product catalog already populated -- skipping")
        return
    for entry in PLACEHOLDER_CATALOG:
        db.add(Product(**entry))
    db.commit()
    print(f"[seed] created {len(PLACEHOLDER_CATALOG)} placeholder catalog products")


def run() -> None:
    db = SessionLocal()
    try:
        _create_if_missing(db, settings.SEED_ADMIN_EMAIL, settings.SEED_ADMIN_PASSWORD, "admin")
        _create_if_missing(db, settings.SEED_AGENT_EMAIL, settings.SEED_AGENT_PASSWORD, "agent")
        _seed_catalog(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
