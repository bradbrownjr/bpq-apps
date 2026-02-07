#!/usr/bin/env python3
"""
PREDICT - HF Propagation Estimator for Packet Radio BBS
--------------------------------------------------------
Estimates best HF bands and times for contacts between locations.

Uses simplified ionospheric model with resilient solar data strategy:
- Fetches live data from hamqsl.com (3-sec timeout)
- Falls back to cached data when offline
- Prompts user for solar data if cache is stale
- Uses conservative defaults as last resort

Accuracy: ~70-80% (simplified model, not full VOACAP)
For precise predictions, use voacap.com

Supports location input as:
- Maidenhead gridsquare (FN43hp)
- Decimal GPS (43.65, -70.25)
- DMS coordinates (43d39m32sN 70d15m24sW)
- US state name or abbreviation (Maine, ME)
- Country name (Germany, Japan)
- Callsign lookup via QRZ/HamDB

Author: Brad Brown KC1JMH
Version: 1.16
Date: January 2026
"""

from __future__ import print_function
import sys
import os

# Version check for Python 3.5+
VERSION = "1.16"

if sys.version_info < (3, 5):
    print("Error: Python 3.5 or higher required.")
    sys.exit(1)

# Add predict module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Note: Modules imported after update check, near main()

APP_NAME = "predict.py"

# Display width
def get_line_width():
    """Get terminal width from COLUMNS env var, default to 80"""
    try:
        if 'COLUMNS' in os.environ:
            width = int(os.environ['COLUMNS'])
            if width > 0:
                return width
    except (ValueError, KeyError, TypeError):
        pass
    return 80  # Default width for packet radio terminals

LINE_WIDTH = get_line_width()


