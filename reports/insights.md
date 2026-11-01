# Executive Insights & Strategic Recommendations

> **Customer Retention & Revenue-at-Risk Portfolio Project**  
> *Derived from 776,844 reconciled retail transactions, 36,600 orders, and 5,853 unique customer accounts (Dec 2009 – Dec 2011).*

---

## 1. Executive Summary

This study diagnoses customer churn dynamics and revenue concentration across a 2-year non-store retail transaction history. Total gross merchandise revenue across the analyzed customer base reconciles to **£17,081,128.74**.

Key business findings:
1. **The 30-Day Drop-Off:** Retention means **bought in that specific month**, not "never returned." Across organic cohorts, **about 4 in 5 new customers don't buy in the very next month** (organic Month 1 retention averages ~21%, meaning ~79% do not make an immediate repeat purchase in Month 1).
2. **Extreme Revenue Concentration:** The top 20% of customers generate **77.17% of total revenue** (£13.18M). Champions alone (23.71% of customers) generate **68.36% of all revenue** (£11.68M) with an average order frequency of 16.2 orders.
3. **Historical Spend in At Risk Accounts:** Formerly loyal accounts in the `Can't Lose Them` and `At Risk` segments (710 customers total) hold **£1,527,282.68 in historical revenue** (cumulative lifetime revenue, not future revenue at risk), having not placed an order in ~11–12 months (avg recency 338 and 374 days).

---

## 2. Organic Cohort Retention Benchmarks

Cohorts are defined by customer acquisition month. To isolate genuine customer behavior, benchmarks exclude both the **Dec 2009 legacy cohort** (which includes existing pre-dataset customers) and the **Dec 2011 partial cohort** (truncated at Dec 9 with zero retention runway):

| Retention Horizon | Evaluated Cohorts | Unweighted Average | Customer-Weighted Average | Total Active Customers | Total Cohort Base |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Month 1** | 22 cohorts | **20.66%** | **20.97%** | 982 | 4,683 |
| **Month 3** | 20 cohorts | **21.02%** | **21.08%** | 901 | 4,274 |
| **Month 6** | 17 cohorts | **17.32%** | **18.44%** | 730 | 3,958 |
| **Month 12** | 11 cohorts | **17.92%** | **18.43%** | 606 | 3,289 |

*Note on Row Count:* The DuckDB `cohort_retention` table contains exactly 325 rows ($\sum_{i=1}^{25} i = 325$). The exported CSV `cohort_retention.csv` contains 326 text lines because line 1 is the column header.

---

## 3. Behavioral RFM Customer Segmentation

Customers were evaluated using snapshot date **2011-12-10**:
- **Recency ($R$) & Monetary ($M$):** Scored 1–5 with quintiles (`NTILE(5)`), where 5 is most recent and highest spend.
- **Frequency ($F$):** Scored 1–5 using fixed integer bands (`1, 2, 3-4, 5-9, 10+`) to guarantee that tied customer order counts receive identical scores:
  - *1 order (Score 1):* 1,619 customers (27.66%, £556,725 revenue)
  - *2 orders (Score 2):* 945 customers (16.15%, £807,675 revenue)
  - *3–4 orders (Score 3):* 1,148 customers (19.61%, £1,459,903 revenue)
  - *5–9 orders (Score 4):* 1,180 customers (20.16%, £2,873,094 revenue)
  - *10+ orders (Score 5):* 961 customers (16.42%, £11,383,732 revenue)

### Segment Summary Table (Ordered Rules, First Match Wins)
| Segment | Criteria | Customers | % Cust | Total Revenue (£) | % Rev | Avg Recency | Avg Frequency | Avg Order Value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Champions** | $R \ge 4 \ \&\ F \ge 4$ | 1,388 | 23.71% | £11,676,846.76 | 68.36% | 20.1 days | 16.2 orders | £415.25 |
| **Loyal** | $R \ge 3 \ \&\ F \ge 3$ | 1,191 | 20.35% | £2,512,599.24 | 14.71% | 76.7 days | 5.6 orders | £366.37 |
| **Can't Lose Them** | $R \le 2 \ \&\ F \ge 4$ | 287 | 4.90% | £952,297.58 | 5.58% | 338.3 days | 8.6 orders | £359.02 |
| **Hibernating/Lost** | $R \le 2 \ \&\ F \le 2$ | 1,632 | 27.88% | £691,967.71 | 4.05% | 454.1 days | 1.3 orders | £327.26 |
| **At Risk** | $R \le 2 \ \&\ F \ge 3$ | 423 | 7.23% | £574,985.10 | 3.37% | 374.3 days | 3.4 orders | £412.38 |
| **New/Promising** | $R \ge 4 \ \&\ F \le 2$ | 511 | 8.73% | £443,209.49 | 2.59% | 27.8 days | 1.5 orders | £511.53 |
| **Need Attention** | *All others* | 421 | 7.19% | £229,222.85 | 1.34% | 107.7 days | 1.4 orders | £392.10 |
| **Total Base** | *Reconciled* | **5,853** | **100.00%** | **£17,081,128.74** | **100.00%** | **202.4 days** | **6.3 orders** | **£390.69** |

