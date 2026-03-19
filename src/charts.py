"""
src/charts.py
Publication-quality charts — consistent style, annotated, recruiter-ready.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from matplotlib.gridspec import GridSpec

PALETTE = {
    "teal":    "#1D9E75",
    "purple":  "#534AB7",
    "amber":   "#BA7517",
    "red":     "#A32D2D",
    "coral":   "#D85A30",
    "neutral": "#5F5E5A",
    "light":   "#F1EFE8",
    "mid":     "#B4B2A9",
}

BASE_STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.spines.left": False,
    "axes.grid":        True,
    "axes.grid.axis":   "x",
    "grid.color":       "#E8E6E0",
    "grid.linewidth":   0.6,
    "font.family":      "DejaVu Sans",
    "axes.titlesize":   13,
    "axes.titleweight": "bold",
    "axes.labelsize":   11,
    "xtick.labelsize":  10,
    "ytick.labelsize":  10,
    "xtick.bottom":     False,
    "ytick.left":       False,
}


def _save(fig, path):
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {path}")


# ── Chart 1: Condition Readmission Rates with CI ──────────────────────────
def chart_condition_rates(rate_df: pd.DataFrame, path: str):
    with plt.rc_context(BASE_STYLE):
        df = rate_df.sort_values("rate_pct")
        avg = rate_df["rate_pct"].mean()

        fig, ax = plt.subplots(figsize=(10, 5.5))
        colors = [PALETTE["red"] if r > avg else PALETTE["teal"] for r in df["rate_pct"]]

        bars = ax.barh(df["group"], df["rate_pct"], color=colors, height=0.55, zorder=3)
        ax.errorbar(
            df["rate_pct"], df["group"],
            xerr=[df["rate_pct"] - df["ci_low_pct"], df["ci_high_pct"] - df["rate_pct"]],
            fmt="none", color=PALETTE["neutral"], capsize=4, linewidth=1.2, zorder=4
        )
        ax.axvline(avg, color=PALETTE["neutral"], linestyle="--", linewidth=1.2,
                   label=f"National avg: {avg:.1f}%", zorder=5)

        for bar, val, ci_hi in zip(bars, df["rate_pct"], df["ci_high_pct"]):
            ax.text(ci_hi + 0.4, bar.get_y() + bar.get_height()/2,
                    f"{val:.1f}%", va="center", fontsize=9.5, color=PALETTE["neutral"])

        ax.set_xlabel("30-Day Readmission Rate (%)")
        ax.set_title("30-Day Readmission Rate by Condition\nWith 95% Wilson Confidence Intervals")
        ax.legend(fontsize=9)

        above = mpatches.Patch(color=PALETTE["red"],  label="Above national avg")
        below = mpatches.Patch(color=PALETTE["teal"], label="Below national avg")
        ax.legend(handles=[above, below], fontsize=9, loc="lower right")

        _save(fig, path)


# ── Chart 2: Hospital Performance Matrix ─────────────────────────────────
def chart_hospital_matrix(df: pd.DataFrame, path: str):
    with plt.rc_context(BASE_STYLE):
        hosp = (df.groupby("hospital_id").agg(
            rate    = ("readmitted_30d", "mean"),
            avg_los = ("los_days",        "mean"),
            volume  = ("patient_id",      "count"),
            quality = ("hospital_quality","first"),
        ).reset_index())
        hosp["rate_pct"] = hosp["rate"] * 100

        color_map = {"High": PALETTE["teal"], "Average": PALETTE["amber"], "Low": PALETTE["red"]}
        colors = [color_map[q] for q in hosp["quality"]]

        fig, ax = plt.subplots(figsize=(10, 6))
        sc = ax.scatter(
            hosp["avg_los"], hosp["rate_pct"],
            s=hosp["volume"] * 0.8,
            c=colors, alpha=0.75, edgecolors="white", linewidths=0.8, zorder=3
        )
        avg_rate = hosp["rate_pct"].mean()
        avg_los  = hosp["avg_los"].mean()
        ax.axhline(avg_rate, color=PALETTE["neutral"], linestyle="--", linewidth=1, alpha=0.7)
        ax.axvline(avg_los,  color=PALETTE["neutral"], linestyle="--", linewidth=1, alpha=0.7)

        ax.text(avg_los + 0.1, ax.get_ylim()[1]*0.98, "Avg LOS →",
                color=PALETTE["neutral"], fontsize=8, va="top")
        ax.text(ax.get_xlim()[0], avg_rate + 0.2, f"Avg rate {avg_rate:.1f}%",
                color=PALETTE["neutral"], fontsize=8)

        patches = [mpatches.Patch(color=v, label=f"{k} quality") for k, v in color_map.items()]
        ax.legend(handles=patches, title="Hospital Quality", fontsize=9)

        ax.set_xlabel("Average Length of Stay (Days)")
        ax.set_ylabel("30-Day Readmission Rate (%)")
        ax.set_title("Hospital Performance Matrix\nBubble size = patient volume")

        _save(fig, path)


# ── Chart 3: ML Feature Importance ───────────────────────────────────────
def chart_feature_importance(importance_df: pd.DataFrame, path: str):
    feature_labels = {
        "prior_admits_12m":    "Prior Admissions (12m)",
        "ed_visits_6m":        "ED Visits (6m)",
        "comorbidity_count":   "Comorbidity Count",
        "age":                 "Patient Age",
        "los_days":            "Length of Stay",
        "discharge_enc":       "Discharge Destination",
        "insurance_enc":       "Insurance Type",
        "condition_enc":       "Primary Condition",
        "hospital_quality_enc":"Hospital Quality Tier",
    }
    with plt.rc_context(BASE_STYLE):
        df = importance_df.copy()
        df["label"] = df["feature"].map(feature_labels).fillna(df["feature"])
        df = df.sort_values("coefficient")

        colors = [PALETTE["red"] if c > 0 else PALETTE["teal"] for c in df["coefficient"]]
        fig, ax = plt.subplots(figsize=(10, 5.5))
        bars = ax.barh(df["label"], df["coefficient"], color=colors, height=0.55, zorder=3)
        ax.axvline(0, color=PALETTE["neutral"], linewidth=1)

        for bar, val in zip(bars, df["coefficient"]):
            xpos = val + 0.005 if val >= 0 else val - 0.005
            ha   = "left" if val >= 0 else "right"
            ax.text(xpos, bar.get_y() + bar.get_height()/2,
                    f"{val:+.3f}", va="center", ha=ha, fontsize=9)

        up   = mpatches.Patch(color=PALETTE["red"],  label="Increases readmission risk")
        down = mpatches.Patch(color=PALETTE["teal"], label="Decreases readmission risk")
        ax.legend(handles=[up, down], fontsize=9)

        ax.set_xlabel("Logistic Regression Coefficient")
        ax.set_title("Predictive Model — Feature Importance\n(Logistic Regression with Balanced Classes)")
        _save(fig, path)


# ── Chart 4: ROC + Calibration (2-panel) ─────────────────────────────────
def chart_model_performance(results: dict, path: str):
    with plt.rc_context({**BASE_STYLE, "axes.grid": False}):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # ROC
        ax1.plot(results["fpr"], results["tpr"],
                 color=PALETTE["purple"], lw=2,
                 label=f"AUC = {results['auc']:.3f}")
        ax1.plot([0,1],[0,1], color=PALETTE["mid"], linestyle="--", lw=1)
        ax1.fill_between(results["fpr"], results["tpr"], alpha=0.08, color=PALETTE["purple"])
        ax1.set_xlabel("False Positive Rate")
        ax1.set_ylabel("True Positive Rate")
        ax1.set_title("ROC Curve\n5-Fold CV AUC: "
                      f"{results['cv_auc_mean']:.3f} ± {results['cv_auc_std']:.3f}")
        ax1.legend(fontsize=10)
        ax1.spines["left"].set_visible(True)
        ax1.spines["bottom"].set_visible(True)

        # Calibration
        ax2.plot(results["calib_pred"], results["calib_true"],
                 "s-", color=PALETTE["teal"], lw=2, markersize=6, label="Model")
        ax2.plot([0,1],[0,1], color=PALETTE["mid"], linestyle="--", lw=1, label="Perfect calibration")
        ax2.set_xlabel("Mean Predicted Probability")
        ax2.set_ylabel("Fraction of Positives")
        ax2.set_title("Calibration Curve\n(Reliability Diagram)")
        ax2.legend(fontsize=10)
        ax2.spines["left"].set_visible(True)
        ax2.spines["bottom"].set_visible(True)

        fig.suptitle("Logistic Regression Model Evaluation", fontsize=14, fontweight="bold", y=1.01)
        _save(fig, path)


# ── Chart 5: Risk Tier Distribution ──────────────────────────────────────
def chart_risk_tiers(scored_df: pd.DataFrame, path: str):
    with plt.rc_context(BASE_STYLE):
        tier_order  = ["Low", "Moderate", "High", "Critical"]
        tier_colors = [PALETTE["teal"], PALETTE["amber"], PALETTE["coral"], PALETTE["red"]]

        counts  = scored_df["risk_tier"].value_counts().reindex(tier_order).fillna(0)
        rates   = (scored_df.groupby("risk_tier", observed=True)["readmitted_30d"]
                             .mean().reindex(tier_order) * 100)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Patient volume per tier
        bars = ax1.bar(tier_order, counts, color=tier_colors, width=0.55, zorder=3)
        for bar, val in zip(bars, counts):
            ax1.text(bar.get_x() + bar.get_width()/2, val + 15,
                     f"{int(val):,}", ha="center", fontsize=10)
        ax1.set_ylabel("Number of Patients")
        ax1.set_title("Patient Distribution by Risk Tier")
        ax1.set_xlabel("Risk Tier")

        # Actual readmission rate per tier
        bars2 = ax2.bar(tier_order, rates, color=tier_colors, width=0.55, zorder=3)
        for bar, val in zip(bars2, rates):
            ax2.text(bar.get_x() + bar.get_width()/2, val + 0.3,
                     f"{val:.1f}%", ha="center", fontsize=10)
        ax2.set_ylabel("Actual 30-Day Readmission Rate (%)")
        ax2.set_title("Actual Readmission Rate by Model Risk Tier")
        ax2.set_xlabel("Risk Tier")

        fig.suptitle("Patient Risk Stratification", fontsize=14, fontweight="bold")
        _save(fig, path)


# ── Chart 6: Cohort Heatmap ───────────────────────────────────────────────
def chart_cohort_heatmap(df: pd.DataFrame, path: str):
    with plt.rc_context({**BASE_STYLE, "axes.grid": False}):
        pivot = (df.pivot_table(
            values="readmitted_30d",
            index="condition", columns="insurance",
            aggfunc="mean"
        ) * 100).round(1)

        fig, ax = plt.subplots(figsize=(10, 5.5))
        sns.heatmap(
            pivot, annot=True, fmt=".1f", cmap="RdYlGn_r",
            linewidths=0.5, linecolor="#E0DED8",
            cbar_kws={"label": "Readmission Rate (%)"},
            ax=ax
        )
        ax.set_title("Readmission Rate Heatmap — Condition × Insurance\n"
                     "Darker = higher readmission risk", fontweight="bold")
        ax.set_xlabel("Insurance Type")
        ax.set_ylabel("Medical Condition")
        plt.xticks(rotation=25, ha="right")
        plt.yticks(rotation=0)
        _save(fig, path)
