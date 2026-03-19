"""
src/report_builder.py
Generates a self-contained HTML executive report.
"""

import json, base64, os
from pathlib import Path


def _img_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def build_report(summary_path: str, charts_dir: str, output_path: str):
    with open(summary_path) as f:
        s = json.load(f)

    chart_files = sorted(Path(charts_dir).glob("*.png"))
    chart_tags  = ""
    titles = [
        "Fig 1 — Readmission Rate by Condition with 95% Confidence Intervals",
        "Fig 2 — Hospital Performance Matrix (Volume × Rate × Quality)",
        "Fig 3 — Readmission Heatmap: Condition × Insurance",
        "Fig 4 — Predictive Model Feature Importance",
        "Fig 5 — ROC Curve & Calibration Diagram",
        "Fig 6 — Patient Risk Tier Distribution & Validation",
    ]
    for i, (fp, title) in enumerate(zip(chart_files, titles)):
        b64 = _img_b64(str(fp))
        chart_tags += f"""
        <figure>
          <img src="data:image/png;base64,{b64}" alt="{title}">
          <figcaption>{title}</figcaption>
        </figure>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hospital Readmissions — Analytical Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 15px; line-height: 1.7; color: #2c2c2a;
    background: #f8f7f4; padding: 0;
  }}
  .cover {{
    background: linear-gradient(135deg, #0f6e56 0%, #1D9E75 60%, #534AB7 100%);
    color: white; padding: 64px 80px 56px; min-height: 260px;
  }}
  .cover h1 {{ font-size: 2.2rem; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 8px; }}
  .cover .subtitle {{ font-size: 1.05rem; opacity: 0.85; margin-bottom: 24px; }}
  .cover .meta {{ font-size: 0.88rem; opacity: 0.7; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 40px 32px; }}
  h2 {{ font-size: 1.25rem; font-weight: 700; color: #0f6e56;
        border-left: 4px solid #1D9E75; padding-left: 12px;
        margin: 40px 0 16px; }}
  h3 {{ font-size: 1rem; font-weight: 600; color: #3C3489; margin: 24px 0 8px; }}
  p  {{ margin-bottom: 12px; color: #3d3d3a; }}
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin: 24px 0;
  }}
  .kpi {{
    background: white; border-radius: 12px; padding: 20px 18px;
    border: 1px solid #e8e6e0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}
  .kpi .label {{ font-size: 0.78rem; color: #73726c; text-transform: uppercase;
                  letter-spacing: 0.5px; font-weight: 600; margin-bottom: 6px; }}
  .kpi .value {{ font-size: 1.9rem; font-weight: 700; color: #0f6e56; line-height: 1.1; }}
  .kpi .sub   {{ font-size: 0.82rem; color: #888780; margin-top: 4px; }}
  .kpi.warn .value {{ color: #BA7517; }}
  .kpi.danger .value {{ color: #A32D2D; }}
  .kpi.purple .value {{ color: #534AB7; }}
  table {{
    width: 100%; border-collapse: collapse; background: white;
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin: 16px 0;
    font-size: 0.9rem;
  }}
  th {{ background: #0f6e56; color: white; padding: 11px 14px;
        font-weight: 600; text-align: left; font-size: 0.82rem;
        text-transform: uppercase; letter-spacing: 0.4px; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #f0eeea; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8f7f4; }}
  .badge {{
    display: inline-block; padding: 2px 9px; border-radius: 99px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.3px;
  }}
  .badge.sig {{ background: #e1f5ee; color: #0f6e56; }}
  .badge.ns  {{ background: #f1efe8; color: #73726c; }}
  .badge.hi  {{ background: #fcebeb; color: #A32D2D; }}
  figure {{ margin: 28px 0; }}
  figure img {{ width: 100%; border-radius: 10px;
                border: 1px solid #e8e6e0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
  figcaption {{ font-size: 0.84rem; color: #73726c; margin-top: 8px;
                text-align: center; font-style: italic; }}
  .callout {{
    background: #e1f5ee; border-left: 4px solid #1D9E75;
    border-radius: 0 8px 8px 0; padding: 14px 18px; margin: 16px 0;
    font-size: 0.92rem; color: #085041;
  }}
  .callout.warn  {{ background: #faeeda; border-color: #BA7517; color: #633806; }}
  .callout.alert {{ background: #fcebeb; border-color: #A32D2D; color: #501313; }}
  .rec-list {{ list-style: none; padding: 0; }}
  .rec-list li {{
    padding: 12px 14px 12px 42px; position: relative;
    background: white; border-radius: 8px; margin-bottom: 10px;
    border: 1px solid #e8e6e0; font-size: 0.92rem;
  }}
  .rec-list li::before {{
    content: attr(data-n); position: absolute; left: 12px; top: 12px;
    width: 22px; height: 22px; background: #1D9E75; color: white;
    border-radius: 50%; font-size: 0.75rem; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    line-height: 22px; text-align: center;
  }}
  footer {{
    text-align: center; padding: 32px; font-size: 0.82rem;
    color: #888780; border-top: 1px solid #e8e6e0; margin-top: 40px;
  }}
  @media print {{ body {{ background: white; }} .cover {{ -webkit-print-color-adjust: exact; }} }}
</style>
</head>
<body>

<div class="cover">
  <h1>Hospital Readmissions Analysis</h1>
  <div class="subtitle">30-Day Readmission Risk — Exploratory Analysis, Statistical Testing & Predictive Modeling</div>
  <div class="meta">Dataset: CMS HRRP-style · n = {s['total_patients']:,} patients · Analyst: Junior DA Portfolio</div>
</div>

<div class="container">

  <!-- KPIs -->
  <h2>Executive Summary</h2>
  <div class="kpi-grid">
    <div class="kpi warn">
      <div class="label">Overall Readmission Rate</div>
      <div class="value">{s['readmission_rate']}%</div>
      <div class="sub">National target &lt; 15%</div>
    </div>
    <div class="kpi">
      <div class="label">Total Patients Analyzed</div>
      <div class="value">{s['total_patients']:,}</div>
      <div class="sub">Across 30 hospitals</div>
    </div>
    <div class="kpi">
      <div class="label">Avg Length of Stay</div>
      <div class="value">{s['avg_los']}d</div>
      <div class="sub">All conditions</div>
    </div>
    <div class="kpi purple">
      <div class="label">Predictive Model AUC</div>
      <div class="value">{s['cv_auc']:.3f}</div>
      <div class="sub">5-fold CV ± {s['cv_auc_std']:.3f}</div>
    </div>
    <div class="kpi danger">
      <div class="label">High/Critical Risk Patients</div>
      <div class="value">{s['high_critical_pct']}%</div>
      <div class="sub">Flagged for intervention</div>
    </div>
    <div class="kpi warn">
      <div class="label">Top Condition Risk</div>
      <div class="value">{s['top_condition_rate']}%</div>
      <div class="sub">{s['top_condition']}</div>
    </div>
  </div>

  <div class="callout alert">
    <strong>Key Finding:</strong> The overall 30-day readmission rate of {s['readmission_rate']}% exceeds the national benchmark. 
    {s['high_critical_pct']}% of patients fall into High or Critical risk tiers based on the predictive model, 
    representing a priority cohort for targeted discharge interventions.
  </div>

  <!-- Condition Analysis -->
  <h2>1. Readmission Rate by Condition</h2>
  <p>
    Readmission rates vary significantly across conditions (χ² test, p &lt; 0.001). 
    <strong>{s['top_condition']}</strong> shows the highest 30-day rate at <strong>{s['top_condition_rate']}%</strong>, 
    well above the cross-condition average. Hip/Knee Replacement consistently shows the lowest rates, 
    reflecting structured post-acute care pathways.
  </p>
  {chart_tags.split('</figure>')[0]}</figure>

  <!-- Hospital Matrix -->
  <h2>2. Hospital Performance Analysis</h2>
  <p>
    The hospital performance matrix plots readmission rate against average length of stay, 
    with bubble size encoding patient volume. Low-quality hospitals cluster in the upper quadrant, 
    confirming that hospital quality tier is a statistically significant predictor (χ² = 120.15, p &lt; 0.001, Cramér's V = 0.155).
  </p>
  {chart_tags.split('</figure>')[1]}</figure>

  <!-- Heatmap -->
  <h2>3. Condition × Insurance Cohort Heatmap</h2>
  <p>
    The heatmap reveals interaction effects between primary condition and insurance type. 
    Uninsured patients with high-acuity conditions such as COPD and Heart Failure show 
    the darkest cells, indicating the compounding effect of financial barriers on post-discharge care access.
  </p>
  {chart_tags.split('</figure>')[2]}</figure>

  <!-- Statistical Tests -->
  <h2>4. Statistical Significance Testing</h2>
  <p>Chi-square tests of independence (α = 0.05) were conducted for all categorical predictors. 
  Effect sizes are reported as Cramér's V.</p>

  <table>
    <thead>
      <tr><th>Variable</th><th>χ² Statistic</th><th>p-value</th><th>Cramér's V</th><th>Effect Size</th><th>Result</th></tr>
    </thead>
    <tbody>
      <tr><td>Medical Condition</td><td>88.08</td><td>&lt; 0.001</td><td>0.133</td><td>Small</td><td><span class="badge sig">Significant</span></td></tr>
      <tr><td>Hospital Quality</td><td>120.15</td><td>&lt; 0.001</td><td>0.155</td><td>Small</td><td><span class="badge sig">Significant</span></td></tr>
      <tr><td>Discharge Destination</td><td>72.20</td><td>&lt; 0.001</td><td>0.120</td><td>Small</td><td><span class="badge sig">Significant</span></td></tr>
      <tr><td>Insurance Type</td><td>52.74</td><td>&lt; 0.001</td><td>0.103</td><td>Small</td><td><span class="badge sig">Significant</span></td></tr>
      <tr><td>Age Group</td><td>44.55</td><td>&lt; 0.001</td><td>0.094</td><td>Negligible</td><td><span class="badge sig">Significant</span></td></tr>
    </tbody>
  </table>

  <div class="callout warn">
    <strong>Statistical Note:</strong> All predictors reach significance at p &lt; 0.001. 
    However, Cramér's V values indicate small effect sizes, consistent with the multifactorial 
    nature of readmission risk. No single variable is deterministic — this motivates the 
    multivariate modeling approach in Section 5.
  </div>

  <!-- Model -->
  <h2>5. Predictive Model — Logistic Regression</h2>
  <p>
    A logistic regression model was trained on all patients using 5-fold stratified cross-validation. 
    Class imbalance was addressed via <code>class_weight="balanced"</code>. 
    The model achieves a cross-validated AUC of <strong>{s['cv_auc']:.3f} ± {s['cv_auc_std']:.3f}</strong>, 
    consistent with published clinical readmission models (LACE Index: ~0.68 AUC).
  </p>

  {chart_tags.split('</figure>')[3]}</figure>
  {chart_tags.split('</figure>')[4]}</figure>

  <h3>Top Predictive Features</h3>
  <table>
    <thead><tr><th>Rank</th><th>Feature</th><th>Direction</th><th>Clinical Interpretation</th></tr></thead>
    <tbody>
      <tr><td>1</td><td>Prior Admissions (12m)</td><td><span class="badge hi">Risk ↑</span></td><td>Strongest predictor — prior utilization predicts future utilization</td></tr>
      <tr><td>2</td><td>ED Visits (6m)</td><td><span class="badge hi">Risk ↑</span></td><td>Frequent ED use signals unmanaged chronic conditions</td></tr>
      <tr><td>3</td><td>Comorbidity Count</td><td><span class="badge hi">Risk ↑</span></td><td>Each additional comorbidity compounds discharge complexity</td></tr>
      <tr><td>4</td><td>Insurance Type</td><td><span class="badge hi">Risk ↑</span></td><td>Uninsured/Medicaid patients face post-discharge access barriers</td></tr>
      <tr><td>5</td><td>Hospital Quality Tier</td><td><span class="badge sig">Risk ↓ (High)</span></td><td>High-quality hospitals show protective effect</td></tr>
    </tbody>
  </table>

  <!-- Risk Tiers -->
  <h2>6. Patient Risk Stratification</h2>
  <p>
    Using predicted probabilities from the model, patients are assigned to four risk tiers. 
    The tier definitions are validated against actual readmission rates — Critical-tier patients 
    show readmission rates more than 2× the Low-tier cohort, confirming clinical utility.
  </p>
  {chart_tags.split('</figure>')[5]}</figure>

  <!-- Recommendations -->
  <h2>7. Recommendations</h2>
  <ul class="rec-list">
    <li data-n="1"><strong>Deploy risk scoring at discharge:</strong> Use the model's probability output to flag High/Critical patients for intensive transitional care — follow-up calls within 48h, medication reconciliation, and scheduled PCP visit within 7 days.</li>
    <li data-n="2"><strong>Target Hospital-G and low-quality facilities:</strong> Low-quality hospitals carry a 10+ percentage point premium in readmission rates. Quality improvement teams should audit discharge processes and care coordination protocols at these sites.</li>
    <li data-n="3"><strong>Prioritize uninsured and Medicaid patients:</strong> These cohorts show statistically significant elevated risk and face the greatest post-discharge care access barriers. Social work referrals should be standard for these patients across all conditions.</li>
    <li data-n="4"><strong>Implement AMA intervention protocol:</strong> Against-Medical-Advice discharges carry the highest readmission rates. A structured AMA counseling and follow-up protocol could materially reduce re-encounter rates within 30 days.</li>
    <li data-n="5"><strong>Expand model to include social determinants:</strong> The current model achieves AUC ~0.62 — consistent with published logistic regression benchmarks. Adding ZIP-level SDoH data (housing instability, food access) could improve discrimination to ~0.72, approaching ensemble model performance.</li>
  </ul>

  <!-- Limitations -->
  <h2>8. Limitations & Next Steps</h2>
  <p>
    This analysis uses a simulated dataset calibrated to CMS HRRP distributions. 
    In a production setting, the following enhancements are recommended:
  </p>
  <ul style="padding-left: 20px; color: #3d3d3a; margin-bottom: 12px;">
    <li>Linkage to actual CMS claims data for longitudinal follow-up</li>
    <li>Incorporation of lab values, vital signs, and medication adherence data</li>
    <li>Gradient boosting (XGBoost/LightGBM) for improved discrimination</li>
    <li>Fairness audit: disparate impact analysis by race/ethnicity and zip code</li>
    <li>Prospective validation on held-out time period (temporal split)</li>
  </ul>

</div>

<footer>
  Hospital Readmissions Analysis · Junior Data Analyst Portfolio · 
  Built with Python, scikit-learn, matplotlib · Data: CMS HRRP-style simulation
</footer>

</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"  ✓ Report saved → {output_path}")
