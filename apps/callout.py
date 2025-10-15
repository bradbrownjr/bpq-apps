#!/usr/bin/env python3
"""
Call Output Test Application
-----------------------------
Simple test application to demonstrate capturing the callsign
passed from BPQ32 when a user connects.

When BPQ is configured to pass the callsign (without NOCALL flag),
the callsign is sent on the first line via stdin.

Usage in bpq32.cfg:
  APPLICATION 7,CALLOUT,C 9 HOST 3 S

This demonstrates the callsign capture mechanism that can be used
in other applications like forms.py.

Author: Brad Brown KC1JMH
Date: October 2025
"""

import sys

# Capture BPQ callsign from stdin (first line)
try:
    call = input().strip()  # Read first line from stdin
    if call:
        print("Hello, {}!".format(call))
        print()
        print("Your callsign was successfully captured from BPQ32.")
        print()
        print("This demonstrates how BPQ passes the connecting user's")
        print("callsign to applications when configured without the")
        print("NOCALL flag.")
        print()
        print("Configuration used:")
        print("  APPLICATION X,CALLOUT,C 9 HOST X S")
        print()
        print("The 'S' flag strips the SSID if you want just the base call.")
        print("Remove the 'S' to include SSID (e.g., KC1JMH-8).")
    else:
        print("No callsign received.")
        print("Check BPQ32 configuration.")
except EOFError:
    print("Error: Could not read callsign from stdin.")
    print("This application expects input from BPQ32.")
except Exception as e:
    print("Error: {}".format(str(e)))

# Optional: Demonstrate reading additional lines
# Uncomment below to test capturing multiple lines of input

#print("\n--- Testing multi-line input capture ---")
#print("Type some text and press Ctrl+D (Linux) or Ctrl+Z (Windows):")
#print()
#
#import fileinput
#for line in fileinput.input():
#    print("Received: {}".format(line.strip()))

# Alternative method using sys.stdin.read()
# Uncomment to test reading all stdin at once

#print("\n--- Alternative: Reading all stdin ---")
#all_input = sys.stdin.read()
#print("All input received:")
#print(all_input)
