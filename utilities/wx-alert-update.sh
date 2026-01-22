#!/bin/bash
#
# wx-alert-update.sh - Update weather beacon text for BPQ node
#
# This script calls wx.py --beacon and saves the output to a beacon text file.
# The beacon includes local weather alert count and directs users to connect
# to the WX app for details. Run via cron every 15-30 minutes.
#
# Note: SKYWARN spotter activation monitoring is handled separately via
#       https://github.com/bradbrownjr/skywarn-activation-alerts
#
# Usage:
#   wx-alert-update.sh [output_file] [gridsquare]
#
# Defaults:
#   output_file: ~/linbpq/beacontext.txt
#   gridsquare: From bpq32.cfg LOCATOR
#
# Cron example (every 15 minutes):
#   */15 * * * * /home/ect/utilities/wx-alert-update.sh >/dev/null 2>&1
#
# Author: Brad Brown KC1JMH
# Date: January 2026

# Configuration
OUTPUT_FILE="${1:-$HOME/linbpq/beacontext.txt}"
GRIDSQUARE="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WX_PY="$SCRIPT_DIR/../apps/wx.py"

# Check if wx.py exists
if [[ ! -x "$WX_PY" ]]; then
    echo "Error: wx.py not found or not executable at $WX_PY" >&2
    exit 1
fi

# Run wx.py to get beacon text (includes alerts + SKYWARN status)
if [[ -n "$GRIDSQUARE" ]]; then
    BEACON_TEXT=$("$WX_PY" --beacon "$GRIDSQUARE" 2>/dev/null)
else
    BEACON_TEXT=$("$WX_PY" --beacon 2>/dev/null)
fi

# Check if we got output
if [[ -z "$BEACON_TEXT" ]]; then
    # Fallback message if script fails
    BEACON_TEXT="WS1EC-15: Weather info unavailable"
fi

# Write to output file (atomic write with temp file)
TEMP_FILE="${OUTPUT_FILE}.tmp"
echo "$BEACON_TEXT" > "$TEMP_FILE"
mv "$TEMP_FILE" "$OUTPUT_FILE"

# Exit successfully
exit 0
