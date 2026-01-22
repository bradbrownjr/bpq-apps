#!/usr/bin/env python3
"""
Weather for Packet Radio
------------------------
Local and regional weather from National Weather Service API.

Features:
- Current conditions and forecasts from NWS
- Gridsquare-based location detection from bpq32.cfg
- Callsign-based weather lookup via HamDB
- Multiple location input formats: gridsquare, GPS, state, country, callsign
- Graceful offline fallback

Author: Brad Brown KC1JMH
Version: 1.3
Date: January 2026
"""

from __future__ import print_function
import sys
import os
import re
from datetime import datetime

VERSION = "1.3"
APP_NAME = "wx.py"


def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
        import stat
        
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read().decode('utf-8')
        
        version_match = re.search(r'Version:\s*([0-9.]+)', content)
        if version_match:
            github_version = version_match.group(1)
            
            if compare_versions(github_version, current_version) > 0:
                print("\nUpdate available: v{} -> v{}".format(current_version, github_version))
                print("Downloading new version...")
                
                script_path = os.path.abspath(__file__)
                try:
                    temp_path = script_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                             stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    os.replace(temp_path, script_path)
                    
                    print("\nUpdate installed successfully!")
                    print("Please re-run this command to use the updated version.")
                    print("\nQuitting...")
                    sys.exit(0)
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
    except Exception:
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


def get_bpq_locator():
    """Read LOCATOR from BPQ32 config file"""
    try:
        pwd = os.getcwd()
        config_path = os.path.join(pwd, "linbpq", "bpq32.cfg")
        with open(config_path, "r") as f:
            for line in f:
                if "LOCATOR" in line.upper():
                    grid = line.split("=")[1].strip()
                    return grid
    except (IOError, OSError):
        pass
    return None


def lookup_callsign(callsign):
    """Look up callsign gridsquare via HamDB"""
    try:
        import urllib.request
        import json
        
        url = "https://api.hamdb.org/v1/{}/json".format(callsign.upper())
        req = urllib.request.Request(url, headers={'User-Agent': 'WX-BPQ/1.0'})
        
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        hamdb = data.get('hamdb', {}).get('callsign', {})
        grid = hamdb.get('grid', '')
        
        if grid:
            return grid.upper()
    except Exception:
        pass
    
    return None


def is_internet_available():
    """Check if internet is available"""
    try:
        import socket
        socket.create_connection(('8.8.8.8', 53), timeout=2)
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def strip_html(text):
    """Remove HTML tags and special characters"""
    text = re.sub('<[^<]+?>', '', text)
    text = re.sub('&[a-zA-Z]+;', ' ', text)
    text = text.replace('\r\n', '\n')
    return text


def grid_to_latlon(gridsquare):
    """Convert gridsquare to lat/lon"""
    try:
        import maidenhead as mh
        return mh.to_location(gridsquare)
    except ImportError:
        return None
    except Exception:
        return None


def is_callsign_format(text):
    """Check if text looks like a callsign"""
    pattern = r'^[A-Za-z]{1,2}\d[A-Za-z]{1,3}(-\d{1,2})?$'
    return bool(re.match(pattern, text.strip()))


def is_gridsquare_format(text):
    """Check if text looks like a gridsquare"""
    pattern = r'^[A-Ra-r]{2}[0-9]{2}[a-xa-x]{0,2}$'
    return bool(re.match(pattern, text.strip().upper()))


