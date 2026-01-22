#!/usr/bin/env python3
"""
Weather for Packet Radio
------------------------
Local and regional weather from National Weather Service API.

Features:
- Two-menu interface: location selection, then detailed reports
- 12 comprehensive weather reports per location
- 7-day forecast, current conditions, fire/heat/cold/flood alerts
- Coastal flood alerts and marine forecasts for coastal areas
- Area Forecast Discussion, probability of precipitation
- UV index, pollen forecast, dust/haboob alerts
- SKYWARN activation status from HWO
- Gridsquare-based location detection from bpq32.cfg
- Callsign-based weather lookup via HamDB
- Multiple location input formats: gridsquare, GPS, callsign
- Graceful offline fallback

Author: Brad Brown KC1JMH
Version: 2.0
Date: January 2026
"""

from __future__ import print_function
import sys
import os
import re
from datetime import datetime

VERSION = "2.0"
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
        # BPQ apps run adjacent to linbpq folder, so ../linbpq/bpq32.cfg
        paths_to_try = [
            "../linbpq/bpq32.cfg",
            os.path.join(os.path.dirname(os.getcwd()), "linbpq", "bpq32.cfg"),
            "/home/pi/linbpq/bpq32.cfg",
            "/root/linbpq/bpq32.cfg",
            "/home/bpq/linbpq/bpq32.cfg",
            "/opt/linbpq/bpq32.cfg"
        ]
        
        for config_path in paths_to_try:
            try:
                with open(config_path, "r") as f:
                    for line in f:
                        if "LOCATOR" in line.upper():
                            grid = line.split("=")[1].strip()
                            if grid:
                                return grid
            except (IOError, OSError):
                continue
    except Exception:
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
    # Accept both uppercase and lowercase, validation pattern works on uppercase
    text_upper = text.strip().upper()
    return bool(re.match(pattern, text_upper))


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


def get_alerts(latlon):
    """Get active alerts from NWS for lat/lon"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        url = "https://api.weather.gov/alerts/active?point={},{}".format(lat, lon)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        alerts = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            event = props.get("event", "")
            headline = props.get("headline", "")
            severity = props.get("severity", "")
            description = props.get("description", "")
            
            alerts.append({
                "event": event,
                "headline": headline,
                "severity": severity,
                "description": description
            })
        
        return alerts
    except Exception:
        return None


def get_hwo_skywarn_status(wfo):
    """Check HWO for SKYWARN activation status"""
    try:
        import urllib.request
        
        # Construct HWO URL from WFO code
        # Pattern: https://tgftp.nws.noaa.gov/data/raw/TYPE/CODEFTYPE.WFOID.hwo.ID.txt
        # Example: https://tgftp.nws.noaa.gov/data/raw/fl/flus41.kgyx.hwo.gyx.txt
        # For general pattern, we'll use a simplified approach
        hwo_url = "https://api.weather.gov/offices/{}/headlines".format(wfo)
        
        with urllib.request.urlopen(hwo_url, timeout=3) as response:
            import json
            data = json.loads(response.read().decode('utf-8'))
        
        # Look for "encouraged" in headlines
        for item in data.get("@graph", []):
            content_html = item.get("content", "")
            if "spotters are encouraged" in content_html.lower() or "spotters encouraged" in content_html.lower():
                return "SKYWARN Active", True
        
        return "SKYWARN Not Active", False
    except Exception:
        return "SKYWARN Status Unknown", None


def is_coastal(latlon):
    """Check if location is in coastal area"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Check if marine zone is present (indicates coastal area)
        marine_zone = data.get('properties', {}).get('marineForecastZones')
        return bool(marine_zone)
    except Exception:
        return False


