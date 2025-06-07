#!/usr/bin/env python3
"""
Analyze a transaction CSV and generate comprehensive spending reports.

Features:
- Automatically detects date, amount, and category columns.
- Outputs include:
    - Monthly spending by category
    - Year-to-date spending by category
    - Cumulative spending
    - 3-month rolling average by category
    - Top 10 spending descriptions
    - Monthly total spending trend
    - Category growth/decline (month-over-month % change)
    - Largest single transactions
    - Spending by merchant/vendor
    - Spending by payment method
    - Spending heatmap by day of week
    - Days with no spending
    - Recurring payments detection
    - Budget comparison
    - Spending distribution (histogram)
    - Median and average transaction size
    - Spending by weekday/weekend
    - Cash flow analysis
- Optionally displays a plot of monthly spending by category.
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import logging
from pathlib import Path
import sys
import numpy as np

def parse_args():
    parser = argparse.ArgumentParser(description="Analyze a transaction CSV and generate spending reports.")
    parser.add_argument("--input_csv", default="docs/AccountHistory.csv", help="Path to transactions CSV")
    parser.add_argument("--output_dir", default=".", help="Directory to save output CSVs")
    parser.add_argument("--no-plot", action="store_true", help="Do not display the monthly spending plot")
    parser.add_argument("--budget_csv", default=None, help="Optional: Path to budget CSV")
    return parser.parse_args()

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def detect_column(df, keywords, default=None):
    for col in df.columns:
        if any(keyword in col.lower() for keyword in keywords):
            logging.info(f"Detected column: '{col}'")
            return col
    return default

def detect_date_column(df):
    for col in df.columns:
        try:
            parsed = pd.to_datetime(df[col], errors='coerce')
            if parsed.notna().sum() > len(df) * 0.5:
                logging.info(f"Detected date column: '{col}'")
                return parsed
        except Exception:
            continue
    raise ValueError("No suitable date column found.")

def detect_amount_column(df):
    num_cols = df.select_dtypes(include=['number']).columns
    if not num_cols.empty:
        logging.info(f"Detected amount column: '{num_cols[0]}'")
        return pd.to_numeric(df[num_cols[0]], errors='coerce').fillna(0)
    amount_col = detect_column(df, ['amount'])
    if amount_col:
        return pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
    raise ValueError("No numeric column found for amounts.")

def detect_category_column(df):
    category_col = detect_column(df, ['category', 'cat'])
    if category_col:
        return df[category_col]
    logging.warning("No category column found. Assigning all as 'Uncategorized'.")
    return 'Uncategorized'

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
    report_generators = [
        ('monthly_spending_by_category.csv', lambda: df.groupby(['year_month', 'category'])['amount'].sum().reset_index().pivot(index='year_month', columns='category', values='amount').fillna(0)),
        ('year_to_date_spending_by_category.csv', lambda: df[df['date'] >= (df['date'].max() - pd.DateOffset(months=12))].groupby('category')['amount'].sum().reset_index()),
        ('cumulative_spending.csv', lambda: df.groupby('date')['amount'].sum().cumsum().reset_index()),
        ('3mo_rolling_avg_by_category.csv', lambda: df.groupby(['year_month', 'category'])['amount'].sum().reset_index().pivot(index='year_month', columns='category', values='amount').fillna(0).rolling(window=3).mean().dropna()),
        ('top_10_spenders.csv', lambda: df.groupby(detect_column(df, ['description', 'desc', 'memo', 'name'], df.columns[1]))['amount'].sum().nlargest(10).reset_index().rename(columns={0: 'description', 1: 'amount'})),
        ('monthly_total_spending.csv', lambda: df.groupby('year_month')['amount'].sum().reset_index()),
        ('category_monthly_pct_change.csv', lambda: df.groupby(['year_month', 'category'])['amount'].sum().reset_index().pivot(index='year_month', columns='category', values='amount').fillna(0).pct_change().replace([np.inf, -np.inf], np.nan) * 100),
        ('largest_single_transactions.csv', lambda: df.nlargest(10, 'amount')),
        ('spending_by_merchant.csv', lambda: df.groupby(detect_column(df, ['merchant', 'vendor', 'payee'])).amount.sum().sort_values(ascending=False).reset_index() if detect_column(df, ['merchant', 'vendor', 'payee']) else None),
        ('spending_by_payment_method.csv', lambda: df.groupby(detect_column(df, ['method', 'payment'])).amount.sum().sort_values(ascending=False).reset_index() if detect_column(df, ['method', 'payment']) else None),
        ('spending_by_weekday.csv', lambda: df.assign(weekday=df['date'].dt.day_name()).groupby('weekday')['amount'].sum().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).reset_index()),
        ('days_with_no_spending.csv', lambda: pd.Series(pd.date_range(df['date'].min(), df['date'].max(), freq='D').difference(pd.to_datetime(df['date'].unique()))).to_frame('date')),
        ('recurring_payments.csv', lambda: df.groupby([detect_column(df, ['description', 'desc', 'memo', 'name'], df.columns[1]), 'amount']).size().reset_index(name='count').query('count >= 3')),
        ('budget_comparison.csv', lambda: pd.read_csv(args.budget_csv).merge(df[df['date'] >= (df['date'].max() - pd.DateOffset(months=12))].groupby('category')['amount'].sum().reset_index(), on='category', how='left').assign(over_under=lambda x: x['amount'] - x['budget']) if args.budget_csv and Path(args.budget_csv).exists() else None),
        ('spending_distribution_histogram.png', lambda: df['amount'].plot.hist(bins=50, title='Spending Distribution (Histogram)').get_figure().savefig(output_dir / 'spending_distribution_histogram.png') or plt.close()),
        ('transaction_stats_by_category.csv', lambda: df.groupby('category')['amount'].agg(['mean', 'median', 'count']).reset_index()),
        ('transaction_stats_overall.csv', lambda: df['amount'].agg(['mean', 'median', 'count']).to_frame().T),
        ('spending_by_weekday_weekend.csv', lambda: df.assign(is_weekend=df['date'].dt.weekday >= 5).groupby('is_weekend')['amount'].sum().reset_index().assign(day_type=lambda x: x['is_weekend'].map({True: 'Weekend', False: 'Weekday'})).loc[:, ['day_type', 'amount']]),
        ('cash_flow_analysis.csv', lambda: df.groupby(['year_month', detect_column(df, ['type', 'income', 'expense'])])['amount'].sum().unstack(fill_value=0).assign(net=lambda x: x.sum(axis=1)) if detect_column(df, ['type', 'income', 'expense']) else None)
    ]

    for file_name, generator in report_generators:
        result = generator()
        if result is not None:
            result.to_csv(output_dir / file_name, index=False)
            logging.info(f"Generated report: {file_name}")

    # Optional: display plot for monthly spending
    if not args.no_plot:
        df.groupby(['year_month', 'category'])['amount'].sum().reset_index().pivot(index='year_month', columns='category', values='amount').fillna(0).plot(title='Monthly Spending by Category')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

if __name__ == '__main__':
    main()