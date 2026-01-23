#!/usr/bin/env sh
# System Information for BPQ Packet Radio Node
# Displays OS, disk, and process info (ASCII-only)

echo ""
echo "WS1EC-15 SYSTEM INFORMATION"
echo "----------------------------------------"
echo ""

# OS Information
echo "Operating System:"
lsb_release -d 2>/dev/null | cut -f2
uname -m
echo ""

# Kernel and Uptime
echo "Kernel: $(uname -r)"
uptime -p 2>/dev/null || uptime | sed 's/.*up //' | sed 's/, [0-9]* user.*//'
echo ""

# Disk Usage
echo "Disk Usage:"
df / -h | awk 'NR==1 {print "  "$1, $2, $3, $5} NR==2 {print "  "$1, $2, $3, $5}'
echo ""

# Memory Usage
echo "Memory:"
free -h | awk 'NR==2 {print "  Total: "$2" Used: "$3" Available: "$7}'
echo ""

# Node Processes
echo "Node Processes:"
ps -eo pid,comm,etime | grep -E 'direwolf|linbpq' | awk '{print "  "$2" (PID "$1") - "$3}' | column -t
echo ""
