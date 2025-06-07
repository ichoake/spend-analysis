import os
import re
import json
import pandas as pd
from collections import Counter
from dotenv import load_dotenv
import openai
import logging
from pathlib import Path
import sys

# --- Configuration ---
GPT_CACHE_FILE = "gpt_pattern_suggestions_auto.json"
MERCHANT_CLUES_CSV = "merchant_clues_auto.csv"
TYPE_CLUES_CSV = "type_clues_auto.csv"
MERCHANT_GPT_CSV = "merchant_clues_gpt_auto.csv"
TYPE_GPT_CSV = "type_clues_gpt_auto.csv"
DEFAULT_TOP_N = 30

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

def setup_openai():
    """Load OpenAI API key from .env and set up openai module."""
    env_path = os.path.expanduser("~/.env")
    if not os.path.exists(env_path):
        logging.error(f".env file not found at {env_path}. Please create it and add your OPENAI_API_KEY.")
        sys.exit(1)
    load_dotenv(env_path)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY not found in .env file.")
        sys.exit(1)
    openai.api_key = api_key

def gpt_label_pattern(pattern_desc, cache):
    """
    Query GPT to classify a merchant clue/type and generate a regex pattern.
    Uses a cache to avoid redundant API calls.
    """
    if pattern_desc in cache:
        return cache[pattern_desc]
    prompt = (
        f"This is a US bank transaction merchant clue or substring: '{pattern_desc}'. "
        "Classify it with a finance category (Rent, Utilities, Streaming, Shopping, Bank Fee, SaaS, Payment, Food, Gas, Travel, Other) "
        "AND give a regex pattern to match all similar descriptions. "
        "Format: CATEGORY | REGEX"
    )
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a financial data wrangler and regex expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=32,
            temperature=0.1,
        )
        reply = resp['choices'][0]['message']['content'].strip()
        # Basic validation: ensure format is CATEGORY | REGEX
        if "|" not in reply:
            logging.warning(f"Unexpected GPT reply format for '{pattern_desc}': {reply}")
            reply = "Other | .*"
    except Exception as e:
        logging.error(f"GPT ERROR: {e} for '{pattern_desc[:30]}'")
        reply = "Other | .*"
    cache[pattern_desc] = reply
    return reply

def extract_clues(df):
    """
    Extract merchant and type clues from the Description column.
    Returns two Series: merchant clues and type clues.
    """
    if 'Description' not in df.columns:
        raise ValueError("CSV must have a 'Description' column!")
    merchant = df['Description'].str.extract(r'(?:CO:|NAME:)\s*([A-Za-z0-9.\- ]+)', expand=False)
    type_after = df['Description'].str.extract(r'TYPE:\s*([A-Za-z0-9.\- ]+)', expand=False)
    return merchant, type_after

def save_counts(series, filename, top_n):
    """Save value counts of a Series to CSV."""
    counts = series.value_counts().dropna().head(top_n)
    counts.to_csv(filename)
    return counts

def load_gpt_cache(cache_file):
    """Load GPT cache from file, or return empty dict if not found."""
    try:
        with open(cache_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_gpt_cache(cache, cache_file):
    """Save GPT cache to file."""
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)

def label_clues_with_gpt(clues_counts, clue_label, gpt_cache):
    """
    For each clue, get GPT label/regex and return a list of dicts.
    clue_label: 'Merchant_Clue' or 'Type_Clue'
    """
    results = []
    for clue in clues_counts.index:
        label = gpt_label_pattern(clue, gpt_cache)
        results.append({
            clue_label: clue,
            'Count': int(clues_counts[clue]),
            'GPT_Label_Regex': label
        })
    return results

def compile_category_patterns(merchant_gpt, type_gpt):
    """
    Compile a dictionary of regex: category from GPT results,
    skipping 'Other' and generic patterns.
    """
    patterns = {}
    for row in merchant_gpt + type_gpt:
        suggestion = row['GPT_Label_Regex']
        if '|' in suggestion:
            cat, regex = [s.strip() for s in suggestion.split('|', 1)]
            if cat and regex and cat != "Other" and regex != ".*":
                patterns[regex] = cat
    return patterns

def analyze_and_gpt(csv_path, top_n=DEFAULT_TOP_N):
    """
    Main analysis function:
    - Loads CSV
    - Extracts merchant/type clues
    - Saves top clues
    - Labels clues with GPT (with caching)
    - Saves labeled clues
    - Prints ready-to-paste CATEGORY_PATTERNS
    """
    # Load and filter data
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        sys.exit(1)
    if 'Post Date' not in df.columns:
        logging.error("CSV must have a 'Post Date' column!")
        sys.exit(1)
    df['Post Date'] = pd.to_datetime(df['Post Date'], errors='coerce')
    df = df[df['Post Date'] >= '2023-01-01']

    # Extract clues
    merchant, type_after = extract_clues(df)

    # Save top clues
    merchant_counts = save_counts(merchant, MERCHANT_CLUES_CSV, top_n)
    type_counts = save_counts(type_after, TYPE_CLUES_CSV, top_n)
    logging.info(f"Saved top {top_n} merchant clues to {MERCHANT_CLUES_CSV}")
    logging.info(f"Saved top {top_n} type clues to {TYPE_CLUES_CSV}")

    # Load GPT cache
    gpt_cache = load_gpt_cache(GPT_CACHE_FILE)

    # Label clues with GPT
    logging.info("Labeling merchant clues with GPT...")
    merchant_gpt = label_clues_with_gpt(merchant_counts, 'Merchant_Clue', gpt_cache)
    logging.info("Labeling type clues with GPT...")
    type_gpt = label_clues_with_gpt(type_counts, 'Type_Clue', gpt_cache)

    # Save labeled clues
    pd.DataFrame(merchant_gpt).to_csv(MERCHANT_GPT_CSV, index=False)
    pd.DataFrame(type_gpt).to_csv(TYPE_GPT_CSV, index=False)
    logging.info(f"Saved GPT-labeled merchant clues to {MERCHANT_GPT_CSV}")
    logging.info(f"Saved GPT-labeled type clues to {TYPE_GPT_CSV}")

    # Save updated GPT cache
    save_gpt_cache(gpt_cache, GPT_CACHE_FILE)

    # Compile and print CATEGORY_PATTERNS
    patterns = compile_category_patterns(merchant_gpt, type_gpt)
    print("\n--- Ready-to-paste CATEGORY_PATTERNS ---\n")
    print("CATEGORY_PATTERNS = {")
    for regex, cat in patterns.items():
        print(f'    r"{regex}": "{cat}",')
    print("}")
    print("\nMerchant and type pattern CSVs are saved for further review.")

def main():
    setup_openai()
    csv_path = input("Enter path to your AccountHistory.csv: ").strip()
    if not csv_path or not Path(csv_path).exists():
        logging.error(f"File not found: {csv_path}")
        sys.exit(1)
    try:
        top_n = int(input(f"How many top clues to analyze? (default {DEFAULT_TOP_N}): ").strip() or DEFAULT_TOP_N)
    except Exception:
        top_n = DEFAULT_TOP_N
    analyze_and_gpt(csv_path, top_n=top_n)

if __name__ == "__main__":
    main()
