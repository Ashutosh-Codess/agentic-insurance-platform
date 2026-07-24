import uuid
from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.policy import Policy, Product
from app.models.user import User
from app.schemas.policy import PolicyOut, PolicyPurchaseRequest, ProductCreateRequest, ProductOut

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
def list_products(category: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Product).filter(Product.is_active.is_(True))
    if category:
        query = query.filter(Product.category == category)
    return query.all()


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductCreateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for field, value in payload.model_dump().items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def _check_eligibility(user: User, eligibility_rules: dict) -> None:
    age = user.age()
    min_age = eligibility_rules.get("min_age")
    max_age = eligibility_rules.get("max_age")
    if age is not None:
        if min_age is not None and age < min_age:
            raise HTTPException(status_code=400, detail=f"Age {age} is below the minimum eligible age {min_age}.")
        if max_age is not None and age > max_age:
            raise HTTPException(status_code=400, detail=f"Age {age} is above the maximum eligible age {max_age}.")
    excluded_occupations = eligibility_rules.get("excluded_occupations") or []
    if user.occupation and user.occupation in excluded_occupations:
        raise HTTPException(status_code=400, detail=f"Occupation '{user.occupation}' is not eligible for this product.")


@router.post("/products/{product_id}/purchase", response_model=PolicyOut, status_code=201)
def purchase_policy(
    product_id: uuid.UUID,
    payload: PolicyPurchaseRequest,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found or not currently offered")

    _check_eligibility(current_user, product.eligibility_rules or {})

    risk_score = float(current_user.risk_score or 0)
    premium_amount = round(float(product.base_premium) * (1 + risk_score * 0.01), 2)

    start = date.today()
    policy = Policy(
        user_id=current_user.id,
        product_id=product.id,
        status="active",
        start_date=start,
        end_date=start + relativedelta(years=1),
        sum_insured=payload.sum_insured,
        premium_amount=premium_amount,
        next_due_date=start + relativedelta(months=1),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/customers/me/policies", response_model=list[PolicyOut])
def list_my_policies(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return db.query(Policy).filter(Policy.user_id == current_user.id).all()


@router.get("/policies/{policy_id}", response_model=PolicyOut)
def get_policy(
    policy_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    if current_user.role == "customer" and policy.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This policy does not belong to you")
    return policy
