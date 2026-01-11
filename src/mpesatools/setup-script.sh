#!/data/data/com.termux/files/usr/bin/bash

# Ensure required packages
# pkg install -y termux-api cronie python

# Enable crond
mkdir -p ~/.termux
sv-enable crond 2>/dev/null || true

# Absolute path to scripts directory
SCRIPT_DIR="$HOME/storage/shared/scripts/mpesa-tools"
FINANCE_DIR="$HOME/storage/shared/Documents/Jonnieey-Finances/ledger"
# Create cron job
CRON_JOB="50 23 * * * cd $SCRIPT_DIR && python xtract-android.py --output $FINANCE_DIR/current.beancount >> $SCRIPT_DIR/mpesa-cron.log 2>&1"

# Install cron job if not already present
( crontab -l 2>/dev/null | grep -Fv "xtract-android.py" ; echo "$CRON_JOB" ) | crontab -

echo "✅ Cron job installed:"
echo "$CRON_JOB"
