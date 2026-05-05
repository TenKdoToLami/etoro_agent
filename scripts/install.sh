#!/bin/bash

# Path to the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"
JOB_COMMAND="cd $PROJECT_DIR && $PROJECT_DIR/venv/bin/python -m etoro_bot run-job"
CRON_SCHEDULE="0 17 * * 1-5" # 17:00 Mon-Fri

# Check if the cron job already exists
crontab -l 2>/dev/null | grep -F "$JOB_COMMAND" > /dev/null

if [ $? -eq 0 ]; then
    echo "Cron job already exists."
else
    # Append the cron job
    (crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $JOB_COMMAND") | crontab -
    echo "Cron job installed: $CRON_SCHEDULE $JOB_COMMAND"
fi
