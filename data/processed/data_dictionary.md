# Data Dictionary — Hospital Readmissions

| Column | Type | Description |
|---|---|---|
| patient_id | INT | Unique patient identifier |
| age_group | VARCHAR | 18-44, 45-64, 65-74, 75+ |
| admission_type | VARCHAR | Emergency, Elective, Urgent |
| primary_diagnosis | VARCHAR | ICD-10 category |
| insurance_type | VARCHAR | Medicare, Medicaid, Private, Uninsured |
| los_days | INT | Length of stay in days |
| readmitted_30d | INT | 1 = readmitted within 30 days |
| discharge_disposition | VARCHAR | Home, SNF, AMA, Other |
| risk_score | FLOAT | Model-predicted readmission probability |
| risk_tier | VARCHAR | Critical/High/Moderate/Low |

**Source:** Calibrated to CMS HRRP benchmarks
**Note:** Data generated to match published CMS statistics
