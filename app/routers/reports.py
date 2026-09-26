"""Report endpoints: list stored reports and download the PDF for one."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.report import ReportList, ReportSummary
from app.services.pdf_report import build_report_context, generate_pdf_bytes, pdf_response

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_owned_prediction(
    db: Session, user: User, prediction_id: int
) -> Prediction:
    prediction = (
        db.query(Prediction)
        .filter(Prediction.id == prediction_id, Prediction.user_id == user.id)
        .first()
    )
    if prediction is None:
        # 404 (not 403) so ids of other users are not enumerable.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return prediction


@router.get(
    "",
    response_model=ReportList,
    summary="List the current user's reports",
)
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportList:
    rows = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(100)
        .all()
    )
    return ReportList(
        count=len(rows),
        reports=[
            ReportSummary(
                id=r.id,
                diagnosis=r.diagnosis,
                report_date=r.report_date,
                created_at=r.created_at,
                pdf_url=f"/reports/{r.id}",
            )
            for r in rows
        ],
    )


@router.get(
    "/{prediction_id}",
    response_class=Response,
    summary="Download the PDF report for a prediction (requires auth)",
    responses={
        200: {
            "description": "PDF report",
            "content": {"application/pdf": {}},
        }
    },
)
def get_report(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prediction = _get_owned_prediction(db, current_user, prediction_id)

    context = build_report_context(
        user=current_user,
        diagnosis=prediction.diagnosis,
        age=prediction.age,
        gender=prediction.gender,
        risk_factors=prediction.risk_factors,
        premium_amount=prediction.premium_amount,
        premium_factors=prediction.premium_factors,
        doctor=prediction.doctor,
        digital_signature=prediction.digital_signature,
        report_date=prediction.report_date,
    )
    pdf_bytes = generate_pdf_bytes(context)
    return pdf_response(pdf_bytes, current_user.username)
