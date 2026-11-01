# Data Quality & Cleaning Audit Log

> **Phase 1: Ingestion & Hygiene Execution Log**  
> *Generated automatically by `src/clean.py` during pipeline staging.*

---

## 1. Executive Cleaning Summary

The raw transaction dataset was ingested directly from source and processed through a deterministic multi-stage hygiene sequence.
- **Initial Raw Records:** 1,067,371
- **Final Clean Sales Line Items:** 776,844 (72.78% of raw)
- **Tracked Clean Gross Revenue:** £17,081,128.74
- **Unique Analyzed Accounts:** 5,853
- **Transaction Period:** 2009-12-01 00:00:00 to 2011-12-09 00:00:00 (2-year observation window)

---

## 2. Step-by-Step Row Count Audit Trail

| Step | Cleaning Action | Row Count Before | Delta (Excluded/Isolated) | Row Count After | Retention Rate | Status / Destination |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **0** | Raw Ingestion | 1,067,371 | 0 | **1,067,371** | 100.0% | `Baseline` |
| **1** | Deduplication | 1,067,371 | -34,335 | **1,033,036** | 96.78% | `Removed` |
| **2** | Guest Checkout Isolation | 1,033,036 | -235,151 | **797,885** | 74.75% | `Isolated to stg_guest_checkouts` |
| **3** | Cancellation Isolation | 797,885 | -18,390 | **779,495** | 73.03% | `Isolated to fact_returns` |
| **4** | Invalid / Promo Value Removal | 779,495 | -70 | **779,425** | 73.02% | `Removed` |
| **5** | Non-Product Stock Code Isolation | 779,425 | -2,581 | **776,844** | 72.78% | `Isolated to fact_non_products` |

---

## 3. Isolated Datasets Profile

### A. Non-Product Stock Codes (`fact_non_products`)
- **Total Isolated Line Items:** 2,581
- **Unique Invoices Involved:** 2,518
- **Total Isolated Revenue:** £293,675.53
- **Methodology Rationale:** Non-merchandise items (postage fees, manual adjustments, discount lines, bank charges, and test codes) represent service or operational charges. Retaining them in product sales distorts product retention analysis, basket sizes, and average order values. Isolating them into `fact_non_products` preserves full operational audibility without corrupting retail merchandise metrics.

| Stock Code | Sample Description | Isolated Rows | Isolated Revenue (£) |
| :--- | :--- | :---: | :---: |
| `M` | Manual | 681 | £151,777.67 |
| `POST` | POSTAGE | 1,803 | £124,648.04 |
| `DOT` | DOTCOM POSTAGE | 16 | £11,906.36 |
| `ADJUST` | Adjustment by john on 26/01/2010 16 | 32 | £3,538.52 |
| `ADJUST2` | Adjustment by Peter on Jun 25 2010 | 3 | £731.05 |
| `BANK CHARGES` | Bank Charges | 31 | £450.00 |
| `D` | Discount | 5 | £397.89 |
| `TEST001` | This is a test product. | 9 | £225.00 |
| `TEST002` | This is a test product. | 1 | £1.00 |

### B. Customer Returns & Cancellations (`fact_returns`)
- **Total Cancellation Records:** 18,390
- **Unique Return Invoices:** 7,901
- **Gross Return Value:** £1,084,812.98
- **Methodology Rationale:** Invoices prefixed with `'C'` represent legitimate post-purchase refunds. Rather than netting line items indiscriminately or deleting them from the warehouse, they are isolated into a dedicated returns fact table to measure churn risk and return propensity without distorting sales recency/frequency metrics.

### C. Unregistered Guest Checkouts (`stg_guest_checkouts`)
- **Total Guest Records:** 235,151
- **Unique Guest Invoices:** 8,752
- **Gross Guest Revenue:** £2,565,542.41
- **Methodology Rationale:** Guest checkouts lack a persistent `Customer ID`. They represent valid retail purchases but cannot be linked to longitudinal cohort retention or RFM customer trajectories. They are logged and preserved for aggregate revenue reconciliation.

---

## 4. Final Clean Dataset (`clean_sales`) Profile

| Metric | Value |
| :--- | :--- |
| **Total Clean Line Items** | 776,844 |
| **Unique Invoices (Orders)** | 36,600 |
| **Unique Customer Accounts** | 5,853 |
| **Gross Analyzed Revenue** | £17,081,128.74 |
| **Average Line Item Value** | £21.99 |
| **Observation Window Start** | 2009-12-01 00:00:00 |
| **Observation Window End** | 2011-12-09 00:00:00 |

### Top 5 Geographic Markets
| Country | Line Items | Unique Customers | Revenue (£) | Revenue Share (%) |
| :--- | :---: | :---: | :---: | :---: |
| United Kingdom | 699,684 | 5,334 | £14,291,648.52 | 83.67% |
| EIRE | 15,529 | 3 | £595,601.08 | 3.49% |
| Netherlands | 4,981 | 22 | £549,773.41 | 3.22% |
| Germany | 15,788 | 107 | £383,289.00 | 2.24% |
| France | 13,036 | 94 | £309,799.16 | 1.81% |

---
*Audit log verified against Pytest data integrity test suite.*