#!/bin/bash
#
# wx-alert-update.sh - Update local weather alert file for BPQ CTEXT
#
# This script calls wx.py --alert-summary and saves the output to a file
# that BPQ32's CTEXT can display. Run via cron every 15-30 minutes.
#
# Usage:
#   wx-alert-update.sh [output_file] [gridsquare]
#
# Defaults:
#   output_file: ~/linbpq/wx-alert.txt
#   gridsquare: From bpq32.cfg LOCATOR
#
# Cron example (every 15 minutes):
#   */15 * * * * /home/ect/utilities/wx-alert-update.sh >/dev/null 2>&1
#
# Author: Brad Brown KC1JMH
# Date: January 2026

# Configuration
OUTPUT_FILE="${1:-$HOME/linbpq/wx-alert.txt}"
GRIDSQUARE="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WX_PY="$SCRIPT_DIR/../apps/wx.py"

# Check if wx.py exists
if [[ ! -x "$WX_PY" ]]; then
    echo "Error: wx.py not found or not executable at $WX_PY" >&2
    exit 1
fi

# Run wx.py to get alert summary
if [[ -n "$GRIDSQUARE" ]]; then
    ALERT_LINE=$("$WX_PY" --alert-summary "$GRIDSQUARE" 2>/dev/null)
else
    ALERT_LINE=$("$WX_PY" --alert-summary 2>/dev/null)
fi

# Check if we got output
if [[ -z "$ALERT_LINE" ]]; then
    # Fallback message if script fails
    ALERT_LINE="Local Weather: Status unavailable"
fi

# Write to output file (atomic write with temp file)
TEMP_FILE="${OUTPUT_FILE}.tmp"
echo "$ALERT_LINE" > "$TEMP_FILE"
mv "$TEMP_FILE" "$OUTPUT_FILE"

# Exit successfully
exit 0
