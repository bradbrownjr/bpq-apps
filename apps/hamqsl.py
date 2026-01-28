#!/usr/bin/env python3
"""
Ham QSL Solar Data for Packet Radio
-----------------------------------
Retrieves solar data from hamqsl.com for propagation prediction.
Supports offline operation with cached data.

Author: Brad Brown KC1JMH
Version: 1.2
Date: January 2026
"""

import requests
import xml.etree.ElementTree as ET
import sys
import os
import json
import time
import socket

VERSION = "1.2"
APP_NAME = "hamqsl.py"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hamqsl_cache.json')


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
    """Load cached solar data from disk"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def save_cache(data):
    """Save solar data to cache file"""
    try:
        data['cache_timestamp'] = time.time()
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print("Error saving cache: {}".format(e))
        return False


def fetch_solar_data():
    """Fetch solar data from hamqsl.com and return parsed dict"""
    url = "https://www.hamqsl.com/solarxml.php?nwra=north&muf=grnlnd"
    webxml = (requests.get(url, timeout=10)).content
    root = ET.fromstring(webxml)
    
    data = {}
    
    for solardata in root.findall('solardata'):
        data['source'] = solardata.find('source').attrib['url']
        data['updated'] = solardata.find('updated').text
        
        data['solarflux'] = solardata.find('solarflux').text
        data['sunspots'] = solardata.find('sunspots').text
        data['aindex'] = solardata.find('aindex').text
        data['kindex'] = solardata.find('kindex').text
        data['kindexnt'] = solardata.find('kindexnt').text
        data['xray'] = solardata.find('xray').text
        data['heliumline'] = solardata.find('heliumline').text
        data['protonflux'] = solardata.find('protonflux').text
        data['electronflux'] = solardata.find('electonflux').text  # misspelled in XML source
        data['aurora'] = solardata.find('aurora').text
        data['normalization'] = solardata.find('normalization').text
        data['solarwind'] = solardata.find('solarwind').text
        data['magneticfield'] = solardata.find('magneticfield').text
        
        data['b8040d'] = solardata.findall(".//band[@name='80m-40m'][@time='day']")[0].text
        data['b3020d'] = solardata.findall(".//band[@name='30m-20m'][@time='day']")[0].text
        data['b1715d'] = solardata.findall(".//band[@name='17m-15m'][@time='day']")[0].text
        data['b1210d'] = solardata.findall(".//band[@name='12m-10m'][@time='day']")[0].text
        
        data['b8040n'] = solardata.findall(".//band[@name='80m-40m'][@time='night']")[0].text
        data['b3020n'] = solardata.findall(".//band[@name='30m-20m'][@time='night']")[0].text
        data['b1715n'] = solardata.findall(".//band[@name='17m-15m'][@time='night']")[0].text
        data['b1210n'] = solardata.findall(".//band[@name='12m-10m'][@time='night']")[0].text
        
        data['auroralat'] = solardata.find('latdegree').text
        data['esaura'] = solardata.findall(".//phenomenon[@name='vhf-aurora'][@location='northern_hemi']")[0].text
        data['e6meseu'] = solardata.findall(".//phenomenon[@name='E-Skip'][@location='europe_6m']")[0].text
        data['e4meseu'] = solardata.findall(".//phenomenon[@name='E-Skip'][@location='europe_4m']")[0].text
        data['e2meseu'] = solardata.findall(".//phenomenon[@name='E-Skip'][@location='europe']")[0].text
        data['e2mesna'] = solardata.findall(".//phenomenon[@name='E-Skip'][@location='north_america']")[0].text
        
        data['geomagfield'] = solardata.find('geomagfield').text
        data['snr'] = solardata.find('signalnoise').text
        data['muf'] = solardata.find('muf').text
        data['muffactor'] = solardata.find('muffactor').text
        data['fof2'] = solardata.find('fof2').text
    
    return data


def display_solar_data(data, from_cache=False, cache_timestamp=None):
    """Display solar data in formatted output"""
    lr = "-" * 40
    
    if from_cache:
        print("** OFFLINE: Internet unavailable **")
        if cache_timestamp:
            print("Cached: {}".format(format_cache_timestamp(cache_timestamp)))
            age_hours = (time.time() - cache_timestamp) / 3600
            if age_hours > 24:
                print("WARNING: Data over 24 hours old may be")
                print("         inaccurate.")
        print(lr)
    
    print('From: ', data['source'])
    print('Updated: ', data['updated'])
    
    print(lr)
    print("            Solar-Terrestrial Data")
    print('Solar Flux: ', data['solarflux'], end="\t")
    print('Sunspots: ', data['sunspots'])
    
    if data['kindexnt'] != "No Report":
        knt = "nt"
    else:
        knt = ""
    print('A-Index:', data['aindex'], end="\t\t")
    print('K-Index:', data['kindex'], '/', data['kindexnt'], knt)
    
    print('X-Ray:', data['xray'], end="\t\t")
    print('Helium:', data['heliumline'])
    
    print('Proton Flux: ', data['protonflux'], end="\t")
    print('Electron Flux: ', data['electronflux'])
    
    print('Solar Wind: ', data['solarwind'], end="\t")
    print('Aurora: ', data['aurora'], '/', data['normalization'])
    
    print('Magnetic Field: ', data['magneticfield'])
    
    print(lr)
    print("    HF Conditions           VHF Conditions")
    print("Band\t Day\tNight")
    print('80m-40m\t', data['b8040d'], '\t', data['b8040n'], '\t6m ESkip EU: ', data['e6meseu'])
    print('30m-20m\t', data['b3020d'], '\t', data['b3020n'], '\t4m ESkip EU: ', data['e4meseu'])
    print('17m-15m\t', data['b1715d'], '\t', data['b1715n'], '\t2m ESkip EU: ', data['e2meseu'])
    print('12m-10m\t', data['b1210d'], '\t', data['b1210n'], '\t2m ESkip NA: ', data['e2mesna'])
    print('Auorora Latitude: ', data['auroralat'], 'Aurora Skip: ', data['esaura'])
    
    print(lr)
    print('Geomagnetic Field: ', data['geomagfield'], end="\t")
    print('SNR: ', data['snr'])
    
    print('Max Usable Freq: ', data['muf'], end="\t\t")
    print('MUF Factor: ', data['muffactor'])
    print('Crit foF2 Freq: ', data['fof2'])
    
    print(lr)


def update_cache():
    """Fetch fresh data and update cache (for cron job)"""
    try:
        data = fetch_solar_data()
        if save_cache(data):
            print("Cache updated successfully.")
            return True
        return False
    except Exception as e:
        print("Error updating cache: {}".format(e))
        return False


def show_help():
    """Display help message"""
    print("NAME")
    print("       hamqsl.py - HF propagation data from hamqsl.com")
    print("")
    print("SYNOPSIS")
    print("       hamqsl.py [OPTIONS]")
    print("")
    print("VERSION")
    print("       {}".format(VERSION))
    print("")
    print("DESCRIPTION")
    print("       Retrieves and displays solar data and HF band")
    print("       conditions from hamqsl.com. Supports offline")
    print("       operation using cached data.")
    print("")
    print("OPTIONS")
    print("   -c, --update-cache")
    print("          Fetch fresh data and update local cache.")
    print("          Use with cron for offline support.")
    print("")
    print("   -h, --help, /?")
    print("          Show this help message.")
    print("")
    print("EXAMPLES")
    print("       hamqsl.py")
    print("              Display current solar data.")
    print("")
    print("       hamqsl.py --update-cache")
    print("              Update cache for offline use.")
    print("")
    print("CRON SETUP")
    print("       0 */4 * * * /usr/bin/python3 /path/to/hamqsl.py -c")


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
    
    # Print header with logo
    logo = r"""
 _                               _ 
| |__   __ _ _ __ ___   __ _ ___| |
| '_ \ / _` | '_ ` _ \ / _` / __| |
| | | | (_| | | | | | | (_| \__ \ |
|_| |_|\__,_|_| |_| |_|\__, |___/_|
                          |_|      
"""
    print(logo)
    print("HAMQSL - Solar and Band Conditions")
    print("-" * 40)
    
    try:
        # Try to fetch fresh data
        data = fetch_solar_data()
        # Save to cache on successful fetch
        save_cache(data)
        display_solar_data(data)
        
    except Exception as e:
        # Fetch failed - try cache
        error_str = str(e)
        cache = load_cache()
        
        if cache:
            # Use cached data
            display_solar_data(cache, from_cache=True, 
                             cache_timestamp=cache.get('cache_timestamp'))
        else:
            # No cache available
            if is_internet_available():
                print("\nError: {}".format(error_str))
                print("Please report this issue if it persists.")
            else:
                print("\nInternet appears to be unavailable.")
                print("No cached data available.")
                print("")
                print("Run 'hamqsl.py --update-cache' when online")
                print("to enable offline support.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
