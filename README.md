# Healthcare Accounts Receivable & Claims Aging Dashboard

An enterprise-grade, premium dark-themed analytics platform built using Streamlit and Plotly. This application integrates directly with Google Sheets snapshots to track claims processing efficiency, outstanding accounts receivable (AR), employee productivity, and historical week-over-week financial recovery trends.

---

## 🌟 Key Features

- **Topline Financial KPIs**: Interactive glassmorphic metric cards tracking Total Claims, Open/Closed Counts, `$ Outstanding Balance`, `$ Balance Reductions`, and touched claim counts.
- **Executive Summary Page**: 
  - *Grouped Comparison Charts*: Displays Total Claim Count vs. Completed Claims side-by-side by aging bucket.
  - *AR Balance Groups*: Compares Total Claim Value vs. Outstanding AR Balance side-by-side.
  - *Volume & Value Subplots*: Grouped bar charts tracking completed claims alongside recovered dollars.
- **Productivity Analysis**: Horizontal charts for touches per employee and unique claims completed.
- **Historical Trends**: Weekly multi-snapshot comparative line charts tracking claim volumes, outstanding balances, recovery amounts, and touchpoint trends over time.
- **Premium Glassmorphic UI**: High-contrast, dark-mode visual hierarchy with glowing linear borders, interactive hover transitions, and customized dropdown widgets.
- **Excel & CSV Exports**: Instant report exports for aging summaries and productivity analyses.

---

## 📂 Codebase Architecture

- **[app.py](file:///c:/Users/Acer/OneDrive/Desktop/agent%20trend/app.py)**: Main entry point. Defines page layouts, custom styling overlays, sidebar controls, and topline metrics formatting.
- **[charts.py](file:///c:/Users/Acer/OneDrive/Desktop/agent%20trend/charts.py)**: Houses custom Plotly Express and Graph Objects visualizations styled with transparent layouts and bold outside data labels.
- **[metrics.py](file:///c:/Users/Acer/OneDrive/Desktop/agent%20trend/metrics.py)**: Contains calculations for financial aggregations (outstanding balance, collections, touches, completed claims, and percentages).
- **[cleaning.py](file:///c:/Users/Acer/OneDrive/Desktop/agent%20trend/cleaning.py)**: Pre-processes raw worksheet columns and standardizes names/dates/values.
- **[trend_analysis.py](file:///c:/Users/Acer/OneDrive/Desktop/agent%20trend/trend_analysis.py)**: Aggregates historical snapshot worksheets chronologically.
- **[google_sheets_connector.py](file:///c:/Users/Acer/OneDrive/Desktop/agent%20trend/google_sheets_connector.py)**: Connects securely to the Google Sheets workbook API.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- A Google Cloud Service Account with Google Drive & Google Sheets API access.

### 2. Setup Credentials
Create a service account key from your Google Cloud Console, name it `service_account.json`, and place it in the credentials folder:
```
credentials/service_account.json
```

### 3. Install Dependencies
Create a virtual environment and install the required libraries:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 4. Run the Dashboard
Start the local development server:
```bash
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

---

## 🔒 Security

- Credentials and local virtual environments are secured using [.gitignore](file:///c:/Users/Acer/OneDrive/Desktop/agent%20trend/.gitignore) to prevent accidental uploads to git repositories.
