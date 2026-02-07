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
Version: 1.2
Date: October 2025
"""

import sys
import os

VERSION = "1.2"
APP_NAME = "callout.py"

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
        import re
        import stat
        
        # Get the version from GitHub (silent check with short timeout)
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read().decode('utf-8')
        
        # Extract version from docstring
        version_match = re.search(r'Version:\s*([0-9.]+)', content)
        if version_match:
            github_version = version_match.group(1)
            
            if compare_versions(github_version, current_version) > 0:
                print("\nUpdate available: v{} -> v{}".format(current_version, github_version))
                print("Downloading new version...")
                
                # Download the new version
                script_path = os.path.abspath(__file__)
                try:
                    # Write to temporary file first, then replace
                    temp_path = script_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    # Ensure file is executable (Python script should be executable)
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    
                    # Replace old file with new one
                    os.replace(temp_path, script_path)
                    
                    print("Updated to v{}. Restarting...".format(github_version))
                    print()
                    sys.stdout.flush()
                    restart_args = [script_path] + sys.argv[1:]
                    os.execv(script_path, restart_args)
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    # Clean up temp file if it exists
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
    except Exception as e:
        # Don't block startup if update check fails (no internet, etc.)
        pass

def compare_versions(version1, version2):
    """Compare two version strings"""
    try:
        parts1 = [int(x) for x in str(version1).split('.')]
        parts2 = [int(x) for x in str(version2).split('.')]
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0
    except (ValueError, AttributeError):
        return 0

# Check for app updates
check_for_app_update(VERSION, APP_NAME)

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
