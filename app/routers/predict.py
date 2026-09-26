"""JSON prediction endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import PredictionInput, PredictionResponse
from app.services.ml_service import MLModel
from app.services.pipeline import run_prediction

router = APIRouter(tags=["predict"])


def get_ml_model(request: Request) -> MLModel:
    """The model trained once at startup (stored on app.state by lifespan)."""
    return request.app.state.ml_model


@router.post(
    "/predict",
    response_model=PredictionResponse,
    response_model_by_alias=False,
    summary="Predict lung cancer risk, insurance premium and doctor",
)
@limiter.limit(lambda: request_limit())  # e.g. "10/minute" via PREDICT_RATE_LIMIT
def predict(
    request: Request,
    payload: PredictionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ml_model: MLModel = Depends(get_ml_model),
) -> Prediction:
    """Accepts the 22 model parameters and returns the risk class,
    probability, insurance premium breakdown and doctor recommendation."""
    return run_prediction(db, current_user, payload, ml_model)


def request_limit() -> str:
    # Imported lazily to avoid a circular import at module load time.
    from app.core.config import settings

    return settings.PREDICT_RATE_LIMIT