def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub."""
    try:
        import urllib.request
        import re
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
        
        # Check for missing or outdated predict module files and download them
        script_dir = os.path.dirname(os.path.abspath(__file__))
        predict_dir = os.path.join(script_dir, 'predict')
        module_files = ['__init__.py', 'geo.py', 'solar.py', 'ionosphere.py', 'regions.json']
        
        files_to_download = []
        for filename in module_files:
            file_path = os.path.join(predict_dir, filename)
            if not os.path.exists(file_path):
                # Missing file
                files_to_download.append(filename)
            elif filename.endswith('.py'):
                # Check if module file has a newer version on GitHub
                try:
                    file_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict/{}".format(filename)
                    with urllib.request.urlopen(file_url, timeout=2) as response:
                        remote_content = response.read().decode('utf-8')
                    
                    # Extract version from remote file
                    remote_version = None
                    for line in remote_content.split('\n'):
                        if 'Version:' in line:
                            remote_version = line.split('Version:')[1].strip()
                            break
                    
                    # Extract version from local file
                    local_version = None
                    with open(file_path, 'r') as f:
                        for line in f:
                            if 'Version:' in line:
                                local_version = line.split('Version:')[1].strip()
                                break
                    
                    # Compare versions
                    if remote_version and local_version and compare_versions(remote_version, local_version) > 0:
                        files_to_download.append(filename)
                except:
                    # Silently skip version check on error
                    pass
        
        if files_to_download:
            try:
                # Create predict directory if it doesn't exist
                if not os.path.exists(predict_dir):
                    os.makedirs(predict_dir)
                
                for filename in files_to_download:
                    file_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict/{}".format(filename)
                    with urllib.request.urlopen(file_url, timeout=3) as response:
                        file_content = response.read()
                    
                    file_path = os.path.join(predict_dir, filename)
                    with open(file_path, 'wb') as f:
                        f.write(file_content)
            except:
                # Silently ignore if module file download fails
                pass
    except Exception:
        pass


def compare_versions(version1, version2):
    """Compare two version strings."""
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


# ============= Callsign Cache Functions =============

# Cache settings
CALLSIGN_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "callsign_cache.json")
CALLSIGN_CACHE_TTL = 30 * 24 * 3600  # 30 days in seconds


def load_callsign_cache():
    """Load callsign cache from disk."""
    try:
        import json
        with open(CALLSIGN_CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_callsign_cache(cache):
    """Save callsign cache to disk."""
    try:
        import json
        import time
        # Clean expired entries before saving
        current_time = time.time()
        cleaned = {k: v for k, v in cache.items() 
                   if current_time - v.get('timestamp', 0) < CALLSIGN_CACHE_TTL}
        with open(CALLSIGN_CACHE_FILE, 'w') as f:
            json.dump(cleaned, f, indent=2)
    except Exception:
        pass


def get_cached_callsign(callsign):
    """Get callsign grid from cache if not expired."""
    import time
    cache = load_callsign_cache()
    entry = cache.get(callsign.upper())
    if entry:
        timestamp = entry.get('timestamp', 0)
        if time.time() - timestamp < CALLSIGN_CACHE_TTL:
            return entry.get('grid')
    return None


def cache_callsign(callsign, grid):
    """Cache a callsign->grid lookup."""
    import time
    cache = load_callsign_cache()
    cache[callsign.upper()] = {
        'grid': grid,
        'timestamp': time.time()
    }
    save_callsign_cache(cache)


# ============= End Callsign Cache Functions =============


def get_bpq_locator():
    """
    Read LOCATOR from BPQ32 config file.
    
    Returns:
        Gridsquare string or None
    """
    try:
        pwd = os.getcwd()
        config_path = os.path.join(pwd, "linbpq", "bpq32.cfg")
        with open(config_path, "r") as f:
            for line in f:
                if "LOCATOR" in line.upper():
                    parts = line.split("=")
                    if len(parts) >= 2:
                        grid = parts[1].strip()
                        if geo.validate_grid(grid):
                            return grid.upper()
    except (IOError, OSError):
        pass
    return None


def lookup_callsign(callsign):
    """
    Look up callsign gridsquare via HamDB/QRZ APIs.
    Uses 30-day cache for offline support.
    
    Args:
        callsign: Amateur callsign
        
    Returns:
        Gridsquare string or None
    """
    # Check cache first
    cached_grid = get_cached_callsign(callsign)
    if cached_grid:
        return cached_grid
    
    # Try online lookup
    try:
        import urllib.request
        import json
        
        # Try HamDB first (free, no API key)
        url = "https://api.hamdb.org/v1/{}/json/predict".format(callsign.upper())
        req = urllib.request.Request(url, headers={'User-Agent': 'PREDICT-BPQ/1.0'})
        
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        hamdb = data.get('hamdb', {}).get('callsign', {})
        grid = hamdb.get('grid', '')
        
        if grid and geo.validate_grid(grid):
            grid = grid.upper()
            # Cache the result
            cache_callsign(callsign, grid)
            return grid
    except Exception:
        pass
    
    return None


def print_header():
    """Print app header."""
    print()
    print(r"                    _ _      _   ")
    print(r" _ __  _ __ ___  __| (_) ___| |_ ")
    print(r"| '_ \| '__/ _ \/ _` | |/ __| __|")
    print(r"| |_) | | |  __/ (_| | | (__| |_ ")
    print(r"| .__/|_|  \___|\_|_|_|\___|\___|")
    print(r"|_|                              ")
    print()
    print("PREDICT v{} - HF Propagation Estimator".format(VERSION))
    print()


def print_menu():
    """Print main menu."""
    print("\nPrediction Options:")
    print("1) From me to another ham (by callsign)")
    print("2) From me to a place")
    print("3) Between two places")
    print("\nA) About  Q) Quit")


def prompt_location(prompt_text, allow_callsign=False):
    """
    Prompt user for location input.
    
    Args:
        prompt_text: Prompt to display
        allow_callsign: If True, try callsign lookup
        
    Returns:
        Tuple (lat, lon, description) or None if cancelled
    """
    print("")
    print(prompt_text)
    if allow_callsign:
        print("  Enter: gridsquare, GPS coords, state, country")
        print("         or callsign for automatic lookup")
    else:
        print("  Enter: gridsquare, GPS coords, state, or country")
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
        
        # Try callsign lookup first if allowed
        if allow_callsign and is_callsign_format(response):
            print("Looking up {}...".format(response.upper()))
            grid = lookup_callsign(response)
            if grid:
                coords = geo.grid_to_latlon(grid)
                if coords:
                    print("Found: {} is in {}".format(response.upper(), grid))
                    return (coords[0], coords[1], "{} ({})".format(response.upper(), grid))
            print("Callsign not found or no grid. Enter location manually.")
            continue
        
        # Try parsing as location
        lat, lon, desc = geo.parse_location(response)
        if lat is not None:
            return (lat, lon, desc)
        
        print("Could not parse location. Try:")
        print("  - Gridsquare: FN43hp")
        print("  - GPS: 43.65, -70.25")
        print("  - State: Maine or ME")
        print("  - Country: Germany")


def is_callsign_format(text):
    """Check if text looks like a callsign."""
    import re
    # Basic callsign pattern: 1-2 letters, digit, 1-3 letters, optional SSID
    pattern = r'^[A-Za-z]{1,2}\d[A-Za-z]{1,3}(-\d{1,2})?$'
    return bool(re.match(pattern, text.strip()))


def get_my_location(cached_location=None):
    """
    Get user's location (from callsign, BPQ config, or prompt).
    
    Args:
        cached_location: Pre-looked-up gridsquare from user's callsign (or None)
    
    Returns:
        Tuple (lat, lon, description) or None if cancelled
    """
    # Try cached location from BPQ callsign first
    if cached_location:
        coords = geo.grid_to_latlon(cached_location)
        if coords:
            print("\nYour location: {}".format(cached_location))
            try:
                confirm = input("Use this location? (Y/n) :> ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            
            if confirm.upper() != 'N':
                return (coords[0], coords[1], cached_location)
    
    # Try BPQ config
    bpq_grid = get_bpq_locator()
    
    if bpq_grid:
        coords = geo.grid_to_latlon(bpq_grid)
        if coords:
            print("\nYour location from BPQ config: {}".format(bpq_grid))
            try:
                confirm = input("Use this location? (Y/n) :> ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            
            if confirm.upper() != 'N':
                return (coords[0], coords[1], bpq_grid)
    
    return prompt_location("Enter YOUR location:", allow_callsign=True)


def run_prediction(from_loc, to_loc, solar_data, solar_status, solar_warning):
    """
    Run prediction and display results.
    
    Args:
        from_loc: Tuple (lat, lon, description) for transmitter
        to_loc: Tuple (lat, lon, description) for receiver
        solar_data: Dict with ssn, sfi, kindex
        solar_status: Status message for display
        solar_warning: Warning message or None
    """
    from_lat, from_lon, from_desc = from_loc
    to_lat, to_lon, to_desc = to_loc
    
    # Calculate path geometry
    distance = geo.great_circle_distance(from_lat, from_lon, to_lat, to_lon)
    bearing_deg = geo.bearing(from_lat, from_lon, to_lat, to_lon)
    mid_lat, mid_lon = geo.midpoint(from_lat, from_lon, to_lat, to_lon)
    
    # Get solar parameters
    ssn = solar_data.get('ssn', 100)
    sfi = solar_data.get('sfi', 130)
    kindex = solar_data.get('kindex', 3)
    aindex = solar_data.get('aindex', 10)
    predictions = ionosphere.predict_bands(distance, mid_lat, ssn, kindex)
    
    # Display results
    print("")
    print("-" * 40)
    print("HF Propagation Estimate")
    print("-" * 40)
    print("From: {}".format(from_desc))
    print("To:   {}".format(to_desc))
    print("")
    print("Distance: {}    Bearing: {}".format(
        geo.format_distance(distance),
        geo.format_bearing(bearing_deg)
    ))
    print(solar_status)
    
    # Print prediction table with solar context
    print(ionosphere.format_prediction_table_with_context(
        predictions, distance, bearing_deg, ssn, sfi, kindex, aindex, solar_status))
    
    # Print recommendation
    print(ionosphere.get_recommendation(predictions))
    
    # Print accuracy note
    print("")
    print("-" * 40)
    print("NOTE: Simplified model (~70-80% accuracy).")
    print("For precise predictions: voacap.com")

    print("-" * 40)


def show_about():
    """Display about information."""
    print("")
    print("-" * 40)
    print("About PREDICT v{}".format(VERSION))
    print("-" * 40)
    print("")
    print("PREDICT estimates HF propagation conditions between")
    print("two locations using a simplified ionospheric model.")
    print("")
    print("HOW IT WORKS:")
    print("  - Fetches solar data (SSN, SFI, K-index) from")
    print("    hamqsl.com with offline fallback to cached data")
    print("  - Calculates path distance and geometry")
    print("  - Estimates MUF using ITU-R correlations")
    print("  - Predicts reliability for each amateur band")
    print("")
    print("ACCURACY:")
    print("  This is NOT full VOACAP. The simplified model")
    print("  provides ~70-80% accuracy vs VOACAP's ~90%.")
    print("  Suitable for 'which band should I try?' guidance.")
    print("")
    print("LIMITATIONS:")
    print("  - No terrain or antenna modeling")
    print("  - No sporadic-E or auroral predictions")
    print("  - Simplified F2 layer model only")
    print("  - State/country locations use centroids")
    print("")
    print("For precise circuit planning, use voacap.com")
    print("or install pythonprop/voacapl.")
    print("")
    print("Author: KC1JMH")
    print("-" * 40)


def main():
    """Main program loop."""
    # Import modules (may be old version)
    from predict import geo, solar, ionosphere
    
    # Try to read callsign - CLI arg first (apps.py), env var, then stdin (BPQ direct)
    my_callsign = None
    my_location = None
    
    # Check --callsign CLI argument (from apps.py launcher)
    arg_call = ""
    for i in range(len(sys.argv) - 1):
        if sys.argv[i] == "--callsign":
            arg_call = sys.argv[i + 1].strip().upper()
            break
    
    if arg_call:
        my_callsign = arg_call.split('-')[0] if arg_call else None
        if my_callsign:
            my_location = lookup_callsign(my_callsign)
    else:
        env_call = os.environ.get("BPQ_CALLSIGN", "").strip().upper()
        if env_call:
            my_callsign = env_call.split('-')[0] if env_call else None
            if my_callsign:
                my_location = lookup_callsign(my_callsign)
        elif not sys.stdin.isatty():
            try:
                import select
                if select.select([sys.stdin], [], [], 0.5)[0]:
                    line = sys.stdin.readline().strip().upper()
                    if line:
                        my_callsign = line.split('-')[0] if line else None
                # Reopen stdin for interactive use
                try:
                    sys.stdin = open('/dev/tty', 'r')
                except (OSError, IOError):
                    pass
                if my_callsign:
                    my_location = lookup_callsign(my_callsign)
            except (EOFError, KeyboardInterrupt, ImportError):
                try:
                    sys.stdin = open('/dev/tty', 'r')
                except (OSError, IOError):
                    pass
    
    # Check for updates
    check_for_app_update(VERSION, APP_NAME)
    
    # Reload modules in case they were updated
    import importlib
    importlib.reload(geo)
    importlib.reload(solar)
    importlib.reload(ionosphere)
    
    # Print header
    print_header()
    
    # Get solar data once at startup
    print("\nLoading solar data...")
    sys.stdout.flush()
    solar_data, solar_status, solar_warning = solar.get_solar_data(interactive=True)
    print(solar_status)
    sys.stdout.flush()
    
    if solar_warning:
        print(solar_warning)
    
    # Show callsign detection result if available
    if my_callsign:
        print("\nCallsign detected: {}".format(my_callsign))
        if my_location:
            print("Location auto-detected: {}".format(my_location))
        else:
            print("(Location lookup failed - will prompt when needed)")
    
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
            # From me to another ham
            my_loc = get_my_location(cached_location=my_location)
            if not my_loc:
                continue
            
            their_loc = prompt_location(
                "Enter the OTHER station's callsign or location:",
                allow_callsign=True
            )
            if not their_loc:
                continue
            
            run_prediction(my_loc, their_loc, solar_data, solar_status, solar_warning)
        
        elif choice == '2':
            # From me to a place
            my_loc = get_my_location(cached_location=my_location)
            if not my_loc:
                continue
            
            place_loc = prompt_location("Enter the DESTINATION location:")
            if not place_loc:
                continue
            
            run_prediction(my_loc, place_loc, solar_data, solar_status, solar_warning)
        
        elif choice == '3':
            # Between two places
            from_loc = prompt_location("Enter the FIRST location:")
            if not from_loc:
                continue
            
            to_loc = prompt_location("Enter the SECOND location:")
            if not to_loc:
                continue
            
            run_prediction(from_loc, to_loc, solar_data, solar_status, solar_warning)
        
        elif choice == 'A':
            show_about()
        
        else:
            print("\nInvalid choice. Enter 1-3, A, or Q.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print("\nError: {}".format(str(e)))
        print("Please report this issue if it persists.")
