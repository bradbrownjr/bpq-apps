#!/usr/bin/env python3
"""
NWS FTP File Downloader for Weather Data
----------------------------------------
Download raw NWS products via FTP for offline processing.

Version: 1.0
"""

import sys
import os

VERSION = "1.0"
APP_NAME = "wxnws-ftp.py"

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
                    
                    print("\nUpdate installed successfully!")
                    print("Please re-run this command to use the updated version.")
                    print("\nQuitting...")
                    sys.exit(0)
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

print()
print(r"__      ____  __")
print(r"\ \ /\ / /\ \/ /")
print(r" \ V  V /  >  < ")
print("  \\_/\\_/  /_/\\_\\")
print()
print("WXNWS-FTP v{} - NWS FTP Product Downloader".format(VERSION))
print()

# Variables
region = "gyx" # Lowercase region code for local NWS office

# Enable use of FTP with Python
import ftplib

try:
    # Define the FTP server and credentials
    ftp = ftplib.FTP('tgftp.nws.noaa.gov')
    ftp.login()

    # Define the directory to change to
    ftp.cwd('data/raw/fx')

    # Find files fxus[##].kgyx.afd.gyx.txt and download them
    files = ftp.nlst('fxus*.afd.$region.txt')
    for file in files:
        with open(file, 'wb') as f:
            ftp.retrbinary('RETR ' + file, f.write)

    # Display the files downloaded, pausing for input on every line containging "&&" to continue or quit
    for file in files:
        with open(file, 'r') as f:
            for line in f:
                print(line)
                if "&&" in line:
                    # Input "press enter to continue or Q to quit"
                    user_input = input("Press Enter to continue or Q to quit...")
                    if user_input.lower() == "q":
                        break
                elif "&&" not in line:
                    continue
                else:
                    break

except KeyboardInterrupt:
    print("\n\nExiting...")
except Exception as e:
    print("\nError: {}".format(str(e)))
    print("Please report this issue if it persists.")
