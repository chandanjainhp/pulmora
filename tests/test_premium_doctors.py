"""Business-rule parity tests.

Golden values below were produced by running the ORIGINAL Django code
(Home/views.py calculate_premium + build_risk_factors, extracted verbatim)
on the same inputs - they pin bug-compatible behaviour.  See
MIGRATION_NOTES.md: the original loop re-uses the previous factor's impact
for factors that match no branch; that behaviour is preserved.
"""
import pytest

from app.services.premium import build_risk_factors, calculate_premium
from app.services.doctors import get_doctor_recommendation

# (age, gender, air, alcohol, dust, occupational, genetic, chronic, smoking,
#  passive, chest, coughing_blood, diagnosis, expected_total_inr)
GOLDEN_CASES = [
    (33, 1, 2, 4, 5, 4, 3, 2, 3, 2, 2, 4, "Negative", 19098.75),
    (55, 1, 7, 8, 7, 6, 7, 6, 8, 7, 8, 8, "Positive", 48757.5),
    (45, 2, 5, 3, 5, 4, 5, 3, 2, 4, 5, 3, "Medium", 26718.75),
    (25, 2, 1, 1, 2, 1, 2, 1, 1, 1, 2, 1, "Negative", 14062.5),
    (65, 1, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, "Positive", 53484.75),
]

# Golden factor breakdowns (name, impact) from the original code.
GOLDEN_FACTORS = {
    19098.75: [("Age Factor", 1237.5), ("Base Premium", 3750.0)],
    48757.5: [
        ("Age Factor", 2062.5), ("Air Pollution", 630.0), ("Alcohol use", 720.0),
        ("Dust Allergy", 630.0), ("OccuPational Hazards", 540.0),
        ("Genetic Risk", 1312.5), ("Chronic Lung Disease", 1260.0),
        ("Smoking", 1800), ("Passive Smoker", 630.0), ("Chest Pain", 720.0),
        ("Coughing of Blood", 720.0), ("Base Premium", 3750.0),
        ("Diagnosis Risk", 7500.0),
    ],
    26718.75: [
        ("Age Factor", 1687.5), ("Genetic Risk", 937.5),
        ("Base Premium", 3750.0), ("Diagnosis Risk", 1875.0),
    ],
    14062.5: [("Age Factor", 937.5), ("Base Premium", 3750.0)],
    53484.75: [
        ("Age Factor", 2437.5), ("Air Pollution", 720.0), ("Alcohol use", 720.0),
        ("Dust Allergy", 720.0), ("OccuPational Hazards", 720.0),
        ("Genetic Risk", 1500.0), ("Chronic Lung Disease", 1680.0),
        ("Smoking", 1800), ("Passive Smoker", 720.0), ("Chest Pain", 720.0),
        ("Coughing of Blood", 720.0), ("Base Premium", 3750.0),
        ("Diagnosis Risk", 7500.0),
    ],
}


def _risk_factors(case):
    (age, _gender, air, alcohol, dust, occupational, genetic, chronic,
     smoking, passive, chest, cough, _diagnosis, _expected) = case
    return build_risk_factors(
        age, air, alcohol, dust, occupational, genetic, chronic,
        smoking, passive, chest, cough,
    )


@pytest.mark.parametrize("case", GOLDEN_CASES)
def test_premium_matches_original_views_py(case):
    age, gender = case[0], case[1]
    diagnosis, expected_total = case[12], case[13]
    factors = _risk_factors(case)

    total, premium_factors = calculate_premium(age, gender, diagnosis, factors)

    assert total == expected_total
    expected_factors = GOLDEN_FACTORS[expected_total]
    assert [(f["name"], f["impact"]) for f in premium_factors] == expected_factors


def test_risk_factor_thresholds_match_original():
    factors = build_risk_factors(
        # age, air, alcohol, dust, occupational, genetic, chronic,
        # smoking, passive, chest, cough
        65, 7, 3, 4, 7, 5, 2, 5, 2, 7, 6,
    )
    by_name = {f["name"]: f for f in factors}
    # Age: >60 High, >40 Medium, else Low
    assert by_name["Age"]["risk_level"] == "High"
    # value > 6 -> High, > 3 -> Medium, else Low
    assert by_name["Air Pollution"]["risk_level"] == "High"
    assert by_name["Alcohol use"]["risk_level"] == "Low"  # 3 is not > 3
    assert by_name["Dust Allergy"]["risk_level"] == "Medium"
    assert by_name["OccuPational Hazards"]["risk_level"] == "High"
    assert by_name["Genetic Risk"]["risk_level"] == "Medium"
    assert by_name["chronic Lung Disease"]["risk_level"] == "Low"
    assert by_name["Smoking"]["risk_level"] == "Medium"
    assert by_name["Passive Smoker"]["risk_level"] == "Low"
    assert by_name["Chest Pain"]["risk_level"] == "High"
    assert by_name["Coughing of Blood"]["risk_level"] == "Medium"
    # Exactly the 11 factors of the original view, in the original order.
    assert [f["name"] for f in factors] == [
        "Age", "Air Pollution", "Alcohol use", "Dust Allergy",
        "OccuPational Hazards", "Genetic Risk", "chronic Lung Disease",
        "Smoking", "Passive Smoker", "Chest Pain", "Coughing of Blood",
    ]


def test_doctor_mapping_matches_original():
    assert get_doctor_recommendation("Positive")["name"] == "Dr. Michael Chen"
    assert get_doctor_recommendation("Positive")["specialty"] == "Oncology"
    assert get_doctor_recommendation("Medium")["name"] == "Dr. Sarah Johnson"
    assert get_doctor_recommendation("Medium")["specialty"] == "Pulmonology"
    assert get_doctor_recommendation("Negative")["name"] == "Dr. Emily Rodriguez"
    assert get_doctor_recommendation("Negative")["specialty"] == "Thoracic Surgery"
    # Anything unexpected falls through to the thoracic surgeon, as in views.py.
    assert get_doctor_recommendation("whatever")["name"] == "Dr. Emily Rodriguez"