def get_coastal_flood_info(latlon):
    """Get coastal flood and marine forecast info"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        marine_zones = data.get('properties', {}).get('marineForecastZones', [])
        if not marine_zones:
            return None
        
        # Get first marine zone forecast
        coastal_info = []
        for marine_zone_url in marine_zones[:1]:
            try:
                with urllib.request.urlopen(marine_zone_url, timeout=3) as response:
                    zone_data = json.loads(response.read().decode('utf-8'))
                
                zone_props = zone_data.get('properties', {})
                zone_name = zone_props.get('name', 'Marine Zone')
                forecast = zone_props.get('forecast', '')
                
                if forecast:
                    forecast_text = strip_html(forecast)
                    coastal_info.append({
                        'zone': zone_name,
                        'forecast': forecast_text
                    })
            except Exception:
                continue
        
        return coastal_info if coastal_info else None
    except Exception:
        return None


def get_forecast_7day(gridpoint):
    """Get 7-day forecast from NWS gridpoint forecast URL"""
    try:
        import urllib.request
        import json
        
        if not gridpoint:
            return None
        
        with urllib.request.urlopen(gridpoint, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        periods = data.get('properties', {}).get('periods', [])
        forecast_list = []
        
        for period in periods[:7]:
            name = period.get('name', '')
            short_forecast = period.get('shortForecast', '')
            temp = period.get('temperature', '')
            wind = period.get('windSpeed', '')
            
            forecast_list.append({
                'name': name,
                'forecast': short_forecast,
                'temp': temp,
                'wind': wind
            })
        
        return forecast_list if forecast_list else None
    except Exception:
        return None


def get_current_observations(latlon):
    """Get current weather observations from NWS stations"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        # Use grid points to find nearest observation station
        url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        obs_stations = data.get('properties', {}).get('observationStations', '')
        if not obs_stations:
            return None
        
        # Get latest observation from first station
        with urllib.request.urlopen(obs_stations, timeout=3) as response:
            stations_data = json.loads(response.read().decode('utf-8'))
        
        features = stations_data.get('features', [])
        if not features:
            return None
        
        station_url = features[0].get('id', '') + '/observations/latest'
        with urllib.request.urlopen(station_url, timeout=3) as response:
            obs_data = json.loads(response.read().decode('utf-8'))
        
        props = obs_data.get('properties', {})
        obs = {
            'temp': props.get('temperature', {}).get('value'),
            'wind_speed': props.get('windSpeed', {}).get('value'),
            'wind_dir': props.get('windDirection', {}).get('value'),
            'visibility': props.get('visibility', {}).get('value'),
            'weather': props.get('textDescription', ''),
            'pressure': props.get('barometricPressure', {}).get('value')
        }
        
        return obs
    except Exception:
        return None


def get_fire_weather_outlook(wfo):
    """Extract fire weather outlook from headlines"""
    try:
        headlines = get_headlines(wfo)
        if not headlines:
            return None
        
        fire_outlook = None
        for hl in headlines:
            if 'fire' in hl['title'].lower():
                fire_outlook = {
                    'title': hl['title'],
                    'content': hl['content'][:400]
                }
                break
        
        return fire_outlook
    except Exception:
        return None


def get_heat_cold_advisories(alerts):
    """Extract heat and cold advisories from alerts"""
    try:
        if not alerts:
            return None
        
        advisories = []
        for alert in alerts:
            event = alert.get('event', '').upper()
            if any(term in event for term in ['HEAT', 'COLD', 'WIND CHILL', 'FREEZE']):
                advisories.append({
                    'event': alert.get('event'),
                    'severity': alert.get('severity'),
                    'headline': alert.get('headline')
                })
        
        return advisories if advisories else None
    except Exception:
        return None


def get_river_flood_info(alerts):
    """Extract river and flood info from alerts"""
    try:
        if not alerts:
            return None
        
        flood_info = []
        for alert in alerts:
            event = alert.get('event', '').upper()
            if any(term in event for term in ['FLOOD', 'RIVER']):
                flood_info.append({
                    'event': alert.get('event'),
                    'severity': alert.get('severity'),
                    'headline': alert.get('headline')
                })
        
        return flood_info if flood_info else None
    except Exception:
        return None


