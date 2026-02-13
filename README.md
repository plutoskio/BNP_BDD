# BNP Paribas - Hobart Database Analysis Project

**Status:** ✅ Database Build Complete - Ready for Analysis  
**Last Updated:** Feb 13, 2026

---

## 🎯 Project Overview

This project builds and analyzes a SQLite database of **4.8 million service request tickets** from BNP Paribas's Hobart ticketing system, spanning May 2019 - Dec 2025.

**Key Deliverables:**
- ✅ Clean, queryable SQLite database (`hobart.db`, ~14 GB)
- ✅ Parsed date fields for time-series analysis
- ✅ 100% data integrity (verified against CSVs)
- ✅ Comprehensive documentation 

---

## 🚀 Quick Start for New Agents

### 1. Understanding the Database

**Read this first:** [`database_documentation.md`](./database_documentation.md)

This is your **primary reference** - it contains:
- Complete schema (54 columns in SR table, 7 foreign keys)
- All table definitions
- Query examples
- Data quality notes
- Visual schema diagrams

### 2. Key Database Stats

| Table | Rows | Description |
|-------|------|-------------|
| `sr` | 4,795,906 | Service requests (main table) |
| `jur_user` | 5,177 | Users (staff/agents) |
| `category` | 46,005 | Request categories |
| `label` | 15 | Status labels (CLOSED, ONGOING, etc.) |

**Date Fields:** Use `_parsed` columns (e.g., `creationdate_parsed`) for queries.

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
-- ✅ CORRECT - Use parsed dates
SELECT * FROM sr 
WHERE creationdate_parsed > '2024-06-01' 
ORDER BY creationdate_parsed DESC;

-- ❌ WRONG - Don't use original text dates
-- WHERE creationdate > '24-06-01'  -- This won't work!
```

---

## 🏗️ Database Build Process (Completed)

The database has been fully built and verified. The build scripts and intermediate mappings have been removed to keep the project clean for analysis.

**Build Highlights:**
1.  **Schema Normalization:** Created new auto-increment primary keys to handle ID conflicts in source CSVs.
2.  **Referential Integrity:** 100% validation of Foreign Keys.
3.  **Date Parsing:** Converted Oracle-style timestamps to ISO-8601 for easy querying.

---

## 📋 Data Quality Notes

### ✅ What's Good
- 100% row count match with CSVs
- 97.5% ticket closure rate (healthy)
- 0 orphaned foreign keys

### ⚠️ Known Issues
1.  **~17% of tickets** have `closingdate < creationdate` (legacy data quirk).
2.  **~50% NULL assignees** in SR table.
3.  **Parsers:** Only `creationdate` and `closingdate` are fully parsed to `_parsed` columns.

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
