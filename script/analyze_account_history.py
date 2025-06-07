#!/usr/bin/env python3
"""
Analyze a transaction CSV and generate spending reports.

Features:
- Automatically detects date, amount, and category columns.
- Outputs:
    - Monthly spending by category
    - Year-to-date (last 12 months) spending by category
    - Cumulative spending
    - 3-month rolling average by category
    - Top 10 spending descriptions
- Optionally displays a plot of monthly spending by category.
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import logging
from pathlib import Path
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Analyze a transaction CSV and generate spending reports.")
    parser.add_argument(
        "--input_csv",
        default="docs/AccountHistory.csv",
        help="Path to transactions CSV (default: docs/AccountHistory.csv)"
    )
    parser.add_argument(
        "--output_dir",
        default=".",
        help="Directory to save output CSVs (default: current directory)"
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Do not display the monthly spending plot"
    )
    return parser.parse_args()

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )

def detect_date_column(df):
    """Detect the date column in the DataFrame."""
    for col in df.columns:
        try:
            parsed = pd.to_datetime(df[col], errors='coerce')
            if parsed.notna().sum() > len(df) * 0.5:
                logging.info(f"Detected date column: '{col}'")
                return parsed
        except Exception:
            continue
    raise ValueError("No suitable date column found. Please ensure your CSV has a date column.")

def detect_amount_column(df):
    """Detect the first numeric column as the amount column."""
    num_cols = df.select_dtypes(include=['number']).columns
    if not num_cols.empty:
        logging.info(f"Detected amount column: '{num_cols[0]}'")
        return pd.to_numeric(df[num_cols[0]], errors='coerce').fillna(0)
    for col in df.columns:
        if 'amount' in col.lower():
            logging.info(f"Detected amount column by name: '{col}'")
            return pd.to_numeric(df[col], errors='coerce').fillna(0)
    raise ValueError("No numeric column found for amounts.")

def detect_category_column(df):
    """Ensure a category column exists."""
    if 'category' in df.columns:
        logging.info("Detected category column: 'category'")
        return df['category']
    for col in df.columns:
        if 'cat' in col.lower():
            logging.info(f"Detected category column: '{col}'")
            return df[col]
    logging.warning("No category column found. Assigning all as 'Uncategorized'.")
    return 'Uncategorized'

def detect_description_column(df):
    """Detect a description column for top spenders."""
    if 'description' in df.columns:
        return 'description'
    for col in df.columns:
        if 'desc' in col.lower() or 'memo' in col.lower() or 'name' in col.lower():
            return col
    return df.columns[1] if len(df.columns) > 1 else df.columns[0]

def main():
    setup_logging()
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        df = pd.read_csv(args.input_csv)
    except Exception as e:
        logging.error(f"Failed to read input CSV: {e}")
        sys.exit(1)

    try:
        df['date'] = detect_date_column(df)
        df['amount'] = detect_amount_column(df)
        df['category'] = detect_category_column(df)
    except Exception as e:
        logging.error(e)
        sys.exit(1)

    df['year_month'] = df['date'].dt.to_period('M').dt.to_timestamp()

    # Generate reports
    generate_reports(df, output_dir)

    # Optional: display plot for monthly spending
    if not args.no_plot:
        display_monthly_spending_plot(df)

def generate_reports(df, output_dir):
    """Generate various spending reports."""
    # 1. Monthly spending by category
    monthly = df.groupby(['year_month', 'category'])['amount'].sum().reset_index()
    pivot = monthly.pivot(index='year_month', columns='category', values='amount').fillna(0)
    pivot_path = output_dir / 'monthly_spending_by_category.csv'
    pivot.to_csv(pivot_path)

    # 2. Year-to-date (last 12 months) summary
    latest = df['date'].max()
    ytd = df[df['date'] >= (latest - pd.DateOffset(months=12))]
    ytd_summary = ytd.groupby('category')['amount'].sum().reset_index()
    ytd_path = output_dir / 'year_to_date_spending_by_category.csv'
    ytd_summary.to_csv(ytd_path, index=False)

    # 3. Cumulative spend
    cum = df.groupby('date')['amount'].sum().cumsum().reset_index()
    cum_path = output_dir / 'cumulative_spending.csv'
    cum.to_csv(cum_path, index=False)

    # 4. 3-month rolling average
    rolling = pivot.rolling(window=3).mean().dropna()
    rolling_path = output_dir / '3mo_rolling_avg_by_category.csv'
    rolling.to_csv(rolling_path)

    # 5. Top 10 spending descriptions
    desc_col = detect_description_column(df)
    top = df.groupby(desc_col)['amount'].sum().nlargest(10).reset_index()
    top.columns = ['description', 'amount']
    top_path = output_dir / 'top_10_spenders.csv'
    top.to_csv(top_path, index=False)

    # Print report summary
    logging.info("Generated reports:")
    for f in [pivot_path, ytd_path, cum_path, rolling_path, top_path]:
        logging.info(f"- {f}")

def display_monthly_spending_plot(df):
    """Display a plot for monthly spending by category."""
    pivot = df.pivot(index='year_month', columns='category', values='amount').fillna(0)
    pivot.plot(title='Monthly Spending by Category')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()