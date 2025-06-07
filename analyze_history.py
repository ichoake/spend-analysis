#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import logging
from pathlib import Path
import sys

INPUT_CSV = "docs/AccountHistory.csv"
OUTPUT_DIR = "."

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
    raise ValueError("No suitable date column found.")

def detect_amount_column(df):
    """Detect the first numeric column as the amount column."""
    num_cols = df.select_dtypes(include=['number']).columns
    if not num_cols.empty:
        logging.info(f"Detected amount column: '{num_cols[0]}'")
        return pd.to_numeric(df[num_cols[0]], errors='coerce').fillna(0)
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

def main():
    setup_logging()
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        df = pd.read_csv(INPUT_CSV)
    except Exception as e:
        logging.error(f"Failed to read input CSV: {e}")
        sys.exit(1)

    df['date'] = detect_date_column(df)
    df['amount'] = detect_amount_column(df)
    df['category'] = detect_category_column(df)
    df['year_month'] = df['date'].dt.to_period('M').dt.to_timestamp()

    # Generate reports
    generate_reports(df, output_dir)

    # Display plot for monthly spending
    plot_monthly_spending(df)

def generate_reports(df, output_dir):
    """Generate various spending reports."""
    # 1. Monthly spending by category
    monthly = df.groupby(['year_month', 'category'])['amount'].sum().reset_index()
    pivot = monthly.pivot(index='year_month', columns='category', values='amount').fillna(0)
    pivot.to_csv(output_dir / 'monthly_spending_by_category.csv')

    # 2. Year-to-date (last 12 months) summary
    latest = df['date'].max()
    ytd = df[df['date'] >= (latest - pd.DateOffset(months=12))]
    ytd_summary = ytd.groupby('category')['amount'].sum().reset_index()
    ytd_summary.to_csv(output_dir / 'year_to_date_spending_by_category.csv', index=False)

    # 3. Cumulative spend
    cum = df.groupby('date')['amount'].sum().cumsum().reset_index()
    cum.to_csv(output_dir / 'cumulative_spending.csv', index=False)

    # 4. 3-month rolling average
    rolling = pivot.rolling(window=3).mean().dropna()
    rolling.to_csv(output_dir / '3mo_rolling_avg_by_category.csv')

    # 5. Top 10 spending descriptions
    desc_col = 'description' if 'description' in df.columns else df.columns[1]
    top = df.groupby(desc_col)['amount'].sum().nlargest(10).reset_index()
    top.columns = ['description', 'amount']
    top.to_csv(output_dir / 'top_10_spenders.csv', index=False)

    # Print report summary
    logging.info("Generated reports:")
    for report in [
        'monthly_spending_by_category.csv',
        'year_to_date_spending_by_category.csv',
        'cumulative_spending.csv',
        '3mo_rolling_avg_by_category.csv',
        'top_10_spenders.csv'
    ]:
        logging.info(f"- {report}")

def plot_monthly_spending(df):
    """Plot the monthly spending by category."""
    monthly = df.groupby(['year_month', 'category'])['amount'].sum().reset_index()
    pivot = monthly.pivot(index='year_month', columns='category', values='amount').fillna(0)
    pivot.plot(title='Monthly Spending by Category')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()