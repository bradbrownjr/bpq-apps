#!/usr/bin/env python3
"""
Weather Reports for Packet Radio
--------------------------------
Pull weather data from the National Weather Service API.

Features:
- Current conditions and forecasts
- Gridsquare-based location detection
- BPQ32 config integration

Author: Brad Brown KC1JMH
Version: 1.2
Date: October 2025
"""

# Import necessary modules
import requests # Import requests module for making HTTP requests, for pulling data from the NWS API
import json # Import json module for parsing JSON data
import os # Import os module for file operations
import sys # Import sys module for command-line arguments
import re # Import re module for stripping HTML tags from text with regular expressions
from datetime import datetime # Import datetime module for parsing ISO 8601 date strings into human-readable format

VERSION = "1.2"
APP_NAME = "wx.py"

try:
    import maidenhead as mh # Import what's needed to get lattitude and longitude from gridsquare location
except ImportError:
    os.system('python3 -m pip install maidenhead')
    import maidenhead as mh

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
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


# User variables
url="https://api.weather.gov"
state="ME" # State abbreviation

# Look for the LOCATOR variable in the BPQ32 config file ""../linbpq/bpq32.cfg", assuming the apps folder is adjacent
pwd=os.getcwd() # Get the current working directory
try:
    config_path = os.path.join(pwd, "linbpq", "bpq32.cfg") # Path to the BPQ32 config file
    with open(config_path, "r") as f:
        for line in f:
            if "LOCATOR" in line: # Look for the LOCATOR variable
                gridsquare = line.split("=")[1].strip()
except FileNotFoundError:
    print("File not found. Using default gridsquare.")
    gridsquare="FN43pp" # Default gridsquare is in Southern Maine, author's QTH

# Get the gridpoint for the NWS office from the lattitude and longitude of the maidenhead gridsquare
def get_gridpoint(latlon):
    lat, lon = latlon
    response = requests.get("{}/points/{},{}".format(url, lat, lon))
    data = response.json()
    gridpoint = data['properties']['forecastGridData']
    wfo = data['properties']['cwa']
    return gridpoint, wfo

# Strip html and special characters from a value with the re module
def strip_html(text):
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Remove special characters like &nbsp;
    text = re.sub('&[a-zA-Z]+;', ' ', text)
    # Replace \r\n with a single carriage return
    text = text.replace('\r\n', '\r')
    return text

# Get the gridpoint and WFO values for the local NWS office
gridpoint, wfo = get_gridpoint(mh.to_location(gridsquare))
print("Gridpoint URL: {}".format(gridpoint))
print("WFO: {}".format(wfo))

# Get weather office headlines from "/offices/{officeId}/headlines"
def get_headlines():
    response = requests.get("{}/offices/{}/headlines".format(url, wfo))
    data = response.json()
    headlines = []
    for item in data["@graph"]:
        title = item["title"]
        # Parse the ISO 8601 date string and format the date into a more human-readable format
        issuance_time_human_str = datetime.fromisoformat(item["issuanceTime"]).strftime("%Y-%m-%d %H:%M:%S")
        content_html = item["content"]
        content_text = strip_html(content_html)
        headlines.append({
            "title": title,
            "issuanceTime": issuance_time_human_str,
            "content": content_text
        })
    return headlines

# Check for app updates
check_for_app_update(VERSION, APP_NAME)

# Print weather header
print()
print(r"__      ____  __")
print(r"\ \ /\ / /\ \ /")
print(r" \ V  V /  >  <")
print(r"  \_/\_/  /_/\_/")
print()
print("WX v{} - Maine/NH Weather Reports".format(VERSION))
print()

try:
    headlines = get_headlines()
    for headline in headlines:
        print("Title: {}".format(headline['title']))
        print("Issuance Time: {}".format(headline['issuanceTime']))
        print("Content: {}\n".format(headline['content']))

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
