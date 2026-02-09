#!/usr/bin/env python3
"""
Weather Reports for Southern Maine and New Hampshire  
----------------------------------------------------
Local weather reports from National Weather Service Gray Office.

Author: Brad Brown KC1JMH
Version: 1.6
Date: February 2026
"""

import requests
import sys
import os

VERSION = "1.6"
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

def paginate_content(content, title=""):
    """Display content with pagination (20 lines per page)"""
    lines = content.split('\n')
    page_size = 20
    total_pages = (len(lines) + page_size - 1) // page_size
    
    if total_pages <= 1:
        # Content fits on one page
        if title:
            print("\n{}\n".format(title))
        print("{}\n".format(content))
        return
    
    # Paginated display
    current_page = 0
    while True:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(lines))
        page_content = '\n'.join(lines[start_idx:end_idx])
        
        print("\n{}\n".format(page_content))
        print("-" * 40)
        
        # Build prompt based on available actions
        prompt_parts = ["({}/{})".format(current_page + 1, total_pages)]
        prompt_parts.append("[Q)uit M)enu")
        
        if current_page > 0:
            prompt_parts.append("B)ack")
        
        if current_page < total_pages - 1:
            prompt_parts.append("N)ext")
        
        prompt_parts.append("] :>")
        prompt = " ".join(prompt_parts)
        
        selected = str(input(prompt)).strip().lower()
        
        if selected == 'q':
            return 'quit'
        elif selected == 'm':
            return 'menu'
        elif selected == 'b' and current_page > 0:
            current_page -= 1
        elif selected == 'n' and current_page < total_pages - 1:
            current_page += 1
        elif selected == '':
            # Enter key - go to next page
            if current_page < total_pages - 1:
                current_page += 1

def pullthis(url):
        response = requests.get(url)
        data = response.text
        return paginate_content(data)

try:
    print (menu)
    while True:
            selected = str(input("Menu: Q)uit R)elist A)bout [1-5] :> "))
            if "1" in selected:
                    result = pullthis("https://tgftp.nws.noaa.gov/data/raw/aw/awus81.kgyx.rws.gyx.txt")
                    if result == 'quit':
                            raise KeyboardInterrupt()
                    elif result == 'menu':
                            print(menu)
            elif "2" in selected:
                    result = pullthis("https://tgftp.nws.noaa.gov/data/raw/as/asus41.kgyx.rwr.gyx.txt")
                    if result == 'quit':
                            raise KeyboardInterrupt()
                    elif result == 'menu':
                            print(menu)
            elif "3" in selected:
                    result = pullthis("https://tgftp.nws.noaa.gov/data/forecasts/state/nh/nhz010.txt")
                    if result == 'quit':
                            raise KeyboardInterrupt()
                    elif result == 'menu':
                            print(menu)
            elif "4" in selected:
                    result = pullthis("https://tgftp.nws.noaa.gov/data/raw/fp/fpus61.kcar.sft.car.txt")
                    if result == 'quit':
                            raise KeyboardInterrupt()
                    elif result == 'menu':
                            print(menu)
            elif "5" in selected:
                    result = pullthis("https://tgftp.nws.noaa.gov/data/raw/as/asus61.kgyx.rtp.gyx.txt")
                    if result == 'quit':
                            raise KeyboardInterrupt()
                    elif result == 'menu':
                            print(menu)
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
