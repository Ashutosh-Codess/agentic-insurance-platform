"""
Application entrypoint. Every router is included here with the shared
/api/v1 prefix -- this is the one place that shows the entire API surface
of the project at a glance.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import agents, auth, claims, customers, products

app = FastAPI(
    title=settings.APP_NAME,
    description="A final-year-project-scoped Agentic Insurance Platform: FastAPI + PostgreSQL + OpenCV/TensorFlow AI modules.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CUSTOMER_PORTAL_ORIGIN, settings.AGENT_PORTAL_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """A single, consistent JSON error shape across the whole API."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(customers.router, prefix=settings.API_PREFIX)
app.include_router(products.router, prefix=settings.API_PREFIX)
app.include_router(claims.router, prefix=settings.API_PREFIX)
app.include_router(agents.router, prefix=settings.API_PREFIX)


@app.get("/health")
def health():
    """Liveness probe -- no DB dependency on purpose, so it reflects
    process health, not database health."""
    return {"status": "ok"}
