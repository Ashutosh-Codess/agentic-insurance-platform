"""Import every model module here so Base.metadata is fully populated
before Alembic autogenerate or Base.metadata.create_all() runs."""
from app.models.user import User, RefreshToken  # noqa: F401
from app.models.policy import Product, Policy, Recommendation  # noqa: F401
from app.models.claim import Claim, Notification  # noqa: F401
from app.models.document import Document  # noqa: F401
