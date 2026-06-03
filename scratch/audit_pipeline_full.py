import sys
sys.path.append(r"c:\Users\Acer\OneDrive\Desktop\agent trend")

import pandas as pd
from google_sheets_connector import load_spreadsheet_workbook
from cleaning import clean_claim_data, normalize_aging_bucket
from metrics import (
    resolve_aging_bucket_column,
    resolve_claim_status_column,
    resolve_worked_by_column,
    _resolve_column,
    _to_numeric_series,
    _derive_recovered_amount,
    BALANCE_CANDIDATES
)

SPREADSHEET_ID = "1c6m8b_8a7liJZx0Am1suxbXeZnpVwHYB35FNStUQtE8"
CREDENTIALS_PATH = "credentials/service_account.json"

def main():
    workbook = load_spreadsheet_workbook(SPREADSHEET_ID, credentials_path=CREDENTIALS_PATH)
    
    # 3. Print and compare for each worksheet:
    # Worksheet name, row count, total balance, total pending balance, total recovered amount
    print("=== Worksheet Audit (Raw Data) ===")
    for name, df in workbook.items():
        row_count = len(df)
        
        # We can look at different balance columns in raw data
        # Let's check for 'claim_balance', 'claim_insurance_due', 'claim_amount'
        claim_balance_sum = 0.0
        claim_insurance_due_sum = 0.0
        claim_amount_sum = 0.0
        
        # Let's clean the currency values in raw data to see what the raw sums are
        def raw_sum(series):
            return pd.to_numeric(series.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce").fillna(0).sum()
        
        if 'claim_balance' in df.columns:
            claim_balance_sum = raw_sum(df['claim_balance'])
        if 'claim_insurance_due' in df.columns:
            claim_insurance_due_sum = raw_sum(df['claim_insurance_due'])
        if 'claim_amount' in df.columns:
            claim_amount_sum = raw_sum(df['claim_amount'])
            
        print(f"Worksheet: {name}")
        print(f"  Row Count: {row_count}")
        print(f"  Raw sum('claim_amount'): ${claim_amount_sum:,.2f}")
        print(f"  Raw sum('claim_balance'): ${claim_balance_sum:,.2f}")
        print(f"  Raw sum('claim_insurance_due'): ${claim_insurance_due_sum:,.2f}")
        
    print("\n=== Dataflow Audit per sheet ===")
    
    cleaned_sheets = {}
    for name, df in workbook.items():
        print(f"Sheet: {name}")
        
        # Row count & total balance BEFORE cleaning
        # Let's check raw claim_balance column or whatever column maps to BALANCE_CANDIDATES
        # Since _resolve_column works on df, let's see which column is resolved
        balance_col = _resolve_column(df, BALANCE_CANDIDATES)
        print(f"  Resolved balance column: {balance_col}")
        
        raw_balance = pd.to_numeric(df[balance_col].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce").fillna(0)
        print(f"  BEFORE CLEANING: Row Count = {len(df)}, Total Balance = ${raw_balance.sum():,.2f}")
        
        # AFTER cleaning
        cleaned_df = clean_claim_data(df)
        cleaned_sheets[name] = cleaned_df
        clean_balance_col = _resolve_column(cleaned_df, BALANCE_CANDIDATES)
        clean_balance = cleaned_df[clean_balance_col]
        print(f"  AFTER CLEANING: Row Count = {len(cleaned_df)}, Total Balance = ${clean_balance.sum():,.2f}")
        
        # Let's see if duplicates were dropped or what
        print(f"  Duplicates dropped: {len(df) - len(cleaned_df)}")
        
    # Combine to find global attributes
    all_cleaned_rows = pd.concat(cleaned_sheets.values(), ignore_index=True)
    aging_column_for_filters = resolve_aging_bucket_column(all_cleaned_rows)
    employee_column_for_filters = resolve_worked_by_column(all_cleaned_rows)
    status_column_for_filters = resolve_claim_status_column(all_cleaned_rows)
    
    print("\n=== Global Filters & Columns resolved ===")
    print(f"Aging Bucket Column: {aging_column_for_filters}")
    print(f"Employee Column: {employee_column_for_filters}")
    print(f"Status Column: {status_column_for_filters}")
    
    # 5. Dashboard filters currently applied
    # Let's see what app.py filters do:
    # app.py:
    # default_aging = aging_options (all non-null buckets)
    # default_employees = employee_options (all non-null employees)
    # default_statuses = status_options (all non-null statuses)
    # let's see what options are:
    aging_options = sorted({str(normalize_aging_bucket(value)) for value in all_cleaned_rows[aging_column_for_filters].dropna().tolist()})
    employee_options = sorted(all_cleaned_rows[employee_column_for_filters].dropna().astype(str).unique().tolist())
    status_options = sorted(all_cleaned_rows[status_column_for_filters].dropna().astype(str).unique().tolist())
    
    print(f"Aging Options: {aging_options}")
    print(f"Employee Options Count: {len(employee_options)}")
    print(f"Status Options: {status_options}")
    
    # Let's apply filters as app.py does:
    def apply_filters(df):
        # In app.py:
        # filtered = df.copy()
        # and it filters by matching buckets in selected_aging_buckets
        # wait! What if some rows have null or different aging buckets?
        # let's look at app.py:
        # if aging_column and selected_aging:
        #     filtered = filtered[filtered[aging_column].map(normalize_aging_bucket).astype(str).isin(selected_aging)]
        # This will convert any pd.NA to "NA" or "None" or "nan" as string! Let's check!
        # If pd.NA is mapped to "NA" or "None", and it is not in aging_options (which is from dropna),
        # those rows with NA aging buckets are EXCLUDED by the aging bucket filter!
        # Let's check if this is the case!
        pass
        
    print("\n=== Exclusions Analysis ===")
    for name, df in workbook.items():
        print(f"Sheet: {name}")
        cleaned_df = cleaned_sheets[name]
        
        # Let's check how many rows are missing claim_balance_aging
        missing_aging = cleaned_df[aging_column_for_filters].isna().sum()
        print(f"  Cleaned rows with missing aging bucket: {missing_aging}")
        
        # Let's calculate sum of balance for rows with missing aging bucket
        balance_col = _resolve_column(cleaned_df, BALANCE_CANDIDATES)
        missing_aging_balance = cleaned_df[cleaned_df[aging_column_for_filters].isna()][balance_col].sum()
        print(f"  Sum of balance for missing aging bucket rows: ${missing_aging_balance:,.2f}")
        
        # Let's check if there are other exclusions, e.g., claims with balance <= 0
        zero_or_negative_balance = (cleaned_df[balance_col] <= 0).sum()
        positive_balance_df = cleaned_df[cleaned_df[balance_col] > 0]
        print(f"  Claims with balance <= 0: {zero_or_negative_balance}")
        
        # Let's see if the dashboard shows only Open Claims (balance > 0)
        # Wait, the Aging Bucket chart in app.py uses:
        # aging_summary_df = calculate_aging_summary(frame)
        # which uses frame = filtered_sheets[sheet_name]
        # Wait, does the dashboard filter to open claims only? No, app.py doesn't filter to balance > 0,
        # but let's check what calculate_aging_summary(frame) does!
        # It does:
        # summary = (df.groupby(aging_col, dropna=False)...)
        # But wait! If the dashboard excludes NA or if we filter out claims?
        # Let's print out the exact calculation results for dashboard for each sheet!
        
        # Let's print the actual default filtered sheet row count and balance:
        # In app.py, the filters are applied as:
        # selected_aging_buckets = aging_options (from dropna of all_cleaned_rows)
        # filtered = filtered[filtered[aging_column].map(normalize_aging_bucket).astype(str).isin(selected_aging_buckets)]
        # Since selected_aging_buckets does NOT contain "nan" or "<NA>", this filter EXCLUDES any claims with a missing aging bucket!
        # Let's test this!
        mapped_aging_series = cleaned_df[aging_column_for_filters].map(normalize_aging_bucket).astype(str)
        is_in_buckets = mapped_aging_series.isin(aging_options)
        filtered_df = cleaned_df[is_in_buckets]
        
        print(f"  Filtered Row Count: {len(filtered_df)}")
        print(f"  Filtered Total Balance: ${filtered_df[balance_col].sum():,.2f}")
        print(f"  Difference due to filters: ${cleaned_df[balance_col].sum() - filtered_df[balance_col].sum():,.2f}")
        
    print("\n=== Aging Bucket Totals by Worksheet ===")
    for name, df in cleaned_sheets.items():
        print(f"Worksheet: {name}")
        balance_col = _resolve_column(df, BALANCE_CANDIDATES)
        # Let's group by clean aging bucket and sum
        grouped = df.groupby(aging_column_for_filters, dropna=False)[balance_col].sum()
        for bucket in ["0-30", "31-45", "46-60", "60+", pd.NA]:
            val = grouped.get(bucket, 0)
            print(f"  Bucket {bucket}: ${val:,.2f}")
        print(f"  Total Aging Balance (Sum of Buckets): ${df[balance_col].sum():,.2f}")

if __name__ == "__main__":
    main()
