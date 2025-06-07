#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze 12 months of spending from a transactions CSV."
    )
    parser.add_argument(
        "input_csv",
        help=(
            "Path to transactions CSV (must have date, amount, category columns)"
        ),
    )
    parser.add_argument(
        "--output_dir",
        default=".",
        help="Directory to save output CSVs (default: current directory)",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Do not display the monthly spending plot",
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
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() > len(df) * 0.5:
                logging.info(f"Detected date column: '{col}'")
                return parsed
        except Exception:
            continue
    raise ValueError("No suitable date column found.")


def detect_amount_column(df):
    """Detect the first numeric column as the amount column."""
    num_cols = df.select_dtypes(include=["number"]).columns
    if len(num_cols) > 0:
        logging.info(f"Detected amount column: '{num_cols[0]}'")
        return pd.to_numeric(df[num_cols[0]], errors="coerce").fillna(0)
    # Try to find a likely amount column by name if no numeric columns
    for col in df.columns:
        if "amount" in col.lower():
            try:
                vals = pd.to_numeric(df[col], errors="coerce")
                if vals.notna().sum() > len(df) * 0.5:
                    logging.info(f"Detected amount column by name: '{col}'")
                    return vals.fillna(0)
            except Exception:
                continue
    raise ValueError("No numeric column found for amounts.")


def ensure_category_column(df):
    """Ensure a category column exists."""
    if "category" not in df.columns:
        logging.warning(
            "No category column found. Assigning all as 'Uncategorized'."
        )
        df["category"] = "Uncategorized"
    return df["category"]


def generate_reports(df, output_dir="."):
    """Generate various spending reports and save them to output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare grouping columns
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["year_month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    # 1. Monthly spending by category
    monthly = (
        df.groupby(["year_month", "category"], as_index=False)["amount"]
        .sum()
    )
    pivot = (
        monthly.pivot(index="year_month", columns="category", values="amount")
        .fillna(0)
    )
    monthly_csv = output_dir / "monthly_spending_by_category.csv"
    pivot.to_csv(monthly_csv)

    # 2. Year-to-date (last 12 months) summary
    latest = df["date"].max()
    if pd.isnull(latest):
        raise ValueError("No valid dates found in the data.")
    ytd_start = latest - pd.DateOffset(months=12)
    ytd = df[df["date"] >= ytd_start]
    ytd_summary = ytd.groupby("category", as_index=False)["amount"].sum()
    ytd_csv = output_dir / "year_to_date_spending_by_category.csv"
    ytd_summary.to_csv(ytd_csv, index=False)

    # 3. Cumulative spend
    cum = (
        df.sort_values("date")
        .groupby("date", as_index=False)["amount"]
        .sum()
    )
    cum["cumulative_amount"] = cum["amount"].cumsum()
    cum_csv = output_dir / "cumulative_spending.csv"
    cum[["date", "cumulative_amount"]].to_csv(cum_csv, index=False)

    # 4. 3-month rolling average
    rolling = pivot.rolling(window=3, min_periods=1).mean()
    rolling_csv = output_dir / "3mo_rolling_avg_by_category.csv"
    rolling.to_csv(rolling_csv)

    # 5. Top 10 spending descriptions
    if "description" in df.columns:
        desc_col = "description"
    else:
        # Try to find a likely description column
        possible_desc = [col for col in df.columns if "desc" in col.lower()]
        if possible_desc:
            desc_col = possible_desc[0]
        else:
            # Fallback: use the first non-date, non-amount, non-category column
            exclude = {"date", "amount", "category", "year_month"}
            candidates = [col for col in df.columns if col not in exclude]
            desc_col = candidates[0] if candidates else df.columns[0]
    top = (
        df.groupby(desc_col, as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(10)
    )
    top.columns = ["description", "amount"]
    top_csv = output_dir / "top_10_spenders.csv"
    top.to_csv(top_csv, index=False)

    # Print report summary
    logging.info("Generated reports:")
    for f in [
        monthly_csv,
        ytd_csv,
        cum_csv,
        rolling_csv,
        top_csv,
    ]:
        logging.info(f"- {f}")

    # Optional: display plot for monthly spending
    return pivot


def main():
    setup_logging()
    args = parse_args()

    # Load data
    try:
        df = pd.read_csv(args.input_csv)
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return

    # Detect and assign columns
    try:
        df["date"] = detect_date_column(df)
        df["amount"] = detect_amount_column(df)
        df["category"] = ensure_category_column(df)
    except Exception as e:
        logging.error(f"Error detecting columns: {e}")
        return

    # Generate reports
    try:
        pivot = generate_reports(df, output_dir=args.output_dir)
    except Exception as e:
        logging.error(f"Error generating reports: {e}")
        return

    # Show plot unless suppressed
    if not args.no_plot:
        try:
            ax = pivot.plot(title="Monthly Spending by Category", figsize=(10, 6))
            ax.set_ylabel("Amount")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            logging.error(f"Error displaying plot: {e}")


if __name__ == "__main__":
    main()
