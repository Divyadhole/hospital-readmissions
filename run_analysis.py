"""
run_analysis.py
End-to-end pipeline: generate → analyze → model → score → report
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from src.data_generator import generate
from src.stats_analysis  import (
    readmission_by_group, chi_square_test,
    t_test_los, risk_factor_summary
)
from src.model  import train_evaluate, score_patients
from src.charts import (
    chart_condition_rates, chart_hospital_matrix,
    chart_feature_importance, chart_model_performance,
    chart_risk_tiers, chart_cohort_heatmap,
)

CHARTS = "outputs/charts"
os.makedirs(CHARTS, exist_ok=True)
os.makedirs("outputs/report", exist_ok=True)
os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

print("=" * 60)
print("  HOSPITAL READMISSIONS ANALYSIS — FULL PIPELINE")
print("=" * 60)

# ── 1. Data ───────────────────────────────────────────────────
print("\n[1/5] Generating dataset...")
df = generate(n=5000, seed=42)
df.to_csv("data/raw/hospital_readmissions.csv", index=False)
print(f"  ✓ {len(df):,} patients · {df.columns.size} features")
print(f"  ✓ Overall readmission rate: {df['readmitted_30d'].mean()*100:.2f}%")

# ── 2. Statistical Analysis ───────────────────────────────────
print("\n[2/5] Running statistical analysis...")

condition_rates = readmission_by_group(df, "condition")
insurance_rates = readmission_by_group(df, "insurance")
discharge_rates = readmission_by_group(df, "discharge_to")
quality_rates   = readmission_by_group(df, "hospital_quality")
age_rates       = readmission_by_group(df, "age_group")

chi_tests = [
    chi_square_test(df, col)
    for col in ["condition","insurance","discharge_to","hospital_quality","age_group"]
]
chi_df = pd.DataFrame(chi_tests)

los_test = t_test_los(df)
risk_factors = risk_factor_summary(df)

print("  Chi-square results:")
for r in chi_tests:
    sig = "✓ SIGNIFICANT" if r["significant"] else "✗ not significant"
    print(f"    {r['variable']:25s} χ²={r['chi2']:8.2f}  p={r['p_value']:.4f}  "
          f"Cramér's V={r['cramers_v']:.3f} [{r['effect_size']}]  {sig}")

print(f"\n  LOS t-test: readmitted={los_test['mean_readmitted']}d vs "
      f"not={los_test['mean_not_readmitted']}d  "
      f"p={los_test['p_value']:.4f}  Cohen's d={los_test['cohens_d']:.3f}")

# ── 3. Charts ─────────────────────────────────────────────────
print("\n[3/5] Generating charts...")
chart_condition_rates(condition_rates, f"{CHARTS}/01_condition_rates_ci.png")
chart_hospital_matrix(df,              f"{CHARTS}/02_hospital_matrix.png")
chart_cohort_heatmap(df,               f"{CHARTS}/03_cohort_heatmap.png")

# ── 4. ML Model ───────────────────────────────────────────────
print("\n[4/5] Training predictive model...")
results = train_evaluate(df)
print(f"  ✓ CV AUC : {results['cv_auc_mean']:.4f} ± {results['cv_auc_std']:.4f}")
print(f"  ✓ Test AUC: {results['auc']:.4f}")
print(f"  ✓ Avg Precision: {results['avg_precision']:.4f}")

chart_feature_importance(results["importance"], f"{CHARTS}/04_feature_importance.png")
chart_model_performance(results,                f"{CHARTS}/05_model_performance.png")

scored_df = score_patients(df, results)
scored_df.to_csv("data/processed/scored_patients.csv", index=False)
chart_risk_tiers(scored_df, f"{CHARTS}/06_risk_tiers.png")

# ── 5. Summary stats for report ───────────────────────────────
print("\n[5/5] Writing processed data...")

summary = {
    "total_patients":      len(df),
    "readmission_rate":    round(df["readmitted_30d"].mean()*100, 2),
    "avg_los":             round(df["los_days"].mean(), 1),
    "cv_auc":              results["cv_auc_mean"],
    "cv_auc_std":          results["cv_auc_std"],
    "auc":                 results["auc"],
    "avg_precision":       results["avg_precision"],
    "top_condition":       condition_rates.iloc[0]["group"],
    "top_condition_rate":  condition_rates.iloc[0]["rate_pct"],
    "top_insurer_risk":    insurance_rates.iloc[0]["group"],
    "top_insurer_rate":    insurance_rates.iloc[0]["rate_pct"],
    "top_discharge_risk":  discharge_rates.iloc[0]["group"],
    "high_critical_pct":   round(
        scored_df["risk_tier"].isin(["High","Critical"]).mean()*100, 1
    ),
    "los_p_value":         los_test["p_value"],
    "los_cohens_d":        los_test["cohens_d"],
}
pd.Series(summary).to_json("outputs/report/summary_stats.json")

condition_rates.to_csv("data/processed/condition_rates.csv", index=False)
insurance_rates.to_csv("data/processed/insurance_rates.csv", index=False)
chi_df.to_csv("data/processed/chi_square_results.csv",      index=False)
results["importance"].to_csv("data/processed/feature_importance.csv", index=False)
scored_df.groupby("risk_tier", observed=True)[["readmitted_30d","los_days","age"]]\
         .mean().round(2)\
         .to_csv("data/processed/risk_tier_profile.csv")

print("\n" + "=" * 60)
print("  PIPELINE COMPLETE")
print("=" * 60)
print(f"  Charts  → outputs/charts/   ({6} files)")
print(f"  Data    → data/processed/   ({5} files)")
print(f"  Report  → outputs/report/")
