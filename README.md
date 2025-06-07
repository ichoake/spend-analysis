# Spend Analysis

A set of scripts and data files for analyzing spending patterns.

## Getting Started

1. **Clone the repository:**
   ```sh
   git clone https://github.com/ichoake/spend-analysis.git
   cd spend-analysis
   ```

2. **(Optional) Set up a virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   - If you have a `requirements.txt`, run:
     ```sh
     pip install -r requirements.txt
     ```
   - Otherwise, install any needed packages manually.

4. **Run the analysis scripts:**
   ```sh
   python analyze_transactions_for_patterns.py
   ```

## Project Structure

- `analyze_transactions_for_patterns.py` - Main analysis script
- `pattern_auto_discovery.py` - Pattern discovery script
- `script/` - Additional scripts
- `docs/` - Documentation
- `AccountHistory.csv`, `CampusAccountHistory.csv` - Example data files

## License

MIT