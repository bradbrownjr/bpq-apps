#!/usr/bin/env python3
"""
Weather Reports for Southern Maine and New Hampshire  
----------------------------------------------------
Local weather reports from National Weather Service Gray Office.

Author: Brad Brown KC1JMH
Version: 1.2
Date: January 2026
"""

import requests
import sys
import os

VERSION = "1.2"
APP_NAME = "wx-me.py"

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
print(r"  __ _ _   ___  __")
print(r" / _` | | | \ \/ /")
print(r"| (_| | |_| |>  < ")
print(r" \__, |\__, /_/\_\\")
print(r" |___/ |___/      ")
print()
print("WX-ME v{} - Maine/NH Weather Reports".format(VERSION))
print("-" * 40)

menu = """
Main Menu:
----------------------------------------
1) Maine/New Hampshire Weather Summary
2) Maine/New Hampshire Weather Roundup  
3) Western Maine/New Hampshire Forecast
4) Northern and Eastern Maine Forecast
5) Maine/New Hampshire Max/Min Temperature
   and Precipitation Table
----------------------------------------"""

about = """
Get text products right from the
National Weather Service in Gray, ME.

This is a Python3 script which pulls data from
https://www.maine.gov/mema/weather/general-information

Script developed by Brad Brown KC1JMH
"""

def pullthis(url):
        response = requests.get(url)
        data = response.text
        print("\n{}\n".format(data))

try:
    print (menu)
    while True:
            selected = str(input("Menu: [1-5] R)elist A)bout Q)uit :> "))
            if "1" in selected:
                    pullthis("https://tgftp.nws.noaa.gov/data/raw/aw/awus81.kgyx.rws.gyx.txt")
            elif "2" in selected:
                    pullthis("https://tgftp.nws.noaa.gov/data/raw/as/asus41.kgyx.rwr.gyx.txt")
            elif "3" in selected:
                    pullthis("https://tgftp.nws.noaa.gov/data/forecasts/state/nh/nhz010.txt")
            elif "4" in selected:
                    pullthis("https://tgftp.nws.noaa.gov/data/raw/fp/fpus61.kcar.sft.car.txt")
            elif "5" in selected:
                    pullthis("https://tgftp.nws.noaa.gov/data/raw/as/asus61.kgyx.rtp.gyx.txt")
            elif "a" in selected.lower():
                    print (about)
            elif "r" in selected.lower():
                    print (menu)
            elif "q" in selected.lower():
                    print("\nExiting...")
                    break

except KeyboardInterrupt:
    print("\n\nExiting...")
except Exception as e:
    error_str = str(e)
    if 'timeout' in error_str.lower() or 'connection' in error_str.lower() or 'urlopen' in error_str.lower():
        try:
            import socket
            socket.create_connection(('8.8.8.8', 53), timeout=2)
            print("\nConnection Error: {}".format(error_str))
        except (socket.timeout, socket.error, OSError):
            print("\nInternet appears to be unavailable.")
            print("Try again later or check your connection.")
    else:
        print("\nError: {}".format(error_str))
    print("Please report this issue if it persists.")
