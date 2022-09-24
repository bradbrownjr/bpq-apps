#!/bin/sh
neofetch
df /
echo
ps -A | grep -E 'direwolf|linbpq' | column -t

