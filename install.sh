#!/usr/bin/env bash
# install.sh: One-step installer for Spend-Analysis on macOS
# Installs prerequisites, clones/updates the repo, sets up virtualenv, and installs Python deps.

set -euo pipefail

# Destination directory
DEST_DIR="$HOME/Documents/GitHub/spend-analysis"

# 1. Ensure Homebrew is installed
if ! command -v brew &>/dev/null; then
  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 2. Install Python 3.11 via Homebrew if missing
if ! brew list python@3.11 &>/dev/null; then
  echo "Installing Python 3.11..."
  brew install python@3.11
fi

# 3. Install Git if missing
if ! command -v git &>/dev/null; then
  echo "Git not found. Installing Git..."
  brew install git
fi

# 4. Clone or update the spend-analysis project
mkdir -p "$(dirname "$DEST_DIR")"
if [ ! -d "$DEST_DIR" ]; then
  echo "Cloning spend-analysis into $DEST_DIR..."
  git clone https://github.com/yourusername/spend-analysis.git "$DEST_DIR"
else
  echo "Updating spend-analysis in $DEST_DIR..."
  git -C "$DEST_DIR" pull
fi

# 5. Enter project directory
cd "$DEST_DIR"

# 6. Create and activate Python virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
# shellcheck source=/dev/null
source venv/bin/activate

# 7. Upgrade pip and install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 8. Report completion
cat << 'EOF'

✅ Spend-Analysis setup complete!

Next steps:
  cd "$DEST_DIR"
  source venv/bin/activate
  ./analysis.py /path/to/AccountHistory.csv

Generated reports will appear in this directory.
EOF