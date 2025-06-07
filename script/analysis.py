#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import logging

def parse_args():
    parser = argparse.ArgumentParser(description="12-month spending analysis")
    parser.add_argument("input_csv", help="Path to transactions CSV (must have date, amount, category)")
    return parser.parse_args()

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
    raise ValueError("No suitable date column found.")

def detect_amount_column(df):
    """Detect the first numeric column as the amount column."""
    num_cols = df.select_dtypes(include=['number']).columns
    if not num_cols.empty:
        logging.info(f"Detected amount column: '{num_cols[0]}'")
        return pd.to_numeric(df[num_cols[0]], errors='coerce').fillna(0)
    raise ValueError("No numeric column found for amounts.")

def ensure_category_column(df):
    """Ensure a category column exists."""
    if 'category' not in df.columns:
        logging.warning("No category column found. Assigning all as 'Uncategorized'.")
        df['category'] = 'Uncategorized'
    return df['category']

def generate_reports(df):
    """Generate various spending reports."""
    # Prepare grouping columns
    df['year_month'] = df['date'].dt.to_period('M').dt.to_timestamp()

    # 1. Monthly spending by category
    monthly = df.groupby(['year_month', 'category'])['amount'].sum().reset_index()
    pivot = monthly.pivot(index='year_month', columns='category', values='amount').fillna(0)
    pivot.to_csv('monthly_spending_by_category.csv')

    # 2. Year-to-date (last 12 months) summary
    latest = df['date'].max()
    ytd = df[df['date'] >= (latest - pd.DateOffset(months=12))]
    ytd_summary = ytd.groupby('category')['amount'].sum().reset_index()
    ytd_summary.to_csv('year_to_date_spending_by_category.csv', index=False)

    # 3. Cumulative spend
    cum = df.groupby('date')['amount'].sum().cumsum().reset_index()
    cum.to_csv('cumulative_spending.csv', index=False)

    # 4. 3-month rolling average
    rolling = pivot.rolling(window=3).mean().dropna()
    rolling.to_csv('3mo_rolling_avg_by_category.csv')

    # 5. Top 10 spending descriptions
    desc_col = 'description' if 'description' in df.columns else df.columns[1]
    top = df.groupby(desc_col)['amount'].sum().nlargest(10).reset_index()
    top.columns = ['description', 'amount']
    top.to_csv('top_10_spenders.csv', index=False)

    # Print report summary
    logging.info("Generated reports:")
    for f in [
        'monthly_spending_by_category.csv',
        'year_to_date_spending_by_category.csv',
        'cumulative_spending.csv',
        '3mo_rolling_avg_by_category.csv',
        'top_10_spenders.csv'
    ]:
        logging.info(f'- {f}')

    # Optional: display plot for monthly spending
    pivot.plot(title='Monthly Spending by Category')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    setup_logging()
    args = parse_args()
    # Load data
    df = pd.read_csv(args.input_csv)

    # Detect and assign columns
    df['date'] = detect_date_column(df)
    df['amount'] = detect_amount_column(df)
    df['category'] = ensure_category_column(df)

    # Generate reports
    generate_reports(df)
