"""PDF report generation with WeasyPrint (replaces xhtml2pdf/PyPDF2).

Renders the existing ``templates/insurance_report.html`` through Jinja2 and
converts it to PDF, producing the same report content as the original Django
``render_to_pdf`` helper.  The file name and inline Content-Disposition match
the original view:

    Lung_Cancer_Insurance_Report_{username}_{YYYYMMDD}.pdf  (inline)
"""
from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.user import User

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _static(path: str) -> str:
    return f"/static/{path.lstrip('/')}"


_jinja_env.globals["static"] = _static


def build_report_context(
    user: User,
    diagnosis: str,
    age: int,
    gender: int,
    risk_factors: list[dict],
    premium_amount: float,
    premium_factors: list[dict],
    doctor: dict,
    digital_signature: str,
    report_date: str,
) -> dict:
    now = datetime.datetime.now()
    return {
        "user": user,
        "diagnosis": diagnosis,
        "age": age,
        "gender": gender,
        "risk_factors": risk_factors,
        "premium_amount": premium_amount,
        "premium_factors": premium_factors,
        "doctor": doctor,
        "digital_signature": digital_signature,
        "report_date": report_date,
        "now_year": now.strftime("%Y"),
    }


def generate_pdf_bytes(context: dict) -> bytes:
    """Render insurance_report.html to PDF bytes."""
    html = _jinja_env.get_template("insurance_report.html").render(**context)
    return HTML(string=html, base_url=str(BASE_DIR)).write_pdf()


def pdf_response(pdf_bytes: bytes, username: str) -> Response:
    """Build the inline PDF response with the original file-naming scheme."""
    filename = (
        f"Lung_Cancer_Insurance_Report_{username}_"
        f"{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
