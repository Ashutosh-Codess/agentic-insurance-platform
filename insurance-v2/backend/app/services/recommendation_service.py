"""
Recommendation engine: scores every active product in the catalog against
a customer's profile using pandas, and returns the ones that close an
actual coverage gap. All scores are deterministic and explainable -- no
black box, no LLM, per the "no unnecessary abstraction" brief.
"""
import pandas as pd
from sqlalchemy.orm import Session

from app.models.policy import Policy, Product, Recommendation
from app.models.user import User


def compute_risk_score(user: User) -> float:
    score = 20.0
    age = user.age()
    if age is not None and age >= 50:
        score += 10
    health = user.health_data or {}
    if health.get("smoking"):
        score += 20
    if health.get("alcohol"):
        score += 10
    bmi = health.get("bmi")
    if isinstance(bmi, (int, float)) and bmi >= 30:
        score += 15
    conditions = health.get("current_diseases") or []
    score += min(len(conditions) * 10, 30)
    return round(min(score, 100.0), 2)


def compute_need_score(user: User) -> float:
    score = 0.0
    lifestyle = user.lifestyle_data or {}
    dependents = lifestyle.get("dependents") or 0
    if isinstance(dependents, (int, float)):
        score += min(dependents * 10, 40)

    assets = user.assets or {}
    score += 15 if assets.get("house") else 0
    score += 10 if assets.get("vehicle") else 0
    score += 15 if assets.get("business") else 0

    if user.income is not None and float(user.income) < 500_000:
        score += 10

    return round(min(score, 100.0), 2)


def _estimate_premium(base_premium: float, risk_score: float) -> float:
    # Simple linear risk loading: +1% of base premium per risk point.
    return round(float(base_premium) * (1 + risk_score * 0.01), 2)


def _reasoning_for(product: Product, user: User, risk_score: float, need_score: float) -> str:
    parts = [f"Closes a coverage gap in '{product.category}'."]
    health = user.health_data or {}
    if product.category == "health" and (health.get("smoking") or health.get("current_diseases")):
        parts.append("Health risk factors on file make health coverage a priority.")
    lifestyle = user.lifestyle_data or {}
    if product.category == "life" and (lifestyle.get("dependents") or 0) > 0:
        parts.append(f"Profile lists {lifestyle.get('dependents')} dependent(s).")
    assets = user.assets or {}
    if product.category == "motor" and assets.get("vehicle"):
        parts.append("Profile lists a vehicle asset with no motor policy on record.")
    if product.category == "home" and assets.get("house"):
        parts.append("Profile lists a house asset with no home policy on record.")
    parts.append(f"Risk score {risk_score}, need score {need_score}.")
    return " ".join(parts)


def refresh_recommendations(db: Session, user: User) -> list[Recommendation]:
    active_policies = db.query(Policy).filter(Policy.user_id == user.id, Policy.status == "active").all()
    covered_categories = set()
    for policy in active_policies:
        product = db.get(Product, policy.product_id)
        if product:
            covered_categories.add(product.category)

    catalog = db.query(Product).filter(Product.is_active.is_(True)).all()
    if not catalog:
        return []

    # A pandas DataFrame is genuinely useful here even at small scale: it's
    # the natural place to add more scoring dimensions later without
    # rewriting the loop that walks the catalog.
    catalog_df = pd.DataFrame(
        [{"id": p.id, "category": p.category, "base_premium": float(p.base_premium)} for p in catalog]
    )
    catalog_df = catalog_df[~catalog_df["category"].isin(covered_categories)]

    risk_score = compute_risk_score(user)
    need_score = compute_need_score(user)
    user.risk_score = risk_score
    user.coverage_score = max(0.0, 100.0 - len(catalog_df) * 5.0)

    products_by_id = {p.id: p for p in catalog}
    rows = []
    for _, row in catalog_df.iterrows():
        product = products_by_id[row["id"]]
        recommendation = Recommendation(
            user_id=user.id,
            product_id=product.id,
            score=need_score,
            reasoning=_reasoning_for(product, user, risk_score, need_score),
            estimated_premium=_estimate_premium(product.base_premium, risk_score),
        )
        db.add(recommendation)
        rows.append(recommendation)

    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def get_latest_recommendations(db: Session, user: User, limit: int = 10) -> list[Recommendation]:
    return (
        db.query(Recommendation)
        .filter(Recommendation.user_id == user.id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )
