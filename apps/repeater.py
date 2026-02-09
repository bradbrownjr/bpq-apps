#!/usr/bin/env python3
"""
Repeater Directory for Packet Radio
------------------------------------
Search for amateur radio repeaters using RepeaterBook API.
Search by gridsquare, location, or frequency. Supports offline
operation with cached data.

Data from https://www.repeaterbook.com/

Author: Brad Brown KC1JMH
Version: 1.17
Date: February 2026
"""

import sys
import os
import json
import time
import socket
import math
import re

try:
    import urllib.request
    import urllib.parse
    import urllib.error
except ImportError:
    print("Error: urllib not available")
    sys.exit(1)

VERSION = "1.17"
APP_NAME = "repeater.py"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'repeater_cache.json')
CACHE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'repeater.conf')

# RepeaterBook API base URL
API_BASE = "https://www.repeaterbook.com/api/export.php"
# User-Agent required per RepeaterBook API docs
USER_AGENT = "BPQ-Repeater-Directory/1.2 (https://github.com/bradbrownjr/bpq-apps, kc1jmh@mainehamradio.com)"

LOGO = r"""
                           _            
  ____ ___  ____  ___  ___(_)______ _____
 / ___/ _ \/ __ \/ _ \/ __/ __/ _ \/ ___/
/ /  /  __/ /_/ /  __/ /_/ /_/  __/ /    
\_|  \___/ .___/\___/\__/\__/\___/_/     
        /_/                               
"""


def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import stat
        
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        req = urllib.request.Request(github_url, headers={'User-Agent': 'BPQ-Apps'})
        
        with urllib.request.urlopen(req, timeout=3) as response:
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
                    
                    current_mode = os.stat(script_path).st_mode
                    os.chmod(temp_path, current_mode)
                    os.replace(temp_path, script_path)
                    
                    print("Updated to v{}. Restarting...".format(github_version))
                    print()
                    sys.stdout.flush()
                    restart_args = [script_path] + sys.argv[1:]
                    os.execv(script_path, restart_args)
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


def is_internet_available():
    """Quick check if internet is available"""
    try:
        socket.create_connection(('8.8.8.8', 53), timeout=2)
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def lookup_gridsquare_from_callsign(callsign):
    """Look up gridsquare from callsign using HamDB API"""
    try:
        base_call = callsign.split('-')[0] if callsign else ""
        if not base_call:
            return None
        
        url = "https://api.hamdb.org/v1/{}/json/bpq-apps".format(base_call)
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if data.get('hamdb', {}).get('messages', {}).get('status') == 'OK':
            callsign_data = data.get('hamdb', {}).get('callsign', {})
            grid = callsign_data.get('grid', '')
            if grid and len(grid) >= 4:
                return grid.upper()
        
        return None
    except Exception:
        return None


def load_config():
    """Load app configuration"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(config):
    """Save app configuration"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def get_api_key():
    """Get RepeaterBook API key from config"""
    config = load_config()
    return config.get('repeaterbook_api_key')


def set_api_key(api_key):
    """Save RepeaterBook API key to config"""
    config = load_config()
    config['repeaterbook_api_key'] = api_key
    return save_config(config)


