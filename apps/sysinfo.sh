#!/bin/sh
# Prints neofetch output without ANSI color
# Ref https://github.com/dylanaraps/neofetch/issues/753
neofetch|sed 's/\x1B\[[0-9;\?]*[a-zA-Z]//g'

# Get disk space / utilization
df / -h
echo

# List node-required processes
ps -A | grep -E 'direwolf|linbpq' | column -t