def get_gridpoint(latlon):
    """Get NWS gridpoint and WFO from lat/lon"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        gridpoint = data['properties']['forecastGridData']
        wfo = data['properties']['cwa']
        return gridpoint, wfo
    except Exception:
        return None, None


def get_headlines(wfo):
    """Get weather headlines from NWS office"""
    try:
        import urllib.request
        import json
        
        url = "https://api.weather.gov/offices/{}/headlines".format(wfo)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        headlines = []
        for item in data.get("@graph", []):
            title = item.get("title", "")
            issue_time = item.get("issuanceTime", "")
            content_html = item.get("content", "")
            content_text = strip_html(content_html)
            
            try:
                time_str = datetime.fromisoformat(issue_time.replace('Z', '+00:00')).strftime('%m/%d %H:%M')
            except:
                try:
                    time_str = datetime.strptime(issue_time.rstrip('Z'), '%Y-%m-%dT%H:%M:%S').strftime('%m/%d %H:%M')
                except:
                    time_str = "---"
            
            headlines.append({
                "title": title,
                "time": time_str,
                "content": content_text
            })
        
        return headlines
    except Exception:
        return None


def prompt_location(prompt_text="Enter location"):
    """Prompt for location input"""
    print("")
    print(prompt_text)
    print("  Enter: gridsquare, GPS coords (lat,lon),")
    print("         state (Maine/ME), country, or callsign")
    print("  (Q to cancel)")
    print("")
    
    while True:
        try:
            response = input(":> ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        
        if not response:
            continue
        
        if response.upper() == 'Q':
            return None
        
        # Try callsign first
        if is_callsign_format(response):
            print("Looking up {}...".format(response.upper()))
            grid = lookup_callsign(response)
            if grid and is_gridsquare_format(grid):
                latlon = grid_to_latlon(grid)
                if latlon:
                    return latlon, "{} ({})".format(response.upper(), grid)
            print("Not found. Try gridsquare or coordinates.")
            continue
        
        # Try gridsquare
        if is_gridsquare_format(response):
            latlon = grid_to_latlon(response.upper())
            if latlon:
                return latlon, response.upper()
            print("Invalid gridsquare. Try again.")
            continue
        
        # Try lat,lon
        try:
            parts = response.replace(',', ' ').split()
            if len(parts) == 2:
                lat = float(parts[0])
                lon = float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon), "{:.2f},{:.2f}".format(lat, lon)
        except (ValueError, IndexError):
            pass
        
        print("Could not parse. Try:")
        print("  - Gridsquare: FN43hp")
        print("  - GPS: 43.65, -70.25")
        print("  - Callsign: KC1JMH")


def print_header():
    """Print app header"""
    print()
    print(r"__      ____  __")
    print(r"\ \ /\ / /\ \/ /")
    print(r" \ V  V /  >  < ")
    print(r"  \_/\_/  /_/\_\\")
    print()
    print("WX v{} - Weather Reports".format(VERSION))
    print()


def print_menu():
    """Print main menu"""
    print("\nOptions:")
    print("1) Local weather (from bpq32.cfg)")
    print("2) Weather for a location")
    print("3) Weather for a callsign")
    print("\nQ) Quit")


def show_weather(latlon, desc):
    """Fetch and display weather for location"""
    if not latlon:
        return
    
    print("\nGetting weather for {}...".format(desc))
    
    gridpoint, wfo = get_gridpoint(latlon)
    if not gridpoint or not wfo:
        if is_internet_available():
            print("Error: Could not get weather data.")
        else:
            print("Internet appears to be unavailable.")
            print("Try again later.")
        return
    
    headlines = get_headlines(wfo)
    if not headlines:
        print("No headlines available.")
        return
    
    print("-" * 40)
    for hl in headlines[:3]:
        print("\n[{}] {}".format(hl['time'], hl['title']))
        print(hl['content'][:200])
    print("-" * 40)


def main():
    """Main program loop"""
    # Ensure stdin is opened from terminal
    try:
        sys.stdin = open('/dev/tty', 'r')
    except (OSError, IOError):
        pass
    
    # Try to read callsign from BPQ32 (if piped via S flag)
    my_callsign = None
    my_grid = None
    if not sys.stdin.isatty():
        try:
            line = sys.stdin.readline().strip().upper()
            if line:
                my_callsign = line.split('-')[0] if line else None
                if my_callsign:
                    my_grid = lookup_callsign(my_callsign)
                try:
                    sys.stdin = open('/dev/tty', 'r')
                except (OSError, IOError):
                    pass
        except (EOFError, KeyboardInterrupt):
            pass
    
    # Check for updates
    check_for_app_update(VERSION, APP_NAME)
    
    # Print header
    print_header()
    
    # Get local gridsquare
    local_grid = get_bpq_locator()
    if not local_grid and my_grid:
        local_grid = my_grid
    if not local_grid:
        local_grid = "FN43hp"
    
    local_latlon = grid_to_latlon(local_grid)
    
    # Main loop
    while True:
        print_menu()
        
        try:
            choice = input(":> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break
        
        if choice == 'Q':
            print("\nExiting...")
            break
        
        elif choice == '1':
            # Local weather
            if local_latlon:
                show_weather(local_latlon, "Local ({})".format(local_grid))
            else:
                print("Could not determine local location.")
        
        elif choice == '2':
            # Weather for location
            result = prompt_location("Enter location for weather:")
            if result:
                latlon, desc = result
                show_weather(latlon, desc)
        
        elif choice == '3':
            # Weather for callsign
            print("")
            try:
                call = input("Enter callsign: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                continue
            
            if call:
                grid = lookup_callsign(call)
                if grid and is_gridsquare_format(grid):
                    latlon = grid_to_latlon(grid)
                    if latlon:
                        show_weather(latlon, "{} ({})".format(call, grid))
                    else:
                        print("Could not convert grid to coordinates.")
                else:
                    print("Callsign not found or no grid.")
        
        else:
            print("\nInvalid choice.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print("\nError: {}".format(str(e)))
        if not is_internet_available():
            print("Internet may be unavailable.")
