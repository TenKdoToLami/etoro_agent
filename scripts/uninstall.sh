#!/bin/bash

# Path to the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"
JOB_COMMAND="cd $PROJECT_DIR && python -m etoro_bot run-job"

# Remove the cron job matching the exact command
crontab -l 2>/dev/null | grep -vF "$JOB_COMMAND" | crontab -

echo "Cron job removed: $JOB_COMMAND"
