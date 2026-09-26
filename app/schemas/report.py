"""Pydantic schemas for reports (PDF + listing of stored predictions)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportSummary(BaseModel):
    """Metadata about one stored prediction/report."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    diagnosis: str
    report_date: str
    created_at: datetime
    pdf_url: str


class ReportList(BaseModel):
    count: int
    reports: list[ReportSummary]
