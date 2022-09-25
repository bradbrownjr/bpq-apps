#!/bin/sh
# Install Neofetch with 'sudo apt-get install neofetch'

# OS logo and system information
neofetch

# Disk usage
df /
echo
# Confirm required node processes are running
ps -A | grep -E 'direwolf|linbpq' | column -t

