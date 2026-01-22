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
- Multiple location input formats: gridsquare, GPS, callsign, zipcode
- Case-insensitive gridsquare input
- Graceful offline fallback

Author: Brad Brown KC1JMH
Version: 4.2
Date: January 2026

NWS API Documentation:
- Service overview: https://www.weather.gov/documentation/services-web-api
- General FAQs: https://weather-gov.github.io/api/general-faqs
- GitHub repository: https://github.com/weather-gov/api
- API endpoints: https://api.weather.gov/ (root)
- Products endpoint: https://api.weather.gov/products/types/{TYPE} (HWO, CLI, ZFP, WSW, etc.)
- Points endpoint: https://api.weather.gov/points/{lat},{lon} (location data)
- Forecast: https://api.weather.gov/gridpoints/{wfo}/{x},{y}/forecast
- Hourly: https://api.weather.gov/gridpoints/{wfo}/{x},{y}/forecast/hourly
- Gridpoint data: https://api.weather.gov/gridpoints/{wfo}/{x},{y} (raw observations)
- Alerts: https://api.weather.gov/alerts/active?point={lat},{lon}
"""

from __future__ import print_function
import sys
import os
import re
from datetime import datetime

VERSION = "4.2"
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


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit"""
    if celsius is None:
        return None
    try:
        return int(round(float(celsius) * 9.0 / 5.0 + 32))
    except (ValueError, TypeError):
        return None


def ms_to_mph(ms):
    """Convert meters per second to miles per hour"""
    if ms is None:
        return None
    try:
        return int(round(float(ms) * 2.237))
    except (ValueError, TypeError):
        return None


def meters_to_miles(meters):
    """Convert meters to miles"""
    if meters is None:
        return None
    try:
        miles = float(meters) / 1609.34
        return round(miles, 1)
    except (ValueError, TypeError):
        return None


def pascals_to_inhg(pa):
    """Convert Pascals to inches of mercury"""
    if pa is None:
        return None
    try:
        inhg = float(pa) / 3386.39
        return round(inhg, 2)
    except (ValueError, TypeError):
        return None


def degrees_to_cardinal(degrees):
    """Convert wind direction degrees to cardinal direction"""
    if degrees is None:
        return "?"
    try:
        d = float(degrees)
        # 16-point compass rose
        directions = [
            'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'
        ]
        # Normalize to 0-360
        d = d % 360
        # Each sector is 22.5 degrees (360/16)
        index = int((d + 11.25) / 22.5) % 16
        return directions[index]
    except (ValueError, TypeError):
        return "?"


def windchill_celsius_to_fahrenheit(celsius):
    """Convert wind chill Celsius to Fahrenheit"""
    if celsius is None:
        return None
    try:
        return int(round(float(celsius) * 9.0 / 5.0 + 32))
    except (ValueError, TypeError):
        return None


def mm_to_inches(mm):
    """Convert millimeters to inches"""
    if mm is None or mm == 0:
        return None
    try:
        inches = float(mm) / 25.4
        return round(inches, 2)
    except (ValueError, TypeError):
        return None


def cm_to_inches(cm):
    """Convert centimeters to inches"""
    if cm is None or cm == 0:
        return None
    try:
        inches = float(cm) / 2.54
        return round(inches, 1)
    except (ValueError, TypeError):
        return None


def meters_to_feet(meters):
    """Convert meters to feet"""
    if meters is None or meters == 0:
        return None
    try:
        feet = float(meters) * 3.28084
        return int(feet)
    except (ValueError, TypeError):
        return None


