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
Version: 1.3
Date: January 2026
"""

from __future__ import print_function
import sys
import os

# Version check for Python 3.5+
if sys.version_info < (3, 5):
    print("Error: Python 3.5 or higher required.")
    sys.exit(1)

# Add predict module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predict import geo, solar, ionosphere

# App version
VERSION = "1.4"
APP_NAME = "predict.py"

# Display width
def get_line_width():
    """Get terminal width, fallback to 40 for piped input"""
    try:
        return os.get_terminal_size().columns
    except (OSError, ValueError):
        return 40  # Fallback for piped input or non-terminal

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
    
    Args:
        callsign: Amateur callsign
        
    Returns:
        Gridsquare string or None
    """
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
            return grid.upper()
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


def get_my_location():
    """
    Get user's location (from BPQ config or prompt).
    
    Returns:
        Tuple (lat, lon, description) or None if cancelled
    """
    # Try BPQ config first
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
    print("=" * 40)
    print("HF Propagation Estimate")
    print("=" * 40)
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
    print("=" * 40)
    print("About PREDICT v{}".format(VERSION))
    print("=" * 40)
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
    print("=" * 40)


def main():
    """Main program loop."""
    # Check for updates
    check_for_app_update(VERSION, APP_NAME)
    
    # Print header
    print_header()
    
    # Get solar data once at startup
    print("\nLoading solar data...")
    solar_data, solar_status, solar_warning = solar.get_solar_data(interactive=True)
    print(solar_status)
    
    if solar_warning:
        print(solar_warning)
    
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
            my_loc = get_my_location()
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
            my_loc = get_my_location()
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
    main()
