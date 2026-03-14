#!/usr/bin/env bash
# setup_cron.sh
# Installs a cron job to run main.py every day at midnight (00:00).
# Safe to re-run — it will not add duplicate entries.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(which python3)"
MAIN_SCRIPT="$SCRIPT_DIR/main.py"
LOG_FILE="$SCRIPT_DIR/run.log"

CRON_ENTRY="0 0 * * * $PYTHON_BIN $MAIN_SCRIPT >> $LOG_FILE 2>&1"

# Check if entry already exists
if crontab -l 2>/dev/null | grep -qF "$MAIN_SCRIPT"; then
    echo "Cron job already installed. No changes made."
else
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "Cron job installed:"
    echo "  $CRON_ENTRY"
fi

echo ""
echo "Current crontab:"
crontab -l
