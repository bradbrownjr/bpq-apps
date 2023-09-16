#!/usr/bin/env sh
# Print OS info
lsb_release -a 2>/dev/null

# Get disk space / utilization
df / -h
echo

# List node-required processes
ps -A | grep -E 'direwolf|linbpq' | column -t
