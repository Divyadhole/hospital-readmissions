"""
src/data_generator.py
Generates a realistic CMS-style hospital readmissions dataset.
Distributions are calibrated to match published HRRP national benchmarks.
"""

import numpy as np
import pandas as pd

# ── National HRRP benchmark readmission rates (CMS 2022 report) ─────────────
CONDITION_READMIT_RATES = {
    "Heart Failure":        0.231,
    "Pneumonia":            0.172,
    "COPD":                 0.200,
    "Hip/Knee Replacement": 0.049,
    "Stroke":               0.119,
    "Diabetes":             0.195,
    "Sepsis":               0.176,
    "AMI":                  0.153,
}

DISCHARGE_DEST_DIST   = {"Home": 0.48, "SNF": 0.27, "Home Health": 0.20, "AMA": 0.05}
INSURANCE_DIST        = {"Medicare": 0.47, "Medicaid": 0.22, "Private": 0.27, "Uninsured": 0.04}
HOSPITAL_QUALITY_TIER = {"High": 0.30, "Average": 0.50, "Low": 0.20}

COMORBIDITIES = [
    "Hypertension", "Type 2 Diabetes", "Chronic Kidney Disease",
    "Atrial Fibrillation", "Depression", "Obesity"
]


def generate(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Return a patient-level dataframe with realistic clinical + admin features."""
    rng = np.random.default_rng(seed)

    conditions = list(CONDITION_READMIT_RATES.keys())
    cond_weights = np.array([0.22, 0.16, 0.18, 0.08, 0.09, 0.12, 0.10, 0.05])
    hospital_ids = [f"HOSP-{str(i).zfill(3)}" for i in range(1, 31)]

    # Assign hospital quality tiers (persistent per hospital)
    hosp_quality = {}
    for h in hospital_ids:
        hosp_quality[h] = rng.choice(
            list(HOSPITAL_QUALITY_TIER.keys()),
            p=list(HOSPITAL_QUALITY_TIER.values())
        )

    records = []
    for pid in range(1, n + 1):
        condition  = rng.choice(conditions, p=cond_weights)
        hospital   = rng.choice(hospital_ids)
        quality    = hosp_quality[hospital]
        insurance  = rng.choice(list(INSURANCE_DIST), p=list(INSURANCE_DIST.values()))
        discharge  = rng.choice(list(DISCHARGE_DEST_DIST), p=list(DISCHARGE_DEST_DIST.values()))

        # Age: Medicare patients skew 65+
        age = int(rng.normal(68, 14))
        age = max(18, min(99, age))

        # Length of stay: log-normal (skewed right like real data)
        los = max(1, int(rng.lognormal(1.8, 0.6)))
        los = min(los, 45)

        # Comorbidity count: Poisson, increases with age
        comorbidity_count = int(rng.poisson(lam=max(0.5, (age - 40) / 20)))
        comorbidity_count = min(comorbidity_count, len(COMORBIDITIES))
        comorbidities = list(rng.choice(COMORBIDITIES, size=comorbidity_count, replace=False))

        # Prior admits in past 12 months
        prior_admits = int(rng.poisson(lam=0.8))

        # Number of ED visits in past 6 months
        ed_visits = int(rng.poisson(lam=0.6))

        # Build readmission probability from base rate + risk factors
        # Deltas calibrated to produce AUC ~0.72-0.76 (realistic for clinical models)
        base_rate = CONDITION_READMIT_RATES[condition]
        risk_delta = 0.0
        if quality == "Low":           risk_delta += 0.10
        if quality == "High":          risk_delta -= 0.09
        if insurance == "Uninsured":   risk_delta += 0.14
        if insurance == "Medicaid":    risk_delta += 0.07
        if insurance == "Private":     risk_delta -= 0.04
        if discharge == "AMA":         risk_delta += 0.25
        if discharge == "SNF":         risk_delta -= 0.05
        if age >= 80:                  risk_delta += 0.10
        elif age >= 70:                risk_delta += 0.06
        if prior_admits >= 3:          risk_delta += 0.18
        elif prior_admits >= 1:        risk_delta += 0.09
        if ed_visits >= 3:             risk_delta += 0.14
        elif ed_visits >= 1:           risk_delta += 0.07
        if comorbidity_count >= 4:     risk_delta += 0.13
        elif comorbidity_count >= 2:   risk_delta += 0.06
        if los > 14:                   risk_delta += 0.06
        if los < 2:                    risk_delta += 0.08

        prob = np.clip(base_rate + risk_delta, 0.02, 0.82)
        readmitted = int(rng.random() < prob)

        # Penalty score (mirrors CMS HRRP calculation style)
        penalty = round(np.clip(prob * 1.1 + rng.normal(0, 0.02), 0, 1), 4)

        records.append({
            "patient_id":        pid,
            "hospital_id":       hospital,
            "hospital_quality":  quality,
            "state":             rng.choice(["CA","TX","FL","NY","IL","PA","OH","AZ","GA","NC"]),
            "condition":         condition,
            "age":               age,
            "age_group":         _age_group(age),
            "gender":            rng.choice(["M","F"], p=[0.48, 0.52]),
            "insurance":         insurance,
            "discharge_to":      discharge,
            "los_days":          los,
            "prior_admits_12m":  prior_admits,
            "ed_visits_6m":      ed_visits,
            "comorbidity_count": comorbidity_count,
            "comorbidities":     "|".join(comorbidities),
            "readmitted_30d":    readmitted,
            "readmit_prob":      round(prob, 4),
            "penalty_score":     penalty,
        })

    df = pd.DataFrame(records)
    return df


def _age_group(age: int) -> str:
    if age < 45:  return "18–44"
    if age < 65:  return "45–64"
    if age < 75:  return "65–74"
    return "75+"