def get_bpq_locator():
    """Read LOCATOR from BPQ32 config file"""
    try:
        # BPQ apps run adjacent to linbpq folder, so ../linbpq/bpq32.cfg
        # Use script's directory as base, not current working directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        
        paths_to_try = [
            os.path.join(parent_dir, "linbpq", "bpq32.cfg"),
            os.path.join(script_dir, "..", "linbpq", "bpq32.cfg"),
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
        
        with urllib.request.urlopen(req, timeout=10) as response:
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
    pattern = r'^[A-R]{2}[0-9]{2}[A-X]{0,2}$'
    # Accept both uppercase and lowercase
    text_upper = text.strip().upper()
    return bool(re.match(pattern, text_upper))


def get_gridpoint(latlon):
    """Get NWS gridpoint and WFO from lat/lon"""
    try:
        import urllib.request
        import json
        
        lat, lon = latlon
        url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(url, timeout=10) as response:
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
        with urllib.request.urlopen(url, timeout=10) as response:
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
        with urllib.request.urlopen(url, timeout=10) as response:
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


def get_local_alert_summary(gridsquare=None):
    """Get brief alert summary for CTEXT display (one line)"""
    try:
        if not gridsquare:
            gridsquare = get_bpq_locator()
        if not gridsquare:
            gridsquare = "FN43hp"
        
        latlon = grid_to_latlon(gridsquare)
        if not latlon:
            return "Local Weather: No data"
        
        alerts = get_alerts(latlon)
        if not alerts:
            return "Local Weather: No active alerts"
        
        # Count by severity
        extreme = sum(1 for a in alerts if a['severity'] == 'Extreme')
        severe = sum(1 for a in alerts if a['severity'] == 'Severe')
        moderate = sum(1 for a in alerts if a['severity'] == 'Moderate')
        minor = sum(1 for a in alerts if a['severity'] == 'Minor')
        
        # Build compact summary
        parts = []
        if extreme:
            parts.append("{}E".format(extreme))
        if severe:
            parts.append("{}S".format(severe))
        if moderate:
            parts.append("{}M".format(moderate))
        if minor:
            parts.append("{}m".format(minor))
        
        if parts:
            return "Local Weather: {} alert{} ({})".format(
                len(alerts),
                "s" if len(alerts) > 1 else "",
                " ".join(parts)
            )
        else:
            return "Local Weather: {} alert{}".format(
                len(alerts),
                "s" if len(alerts) > 1 else ""
            )
    except Exception:
        return "Local Weather: Status unavailable"


def get_beacon_text(gridsquare=None):
    """Get beacon text with alert status for BPQ beacon"""
    try:
        if not gridsquare:
            gridsquare = get_bpq_locator()
        if not gridsquare:
            gridsquare = "FN43hp"
        
        latlon = grid_to_latlon(gridsquare)
        if not latlon:
            return "WS1EC-15: Weather info unavailable"
        
        # Get alerts
        alerts = get_alerts(latlon)
        alert_count = len(alerts) if alerts else 0
        
        # Build beacon message
        if alert_count > 0:
            # Count severe/extreme alerts
            severe_count = 0
            if alerts:
                severe_count = sum(1 for a in alerts if a['severity'] in ['Extreme', 'Severe'])
            
            if severe_count > 0:
                msg = "WS1EC-15: {} WEATHER ALERT{}! ".format(
                    alert_count,
                    "S" if alert_count > 1 else ""
                )
            else:
                msg = "WS1EC-15: {} weather alert{}. ".format(
                    alert_count,
                    "s" if alert_count > 1 else ""
                )
        else:
            msg = "WS1EC-15: No active weather alerts. "
        
        # Add call to action
        msg += "Connect to WX app for details."
        
        return msg
    except Exception:
        return "WS1EC-15: Weather info unavailable"


def get_hwo_skywarn_status(wfo):
    """Check HWO for SKYWARN activation status"""
    try:
        import urllib.request
        
        # Construct HWO URL from WFO code
        # Pattern: https://tgftp.nws.noaa.gov/data/raw/TYPE/CODEFTYPE.WFOID.hwo.ID.txt
        # Example: https://tgftp.nws.noaa.gov/data/raw/fl/flus41.kgyx.hwo.gyx.txt
        # For general pattern, we'll use a simplified approach
        hwo_url = "https://api.weather.gov/offices/{}/headlines".format(wfo)
        
        with urllib.request.urlopen(hwo_url, timeout=10) as response:
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
        with urllib.request.urlopen(url, timeout=10) as response:
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
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        marine_zones = data.get('properties', {}).get('marineForecastZones', [])
        if not marine_zones:
            return None
        
        # Get first marine zone forecast
        coastal_info = []
        for marine_zone_url in marine_zones[:1]:
            try:
                with urllib.request.urlopen(marine_zone_url, timeout=10) as response:
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


def get_forecast_7day(latlon):
    """Get 7-day forecast from NWS for lat/lon"""
    try:
        import urllib.request
        import json
        
        if not latlon:
            return None
        
        # Get gridpoint first to find forecast URL
        lat, lon = latlon
        points_url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(points_url, timeout=10) as response:
            points_data = json.loads(response.read().decode('utf-8'))
        
        # Get the forecast URL (12-hourly periods)
        forecast_url = points_data.get('properties', {}).get('forecast')
        if not forecast_url:
            return None
        
        # Fetch the actual forecast
        with urllib.request.urlopen(forecast_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Extract periods
        if not data or not isinstance(data, dict):
            return None
        
        # Check if we have properties
        properties = data.get('properties')
        if not properties or not isinstance(properties, dict):
            return None
        
        # Get periods array - should be a list
        periods = properties.get('periods')
        if not periods or not isinstance(periods, list) or len(periods) == 0:
            return None
        
        forecast_list = []
        
        for period in periods[:7]:
            name = period.get('name', '')
            short_forecast = period.get('shortForecast', '')
            temp = period.get('temperature', '')
            wind = period.get('windSpeed', '')
            
            if name and short_forecast:
                forecast_list.append({
                    'name': name,
                    'forecast': short_forecast,
                    'temp': temp,
                    'wind': wind
                })
        
        return forecast_list if forecast_list else None
    except Exception:
        return None


def get_forecast_hourly(latlon, hours=12):
    """Get hourly forecast from NWS for lat/lon"""
    try:
        import urllib.request
        import json
        
        if not latlon:
            return None
        
        lat, lon = latlon
        points_url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        req = urllib.request.Request(points_url, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            points_data = json.loads(response.read().decode('utf-8'))
        
        hourly_url = points_data.get('properties', {}).get('forecastHourly')
        if not hourly_url:
            return None
        
        req = urllib.request.Request(hourly_url, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        periods = data.get('properties', {}).get('periods', [])
        if not periods:
            return None
        
        forecast_list = []
        for period in periods[:hours]:
            start_time = period.get('startTime', '')[:16]
            temp = period.get('temperature', '')
            short_forecast = period.get('shortForecast', '')
            wind_speed = period.get('windSpeed', '')
            wind_dir = period.get('windDirection', '')
            
            forecast_list.append({
                'time': start_time,
                'temp': temp,
                'forecast': short_forecast,
                'wind_speed': wind_speed,
                'wind_dir': wind_dir
            })
        
        return forecast_list if forecast_list else None
    except Exception:
        return None


def get_climate_report(wfo):
    """Get daily climate report (CLI) from NWS products API"""
    try:
        import urllib.request
        import json
        
        # Convert WFO to ICAO format
        if not wfo.startswith('K'):
            wfo_code = 'K' + wfo
        else:
            wfo_code = wfo
        
        url = "https://api.weather.gov/products/types/CLI"
        req = urllib.request.Request(url, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        graph = data.get('@graph', [])
        wfo_cli = [item for item in graph if item.get('issuingOffice') == wfo_code]
        
        if not wfo_cli:
            return None
        
        latest = wfo_cli[0]
        product_id = latest.get('@id')
        
        req = urllib.request.Request(product_id, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            product_data = json.loads(response.read().decode('utf-8'))
        
        product_text = product_data.get('productText', '')
        if not product_text:
            return None
        
        return {
            'title': 'Daily Climate Report',
            'issued': latest.get('issuanceTime', '')[:16],
            'content': product_text
        }
    except Exception:
        return None


def get_zone_forecast(wfo):
    """Get zone forecast product (ZFP) from NWS products API"""
    try:
        import urllib.request
        import json
        
        if not wfo.startswith('K'):
            wfo_code = 'K' + wfo
        else:
            wfo_code = wfo
        
        url = "https://api.weather.gov/products/types/ZFP"
        req = urllib.request.Request(url, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        graph = data.get('@graph', [])
        wfo_zfp = [item for item in graph if item.get('issuingOffice') == wfo_code]
        
        if not wfo_zfp:
            return None
        
        latest = wfo_zfp[0]
        product_id = latest.get('@id')
        
        req = urllib.request.Request(product_id, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            product_data = json.loads(response.read().decode('utf-8'))
        
        product_text = product_data.get('productText', '')
        if not product_text:
            return None
        
        return {
            'title': 'Zone Forecast',
            'issued': latest.get('issuanceTime', '')[:16],
            'content': product_text
        }
    except Exception:
        return None


def get_winter_weather_warnings(wfo):
    """Get winter weather warnings/watches/advisories (WSW) from NWS products API"""
    try:
        import urllib.request
        import json
        
        if not wfo.startswith('K'):
            wfo_code = 'K' + wfo
        else:
            wfo_code = wfo
        
        url = "https://api.weather.gov/products/types/WSW"
        req = urllib.request.Request(url, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        graph = data.get('@graph', [])
        wfo_wsw = [item for item in graph if item.get('issuingOffice') == wfo_code]
        
        if not wfo_wsw:
            return None
        
        latest = wfo_wsw[0]
        product_id = latest.get('@id')
        
        req = urllib.request.Request(product_id, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            product_data = json.loads(response.read().decode('utf-8'))
        
        product_text = product_data.get('productText', '')
        if not product_text:
            return None
        
        return {
            'title': 'Winter Weather',
            'issued': latest.get('issuanceTime', '')[:16],
            'content': product_text
        }
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
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        obs_stations = data.get('properties', {}).get('observationStations', '')
        if not obs_stations:
            return None
        
        # Get latest observation from first station
        with urllib.request.urlopen(obs_stations, timeout=10) as response:
            stations_data = json.loads(response.read().decode('utf-8'))
        
        features = stations_data.get('features', [])
        if not features:
            return None
        
        station_url = features[0].get('id', '') + '/observations/latest'
        with urllib.request.urlopen(station_url, timeout=10) as response:
            obs_data = json.loads(response.read().decode('utf-8'))
        
        props = obs_data.get('properties', {})
        obs = {
            'temp': props.get('temperature', {}).get('value'),
            'wind_speed': props.get('windSpeed', {}).get('value'),
            'wind_dir': props.get('windDirection', {}).get('value'),
            'wind_gust': props.get('windGust', {}).get('value'),
            'visibility': props.get('visibility', {}).get('value'),
            'weather': props.get('textDescription', ''),
            'pressure': props.get('barometricPressure', {}).get('value'),
            'humidity': props.get('relativeHumidity', {}).get('value')
        }
        
        # Also get wind chill from gridpoint data (more reliable than station)
        gridpoint_url = data.get('properties', {}).get('forecastGridData')
        if gridpoint_url:
            with urllib.request.urlopen(gridpoint_url, timeout=10) as response:
                grid_data = json.loads(response.read().decode('utf-8'))
            grid_props = grid_data.get('properties', {})
            wind_chill = grid_props.get('windChill', {}).get('values', [{}])[0].get('value')
            obs['wind_chill'] = wind_chill
            
            # Get precipitation, snowfall, ceiling
            precip = grid_props.get('quantitativePrecipitation', {}).get('values', [{}])[0].get('value')
            obs['precipitation'] = precip
            
            snowfall = grid_props.get('snowfallAmount', {}).get('values', [{}])[0].get('value')
            obs['snowfall'] = snowfall
            
            ceiling = grid_props.get('ceilingHeight', {}).get('values', [{}])[0].get('value')
            obs['ceiling'] = ceiling
        
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


def get_hazardous_weather_outlook(wfo):
    """Get hazardous weather outlook from NWS products API"""
    try:
        import urllib.request
        import json
        
        # Get all HWO products
        url = "https://api.weather.gov/products/types/HWO"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        graph = data.get('@graph', [])
        if not graph:
            return None
        
        # Convert WFO code to ICAO format (e.g., GYX -> KGYX)
        if not wfo.startswith('K'):
            wfo_code = 'K' + wfo
        else:
            wfo_code = wfo
        
        # Filter for this WFO's most recent HWO
        wfo_hwo = [item for item in graph if isinstance(item, dict) and item.get('issuingOffice') == wfo_code]
        
        if not wfo_hwo:
            return None
        
        # Get the most recent one (first in list)
        latest = wfo_hwo[0]
        product_id = latest.get('@id')
        
        # Fetch full product details (increase timeout - products can be slow)
        with urllib.request.urlopen(product_id, timeout=10) as response:
            product_data = json.loads(response.read().decode('utf-8'))
        
        product_text = product_data.get('productText', '')
        
        if not product_text:
            return None
        
        # Extract headline and summary
        lines = product_text.strip().split('\n')
        
        # Find "Hazardous Weather Outlook" line
        title = 'Hazardous Weather Outlook'
        for line in lines:
            if 'Hazardous' in line and 'Outlook' in line:
                title = line.strip()
                break
        
        # Get full content (skip first 2 header lines, preserve blank lines)
        content_lines = []
        for line in lines[2:]:
            if line.startswith('$$'):
                break
            content_lines.append(line)
        
        content = '\n'.join(content_lines)
        
        return {
            'title': title,
            'content': content
        }
    except Exception:
        return None


def get_regional_weather_summary(wfo):
    """Get regional weather summary (RWS) from NWS products API"""
    try:
        import urllib.request
        import json
        
        if not wfo.startswith('K'):
            wfo_code = 'K' + wfo
        else:
            wfo_code = wfo
        
        url = "https://api.weather.gov/products/types/RWS"
        req = urllib.request.Request(url, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        graph = data.get('@graph', [])
        wfo_rws = [item for item in graph if item.get('issuingOffice') == wfo_code]
        
        if not wfo_rws:
            return None
        
        latest = wfo_rws[0]
        product_id = latest.get('@id')
        
        req = urllib.request.Request(product_id, headers={'User-Agent': 'wx.py packet radio app'})
        with urllib.request.urlopen(req, timeout=10) as response:
            product_data = json.loads(response.read().decode('utf-8'))
        
        product_text = product_data.get('productText', '')
        if not product_text:
            return None
        
        # Extract title and content
        lines = product_text.strip().split('\n')
        
        title = 'Regional Weather Summary'
        for line in lines:
            if 'Weather Summary' in line or 'WEATHER SUMMARY' in line:
                title = line.strip()
                break
        
        # Get full content (skip first 2 header lines, preserve blank lines)
        content_lines = []
        for line in lines[2:]:
            if line.startswith('$$'):
                break
            content_lines.append(line)
        
        content = '\n'.join(content_lines)
        
        return {
            'title': title,
            'content': content
        }
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


def get_pop(latlon):
    """Get probability of precipitation from forecast"""
    try:
        import urllib.request
        import json
        
        if not latlon:
            return None
        
        # Get forecast URL from points endpoint
        lat, lon = latlon
        points_url = "https://api.weather.gov/points/{},{}".format(lat, lon)
        with urllib.request.urlopen(points_url, timeout=10) as response:
            points_data = json.loads(response.read().decode('utf-8'))
        
        # Get the forecast URL (12-hourly periods)
        forecast_url = points_data.get('properties', {}).get('forecast')
        if not forecast_url:
            return None
        
        # Fetch the actual forecast
        with urllib.request.urlopen(forecast_url, timeout=10) as response:
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
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        gridpoint = data.get('properties', {}).get('forecastGridData')
        if not gridpoint:
            return None
        
        with urllib.request.urlopen(gridpoint, timeout=10) as response:
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
    """Pollen forecast no longer available (pollen.com API blocked)"""
    return None


def lookup_zipcode(zipcode):
    """Look up lat/lon from US zipcode"""
    try:
        import urllib.request
        import json
        
        # Use USGS Geocoding API (free, no key required)
        url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={}&benchmark=Public_AR_Current&format=json".format(zipcode)
        with urllib.request.urlopen(url, timeout=10) as response:
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
    # Immediate conditions
    print("1) Current Observations")
    print("2) Hourly Forecast (12hr)")
    print("3) 7-Day Forecast")
    # Safety & alerts
    print("4) Active Alerts*")
    print("5) Hazardous Weather Outlook*")
    # Detailed forecasts
    print("6) Zone Forecast (Narrative)")
    print("7) Regional Weather Summary")
    print("8) Probability of Precip")
    # Seasonal/situational hazards
    print("9) Winter Weather*")
    print("10) Heat/Cold Advisories*")
    print("11) Fire Weather Outlook*")
    print("12) River/Flood Stage*")
    print("13) Coastal Flood Info{}".format("" if is_coastal else " (N/A)"))
    print("14) Dust/Haboob Alerts")
    # Reference
    print("15) UV Index")
    print("16) Daily Climate Report")
    print()
    print("* Alert details may be found here")
    print("1-16) B)ack Q)uit :>")


def show_7day_forecast(latlon):
    """Display 7-day forecast"""
    print("Loading forecast...", end="\r"); sys.stdout.flush()
    forecast = get_forecast_7day(latlon)
    if not forecast:
        print("No forecast available.")
        return
    
    print()
    print("-" * 40)
    print("7-DAY FORECAST")
    print("-" * 40)
    for f in forecast:
        # Note: NWS forecast endpoint returns temp already in F, wind already in mph
        temp = f.get('temp')
        wind = f.get('wind')
        print("\n{}".format(f['name']))
        if temp is not None:
            print("  Temp: {}F".format(temp))
        if wind:
            print("  Wind: {}".format(wind))
        print("  {}".format(f['forecast'][:60]))
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_hourly_forecast(latlon):
    """Display hourly forecast for next 12 hours"""
    print("Loading hourly forecast...", end="\r"); sys.stdout.flush()
    forecast = get_forecast_hourly(latlon, hours=12)
    if not forecast:
        print("No hourly forecast available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("12-HOUR FORECAST")
    print("-" * 40)
    
    for f in forecast:
        time_str = f.get('time', '')[11:16]  # Extract HH:MM
        temp = f.get('temp', '?')
        forecast_text = f.get('forecast', '')[:20]
        wind_speed = f.get('wind_speed', '')
        wind_dir = f.get('wind_dir', '')
        
        print("{}: {}F {} {}{}".format(
            time_str, temp, forecast_text,
            wind_speed, ' ' + wind_dir if wind_dir else ''
        ))
    
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_climate_report(wfo):
    """Display daily climate report"""
    print("Loading climate report...", end="\r"); sys.stdout.flush()
    report = get_climate_report(wfo)
    if not report:
        print("No climate report available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("DAILY CLIMATE REPORT")
    print("-" * 40)
    
    # Parse out key data from the report
    content = report.get('content', '')
    lines = content.split('\n')
    
    # Show a condensed version (skip headers, show key data)
    in_data = False
    line_count = 0
    for line in lines:
        if 'TEMPERATURE' in line or 'PRECIPITATION' in line:
            in_data = True
        if in_data and line.strip():
            print(line)
            line_count += 1
            if line_count > 15:  # Limit output for packet radio
                break
    
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_zone_forecast(wfo):
    """Display zone forecast product"""
    print("Loading zone forecast...", end="\r"); sys.stdout.flush()
    report = get_zone_forecast(wfo)
    if not report:
        print("No zone forecast available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("ZONE FORECAST")
    print("-" * 40)
    
    content = report.get('content', '')
    lines = content.split('\n')
    
    # Show first zone forecast (skip headers)
    line_count = 0
    started = False
    for line in lines:
        if '.TONIGHT' in line or '.TODAY' in line or '.THIS MORNING' in line:
            started = True
        if started and line.strip():
            print(line)
            line_count += 1
            if line_count > 20:  # Limit for packet radio
                break
    
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_winter_weather(wfo):
    """Display winter weather warnings"""
    print("Loading winter weather...", end="\r"); sys.stdout.flush()
    report = get_winter_weather_warnings(wfo)
    if not report:
        print("No winter weather advisories.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("WINTER WEATHER")
    print("-" * 40)
    
    content = report.get('content', '')
    lines = content.split('\n')
    
    # Parse and display formatted sections with pagination
    line_count = 0
    in_body = False
    user_quit = False
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines and footer
        if not stripped or stripped.startswith('$$'):
            continue
        
        # Start printing after header codes
        if 'National Weather Service' in line:
            in_body = True
        
        if in_body:
            # Add spacing before section headers
            if stripped.startswith('...'):
                print()
            print(line)
            line_count += 1
            if line_count >= 20:
                print()
                try:
                    response = input("Press enter for more, Q to quit: ").strip().upper()
                    if response == 'Q':
                        user_quit = True
                        break
                except (EOFError, KeyboardInterrupt):
                    user_quit = True
                    break
                line_count = 0
    
    print()
    print("-" * 40)
    if not user_quit:
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass


def show_current_observations(latlon):
    """Display current weather observations"""
    print("Loading observations...", end="\r"); sys.stdout.flush()
    obs = get_current_observations(latlon)
    if not obs:
        print("No observations available.")
        return
    
    print()
    print("-" * 40)
    print("CURRENT CONDITIONS")
    print("-" * 40)
    
    # Convert units to imperial and readable formats
    temp_f = celsius_to_fahrenheit(obs.get('temp'))
    wind_mph = ms_to_mph(obs.get('wind_speed'))
    wind_gust_mph = ms_to_mph(obs.get('wind_gust'))
    wind_dir = obs.get('wind_dir')
    wind_cardinal = degrees_to_cardinal(wind_dir)
    visibility_miles = meters_to_miles(obs.get('visibility'))
    pressure_inhg = pascals_to_inhg(obs.get('pressure'))
    humidity = obs.get('humidity')
    wind_chill_f = windchill_celsius_to_fahrenheit(obs.get('wind_chill'))
    precip_inches = mm_to_inches(obs.get('precipitation'))
    snowfall_inches = cm_to_inches(obs.get('snowfall'))
    ceiling_feet = meters_to_feet(obs.get('ceiling'))
    
    if temp_f is not None:
        print("Temp: {}F".format(temp_f))
    else:
        print("Temp: N/A")
    
    if wind_mph is not None and wind_cardinal != "?":
        wind_line = "Wind: {} mph".format(wind_mph)
        if wind_gust_mph is not None:
            wind_line += " gust {} mph".format(wind_gust_mph)
        wind_line += " from {}".format(wind_cardinal)
        print(wind_line)
    elif wind_mph is not None:
        print("Wind: {} mph".format(wind_mph))
    else:
        print("Wind: N/A")
    
    if wind_chill_f is not None:
        print("Wind Chill: {}F".format(wind_chill_f))
    
    if humidity is not None:
        try:
            print("Humidity: {}%".format(int(humidity)))
        except (ValueError, TypeError):
            pass
    
    if precip_inches is not None:
        print("Precipitation: {} in".format(precip_inches))
    
    if snowfall_inches is not None:
        print("Snowfall: {} in".format(snowfall_inches))
    
    if ceiling_feet is not None:
        print("Ceiling: {} ft".format(ceiling_feet))
    
    print("Conditions: {}".format(obs.get('weather', 'N/A')))
    
    if visibility_miles is not None:
        print("Visibility: {} mi".format(visibility_miles))
    else:
        print("Visibility: N/A")
    
    if pressure_inhg is not None:
        print("Pressure: {} inHg".format(pressure_inhg))
    else:
        print("Pressure: N/A")
    
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_fire_weather(wfo):
    """Display fire weather outlook"""
    print("Loading fire weather outlook...", end="\r"); sys.stdout.flush()
    fire = get_fire_weather_outlook(wfo)
    if not fire:
        print("No fire weather outlook available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
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
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_hazardous_weather_outlook(wfo):
    """Display hazardous weather outlook"""
    print("Loading hazardous weather outlook...", end="\r"); sys.stdout.flush()
    hwo = get_hazardous_weather_outlook(wfo)
    if not hwo:
        print("No hazardous weather outlook available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("HAZARDOUS WEATHER OUTLOOK")
    print("-" * 40)
    print(hwo['title'])
    print()
    
    # Display with pagination (20 lines at a time)
    lines = hwo['content'].split('\n')
    line_count = 0
    user_quit = False
    for line in lines:
        print(line)
        line_count += 1
        if line_count >= 20:
            print()
            try:
                response = input("Press ENTER to continue or Q to quit: ").strip().upper()
                if response == 'Q':
                    user_quit = True
                    break
            except (EOFError, KeyboardInterrupt):
                user_quit = True
                break
            line_count = 0
    
    print()
    print("-" * 40)
    if not user_quit:
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass


def show_regional_weather_summary(wfo):
    """Display regional weather summary"""
    print("Loading regional weather summary...", end="\r"); sys.stdout.flush()
    rws = get_regional_weather_summary(wfo)
    if not rws:
        print("No regional weather summary available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("REGIONAL WEATHER SUMMARY")
    print("-" * 40)
    print(rws['title'])
    print()
    
    # Display with pagination (20 lines at a time)
    lines = rws['content'].split('\n')
    line_count = 0
    user_quit = False
    for line in lines:
        print(line)
        line_count += 1
        if line_count >= 20:
            print()
            try:
                response = input("Press ENTER to continue or Q to quit: ").strip().upper()
                if response == 'Q':
                    user_quit = True
                    break
            except (EOFError, KeyboardInterrupt):
                user_quit = True
                break
            line_count = 0
    
    print()
    print("-" * 40)
    if not user_quit:
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass


def show_heat_cold(alerts):
    """Display heat/cold advisories"""
    adv = get_heat_cold_advisories(alerts)
    if not adv:
        print("No advisories.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
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
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_river_flood(alerts):
    """Display river and flood alerts"""
    flood = get_river_flood_info(alerts)
    if not flood:
        print("No flood alerts.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
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
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_afd_report(wfo):
    """Display Area Forecast Discussion"""
    print("Loading discussion...", end="\r"); sys.stdout.flush()
    afd = get_afd(wfo)
    if not afd:
        print("No discussion available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
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
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_pop_report(gridpoint):
    """Display probability of precipitation"""
    print("Loading precipitation data...", end="\r"); sys.stdout.flush()
    pop = get_pop(gridpoint)
    if not pop:
        print("No precipitation data available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("PROBABILITY OF PRECIPITATION")
    print("-" * 40)
    for p in pop:
        print("{}: {}%".format(p['period'], p['probability']))
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_uv_report(latlon):
    """Display UV index"""
    print("Loading UV index...", end="\r"); sys.stdout.flush()
    uv = get_uv_index(latlon)
    if uv is None:
        print("No UV index available.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    print()
    print("-" * 40)
    print("UV INDEX")
    print("-" * 40)
    print("Current: {}".format(uv))
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_pollen_report(latlon):
    """Pollen forecast unavailable - pollen.com API blocked"""
    print("Pollen data unavailable.")
    print("(NWS API does not provide pollen data)")
    return


def show_dust_alerts(alerts):
    """Display dust and fire weather alerts"""
    dust = get_fire_weather_alerts(alerts)
    if not dust:
        print("No dust alerts.")
        try:
            input("\nPress enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
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
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


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
    
    if not alerts:
        print("\nNo active alerts.")
    else:
        print("\nActive Alerts: {}".format(len(alerts)))
        print("-" * 40)
        for i, alert in enumerate(alerts, 1):
            severity_marker = "*" if alert['severity'] in ['Extreme', 'Severe'] else " "
            print("\n{}{}: {} ({})".format(severity_marker, i, alert['event'], alert['severity']))
            if alert['headline']:
                print("  {}".format(alert['headline'][:100]))
    
    print()
    print("-" * 40)
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def show_coastal_flood_info(coastal_info):
    """Display coastal flood and marine forecast info"""
    if coastal_info is None:
        print("Loading coastal forecast...", end="\r"); sys.stdout.flush()
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
    try:
        input("\nPress enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    """Main program loop"""
    # Try to read callsign from BPQ32 (if piped via S flag)
    my_callsign = None
    my_grid = None
    if not sys.stdin.isatty():
        try:
            # Use select for non-blocking read with 0.5s timeout
            import select
            if select.select([sys.stdin], [], [], 0.5)[0]:
                line = sys.stdin.readline().strip().upper()
                if line:
                    my_callsign = line.split('-')[0] if line else None
                    if my_callsign:
                        my_grid = lookup_callsign(my_callsign)
            # Reopen stdin from terminal for interactive use
            try:
                sys.stdin = open('/dev/tty', 'r')
            except (OSError, IOError):
                pass
        except (EOFError, KeyboardInterrupt, ImportError):
            pass
    
    # Print header first so user sees output immediately
    print_header()
    
    # Check for updates (non-blocking)
    check_for_app_update(VERSION, APP_NAME)
    
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
                print("Input call sign or press enter for {}".format(my_callsign))
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
                    call = input("Enter call sign: ").strip().upper()
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
                    print("Call sign not in database.")
                    print("Enter gridsquare for {} (or Q to cancel):".format(call))
                    try:
                        manual_grid = input(":> ").strip().upper()
                    except (EOFError, KeyboardInterrupt):
                        continue
                    
                    if manual_grid.upper() == 'Q':
                        continue
                    
                    if is_gridsquare_format(manual_grid):
                        selected_latlon = grid_to_latlon(manual_grid)
                        selected_desc = "{} ({})".format(call, manual_grid)
                        selected_grid = manual_grid
                        if not selected_latlon:
                            print("Could not convert grid to coordinates.")
                            continue
                    else:
                        print("Invalid gridsquare format.")
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
            
            # Immediate conditions (1-3)
            elif choice == '1':
                show_current_observations(selected_latlon)
            
            elif choice == '2':
                show_hourly_forecast(selected_latlon)
            
            elif choice == '3':
                show_7day_forecast(selected_latlon)
            
            # Safety & alerts (4-5)
            elif choice == '4':
                show_alerts(alerts, skywarn_status, skywarn_active) if alerts else print("No active alerts.")
            
            elif choice == '5':
                show_hazardous_weather_outlook(wfo) if wfo else print("No outlook available.")
            
            # Detailed forecasts (6-8)
            elif choice == '6':
                show_zone_forecast(wfo) if wfo else print("No zone forecast available.")
            
            elif choice == '7':
                show_regional_weather_summary(wfo) if wfo else print("No weather summary available.")
            
            elif choice == '8':
                show_pop_report(selected_latlon)
            
            # Seasonal/situational hazards (9-14)
            elif choice == '9':
                show_winter_weather(wfo) if wfo else print("No winter weather data.")
            
            elif choice == '10':
                show_heat_cold(alerts) if alerts else print("No advisories.")
            
            elif choice == '11':
                show_fire_weather(wfo) if wfo else print("No forecast data available.")
            
            elif choice == '12':
                show_river_flood(alerts) if alerts else print("No flood alerts.")
            
            elif choice == '13':
                coastal_info = get_coastal_flood_info(selected_latlon) if is_coastal_area else None
                show_coastal_flood_info(coastal_info)
            
            elif choice == '14':
                show_dust_alerts(alerts) if alerts else print("No dust alerts.")
            
            # Reference (15-16)
            elif choice == '15':
                show_uv_report(selected_latlon)
            
            elif choice == '16':
                show_climate_report(wfo) if wfo else print("No climate report available.")
            
            else:
                print("\nInvalid choice.")


if __name__ == "__main__":
    try:
        # Check for CLI arguments
        if len(sys.argv) > 1:
            if sys.argv[1] in ['--alert-summary', '-a']:
                # Output alert summary for CTEXT (no header, just the line)
                gridsquare = sys.argv[2] if len(sys.argv) > 2 else None
                print(get_local_alert_summary(gridsquare))
                sys.exit(0)
            elif sys.argv[1] in ['--beacon', '-b']:
                # Output beacon text with alerts and SKYWARN status
                gridsquare = sys.argv[2] if len(sys.argv) > 2 else None
                print(get_beacon_text(gridsquare))
                sys.exit(0)
            elif sys.argv[1] in ['--help', '-h', '/?']:
                print("wx.py v{} - Weather Reports for Packet Radio".format(VERSION))
                print()
                print("USAGE:")
                print("  wx.py              - Interactive weather menu")
                print("  wx.py --alert-summary [GRID]")
                print("                     - Output alert summary line")
                print("                       (for CTEXT display)")
                print("  wx.py --beacon [GRID]")
                print("                     - Output beacon text with")
                print("                       alerts and SKYWARN status")
                print()
                print("OPTIONS:")
                print("  -a, --alert-summary [GRID]")
                print("                     Output one-line alert summary")
                print("                     Uses bpq32.cfg LOCATOR if GRID")
                print("                     not provided.")
                print("  -b, --beacon [GRID]")
                print("                     Output beacon text (alerts +")
                print("                     SKYWARN status + call to action)")
                print("  -h, --help, /?     Show this help message")
                print()
                print("EXAMPLES:")
                print("  wx.py --alert-summary")
                print("  wx.py --alert-summary FN43hp")
                print("  wx.py --beacon")
                print()
                sys.exit(0)
        
        # Interactive mode
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print("\nError: {}".format(str(e)))
        if not is_internet_available():
            print("Internet may be unavailable.")
