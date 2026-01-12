#!/data/data/com.termux/files/usr/bin/bash

SCRIPT_DIR="$HOME/mpesa-tools"
LOG="$SCRIPT_DIR/mpesa-tools.log"
BEANCOUNT_FILE="$HOME/storage/shared/Documents/Jonnieey-Finances/ledger/current.beancount"

cd "$HOME/mpesa-tools" || exit 1

/data/data/com.termux/files/usr/bin/python xtract-android.py \
  --output $FINANCE_DIR >> "$LOG" 2>&1
