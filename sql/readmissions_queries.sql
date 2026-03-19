-- ============================================================
-- Hospital Readmissions Analysis — SQL Queries
-- Analytical SQL demonstrating: aggregation, window functions,
-- CTEs, conditional aggregation, and risk segmentation
-- ============================================================

-- ── 1. Overall KPIs ───────────────────────────────────────────────────────
SELECT
    COUNT(*)                                                AS total_patients,
    SUM(readmitted_30d)                                     AS total_readmitted,
    ROUND(AVG(readmitted_30d) * 100, 2)                     AS readmission_rate_pct,
    ROUND(AVG(los_days), 1)                                 AS avg_length_of_stay_days,
    ROUND(AVG(comorbidity_count), 2)                        AS avg_comorbidities,
    ROUND(AVG(prior_admits_12m), 2)                         AS avg_prior_admits
FROM hospital_readmissions;


-- ── 2. Readmission rate by condition with patient volume ──────────────────
SELECT
    condition,
    COUNT(*)                                                AS patient_count,
    SUM(readmitted_30d)                                     AS readmitted,
    ROUND(AVG(readmitted_30d) * 100, 2)                     AS readmission_rate_pct,
    ROUND(AVG(los_days), 1)                                 AS avg_los_days,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)      AS pct_of_total_volume
FROM hospital_readmissions
GROUP BY condition
ORDER BY readmission_rate_pct DESC;


-- ── 3. Hospital performance ranking with percentile ───────────────────────
WITH hospital_stats AS (
    SELECT
        hospital_id,
        hospital_quality,
        COUNT(*)                            AS total_patients,
        ROUND(AVG(readmitted_30d) * 100, 2) AS readmission_rate_pct,
        ROUND(AVG(los_days), 1)             AS avg_los,
        ROUND(AVG(penalty_score), 4)        AS avg_penalty_score
    FROM hospital_readmissions
    GROUP BY hospital_id, hospital_quality
)
SELECT
    *,
    ROUND(
        100.0 * RANK() OVER (ORDER BY readmission_rate_pct) /
        COUNT(*) OVER (),
    1)                                      AS readmission_pctile
FROM hospital_stats
ORDER BY readmission_rate_pct DESC;


-- ── 4. Risk factor: prior admissions × comorbidities interaction ──────────
SELECT
    CASE WHEN prior_admits_12m = 0 THEN '0 prior admits'
         WHEN prior_admits_12m = 1 THEN '1 prior admit'
         ELSE '2+ prior admits' END                         AS prior_admit_band,
    CASE WHEN comorbidity_count = 0 THEN '0 comorbidities'
         WHEN comorbidity_count <= 2 THEN '1-2 comorbidities'
         ELSE '3+ comorbidities' END                        AS comorbidity_band,
    COUNT(*)                                                AS n,
    ROUND(AVG(readmitted_30d) * 100, 1)                     AS readmission_rate_pct
FROM hospital_readmissions
GROUP BY 1, 2
ORDER BY readmission_rate_pct DESC;


-- ── 5. Month-over-month style trend (using patient_id as proxy time) ──────
WITH buckets AS (
    SELECT
        CASE
            WHEN patient_id <= 1000 THEN 'Q1 Cohort'
            WHEN patient_id <= 2000 THEN 'Q2 Cohort'
            WHEN patient_id <= 3000 THEN 'Q3 Cohort'
            WHEN patient_id <= 4000 THEN 'Q4 Cohort'
            ELSE                         'Q5 Cohort'
        END                                                 AS cohort,
        readmitted_30d,
        los_days
    FROM hospital_readmissions
)
SELECT
    cohort,
    COUNT(*)                                                AS patients,
    ROUND(AVG(readmitted_30d) * 100, 2)                     AS readmission_rate_pct,
    ROUND(AVG(readmitted_30d) * 100, 2)
        - ROUND(
            AVG(AVG(readmitted_30d) * 100) OVER (
                ORDER BY cohort
                ROWS BETWEEN 1 PRECEDING AND 1 PRECEDING
            ), 2)                                           AS change_from_prior_cohort
FROM buckets
GROUP BY cohort
ORDER BY cohort;


-- ── 6. High-risk patient identification for care management ───────────────
WITH risk_scores AS (
    SELECT
        patient_id,
        hospital_id,
        condition,
        age,
        insurance,
        discharge_to,
        los_days,
        prior_admits_12m,
        ed_visits_6m,
        comorbidity_count,
        penalty_score,
        -- Composite risk score (weighted sum, normalized 0-100)
        ROUND(
            (prior_admits_12m * 15)
          + (ed_visits_6m     * 10)
          + (comorbidity_count * 8)
          + (CASE WHEN discharge_to = 'AMA' THEN 20 ELSE 0 END)
          + (CASE WHEN insurance IN ('Uninsured','Medicaid') THEN 10 ELSE 0 END)
          + (CASE WHEN age >= 75 THEN 8 ELSE 0 END)
          + (CASE WHEN los_days > 14 THEN 6 ELSE 0 END),
        0)                                                  AS composite_risk_score
    FROM hospital_readmissions
    WHERE readmitted_30d = 1
)
SELECT
    *,
    NTILE(4) OVER (ORDER BY composite_risk_score DESC)      AS risk_quartile
FROM risk_scores
WHERE composite_risk_score >= 20
ORDER BY composite_risk_score DESC
LIMIT 50;


-- ── 7. Insurance equity analysis ──────────────────────────────────────────
SELECT
    insurance,
    COUNT(*)                                                AS patients,
    ROUND(AVG(readmitted_30d) * 100, 2)                     AS readmission_rate_pct,
    ROUND(AVG(los_days), 1)                                 AS avg_los,
    ROUND(AVG(comorbidity_count), 2)                        AS avg_comorbidities,
    ROUND(AVG(ed_visits_6m), 2)                             AS avg_ed_visits,
    -- Relative risk vs private insurance baseline
    ROUND(
        AVG(readmitted_30d) /
        NULLIF(AVG(AVG(readmitted_30d)) FILTER (WHERE insurance = 'Private')
               OVER (), 0),
    2)                                                      AS relative_risk_vs_private
FROM hospital_readmissions
GROUP BY insurance
ORDER BY readmission_rate_pct DESC;
