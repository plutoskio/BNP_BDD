# BNP Paribas - Hobart Database Analysis Project

**Status:** ✅ Database Build Complete - Ready for Analysis  
**Last Updated:** Feb 13, 2026

---

## 🎯 Project Overview

This project builds and analyzes a SQLite database of **4,795,906 service request tickets** from BNP Paribas's Hobart ticketing system. Ticket creation dates span **May 1, 2019 to Dec 31, 2025** (based on `creationdate_parsed`), and the source extracts were delivered in three load periods: `2025-01_to_2025-09`, `2025-12`, and `2026-01`.

**Key Deliverables:**
- ✅ Clean, queryable SQLite database (`hobart.db`, ~14 GB)
- ✅ Parsed date fields for time-series analysis
- ✅ Counts and documentation aligned to the SQLite database (CSV→SQLite migration had minor row loss)
- ✅ Comprehensive documentation

---

## 🚀 Quick Start for New Agents

### 1. Understanding the Database

**Read this first:** [`database_documentation.md`](./database_documentation.md)

This is your **primary reference** - it contains:
- Complete schema (SR has 54 source fields + parsed date columns; 7 FK columns)
- All table definitions
- Query examples
- Data quality notes
- Visual schema diagrams

### 2. Key Database Stats

| Table | Rows | Description |
|-------|------|-------------|
| `sr` | 4,795,906 | Service requests (main table) |
| `srcontact` | 17,514,081 | Email/communication records |
| `activity` | 765,632 | Tasks/activities |
| `historysr` | 28,650,010 | SR audit logs |
| `historycommunication` | 20,891,355 | Communication audit logs |
| `historyactivity` | 2,193,932 | Activity audit logs |
| `client_query` | 113,606,901 | Customer ↔ SR mappings |
| `category` | 46,005 | Request categories |
| `jur_user` | 5,177 | Users (staff/agents) |
| `label` | 15 | Status labels (CLOSED, ONGOING, etc.) |
| `businessline` | 1 | Business lines |
| `businessline_activity` | 3 | Business line activities |
| `businessline_process` | 26 | Business line processes |
| `deskbusinesslinelink` | 0 | Desk ↔ business line mapping (empty) |

**Date Fields:** Use `_parsed` columns in `sr` (e.g., `creationdate_parsed`, `closingdate_parsed`). Format is `YY-MM-DD HH.MM.SS` (text). `creationdate_parsed` is complete; `closingdate_parsed` is ~98.61% populated; other `_parsed` fields are sparsely populated (≈10k rows or fewer each).

### 3. Project Structure

```
BNP_BDD/
├── hobart.db                              # Main SQLite database (~14 GB)
├── database_documentation.md              # 📖 START HERE (Detailed documentation)
├── README.md                              # This file
├── hobart_data_dictionary.md              # Exhaustive field-level dictionary
├── data_inventory_report.md               # Data completeness verification
│
├── student_documentation/                 # Original BNP case study PDFs & slides
│
└── venv/                                  # Python virtual environment
```

---

## 📊 How to Query the Database

### Python Example
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('hobart.db')

# Top 10 categories by volume
query = """
    SELECT c.name, COUNT(*) as tickets
    FROM sr s
    JOIN category c ON s.category_id = c.id
    GROUP BY c.name
    ORDER BY tickets DESC
    LIMIT 10
"""

df = pd.read_sql_query(query, conn)
print(df)
```

### Date Queries (CRITICAL!)
```sql
-- ✅ CORRECT - Use parsed dates (format: 'YY-MM-DD HH.MM.SS')
SELECT *
FROM sr
WHERE creationdate_parsed >= '24-06-01'
ORDER BY creationdate_parsed DESC;

-- ❌ WRONG - Don't use original Oracle-style text dates
-- WHERE creationdate > '24-06-01'  -- creationdate stores values like '02-JAN-24 05.42.56.267000 PM'
```

---

## 🏗️ Database Build Process (Completed)

The database has been fully built and verified. The build scripts and intermediate mappings have been removed to keep the project clean for analysis.

**Build Highlights:**
1.  **Schema Normalization:** Created new auto-increment primary keys to handle ID conflicts in source CSVs.
2.  **Referential Integrity:** Foreign key relationships are defined in the schema.
3.  **Date Parsing:** Normalized Oracle-style timestamps into consistent text dates (`YY-MM-DD HH.MM.SS`) in `_parsed` columns.

---

## 📋 Data Quality Notes

### ✅ What's Good
- SQLite is the source of truth for analysis (counts above reflect the current DB after migration).
- 98.61% of tickets have `closingdate_parsed` populated.
- `creationdate_parsed` is populated for all SRs.

### ⚠️ Known Issues
1.  **~8.13% of tickets** have `closingdate_parsed < creationdate_parsed` (legacy data quirk).
2.  **Other parsed date fields** in `sr` are sparsely populated (≈10k rows or fewer each).
3.  **`deskbusinesslinelink` is empty** (0 rows).

---

## 🔍 Next Steps: Analysis

The database is **production-ready**. Recommended analysis tracks:

1.  **Trend Analysis** - Ticket volumes over time by category/status
2.  **Performance Metrics** - Resolution times, abandonment rates
3.  **User Productivity** - Workload distribution, top performers

---

## 📚 Documentation Reference

*   [`database_documentation.md`](./database_documentation.md) - **Primary Technical Reference**
*   [`hobart_data_dictionary.md`](./hobart_data_dictionary.md) - **Field-by-Field Definitions**
*   [`data_inventory_report.md`](./data_inventory_report.md) - **Data Availability Report**
*   `student_documentation/` - Original case study PDFs.

---

## 👥 Contact

This database was prepared for the BNP Paribas Case Study.
**Status:** ✅ **READY FOR ANALYSIS**
