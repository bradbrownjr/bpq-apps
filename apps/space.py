#!/usr/bin/env python3
"""
Space Weather Reports for Packet Radio
--------------------------------------
Get information about solar storms, geomagnetic storms, 
and more right from NOAA. Supports offline operation with cached data.

This script pulls data from https://services.swpc.noaa.gov/text/.

Author: Brad Brown KC1JMH
Version: 1.5
Date: January 2026
"""

import requests
import sys
import os
import json
import time
import socket

VERSION = "1.5"
APP_NAME = "space.py"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'space_cache.json')

# NOAA SWPC data sources
SPACE_URLS = {
    '1': {
        'name': 'Geophysical Alert Message',
        'url': 'https://services.swpc.noaa.gov/text/wwv.txt'
    },
    '2': {
        'name': 'Advisory Outlook',
        'url': 'https://services.swpc.noaa.gov/text/advisory-outlook.txt'
    },
    '3': {
        'name': 'Forecast Discussion',
        'url': 'https://services.swpc.noaa.gov/text/discussion.txt'
    },
    '4': {
        'name': 'Weekly Highlights and Forecasts',
        'url': 'https://services.swpc.noaa.gov/text/weekly.txt'
    },
    '5': {
        'name': '3-Day Forecast',
        'url': 'https://services.swpc.noaa.gov/text/3-day-forecast.txt'
    },
    '6': {
        'name': '3-Day Geomagnetic Forecast',
        'url': 'https://services.swpc.noaa.gov/text/3-day-geomag-forecast.txt'
    },
    '7': {
        'name': '3-day Space Weather Predictions',
        'url': 'https://services.swpc.noaa.gov/text/3-day-solar-geomag-predictions.txt'
    }
}


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
                    
                    # Ensure file is executable
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
    except Exception:
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


def is_internet_available():
    """Quick check if internet is available"""
    try:
        socket.create_connection(('8.8.8.8', 53), timeout=2)
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def format_cache_timestamp(timestamp):
    """Format cache timestamp for display with local timezone"""
    try:
        dt = time.localtime(timestamp)
        tz = time.strftime('%Z', dt)
        return time.strftime('%m/%d/%Y at %H:%M', dt) + ' ' + tz
    except Exception:
        return 'Unknown'


def load_cache():
    """Load cached space weather data from disk"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def save_cache(data):
    """Save space weather data to cache file"""
    try:
        data['cache_timestamp'] = time.time()
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print("Error saving cache: {}".format(e))
        return False


def fetch_all_space_data():
    """Fetch all space weather reports and return as dict"""
    data = {'reports': {}}
    
    for key, info in SPACE_URLS.items():
        try:
            response = requests.get(info['url'], timeout=10)
            data['reports'][key] = {
                'name': info['name'],
                'content': response.text,
                'fetched': time.time()
            }
        except Exception as e:
            print("Warning: Failed to fetch {}: {}".format(info['name'], e))
    
    return data


def fetch_single_report(key):
    """Fetch a single report from NOAA"""
    if key not in SPACE_URLS:
        return None
    
    try:
        response = requests.get(SPACE_URLS[key]['url'], timeout=10)
        return response.text
    except Exception:
        return None


def display_report(content, name=None, from_cache=False, cache_timestamp=None):
    """Display a space weather report"""
    if from_cache:
        print("\n** OFFLINE: Internet unavailable **")
        if cache_timestamp:
            print("Cached: {}".format(format_cache_timestamp(cache_timestamp)))
            age_hours = (time.time() - cache_timestamp) / 3600
            if age_hours > 24:
                print("WARNING: Data over 24 hours old may be")
                print("         inaccurate.")
        print("-" * 40)
    
    if name:
        print("\n{}".format(name))
        print("=" * 40)
    
    print("\n{}\n".format(content))


def update_cache():
    """Fetch all reports and update cache (for cron job)"""
    try:
        print("Fetching space weather reports...")
        data = fetch_all_space_data()
        
        if data['reports']:
            if save_cache(data):
                print("Cache updated with {} reports.".format(len(data['reports'])))
                return True
        else:
            print("No reports were fetched.")
            return False
    except Exception as e:
        print("Error updating cache: {}".format(e))
        return False


def show_help():
    """Display help message"""
    print("NAME")
    print("       space.py - NOAA space weather reports")
    print("")
    print("SYNOPSIS")
    print("       space.py [OPTIONS]")
    print("")
    print("VERSION")
    print("       {}".format(VERSION))
    print("")
    print("DESCRIPTION")
    print("       Get information about solar storms, geomagnetic")
    print("       storms, and more from NOAA Space Weather")
    print("       Prediction Center. Supports offline operation")
    print("       using cached data.")
    print("")
    print("OPTIONS")
    print("   -c, --update-cache")
    print("          Fetch all reports and update local cache.")
    print("          Use with cron for offline support.")
    print("")
    print("   -h, --help, /?")
    print("          Show this help message.")
    print("")
    print("EXAMPLES")
    print("       space.py")
    print("              Interactive space weather menu.")
    print("")
    print("       space.py --update-cache")
    print("              Update cache for offline use.")
    print("")
    print("CRON SETUP")
    print("       0 */4 * * * /usr/bin/python3 /path/to/space.py -c")


def show_menu():
    """Display main menu"""
    menu = r"""
 ___ _ __   __ _  ___ ___ 
