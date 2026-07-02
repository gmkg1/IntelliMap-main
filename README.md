# 🗺️ IntelliMap - Smart Data Mapper

**Transform messy, inconsistent data into perfect templates — automatically.**

IntelliMap is a privacy-first, industrial-grade data mapping tool that uses advanced algorithms (including the Hungarian Algorithm) to intelligently map your raw data columns to a standard template, ensuring 100% data integrity without sending a single byte of data to the cloud.

---

## 🚀 Key Features

### 🧠 **Industrial-Grade Matching**
- **Optimal Assignment**: Uses the **Hungarian Algorithm** to ensure one-to-one column mapping. No duplicate assignments, ever.
- **Smart Pattern Detection**: Automatically identifies Emails, Dates, Phone Numbers, and Currencies to prevent illogical matches (e.g., matching a date column to an email field).
- **Compound Name Recognition**: Intelligently handles column names with separators (e.g., `customer_email` matches `email`, `user-name` matches `name`).
- **Enhanced Synonym Matching**: Recognizes partial matches in compound names (e.g., `customer_email` and `email` both contain "email" from the synonym list).
- **Expanded Vocabulary**: Recognizes hundreds of synonyms and abbreviations (e.g., `addr` → `Address`, `qty` → `Quantity`).
- **Data Quality Alerts**: Detects and warns about overlapping values between columns that could affect matching accuracy.

### 🔒 **Privacy First**
- **No Cloud Storage**: All processing happens locally in your browser/machine.
- **No AI Training**: Your data is never used to train models.
- **Metadata Only**: We only save your *mapping configuration* (column names), never your actual data rows.
- **Session-Based**: Data exists only during your session and is never persisted.

### ⚡ **Professional Workflow**
- **Prevent Duplicates**: Once a raw column is mapped, it vanishes from other dropdowns.
- **Real-time Feedback**: Instant visual confirmation of mapping confidence with color-coded indicators.
- **Auto-Formatting**: Automatically cleans and standardizes dates, numbers, and text during export.
- **Multiple Formats**: Export clean data to CSV, Excel, or JSON.
- **Save/Load Mappings**: Export mapping configurations for reuse across similar datasets.

---

## 📖 User Guide

1.  **Upload Raw Data**: Upload your messy file (CSV/Excel/JSON) that contains the data you HAVE.
2.  **Upload Template**: Upload a "perfect" file (CSV/Excel) that has the columns you WANT.
3.  **Auto-Map**: Click **🚀 Auto-Map Fields**. The system will intelligently link columns.
4.  **Review & Adjust**:
    *   🟢 Green dots indicate high confidence (≥80%).
    *   🟡 Yellow dots indicate medium confidence (60-79%).
    *   🟠 Orange dots indicate lower confidence (<60%).
    *   Review any unchecked mappings and adjust manually if needed.
    *   Manual overrides are saved automatically.
5.  **Transform**: Click **✨ Transform Data** to apply the mappings.
6.  **Download**: Download your clean, transformed file in your preferred format.

### 💾 Save/Load Mappings
- **Export**: Save your mapping configuration as JSON to reuse later.
- **Import**: Load a previously saved configuration to quickly map similar datasets.

---

## ⚙️ Technical Details

### The Matching Algorithm
IntelliMap uses a multi-stage scoring system to determine the best match:

1.  **Normalization**: Column names are normalized by:
    - Converting to lowercase
    - Replacing separators (`_`, `-`, `.`) with spaces
    - Expanding abbreviations (e.g., `addr` → `address`)
    - Removing special characters

2.  **Scoring**:
    - **Exact Match**: 100% score
    - **Synonym Match (Exact)**: 95% score (e.g., "Mobile" ↔ "Phone")
    - **Synonym Match (Partial)**: 90% score (e.g., "customer_email" ↔ "email")
    - **Subset Match**: 95% score if one header is a subset of another (e.g., "Customer ID" ↔ "ID")
    - **Word Overlap**: 70-90% score based on percentage of shared words
    - **Fuzzy Match**: 70-100% score based on character similarity

3.  **Optimal Assignment**: The **Hungarian Algorithm** (`scipy.optimize.linear_sum_assignment`) is applied to find the globally optimal 1-to-1 mapping that maximizes total confidence.

4.  **Pattern Enhancement**: Data patterns (email, date, numeric, text) are detected to improve low-confidence matches and prevent illogical assignments.

### Directory Structure
```
IntelliMap/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── utils/
│   ├── __init__.py
│   ├── mapper.py              # Core matching logic and pattern detection
│   ├── transformer.py         # Data cleaning and export engine
│   ├── data_reader.py         # File reading utilities
│   └── metadata_manager.py    # Mapping configuration save/load
└── README.md
```

---

## 🛡️ License & Copyright

**Copyright © 2025 IntelliMap. All Rights Reserved.**
See the [LICENSE](LICENSE) file for full terms and conditions.
