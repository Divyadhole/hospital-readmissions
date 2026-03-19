"""
src/model.py
Logistic regression readmission risk model with feature importance,
calibration, and threshold analysis.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model    import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing   import StandardScaler, LabelEncoder
from sklearn.metrics         import (
    roc_auc_score, average_precision_score,
    classification_report, confusion_matrix,
    roc_curve, precision_recall_curve,
)
from sklearn.pipeline        import Pipeline
from sklearn.calibration     import calibration_curve
import warnings
warnings.filterwarnings("ignore")


FEATURES = [
    "age", "los_days", "prior_admits_12m", "ed_visits_6m",
    "comorbidity_count",
    "condition_enc", "insurance_enc", "discharge_enc",
    "hospital_quality_enc",
]


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col, enc_col in [
        ("condition",        "condition_enc"),
        ("insurance",        "insurance_enc"),
        ("discharge_to",     "discharge_enc"),
        ("hospital_quality", "hospital_quality_enc"),
    ]:
        le = LabelEncoder()
        out[enc_col] = le.fit_transform(out[col])
    return out


def train_evaluate(df: pd.DataFrame) -> dict:
    df2 = prepare_features(df)
    X   = df2[FEATURES].values
    y   = df2["readmitted_30d"].values

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)),
    ])

    # 5-fold cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        pipe, X, y, cv=cv,
        scoring=["roc_auc", "average_precision"],
        return_train_score=False,
    )

    # Full fit for feature importance + curves
    pipe.fit(X, y)
    coef     = pipe.named_steps["clf"].coef_[0]
    y_prob   = pipe.predict_proba(X)[:, 1]
    y_pred   = (y_prob >= 0.35).astype(int)   # adjusted threshold for imbalanced data

    # Feature importance dataframe
    importance = pd.DataFrame({
        "feature":    FEATURES,
        "coefficient": coef,
        "abs_coef":   np.abs(coef),
        "direction":  ["Risk ↑" if c > 0 else "Risk ↓" for c in coef],
    }).sort_values("abs_coef", ascending=False).reset_index(drop=True)

    # Calibration
    prob_true, prob_pred = calibration_curve(y, y_prob, n_bins=10)

    # ROC
    fpr, tpr, roc_thresh = roc_curve(y, y_prob)

    # Confusion matrix
    cm = confusion_matrix(y, y_pred)

    return {
        "pipeline":      pipe,
        "cv_auc_mean":   round(cv_results["test_roc_auc"].mean(), 4),
        "cv_auc_std":    round(cv_results["test_roc_auc"].std(),  4),
        "cv_ap_mean":    round(cv_results["test_average_precision"].mean(), 4),
        "auc":           round(roc_auc_score(y, y_prob), 4),
        "avg_precision": round(average_precision_score(y, y_prob), 4),
        "class_report":  classification_report(y, y_pred, output_dict=True),
        "confusion_matrix": cm,
        "importance":    importance,
        "fpr":           fpr,
        "tpr":           tpr,
        "y_prob":        y_prob,
        "y_true":        y,
        "calib_true":    prob_true,
        "calib_pred":    prob_pred,
    }


def score_patients(df: pd.DataFrame, results: dict) -> pd.DataFrame:
    """Attach risk score + tier to every patient."""
    df2  = prepare_features(df)
    pipe = results["pipeline"]
    prob = pipe.predict_proba(df2[FEATURES].values)[:, 1]
    out  = df.copy()
    out["risk_score"] = prob.round(4)
    out["risk_tier"]  = pd.cut(
        prob,
        bins=[0, 0.15, 0.30, 0.50, 1.0],
        labels=["Low", "Moderate", "High", "Critical"],
    )
    return out