/ __| '_ \ / _` |/ __/ _ \
\__ \ |_) | (_| | (_|  __/
|___/ .__/ \__,_|\___\___|
    |_|                   
SPACE v{} - Space Weather Reports
----------------------------------------
1) Geophysical Alert Message
2) Advisory Outlook
3) Forecast Discussion
4) Weekly Highlights and Forecasts
5) 3-Day Forecast
6) 3-Day Geomagnetic Forecast
7) 3-day Space Weather Predictions
----------------------------------------
""".format(VERSION)
    print(menu)


def show_about():
    """Display about information"""
    about = """
Get information about solar storms,
geomagnetic storms, and more right 
from NOAA.

This is a Python3 script which pulls data from
https://services.swpc.noaa.gov/text/.

Script developed by Brad Brown KC1JMH
"""
    print(about)


def main():
    """Main entry point"""
    # Handle command-line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ['-h', '--help', '/?']:
            show_help()
            sys.exit(0)
        elif arg in ['-c', '--update-cache']:
            if update_cache():
                sys.exit(0)
            else:
                sys.exit(1)
    
    # Check for app updates
    check_for_app_update(VERSION, APP_NAME)
    
    # Load cache for offline fallback
    cache = load_cache()
    
    show_menu()
    
    while True:
        selected = str(input("Menu: Q)uit R)elist A)bout [1-7] :> ")).strip()
        
        if selected in ['1', '2', '3', '4', '5', '6', '7']:
            # Try to fetch fresh data
            content = fetch_single_report(selected)
            
            if content:
                # Update cache with this report
                if cache is None:
                    cache = {'reports': {}, 'cache_timestamp': time.time()}
                cache['reports'][selected] = {
                    'name': SPACE_URLS[selected]['name'],
                    'content': content,
                    'fetched': time.time()
                }
                cache['cache_timestamp'] = time.time()
                save_cache(cache)
                
                display_report(content, SPACE_URLS[selected]['name'])
            else:
                # Fetch failed - try cache
                if cache and selected in cache.get('reports', {}):
                    report = cache['reports'][selected]
                    display_report(
                        report['content'],
                        report['name'],
                        from_cache=True,
                        cache_timestamp=report.get('fetched', cache.get('cache_timestamp'))
                    )
                else:
                    if is_internet_available():
                        print("\nError fetching report.")
                        print("Please try again later.")
                    else:
                        print("\nInternet appears to be unavailable.")
                        if cache is None:
                            print("No cached data available.")
                            print("")
                            print("Run 'space.py --update-cache' when")
                            print("online to enable offline support.")
                        else:
                            print("This report is not in the cache.")
        
        elif selected.lower() == 'a':
            show_about()
        elif selected.lower() == 'r':
            show_menu()
        elif selected.lower() == 'q':
            print("\nExiting...\n")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        error_str = str(e)
        if 'timeout' in error_str.lower() or 'connection' in error_str.lower() or 'urlopen' in error_str.lower():
            if is_internet_available():
                print("\nConnection Error: {}".format(error_str))
            else:
                print("\nInternet appears to be unavailable.")
                print("Try again later or check your connection.")
        else:
            print("\nError: {}".format(error_str))