def gridsquare_to_latlon(grid):
    """Convert Maidenhead gridsquare to lat/lon"""
    grid = grid.upper()
    if len(grid) < 4:
        return None, None
    
    try:
        lon = (ord(grid[0]) - ord('A')) * 20 - 180
        lat = (ord(grid[1]) - ord('A')) * 10 - 90
        lon += (ord(grid[2]) - ord('0')) * 2
        lat += (ord(grid[3]) - ord('0'))
        
        if len(grid) >= 6:
            lon += (ord(grid[4]) - ord('A')) * (2.0/24.0)
            lat += (ord(grid[5]) - ord('A')) * (1.0/24.0)
            lon += 1.0/24.0
            lat += 0.5/24.0
        else:
            lon += 1
            lat += 0.5
        
        return lat, lon
    except (IndexError, ValueError):
        return None, None


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in miles"""
    R = 3959.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def format_frequency(freq):
    """Format frequency for display"""
    try:
        f = float(freq)
        if f < 30:
            return "{:.4f}".format(f)
        else:
            return "{:.3f}".format(f)
    except:
        return str(freq)


def load_cache():
    """Load cached repeater data"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_cache(cache_data):
    """Save repeater data to cache"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        return True
    except Exception as e:
        print("Error saving cache: {}".format(e))
        return False


def get_cache_key(state, proximity, lat, lon):
    """Generate cache key for query"""
    return "{}_{}_{}_{:.2f}_{:.2f}".format(state or "NONE", proximity, "search", lat, lon)


def fetch_repeaters(state, proximity, lat, lon):
    """Fetch repeaters from RepeaterBook API"""
    # State names for API
    state_map = {
        'maine': 'Maine', 'new hampshire': 'New%20Hampshire', 'vermont': 'Vermont',
        'massachusetts': 'Massachusetts', 'connecticut': 'Connecticut',
        'rhode island': 'Rhode%20Island', 'nh': 'New%20Hampshire', 'vt': 'Vermont',
        'ma': 'Massachusetts', 'ct': 'Connecticut', 'ri': 'Rhode%20Island', 'me': 'Maine'
    }
    
    if state:
        state_param = state_map.get(state.lower(), state.replace(' ', '%20'))
    else:
        # Default to Maine for gridsquare searches in FN region
        state_param = 'Maine'
    
    url = "{}?country=United%20States&state={}".format(API_BASE, state_param)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if not data:
            return []
        
        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            if 'results' in data:
                return data['results']
            elif 'error' in data:
                raise Exception(data.get('error', 'API error'))
        
        return []
                
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Exception("API authentication error. Check User-Agent.")
        raise Exception("HTTP {} {}".format(e.code, e.reason))
    except Exception as e:
        raise Exception("{}".format(str(e)))


def filter_by_distance(repeaters, center_lat, center_lon, max_distance):
    """Filter repeaters by distance from center point"""
    filtered = []
    for rep in repeaters:
        try:
            lat = float(rep.get('Lat', 0))
            lon = float(rep.get('Long', 0))
            dist = calculate_distance(center_lat, center_lon, lat, lon)
            rep['distance'] = dist
            if dist <= max_distance:
                filtered.append(rep)
        except (ValueError, TypeError):
            continue
    
    filtered.sort(key=lambda x: x.get('distance', 999999))
    return filtered


def format_repeater(rep, index=None, show_distance=True):
    """Format repeater info for display (40-char width)"""
    output = []
    
    # Line 1: Index and frequency with offset
    line1 = ""
    if index is not None:
        line1 = "{}. ".format(index)
    
    freq = format_frequency(rep.get('Frequency', 'N/A'))
    
    # Calculate offset direction from input/output frequencies
    try:
        output_freq = float(rep.get('Frequency', 0))
        input_freq = float(rep.get('Input Freq', 0))
        if output_freq > 0 and input_freq > 0:
            diff = output_freq - input_freq
            input_formatted = format_frequency(rep.get('Input Freq', ''))
            if diff > 0.001:  # Output higher than input
                line1 += "{} - ({})".format(freq, input_formatted)  # Minus offset
            elif diff < -0.001:  # Input higher than output
                line1 += "{} + ({})".format(freq, input_formatted)  # Plus offset
            else:
                line1 += freq  # Simplex
        else:
            line1 += freq
    except (ValueError, TypeError):
        line1 += freq
    
    # Add tone if present
    tone = rep.get('PL', '')
    if tone and tone != 'CSQ':
        line1 += " ({})".format(tone)
    
    output.append(line1)
    
    # Line 2: Modes (check boolean fields from RepeaterBook)
    modes = []
    if rep.get('FM Analog', '').strip().upper() == 'YES':
        modes.append('FM')
    if rep.get('DMR', '').strip().upper() == 'YES':
        modes.append('DMR')
    if rep.get('D-Star', '').strip().upper() == 'YES':
        modes.append('DStar')
    if rep.get('Fusion', '').strip().upper() == 'YES':
        modes.append('YSF')
    if rep.get('NXDN', '').strip().upper() == 'YES':
        modes.append('NXDN')
    if rep.get('P25 Phase I', '').strip().upper() == 'YES':
        modes.append('P25')
    if rep.get('TETRA', '').strip().upper() == 'YES':
        modes.append('TETRA')
    
    if modes:
        output.append(', '.join(modes))
    
    # Line 3: Location
    location = rep.get('Nearest City', '')
    state = rep.get('State', '')
    if location or state:
        loc_line = "{} {}".format(location, state).strip()
        if len(loc_line) > 38:
            loc_line = loc_line[:35] + "..."
        output.append(loc_line)
    
    # Line 4: Callsign (trustee)
    callsign = rep.get('Callsign', '')
    if callsign:
        output.append("Trustee: {}".format(callsign))
    
    # Line 5: Distance
    if show_distance and 'distance' in rep:
        output.append("{:.1f} mi".format(rep['distance']))
    
    return '\n'.join(output)


def display_repeaters(repeaters, page=1, per_page=4):
    """Display paginated repeater list"""
    if not repeaters:
        print("\nNo repeaters found.")
        return False
    
    total = len(repeaters)
    total_pages = (total + per_page - 1) // per_page
    
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    
    print("\n" + "-" * 40)
    print("REPEATERS (Page {}/{})".format(page, total_pages))
    print("-" * 40)
    
    for i in range(start_idx, end_idx):
        if i > start_idx:
            print("-" * 40)
        print(format_repeater(repeaters[i], i + 1))
    
    print("-" * 40)
    print("{} total repeaters".format(total))
    
    return True


def filter_by_band(repeaters, band):
    """Filter repeaters by band"""
    band_filters = {
        '10': (28.0, 29.7),
        '6': (50.0, 54.0),
        '2': (144.0, 148.0),
        '1.25': (219.0, 225.0),
        '70': (420.0, 450.0),
        '33': (902.0, 928.0),
        '23': (1240.0, 1300.0)
    }
    
    if band not in band_filters:
        return repeaters
    
    min_freq, max_freq = band_filters[band]
    filtered = []
    
    for rep in repeaters:
        try:
            freq = float(rep.get('Frequency', 0))
            if min_freq <= freq <= max_freq:
                filtered.append(rep)
        except (ValueError, TypeError):
            continue
    
    return filtered


def filter_by_frequency(repeaters, target_freq, tolerance=0.5):
    """Filter repeaters by frequency with tolerance in MHz"""
    filtered = []
    
    for rep in repeaters:
        try:
            freq = float(rep.get('Frequency', 0))
            if abs(freq - target_freq) <= tolerance:
                filtered.append(rep)
        except (ValueError, TypeError):
            continue
    
    return filtered


def filter_by_mode(repeaters, mode_input):
    """Filter repeaters by mode (comma-delimited: FM,DMR,DStar,etc)"""
    if not mode_input:
        return repeaters
    
    # Parse comma-delimited modes and normalize
    requested_modes = [m.strip().upper() for m in mode_input.split(',')]
    
    # Map field names to mode aliases
    mode_field_map = {
        'FM': 'FM Analog',
        'ANALOG': 'FM Analog',
        'DMR': 'DMR',
        'MOTOTRBO': 'DMR',
        'DSTAR': 'D-Star',
        'D-STAR': 'D-Star',
        'YSF': 'Fusion',
        'FUSION': 'Fusion',
        'C4FM': 'Fusion',
        'NXDN': 'NXDN',
        'P25': 'P25 Phase I',
        'APCO-25': 'P25 Phase I',
        'TETRA': 'TETRA'
    }
    
    # Get field names to check
    fields_to_check = set()
    for mode in requested_modes:
        if mode in mode_field_map:
            fields_to_check.add(mode_field_map[mode])
    
    if not fields_to_check:
        return repeaters
    
    # Filter repeaters that support at least one requested mode
    filtered = []
    for rep in repeaters:
        for field in fields_to_check:
            if rep.get(field, '').strip().upper() == 'YES':
                filtered.append(rep)
                break
    
    return filtered


def get_terminal_width():
    """Get terminal width with fallback"""
    try:
        import shutil
        return shutil.get_terminal_size(fallback=(80, 24))[0]
    except:
        return 80


def wrap_text(text, width=40):
    """Wrap text to specified width"""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_len = len(word)
        if current_length + word_len + len(current_line) <= width:
            current_line.append(word)
            current_length += word_len
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_len
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)


def main_menu(user_callsign=None):
    """Display main menu and handle user interaction"""
    config = load_config()
    
    while True:
        print(LOGO)
        print("\nREPEATER DIRECTORY v{}".format(VERSION))
        print("Data from RepeaterBook.com")
        
        if user_callsign:
            print("User: {}".format(user_callsign))
        
        print("\n" + "-" * 40)
        print("MAIN MENU")
        print("-" * 40)
        print("1) Search by Gridsquare")
        print("2) Search by Callsign")
        print("3) Search by Frequency")
        print("4) Search by State & Proximity")
        
        # Reload config to get latest last_location
        config = load_config()
        if config.get('last_location'):
            print("5) My Location ({})".format(config['last_location'].get('grid', 'saved')))
        
        print("\n6) View Cached Results")
        print("\nA) About  Q) Quit")
        print("-" * 40)
        
        try:
            choice = input("Menu: [1-6 A Q] :> ").strip().upper()
        except EOFError:
            return
        
        if choice == 'Q':
            print("Exiting...")
            return
        elif choice == 'A':
            show_about()
        elif choice == '1':
            search_by_gridsquare()
        elif choice == '2':
            search_by_callsign(user_callsign)
        elif choice == '3':
            search_by_frequency()
        elif choice == '4':
            search_by_state()
        elif choice == '5':
            if config.get('last_location'):
                search_my_location()
        elif choice == '6':
            view_cached_results()


def show_about():
    """Display about information"""
    print("\n" + "-" * 40)
    print("ABOUT REPEATER DIRECTORY")
    print("-" * 40)
    print(wrap_text(
        "Search for amateur radio repeaters using "
        "RepeaterBook.com data. Search by state for "
        "best results. Gridsquare/callsign searches "
        "default to your state. Results cached for "
        "30 days for offline access.", 40
    ))
    print("\n" + wrap_text(
        "Data courtesy of RepeaterBook.com - the "
        "world's largest repeater directory.", 40
    ))
    print("\nAuthor: Brad Brown KC1JMH")
    print("Version: {}".format(VERSION))
    print("-" * 40)
    try:
        resp = input("\n[Q)uit Enter=continue] :> ").strip().upper()
        if resp == "Q":
            print("\nExiting...")
            sys.exit(0)
    except EOFError:
        pass


def search_by_gridsquare():
    """Search repeaters by gridsquare"""
    print("\n" + "-" * 40)
    print("SEARCH BY GRIDSQUARE")
    print("-" * 40)
    
    try:
        grid = input("Gridsquare (e.g., FN43hp): ").strip().upper()
    except EOFError:
        return
    
    if not grid or len(grid) < 4:
        print("Invalid gridsquare format.")
        return
    
    # Validate gridsquare format
    if not re.match(r'^[A-R]{2}[0-9]{2}([A-X]{2})?$', grid):
        print("Invalid gridsquare format.")
        print("Format: AA##aa (e.g., FN43hp)")
        return
    
    lat, lon = gridsquare_to_latlon(grid)
    if lat is None or lon is None:
        print("Invalid gridsquare.")
        return
    
    # Save location for My Location feature
    config = load_config()
    config['last_location'] = {'grid': grid, 'lat': lat, 'lon': lon}
    save_config(config)
    
    try:
        radius = input("Radius in miles [25]: ").strip()
        radius = int(radius) if radius else 25
    except (EOFError, ValueError):
        radius = 25
    
    try:
        band_input = input("Band [10,6,2,1.25,70,33,23] or Enter for all: ").strip()
    except EOFError:
        band_input = ""
    
    try:
        mode_input = input("Mode [FM,DMR,DStar,YSF] or Enter for all: ").strip()
    except EOFError:
        mode_input = ""
    
    print("\nSearching...")
    
    cache = load_cache()
    cache_key = get_cache_key(None, radius, lat, lon)
    
    repeaters = None
    
    if not is_internet_available():
        print("Internet appears to be unavailable.")
        if cache_key in cache:
            print("Using cached data...")
            repeaters = cache[cache_key]['data']
        else:
            print("No cached data available.")
            print("Try again when online.")
            return
    else:
        try:
            repeaters = fetch_repeaters(None, radius, lat, lon)
            repeaters = filter_by_distance(repeaters, lat, lon, radius)
            
            cache[cache_key] = {
                'timestamp': time.time(),
                'data': repeaters,
                'search': {
                    'grid': grid,
                    'radius': radius,
                    'lat': lat,
                    'lon': lon
                }
            }
            save_cache(cache)
        except Exception as e:
            print("Error fetching data: {}".format(str(e)))
            if cache_key in cache:
                print("Using cached data...")
                repeaters = cache[cache_key]['data']
            else:
                return
    
    if band_input:
        repeaters = filter_by_band(repeaters, band_input)
    
    if mode_input:
        repeaters = filter_by_mode(repeaters, mode_input)
    
    if not repeaters:
        print("\nNo repeaters found.")
        return
    
    browse_results(repeaters)


def search_by_callsign(default_callsign=None):
    """Search repeaters by callsign (looks up gridsquare)"""
    print("\n" + "-" * 40)
    print("SEARCH BY CALLSIGN")
    print("-" * 40)
    
    try:
        if default_callsign:
            prompt = "Callsign [{}]: ".format(default_callsign)
            callsign = input(prompt).strip().upper()
            if not callsign:
                callsign = default_callsign
        else:
            callsign = input("Callsign: ").strip().upper()
    except EOFError:
        return
    
    if not callsign:
        print("Callsign required.")
        return
    
    print("\nLooking up gridsquare for {}...".format(callsign))
    
    if not is_internet_available():
        print("Internet appears to be unavailable.")
        print("Callsign lookup requires internet.")
        return
    
    grid = lookup_gridsquare_from_callsign(callsign)
    
    if not grid:
        print("Could not find gridsquare for {}".format(callsign))
        print("Try searching by gridsquare instead.")
        return
    
    print("Found: {}".format(grid))
    
    lat, lon = gridsquare_to_latlon(grid)
    if lat is None or lon is None:
        print("Invalid gridsquare data.")
        return
    
    # Save location
    config = load_config()
    config['last_location'] = {'grid': grid, 'lat': lat, 'lon': lon, 'callsign': callsign}
    save_config(config)
    
    try:
        radius = input("Radius in miles [25]: ").strip()
        radius = int(radius) if radius else 25
    except (EOFError, ValueError):
        radius = 25
    
    try:
        band_input = input("Band [10,6,2,1.25,70,33,23] or Enter for all: ").strip()
    except EOFError:
        band_input = ""
    
    try:
        mode_input = input("Mode [FM,DMR,DStar,YSF] or Enter for all: ").strip()
    except EOFError:
        mode_input = ""
    
    print("\nSearching...")
    
    cache = load_cache()
    cache_key = get_cache_key(None, radius, lat, lon)
    
    repeaters = None
    
    try:
        repeaters = fetch_repeaters(None, radius, lat, lon)
        repeaters = filter_by_distance(repeaters, lat, lon, radius)
        
        cache[cache_key] = {
            'timestamp': time.time(),
            'data': repeaters,
            'search': {
                'callsign': callsign,
                'grid': grid,
                'radius': radius,
                'lat': lat,
                'lon': lon
            }
        }
        save_cache(cache)
    except Exception as e:
        print("Error fetching data: {}".format(str(e)))
        if cache_key in cache:
            print("Using cached data...")
            repeaters = cache[cache_key]['data']
        else:
            return
    
    if band_input:
        repeaters = filter_by_band(repeaters, band_input)
    
    if mode_input:
        repeaters = filter_by_mode(repeaters, mode_input)
    
    if not repeaters:
        print("\nNo repeaters found.")
        return
    
    browse_results(repeaters)


def search_by_frequency():
    """Search repeaters by frequency"""
    print("\n" + "-" * 40)
    print("SEARCH BY FREQUENCY")
    print("-" * 40)
    
    try:
        freq_input = input("Frequency in MHz (e.g., 146.52): ").strip()
    except EOFError:
        return
    
    if not freq_input:
        print("Frequency required.")
        return
    
    try:
        target_freq = float(freq_input)
    except ValueError:
        print("Invalid frequency format.")
        return
    
    try:
        grid = input("Your gridsquare (e.g., FN43hp): ").strip().upper()
    except EOFError:
        return
    
    if not grid or len(grid) < 4:
        print("Invalid gridsquare format.")
        return
    
    lat, lon = gridsquare_to_latlon(grid)
    if lat is None or lon is None:
        print("Invalid gridsquare.")
        return
    
    # Save location
    config = load_config()
    config['last_location'] = {'grid': grid, 'lat': lat, 'lon': lon}
    save_config(config)
    
    try:
        radius = input("Search radius in miles [50]: ").strip()
        radius = int(radius) if radius else 50
    except (EOFError, ValueError):
        radius = 50
    
    print("\nSearching...")
    
    if not is_internet_available():
        print("Internet appears to be unavailable.")
        print("Frequency search requires internet.")
        return
    
    try:
        repeaters = fetch_repeaters(None, radius, lat, lon)
        repeaters = filter_by_distance(repeaters, lat, lon, radius)
        repeaters = filter_by_frequency(repeaters, target_freq, tolerance=0.5)
        
        if not repeaters:
            print("\nNo repeaters found near {:.4f} MHz".format(target_freq))
            return
        
        browse_results(repeaters)
    except Exception as e:
        print("Error fetching data: {}".format(str(e)))


def search_my_location():
    """Quick search using saved location"""
    config = load_config()
    last_loc = config.get('last_location')
    
    if not last_loc:
        print("\nNo saved location found.")
        print("Use another search method first.")
        return
    
    grid = last_loc.get('grid', 'Unknown')
    lat = last_loc.get('lat')
    lon = last_loc.get('lon')
    
    print("\n" + "-" * 40)
    print("MY LOCATION: {}".format(grid))
    print("-" * 40)
    
    try:
        radius = input("Radius in miles [25]: ").strip()
        radius = int(radius) if radius else 25
    except (EOFError, ValueError):
        radius = 25
    
    try:
        band_input = input("Band [10,6,2,1.25,70,33,23] or Enter for all: ").strip()
    except EOFError:
        band_input = ""
    
    try:
        mode_input = input("Mode [FM,DMR,DStar,YSF] or Enter for all: ").strip()
    except EOFError:
        mode_input = ""
    
    print("\nSearching...")
    
    cache = load_cache()
    cache_key = get_cache_key(None, radius, lat, lon)
    
    repeaters = None
    
    if not is_internet_available():
        print("Internet appears to be unavailable.")
        if cache_key in cache:
            print("Using cached data...")
            repeaters = cache[cache_key]['data']
        else:
            print("No cached data available.")
            return
    else:
        try:
            repeaters = fetch_repeaters(None, radius, lat, lon)
            repeaters = filter_by_distance(repeaters, lat, lon, radius)
            
            cache[cache_key] = {
                'timestamp': time.time(),
                'data': repeaters,
                'search': {
                    'grid': grid,
                    'radius': radius,
                    'lat': lat,
                    'lon': lon
                }
            }
            save_cache(cache)
        except Exception as e:
            print("Error fetching data: {}".format(str(e)))
            if cache_key in cache:
                print("Using cached data...")
                repeaters = cache[cache_key]['data']
            else:
                return
    
    if band_input:
        repeaters = filter_by_band(repeaters, band_input)
    
    if mode_input:
        repeaters = filter_by_mode(repeaters, mode_input)
    
    if not repeaters:
        print("\nNo repeaters found.")
        return
    
    browse_results(repeaters)


def search_by_state():
    """Search repeaters by state and city"""
    print("\n" + "-" * 40)
    print("SEARCH BY STATE")
    print("-" * 40)
    
    try:
        state = input("State (e.g., Maine): ").strip()
    except EOFError:
        return
    
    if not state:
        print("State required.")
        return
    
    try:
        city = input("City (optional): ").strip()
    except EOFError:
        city = ""
    
    try:
        radius = input("Radius in miles [25]: ").strip()
        radius = int(radius) if radius else 25
    except (EOFError, ValueError):
        radius = 25
    
    try:
        band_input = input("Band [10,6,2,1.25,70,33,23] or Enter for all: ").strip()
    except EOFError:
        band_input = ""
    
    try:
        mode_input = input("Mode [FM,DMR,DStar,YSF] or Enter for all: ").strip()
    except EOFError:
        mode_input = ""
    
    print("\nSearching...")
    
    if not is_internet_available():
        print("Internet appears to be unavailable.")
        print("Try search by gridsquare with cached data.")
        return
    
    try:
        repeaters = fetch_repeaters(state, radius, 0, 0)
        
        if band_input:
            repeaters = filter_by_band(repeaters, band_input)
        
        if mode_input:
            repeaters = filter_by_mode(repeaters, mode_input)
        
        if not repeaters:
            print("\nNo repeaters found.")
            return
        
        browse_results(repeaters)
    except Exception as e:
        print("Error fetching data: {}".format(str(e)))


def view_cached_results():
    """View previously cached searches"""
    cache = load_cache()
    
    if not cache:
        print("\nNo cached searches found.")
        return
    
    print("\n" + "-" * 40)
    print("CACHED SEARCHES")
    print("-" * 40)
    
    cache_list = []
    for key, data in cache.items():
        if 'search' in data:
            cache_list.append((key, data))
    
    if not cache_list:
        print("No cached searches found.")
        return
    
    for idx, (key, data) in enumerate(cache_list, 1):
        search = data['search']
        age_days = (time.time() - data['timestamp']) / 86400
        print("{}. Grid: {} Radius: {}mi ({:.0f} days old)".format(
            idx, search.get('grid', 'N/A'), search.get('radius', 'N/A'), age_days
        ))
    
    print("-" * 40)
    
    try:
        choice = input("Select [1-{}] or Q: ".format(len(cache_list))).strip()
    except EOFError:
        return
    
    if choice.upper() == 'Q':
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(cache_list):
            key, data = cache_list[idx]
            repeaters = data['data']
            browse_results(repeaters)
    except (ValueError, IndexError):
        print("Invalid selection.")


def browse_results(repeaters):
    """Browse repeater results with pagination"""
    if not repeaters:
        print("\nNo results to display.")
        return
    
    page = 1
    per_page = 4
    total_pages = (len(repeaters) + per_page - 1) // per_page
    
    while True:
        display_repeaters(repeaters, page, per_page)
        
        if total_pages > 1:
            if page < total_pages:
                prompt = "Q)uit M)enu N)ext P)rev Enter=next :> "
            else:
                prompt = "Q)uit M)enu P)rev :> "
        else:
            prompt = "Q)uit M)enu :> "
        
        try:
            choice = input(prompt).strip().upper()
        except EOFError:
            return
        
        if choice == 'Q':
            print("\nExiting...")
            sys.exit(0)
        elif choice == 'M':
            break  # Return to main menu
        elif choice == 'N' and page < total_pages:
            page += 1
        elif choice == 'P' and page > 1:
            page -= 1
        elif choice == '' and page < total_pages:
            # Enter key advances to next page
            page += 1


def main():
    """Main entry point"""
    check_for_app_update(VERSION, APP_NAME)
    
    # Read callsign - CLI arg first (apps.py), env var, then stdin (BPQ direct)
    user_callsign = None
    
    # Check --callsign CLI argument (from apps.py launcher)
    arg_call = ""
    for i in range(len(sys.argv) - 1):
        if sys.argv[i] == "--callsign":
            arg_call = sys.argv[i + 1].strip().upper()
            break
    
    if arg_call and re.match(r'^[A-Z0-9]{3,7}(-\d{1,2})?$', arg_call):
        user_callsign = arg_call
        print("Callsign: {}".format(user_callsign))
    else:
        env_call = os.environ.get("BPQ_CALLSIGN", "").strip()
        if env_call and re.match(r'^[A-Z0-9]{3,7}(-\d{1,2})?$', env_call):
            user_callsign = env_call
            print("Callsign: {}".format(user_callsign))
        else:
            try:
                if not sys.stdin.isatty():
                    first_line = sys.stdin.readline().strip()
                    if first_line and re.match(r'^[A-Z0-9]{3,7}(-\d{1,2})?$', first_line):
                        user_callsign = first_line
                        print("Callsign: {}".format(user_callsign))
            except Exception:
                pass
    
    try:
        main_menu(user_callsign)
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        if is_internet_available():
            print("Error: {}".format(str(e)))
        else:
            print("Internet appears to be unavailable.")
            print("Try again later.")


if __name__ == '__main__':
    main()