def get_fire_weather_alerts(alerts):
    """Extract dust and fire weather alerts"""
    try:
        if not alerts:
            return None
        
        fire_alerts = []
        for alert in alerts:
            event = alert.get('event', '').upper()
            if any(term in event for term in ['DUST', 'FIRE', 'HABOOB', 'SMOKE']):
                fire_alerts.append({
                    'event': alert.get('event'),
                    'severity': alert.get('severity'),
                    'headline': alert.get('headline')
                })
        
        return fire_alerts if fire_alerts else None
    except Exception:
        return None


def get_afd(wfo):
    """Get Area Forecast Discussion from headlines"""
    try:
        headlines = get_headlines(wfo)
        if not headlines:
            return None
        
        for hl in headlines:
            if 'discussion' in hl['title'].lower() or 'afd' in hl['title'].lower():
                return {
                    'title': hl['title'],
                    'time': hl['time'],
                    'content': hl['content'][:400]
                }
        
        return None
    except Exception:
        return None


def get_pop(gridpoint):
    """Get probability of precipitation from forecast"""
    try:
        import urllib.request
        import json
        
        if not gridpoint:
            return None
        
        with urllib.request.urlopen(gridpoint, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        periods = data.get('properties', {}).get('periods', [])
        pop_list = []
        
        for period in periods[:5]:
            name = period.get('name', '')
            prob_precip = period.get('probabilityOfPrecipitation', {}).get('value')
            
            if prob_precip:
                pop_list.append({
                    'period': name,
                    'probability': prob_precip
                })
        
        return pop_list if pop_list else None
    except Exception:
        return None


def get_uv_index(latlon):
    """Get UV index forecast"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        gridpoint = data.get('properties', {}).get('forecastGridData')
        if not gridpoint:
            return None
        
        with urllib.request.urlopen(gridpoint, timeout=3) as response:
            forecast_data = json.loads(response.read().decode('utf-8'))
        
        uv_data = forecast_data.get('properties', {}).get('uvIndex', [])
        if uv_data and len(uv_data) > 0:
            values = uv_data[0].get('values', [])
            if values:
                return values[0].get('value')
        
        return None
    except Exception:
        return None


def get_pollen_forecast(latlon):
    """Get pollen forecast (simplified, from EPA/NWS integration)"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        # Try EPA pollen API
        url = "https://www.pollen.com/api/forecast/current/pollen?location={},{}".format(lat, lon)
        req = urllib.request.Request(url, headers={'User-Agent': 'WX-BPQ/1.5'})
        
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        location = data.get('Location', {})
        periods = location.get('periods', [])
        
        if periods:
            today = periods[0]
            triggers = today.get('Triggers', [])
            
            pollen_info = {
                'date': today.get('Date'),
                'triggers': [t.get('Name') for t in triggers[:5]]
            }
            return pollen_info
        
        return None
    except Exception:
        return None


def lookup_zipcode(zipcode):
    """Look up lat/lon from US zipcode"""
    try:
        import urllib.request
        import json
        
        # Use USGS Geocoding API (free, no key required)
        url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={}&benchmark=Public_AR_Current&format=json".format(zipcode)
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if data.get('result', {}).get('addressMatches'):
            match = data['result']['addressMatches'][0]
            coords = match.get('coordinates', {})
            lat = coords.get('y')
            lon = coords.get('x')
            if lat and lon:
                return (lat, lon), "Zipcode {}".format(zipcode)
    except Exception:
        pass
    
    return None, None


def prompt_location(prompt_text="Enter location"):
    """Prompt for location input"""
    print("")
    print(prompt_text)
    print("  Enter: gridsquare (FN43sr), GPS (lat,lon),")
    print("         US zipcode, or callsign")
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
        
        # Try gridsquare (case-insensitive)
        if is_gridsquare_format(response):
            latlon = grid_to_latlon(response.upper())
            if latlon:
                return latlon, response.upper()
            print("Invalid gridsquare. Try again.")
            continue
        
        # Try zipcode (5 digits)
        if response.isdigit() and len(response) == 5:
            print("Looking up zipcode {}...".format(response))
            latlon, desc = lookup_zipcode(response)
            if latlon:
                return latlon, desc
            print("Zipcode not found. Try another.")
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
        print("  - Gridsquare: FN43sr")
        print("  - Zipcode: 04123")
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


def print_main_menu():
    """Print main location selection menu"""
    print("\nSelect Location:")
    print("1) Local weather")
    print("2) Weather for a location")
    print("3) Weather for a callsign")
    print("\nQ) Quit")


def print_reports_menu(location_desc, is_coastal):
    """Print reports menu for selected location"""
    print("\nREPORTS FOR: {}".format(location_desc))
    print("-" * 40)
    print("1) 7-Day Forecast")
    print("2) Current Observations")
    print("3) Fire Weather Outlook")
    print("4) Heat/Cold Advisories")
    print("5) River/Flood Stage")
    if is_coastal:
        print("6) Coastal flood info")
    print("7) Area Forecast Discussion")
    print("8) Probability of Precipitation")
    print("9) UV Index")
    print("10) Pollen Forecast")
    print("11) Dust/Haboob Alerts")
    print("12) Active Alerts")
    print()
    print("1-12) B)ack Q)uit :>")


def show_7day_forecast(gridpoint):
    """Display 7-day forecast"""
    forecast = get_forecast_7day(gridpoint)
    if not forecast:
        print("No forecast available.")
        return
    
    print()
    print("-" * 40)
    print("7-DAY FORECAST")
    print("-" * 40)
    for f in forecast:
        print("\n{}".format(f['name']))
        print("  Temp: {}".format(f['temp']))
        print("  Wind: {}".format(f['wind']))
        print("  {}".format(f['forecast'][:60]))
    print()
    print("-" * 40)


def show_current_observations(latlon):
    """Display current weather observations"""
    obs = get_current_observations(latlon)
    if not obs:
        print("No observations available.")
        return
    
    print()
    print("-" * 40)
    print("CURRENT CONDITIONS")
    print("-" * 40)
    print("Temp: {}C".format(obs.get('temp')))
    print("Wind: {} {}".format(obs.get('wind_speed'), obs.get('wind_dir')))
    print("Conditions: {}".format(obs.get('weather')))
    print("Visibility: {}".format(obs.get('visibility')))
    print("Pressure: {}".format(obs.get('pressure')))
    print()
    print("-" * 40)


def show_fire_weather(wfo):
    """Display fire weather outlook"""
    fire = get_fire_weather_outlook(wfo)
    if not fire:
        print("No fire weather outlook available.")
        return
    
    print()
    print("-" * 40)
    print("FIRE WEATHER")
    print("-" * 40)
    print(fire['title'])
    print()
    print(fire['content'][:300])
    print()
    print("-" * 40)


def show_heat_cold(alerts):
    """Display heat/cold advisories"""
    adv = get_heat_cold_advisories(alerts)
    if not adv:
        print("No heat/cold advisories.")
        return
    
    print()
    print("-" * 40)
    print("HEAT/COLD ADVISORIES")
    print("-" * 40)
    for a in adv:
        print("\n{}: {}".format(a['event'], a['severity']))
        if a['headline']:
            print("  {}".format(a['headline'][:80]))
    print()
    print("-" * 40)


def show_river_flood(alerts):
    """Display river and flood alerts"""
    flood = get_river_flood_info(alerts)
    if not flood:
        print("No river/flood alerts.")
        return
    
    print()
    print("-" * 40)
    print("RIVER/FLOOD STAGE")
    print("-" * 40)
    for f in flood:
        print("\n{}: {}".format(f['event'], f['severity']))
        if f['headline']:
            print("  {}".format(f['headline'][:80]))
    print()
    print("-" * 40)


def show_afd_report(wfo):
    """Display Area Forecast Discussion"""
    afd = get_afd(wfo)
    if not afd:
        print("No discussion available.")
        return
    
    print()
    print("-" * 40)
    print("AREA FORECAST DISCUSSION")
    print("-" * 40)
    print("[{}] {}".format(afd['time'], afd['title']))
    print()
    print(afd['content'][:300])
    print()
    print("-" * 40)


def show_pop_report(gridpoint):
    """Display probability of precipitation"""
    pop = get_pop(gridpoint)
    if not pop:
        print("No precipitation data available.")
        return
    
    print()
    print("-" * 40)
    print("PROBABILITY OF PRECIPITATION")
    print("-" * 40)
    for p in pop:
        print("{}: {}%".format(p['period'], p['probability']))
    print()
    print("-" * 40)


def show_uv_report(latlon):
    """Display UV index"""
    uv = get_uv_index(latlon)
    if uv is None:
        print("No UV index available.")
        return
    
    print()
    print("-" * 40)
    print("UV INDEX")
    print("-" * 40)
    print("Current: {}".format(uv))
    print()
    print("-" * 40)


def show_pollen_report(latlon):
    """Display pollen forecast"""
    pollen = get_pollen_forecast(latlon)
    if not pollen:
        print("No pollen data available.")
        return
    
    print()
    print("-" * 40)
    print("POLLEN FORECAST")
    print("-" * 40)
    print("Date: {}".format(pollen.get('date')))
    triggers = pollen.get('triggers', [])
    if triggers:
        print("Triggers:")
        for t in triggers:
            print("  - {}".format(t))
    else:
        print("No major pollen triggers.")
    print()
    print("-" * 40)


def show_dust_alerts(alerts):
    """Display dust and fire weather alerts"""
    dust = get_fire_weather_alerts(alerts)
    if not dust:
        print("No dust/fire alerts.")
        return
    
    print()
    print("-" * 40)
    print("DUST/HABOOB/FIRE ALERTS")
    print("-" * 40)
    for d in dust:
        print("\n{}: {}".format(d['event'], d['severity']))
        if d['headline']:
            print("  {}".format(d['headline'][:80]))
    print()
    print("-" * 40)


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


def show_alerts(alerts, skywarn_status, skywarn_active):
    """Display weather alerts and SKYWARN status"""
    print()
    print("-" * 40)
    print(skywarn_status)
    print("-" * 40)
    print()
    
    if not alerts:
        print("No active weather alerts.")
    else:
        print("Active Alerts: {}".format(len(alerts)))
        print("-" * 40)
        for i, alert in enumerate(alerts, 1):
            severity_marker = "*" if alert['severity'] in ['Extreme', 'Severe'] else " "
            print("\n{}{}: {} ({})".format(severity_marker, i, alert['event'], alert['severity']))
            if alert['headline']:
                print("  {}".format(alert['headline'][:100]))
    
    print()
    print("-" * 40)


def show_coastal_flood_info(coastal_info):
    """Display coastal flood and marine forecast info"""
    print()
    print("-" * 40)
    print("COASTAL/MARINE FORECAST")
    print("-" * 40)
    print()
    
    if not coastal_info:
        print("No coastal forecast available.")
    else:
        for item in coastal_info:
            print("Zone: {}".format(item['zone']))
            print()
            forecast_text = item['forecast'][:300]
            print(forecast_text)
            if len(item['forecast']) > 300:
                print("...")
    
    print()
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
    
    # Main menu loop
    while True:
        print_main_menu()
        
        try:
            choice = input(":> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break
        
        if choice == 'Q':
            print("\nExiting...")
            break
        
        # Determine location based on user choice
        selected_latlon = None
        selected_desc = None
        selected_grid = None
        
        if choice == '1':
            # Local weather
            selected_latlon = local_latlon
            selected_desc = "Local ({})".format(local_grid)
            selected_grid = local_grid
        
        elif choice == '2':
            # Weather for location
            result = prompt_location("Enter location for weather:")
            if result:
                selected_latlon, selected_desc = result
                selected_grid = selected_desc.split('(')[1].rstrip(')') if '(' in selected_desc else selected_desc
            else:
                continue
        
        elif choice == '3':
            # Weather for callsign
            if my_callsign:
                print("")
                print("Callsign: {} (stdin) or enter different".format(my_callsign))
                try:
                    call = input(":> ").strip().upper()
                except (EOFError, KeyboardInterrupt):
                    continue
                
                if not call:
                    # Use stdin callsign
                    call = my_callsign
            else:
                print("")
                try:
                    call = input("Enter callsign: ").strip().upper()
                except (EOFError, KeyboardInterrupt):
                    continue
            
            if call:
                grid = lookup_callsign(call)
                if grid and is_gridsquare_format(grid):
                    selected_latlon = grid_to_latlon(grid)
                    selected_desc = "{} ({})".format(call, grid)
                    selected_grid = grid
                    if not selected_latlon:
                        print("Could not convert grid to coordinates.")
                        continue
                else:
                    print("Callsign not found or no grid.")
                    continue
            else:
                continue
        
        else:
            continue
        
        # Fetch data for selected location
        if not selected_latlon:
            print("Could not determine location.")
            continue
        
        print("\nGetting data for {}...".format(selected_desc))
        gridpoint, wfo = get_gridpoint(selected_latlon)
        alerts = get_alerts(selected_latlon) if selected_latlon else None
        is_coastal_area = is_coastal(selected_latlon)
        skywarn_status, skywarn_active = get_hwo_skywarn_status(wfo) if wfo else ("Unknown", None)
        
        # Show alert summary if any
        if alerts and len(alerts) > 0:
            print()
            print("!!! ALERTS DETECTED !!!")
            print("Active: {}".format(len(alerts)))
            for alert in alerts:
                if alert['severity'] in ['Extreme', 'Severe']:
                    print("  *{}: {}".format(alert['event'], alert['severity']))
                else:
                    print("  {}: {}".format(alert['event'], alert['severity']))
            print()
        
        if skywarn_active:
            print("*** {} ***".format(skywarn_status))
            print()
        
        # Reports submenu loop for this location
        while True:
            print_reports_menu(selected_desc, is_coastal_area)
            
            try:
                choice = input(":> ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                sys.exit(0)
            
            if choice == 'Q':
                print("\nExiting...")
                sys.exit(0)
            
            elif choice == 'B':
                # Back to main menu
                break
            
            elif choice == '1':
                show_7day_forecast(gridpoint)
            
            elif choice == '2':
                show_current_observations(selected_latlon)
            
            elif choice == '3':
                show_fire_weather(wfo) if wfo else print("No forecast data available.")
            
            elif choice == '4':
                show_heat_cold(alerts) if alerts else print("No advisories.")
            
            elif choice == '5':
                show_river_flood(alerts) if alerts else print("No flood alerts.")
            
            elif choice == '6' and is_coastal_area:
                coastal_info = get_coastal_flood_info(selected_latlon)
                show_coastal_flood_info(coastal_info)
            
            elif choice == '7':
                show_afd_report(wfo) if wfo else print("No discussion available.")
            
            elif choice == '8':
                show_pop_report(gridpoint)
            
            elif choice == '9':
                show_uv_report(selected_latlon)
            
            elif choice == '10':
                show_pollen_report(selected_latlon)
            
            elif choice == '11':
                show_dust_alerts(alerts) if alerts else print("No dust alerts.")
            
            elif choice == '12':
                show_alerts(alerts, skywarn_status, skywarn_active) if alerts else print("No active alerts.")
            
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
