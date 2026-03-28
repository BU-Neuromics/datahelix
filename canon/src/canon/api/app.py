"""Canon FastAPI application — dynamic rule registration API."""

from __future__ import annotations

try:
    from fastapi import FastAPI
except ImportError as _exc:
    raise ImportError(
        "fastapi is required for the Canon API. "
        "Install it with: pip install canon[api]"
    ) from _exc

from canon.api.rules import router

app = FastAPI(
    title="Canon API",
    description="Dynamic rule registration and runtime management for Canon.",
    version="0.2.0",
)

app.include_router(router, prefix="/api/v1")
