"""
src/stats_analysis.py
Rigorous statistical testing — chi-square, t-tests, effect sizes, confidence intervals.
"""

import numpy as np
import pandas as pd
from scipy import stats


def readmission_by_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Rate, CI, and n for each category. Wilson score interval."""
    rows = []
    for val, grp in df.groupby(group_col):
        n   = len(grp)
        k   = grp["readmitted_30d"].sum()
        p   = k / n
        lo, hi = _wilson_ci(k, n)
        rows.append({
            "group":            val,
            "n":                n,
            "readmitted":       k,
            "rate_pct":         round(p * 100, 2),
            "ci_low_pct":       round(lo * 100, 2),
            "ci_high_pct":      round(hi * 100, 2),
        })
    return pd.DataFrame(rows).sort_values("rate_pct", ascending=False).reset_index(drop=True)


def chi_square_test(df: pd.DataFrame, col: str) -> dict:
    """Chi-square test of independence between `col` and readmission."""
    ct  = pd.crosstab(df[col], df["readmitted_30d"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    cramers_v = np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))
    return {
        "variable":    col,
        "chi2":        round(chi2, 3),
        "p_value":     round(p, 6),
        "dof":         dof,
        "cramers_v":   round(cramers_v, 4),
        "significant": p < 0.05,
        "effect_size": _effect_label(cramers_v),
    }


def t_test_los(df: pd.DataFrame) -> dict:
    """Independent t-test: LOS for readmitted vs not."""
    a = df[df["readmitted_30d"] == 1]["los_days"]
    b = df[df["readmitted_30d"] == 0]["los_days"]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    cohens_d = (a.mean() - b.mean()) / np.sqrt((a.std()**2 + b.std()**2) / 2)
    return {
        "mean_readmitted":     round(a.mean(), 2),
        "mean_not_readmitted": round(b.mean(), 2),
        "t_stat":              round(t, 3),
        "p_value":             round(p, 6),
        "cohens_d":            round(cohens_d, 4),
        "significant":         p < 0.05,
    }


def risk_factor_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Odds ratios for binary/binned risk factors."""
    rows = []
    binary_cols = ["prior_admits_12m", "ed_visits_6m", "comorbidity_count"]
    for col in binary_cols:
        threshold = df[col].median()
        hi = df[df[col] > threshold]["readmitted_30d"]
        lo = df[df[col] <= threshold]["readmitted_30d"]
        p_hi, p_lo = hi.mean(), lo.mean()
        if p_lo in (0, 1):
            continue
        or_ = (p_hi / (1 - p_hi)) / (p_lo / (1 - p_lo))
        rows.append({
            "factor":       col,
            "threshold":    f"> {threshold}",
            "rate_above":   round(p_hi * 100, 1),
            "rate_below":   round(p_lo * 100, 1),
            "odds_ratio":   round(or_, 3),
        })
    return pd.DataFrame(rows).sort_values("odds_ratio", ascending=False)


# ── helpers ──────────────────────────────────────────────────────────────────

def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple:
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return max(0, center - margin), min(1, center + margin)


def _effect_label(v: float) -> str:
    if v < 0.1:  return "negligible"
    if v < 0.3:  return "small"
    if v < 0.5:  return "medium"
    return "large"
