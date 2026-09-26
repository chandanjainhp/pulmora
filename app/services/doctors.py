"""Doctor recommendation logic — ported verbatim from Home/views.py.

Mapping (unchanged from the original):
    Positive -> Dr. Michael Chen (Oncology)
    Medium   -> Dr. Sarah Johnson (Pulmonology)
    Negative -> Dr. Emily Rodriguez (Thoracic Surgery)
"""
from __future__ import annotations

DOCTORS: list[dict] = [
    {
        "name": "Dr. Sarah Johnson",
        "specialty": "Pulmonology",
        "hospital": "Memorial Cancer Institute",
        "contact": "+1 (555) 123-4567",
        "recommendation": (
            "Recommended for comprehensive lung evaluation and treatment planning."
        ),
    },
    {
        "name": "Dr. Michael Chen",
        "specialty": "Oncology",
        "hospital": "City Medical Center",
        "contact": "+1 (555) 987-6543",
        "recommendation": (
            "Specializes in early-stage lung cancer treatment with minimally "
            "invasive approaches."
        ),
    },
    {
        "name": "Dr. Emily Rodriguez",
        "specialty": "Thoracic Surgery",
        "hospital": "University Hospital",
        "contact": "+1 (555) 456-7890",
        "recommendation": (
            "Expert in surgical interventions for lung conditions with advanced "
            "robotic techniques."
        ),
    },
]


def get_doctor_recommendation(diagnosis: str) -> dict:
    if diagnosis == "Positive":
        return DOCTORS[1]  # Oncologist for positive diagnosis
    elif diagnosis == "Medium":
        return DOCTORS[0]  # Pulmonologist for medium risk
    else:
        return DOCTORS[2]  # Thoracic surgeon for general cases
