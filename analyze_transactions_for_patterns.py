#!/usr/bin/env python3

import pandas as pd

csv_path = input("Enter path to your transaction CSV: ").strip()
df = pd.read_csv(csv_path)

print("\n--- Column Names ---")
print(df.columns.tolist())

if 'Description' not in df.columns:
    raise ValueError("CSV must have a 'Description' column!")

print("\n--- 50 Most Common Descriptions (Vendor Strings) ---")
desc_counts = df['Description'].value_counts().head(50)
print(desc_counts.to_string())

print("\n--- Most Common Words/Phrases in Descriptions ---")
from collections import Counter
words = df['Description'].astype(str).str.upper().str.split(expand=True).stack()
common_words = Counter(words).most_common(40)
for word, count in common_words:
    print(f"{word:15} {count}")

print("\n--- Top 20 Vendors by Unique Transaction Count ---")
top_vendors = df['Description'].value_counts().head(20)
print(top_vendors)

print("\n--- Transaction Type Frequency (by first word) ---")
first_words = df['Description'].astype(str).str.split().str[0].str.upper().value_counts().head(20)
print(first_words)

if 'Debit' in df.columns:
    print("\n--- Outgoing (Debit) Amount Distribution ---")
    print(df['Debit'].describe())
if 'Credit' in df.columns:
    print("\n--- Incoming (Credit) Amount Distribution ---")
    print(df['Credit'].describe())

print("\n--- Unique Descriptions: ", df['Description'].nunique())

# Optionally: Export most common descriptions for your regex pattern mapping
desc_counts.to_csv("most_common_descriptions.csv")
