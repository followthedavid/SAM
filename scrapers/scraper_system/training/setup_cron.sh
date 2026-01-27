#!/bin/bash
# Setup cron job for continuous training pipeline
#
# This runs the pipeline every 2 hours to:
# 1. Process new scraped data
# 2. Auto-trigger training when threshold is met
#
# Usage: ./setup_cron.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3)
PIPELINE_SCRIPT="$SCRIPT_DIR/continuous_pipeline.py"
LOG_FILE="/tmp/sam_continuous_pipeline.log"

# Create the cron entry
CRON_ENTRY="0 */2 * * * cd $SCRIPT_DIR/.. && $PYTHON_PATH $PIPELINE_SCRIPT --process --auto-train --threshold 500 >> $LOG_FILE 2>&1"

# Check if already exists
if crontab -l 2>/dev/null | grep -q "continuous_pipeline.py"; then
    echo "Cron job already exists. Updating..."
    crontab -l | grep -v "continuous_pipeline.py" | crontab -
fi

# Add the cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "Cron job installed!"
echo "Schedule: Every 2 hours"
echo "Log file: $LOG_FILE"
echo ""
echo "Current cron jobs:"
crontab -l

echo ""
echo "To remove: crontab -l | grep -v continuous_pipeline | crontab -"
