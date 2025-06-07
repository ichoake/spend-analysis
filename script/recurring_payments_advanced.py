#!/usr/bin/env python3
"""
Recurring Payment Analyzer - TechnoMancer Edition (Prompt version)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# If you want fuzzy grouping, uncomment the following and run `pip install rapidfuzz`
try:
    from rapidfuzz import process, fuzz
    FUZZY = True
except ImportError:
    print("RapidFuzz not installed; skipping fuzzy vendor grouping.")
    FUZZY = False

# ---------- CONFIG ----------
INPUT_CSV = input("Enter the full path to your transaction CSV file: ").strip()
SUMMARY_CSV = "recurring_payments_summary.csv"
TRANSACTIONS_CSV = "transactions_with_groups.csv"
TOLERANCE = 1.0  # Dollar tolerance for amount grouping
MIN_COUNT = 3    # Minimum times a payment must occur to be considered recurring
FUZZY_THRESHOLD = 85  # For vendor grouping (if fuzzy enabled)

def load_data(filepath):
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['Post Date'], errors='coerce')
    df['amount'] = pd.to_numeric(df['Debit'], errors='coerce')
    df = df[df['amount'] > 0].dropna(subset=['date', 'Description', 'amount'])
    return df

def fuzzy_group_vendors(df):
    vendor_names = df['Description'].unique()
    clusters = {}
    for name in vendor_names:
        if name in clusters:
            continue
        matches = process.extract(name, vendor_names, scorer=fuzz.token_sort_ratio, limit=20)
        similar = [m[0] for m in matches if m[1] >= FUZZY_THRESHOLD]
        for s in similar:
            clusters[s] = name
    df['vendor_group'] = df['Description'].map(clusters)
    return df

def group_amounts_with_tolerance(df, tol=TOLERANCE):
    def group(series):
        base = []
        for amt in sorted(series.unique()):
            for group in base:
                if abs(group[0] - amt) <= tol:
                    group.append(amt)
                    break
            else:
                base.append([amt])
        mapping = {amt: np.mean(g) for g in base for amt in g}
        return series.map(mapping)
    df['amount_grouped'] = df.groupby('vendor_group')['amount'].transform(group)
    return df

def detect_periodicity(dates):
    gaps = pd.Series(sorted(dates)).diff().dt.days.dropna()
    if len(gaps) == 0:
        return None, None
    freq = int(np.median(gaps))
    if 27 <= freq <= 33:
        pattern = 'Monthly'
    elif 6 <= freq <= 8:
        pattern = 'Weekly'
    elif 13 <= freq <= 16:
        pattern = 'Bi-Weekly'
    elif 350 <= freq <= 380:
        pattern = 'Yearly'
    else:
        pattern = 'Irregular'
    return freq, pattern

def recurring_summary(df):
    recurring = df.groupby(['vendor_group', 'amount_grouped']).agg(
        count=('date', 'count'),
        first_date=('date', 'min'),
        last_date=('date', 'max'),
        all_dates=('date', lambda x: sorted(x))
    ).reset_index()
    recurring = recurring[recurring['count'] >= MIN_COUNT].copy()
    recurring[['median_freq_days', 'pattern']] = recurring['all_dates'].apply(
        lambda dates: pd.Series(detect_periodicity(dates))
    )
    recurring.drop(columns=['all_dates'], inplace=True)
    recurring = recurring.sort_values(['count', 'vendor_group', 'amount_grouped'], ascending=[False, True, True]).reset_index(drop=True)
    return recurring

def main():
    # Load data
    df = load_data(INPUT_CSV)
    # Fuzzy vendor grouping if possible, else just use Description
    if FUZZY:
        df = fuzzy_group_vendors(df)
    else:
        df['vendor_group'] = df['Description']
    # Amount tolerance grouping
    df = group_amounts_with_tolerance(df)
    # Summarize recurring payments
    recurring = recurring_summary(df)
    # Save outputs
    recurring.to_csv(SUMMARY_CSV, index=False)
    df.to_csv(TRANSACTIONS_CSV, index=False)
    print(f"Recurring payment summary saved to {SUMMARY_CSV}")
    print(f"All grouped transactions saved to {TRANSACTIONS_CSV}")
    print("\nRecurring Payment Preview:\n", recurring.head(15).to_string())

if __name__ == '__main__':
    main()
