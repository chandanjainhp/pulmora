"""FastAPI application entry point.

Run with:

    uvicorn app.main:app --reload

The logistic regression model is trained once at startup (lifespan handler)
instead of on every request as the original Django view did.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from starlette.requests import Request

from app.core.config import settings
from app.core.rate_limit import limiter
from app.routers import auth, pages, predict, reports
from app.services.ml_service import train_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Train / load the ML model once, before serving requests ---
    app.state.ml_model = train_model(settings.DATASET_PATH)
    logger.info(
        "Model ready (held-out accuracy: %.4f)", app.state.ml_model.train_accuracy
    )
    yield
    # Nothing to tear down (in-memory model, pooled DB connections).
    app.state.ml_model = None


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Lung cancer risk prediction with insurance premium calculation, "
        "doctor recommendations and PDF reports. "
        "Interactive docs at /docs, ReDoc at /redoc."
    ),
    lifespan=lifespan,
)

# --- Rate limiting (slowapi) --------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files (same /static/ URLs the templates used in Django) ----------
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Routers -------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(reports.router)
app.include_router(pages.router)


@app.get("/health", tags=["health"], summary="Liveness probe")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "model_loaded": getattr(request.app.state, "ml_model", None) is not None,
    }


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    # Original site root served home.html; keep the same behaviour.
    return RedirectResponse(url="/pages/home", status_code=307)
