#!/data/data/com.termux/files/usr/bin/bash

pkg install -y termux-api cronie python

# Enable crond
mkdir -p ~/.termux
sv-enable crond 2>/dev/null || true

# Absolute path to scripts directory
SCRIPT_DIR="$HOME/mpesa-tools"
LOG="$SCRIPT_DIR/mpesa-tools.log"
BEANCOUNT_FILE="$HOME/storage/shared/Documents/Jonnieey-Finances/ledger/current.beancount"

# Create cron job
CRON_JOB="50 23 * * * cd $SCRIPT_DIR && bash run-mpesa.sh

# Install cron job if not already present
( crontab -l 2>/dev/null | grep -Fv "xtract-android.py" ; echo "$CRON_JOB" ) | crontab -

echo "✅ Cron job installed:"
echo "$CRON_JOB"
