"""Prediction ORM model.

The original Django app kept predictions only in the session (nothing was
persisted).  The FastAPI version stores each prediction so that
``GET /reports/{prediction_id}`` can regenerate the PDF later.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    user: Mapped["User"] = relationship(back_populates="predictions")  # noqa: F821

    # --- 22 model input features (values exactly as submitted) ---
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[int] = mapped_column(Integer)
    air_pollution: Mapped[int] = mapped_column(Integer)
    alcohol_use: Mapped[int] = mapped_column(Integer)
    dust_allergy: Mapped[int] = mapped_column(Integer)
    occupational_hazards: Mapped[int] = mapped_column(Integer)
    genetic_risk: Mapped[int] = mapped_column(Integer)
    chronic_lung_disease: Mapped[int] = mapped_column(Integer)
    balanced_diet: Mapped[int] = mapped_column(Integer)
    obesity: Mapped[int] = mapped_column(Integer)
    smoking: Mapped[int] = mapped_column(Integer)
    passive_smoker: Mapped[int] = mapped_column(Integer)
    chest_pain: Mapped[int] = mapped_column(Integer)
    coughing_of_blood: Mapped[int] = mapped_column(Integer)
    fatigue: Mapped[int] = mapped_column(Integer)
    weight_loss: Mapped[int] = mapped_column(Integer)
    shortness_of_breath: Mapped[int] = mapped_column(Integer)
    wheezing: Mapped[int] = mapped_column(Integer)
    swallowing_difficulty: Mapped[int] = mapped_column(Integer)
    clubbing_of_finger_nails: Mapped[int] = mapped_column(Integer)
    frequent_cold: Mapped[int] = mapped_column(Integer)
    dry_cough: Mapped[int] = mapped_column(Integer)
    snoring: Mapped[int] = mapped_column(Integer)

    # --- Prediction output ---
    diagnosis: Mapped[str] = mapped_column(String(16))  # Positive / Medium / Negative
    diagnosis_code: Mapped[int] = mapped_column(Integer)  # 1 / 0 / -1
    probability: Mapped[float] = mapped_column(Float)

    # --- Derived report data (stored as JSON, structure matches views.py) ---
    risk_factors: Mapped[list] = mapped_column(JSON)
    premium_amount: Mapped[float] = mapped_column(Float)
    premium_factors: Mapped[list] = mapped_column(JSON)
    doctor: Mapped[dict] = mapped_column(JSON)
    digital_signature: Mapped[str] = mapped_column(String(255))
    report_date: Mapped[str] = mapped_column(String(10))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Prediction id={self.id} user_id={self.user_id} {self.diagnosis}>"