---

## 4. Plain-English Business Observations

### Observation 1: Extreme Pareto Concentration (Top 20% = 77.2% of Revenue)
Across the entire 5,853 customer base, the top 20% of customers (1,171 accounts) generate **77.17% of total revenue** (£13.18M out of £17.08M). Furthermore, the top 1% (59 accounts) generate 32.12% (£5.49M) and the top 5% (293 accounts) generate 52.00% (£8.88M). The business is heavily dependent on high-volume wholesale/repeat buyers.

### Observation 2: £1.53M in Historical Revenue from At Risk and Can't Lose Them Customers
There is **£1.53M in historical revenue from At Risk and Can't Lose Them customers** (710 accounts total: 287 `Can't Lose Them` accounts with £952k past revenue, and 423 `At Risk` accounts with £575k past revenue). That is cumulative lifetime revenue, not future revenue at risk. A meaningful portion of these high-value accounts have not purchased in nearly a year (average recency of ~340–375 days).
*Limitation note:* Some at-risk customers may be seasonal buyers (e.g., annual holiday/gift purchasers who only place orders in November–December) rather than permanently churned accounts.

### Observation 3: The "One-and-Done" Trialist Trap
1,619 customers (27.66% of accounts) bought exactly once, accounting for only £556,725 (3.26% of turnover). The average order value of these one-time buyers is £343.87, but without automated post-purchase onboarding or replenishment incentives, about 4 in 5 new customers don't buy in the very next month. Converting just 10% of one-time buyers to repeat status would unlock ~£55k in immediate incremental revenue.

---

## 5. Revenue-at-Risk & Win-Back Scenarios

### Core Definitions
- **Expected Annual Value (EAV):** `total_revenue / MAX(1, years since first order)` (where years are measured to snapshot date 2011-12-10).
- **At-Risk Flag:** Segment is `'At Risk'` or `'Can\'t Lose Them'`.
- **Revenue-at-Risk:** `SUM(expected_annual_value)` for `is_at_risk` accounts.
- **Revenue-at-Risk %:** `Revenue-at-Risk / SUM(expected_annual_value)` for all customers.

### Revenue-at-Risk Summary
The total annualized enterprise Expected Annual Value across all 5,853 accounts is **£10,420,530.94**.
The combined Revenue-at-Risk is **£886,993.14 (8.51% of customer base EAV)** across 710 accounts:

| Segment | Customers | % Cust | Historical Spend (£) | Revenue-at-Risk (£) | RAR % | Average Recency | Suggested Strategy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Can't Lose Them** | 287 | 4.90% | £952,698.87 | £516,432.19 | 4.96% | 338.3 days | personal call + loyalty offer |
| **At Risk** | 423 | 7.23% | £574,985.10 | £370,560.95 | 3.56% | 374.3 days | win-back email with a discount |
| **Total Revenue-at-Risk** | **710** | **12.13%** | **£1,527,683.97** | **£886,993.14** | **8.51%** | **359.8 days** | Prioritized Account Outreach |

### Win-Back Opportunity Matrix
*(Label: scenario assumptions, not forecasts)*

| Recovery Rate | Can't Lose Them Only (287 accounts) | At Risk Only (423 accounts) | Both Combined (710 accounts) |
| :---: | :---: | :---: | :---: |
| **5% Recovery** | £25,821.61 | £18,528.05 | **£44,349.66** |
| **10% Recovery** | £51,643.22 | £37,056.10 | **£88,699.31** |
| **15% Recovery** | £77,464.83 | £55,584.14 | **£133,048.97** |

### Top 50 Prioritized Action Plan
The exported `action_list.csv` highlights the 50 accounts with highest Expected Annual Value:
1. **High Leverage:** The top 50 accounts account for **£381,007.79** (42.96% of the entire £887.0k Revenue-at-Risk). Focus sales outreach here first.
2. **Action Allocations:**
   - **41 `Can't Lose Them` accounts:** Assigned **"personal call + loyalty offer"** (average 25+ orders historically; personal relationship management by account directors).
   - **9 `At Risk` accounts:** Assigned **"win-back email with a discount"** (e.g. accounts `15749` and `12346` placed 3 high-value orders averaging >£25k each; automated high-value discount campaign).

