#!/usr/bin/env python3
"""
PREDICT Geolocation Utilities
-----------------------------
Coordinate conversion and distance calculations for HF propagation.

Supports:
- Maidenhead grid squares (4 or 6 char)
- Decimal GPS coordinates
- DMS (degrees/minutes/seconds)
- State/country name lookup

Author: Brad Brown KC1JMH
Version: 1.0
Date: January 2026
"""

import math
import re
import json
import os

# Earth radius in km
EARTH_RADIUS_KM = 6371.0

# Grid square validation regex
GRID_REGEX = re.compile(r'^[A-R]{2}[0-9]{2}([A-X]{2})?$', re.IGNORECASE)

# DMS coordinate regex patterns
DMS_REGEX = re.compile(
    r'(\d+)[°d]\s*(\d+)[\'m]\s*(\d+(?:\.\d+)?)[\"s]?\s*([NSns])\s*'
    r'(\d+)[°d]\s*(\d+)[\'m]\s*(\d+(?:\.\d+)?)[\"s]?\s*([EWew])',
    re.IGNORECASE
)

# Decimal GPS regex (lat, lon)
DECIMAL_REGEX = re.compile(
    r'^(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)$'
)


def grid_to_latlon(grid):
    """
    Convert Maidenhead grid square to lat/lon center point.
    
    Args:
        grid: 4 or 6 character grid square (e.g., FN43, FN43sr)
        
    Returns:
        Tuple (lat, lon) or None if invalid
    """
    if not grid or len(grid) < 4:
        return None
    
    grid = grid.upper().strip()
    
    # Validate format
    if not GRID_REGEX.match(grid):
        return None
    
    # Field (2 letters A-R)
    field1 = ord(grid[0]) - ord('A')
    field2 = ord(grid[1]) - ord('A')
    
    # Square (2 digits 0-9)
    square1 = int(grid[2])
    square2 = int(grid[3])
    
    # Base calculation (center of 4-char grid)
    lon = (field1 * 20) - 180 + (square1 * 2) + 1
    lat = (field2 * 10) - 90 + (square2 * 1) + 0.5
    
    # Subsquare (2 letters a-x) if present - more precise
    if len(grid) >= 6:
        sub1 = ord(grid[4]) - ord('A')
        sub2 = ord(grid[5]) - ord('A')
        lon = (field1 * 20) - 180 + (square1 * 2) + (sub1 * 2.0 / 24) + (1.0 / 24)
        lat = (field2 * 10) - 90 + (square2 * 1) + (sub2 * 1.0 / 24) + (0.5 / 24)
    
    return (lat, lon)


def latlon_to_grid(lat, lon, precision=6):
    """
    Convert lat/lon to Maidenhead grid square.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        precision: 4 or 6 characters (default 6)
        
    Returns:
        Grid square string or None if invalid
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    
    if lat < -90 or lat > 90 or lon < -180 or lon > 180:
        return None
    
    # Normalize longitude
    lon = lon + 180
    lat = lat + 90
    
    # Field
    field1 = chr(ord('A') + int(lon / 20))
    field2 = chr(ord('A') + int(lat / 10))
    
    # Square
    lon_remainder = lon % 20
    lat_remainder = lat % 10
    square1 = str(int(lon_remainder / 2))
    square2 = str(int(lat_remainder))
    
    grid = field1 + field2 + square1 + square2
    
    if precision >= 6:
        # Subsquare
        lon_sub = (lon_remainder % 2) * 12
        lat_sub = (lat_remainder % 1) * 24
        sub1 = chr(ord('a') + int(lon_sub))
        sub2 = chr(ord('a') + int(lat_sub))
        grid = grid + sub1 + sub2
    
    return grid


def parse_dms(dms_str):
    """
    Parse DMS (degrees/minutes/seconds) coordinate string.
    
    Args:
        dms_str: String like "43°39'32\"N 70°15'24\"W"
        
    Returns:
        Tuple (lat, lon) or None if invalid
    """
    match = DMS_REGEX.search(dms_str)
    if not match:
        return None
    
    lat_d, lat_m, lat_s, lat_dir = match.group(1, 2, 3, 4)
    lon_d, lon_m, lon_s, lon_dir = match.group(5, 6, 7, 8)
    
    lat = float(lat_d) + float(lat_m) / 60 + float(lat_s) / 3600
    lon = float(lon_d) + float(lon_m) / 60 + float(lon_s) / 3600
    
    if lat_dir.upper() == 'S':
        lat = -lat
    if lon_dir.upper() == 'W':
        lon = -lon
    
    return (lat, lon)


def parse_decimal(coord_str):
    """
    Parse decimal GPS coordinate string.
    
    Args:
        coord_str: String like "43.6591, -70.2568" or "43.6591 -70.2568"
        
    Returns:
        Tuple (lat, lon) or None if invalid
    """
    match = DECIMAL_REGEX.match(coord_str.strip())
    if not match:
        return None
    
    try:
        lat = float(match.group(1))
        lon = float(match.group(2))
        
        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            return None
        
        return (lat, lon)
    except ValueError:
        return None


def parse_location(location_str):
    """
    Parse location string in any supported format.
    
    Tries: gridsquare, decimal GPS, DMS, state/country name
    
    Args:
        location_str: Location in any format
        
    Returns:
        Tuple (lat, lon, description) or (None, None, error_msg)
    """
    location_str = location_str.strip()
    
    # Try gridsquare first
    if GRID_REGEX.match(location_str):
        coords = grid_to_latlon(location_str)
        if coords:
            return (coords[0], coords[1], location_str.upper())
    
    # Try decimal GPS
    coords = parse_decimal(location_str)
    if coords:
        grid = latlon_to_grid(coords[0], coords[1])
        desc = grid if grid else "{:.2f}, {:.2f}".format(coords[0], coords[1])
        return (coords[0], coords[1], desc)
    
    # Try DMS
    coords = parse_dms(location_str)
    if coords:
        grid = latlon_to_grid(coords[0], coords[1])
        desc = grid if grid else "{:.2f}, {:.2f}".format(coords[0], coords[1])
        return (coords[0], coords[1], desc)
    
    # Try state/country lookup
    coords = lookup_region(location_str)
    if coords:
        return (coords[0], coords[1], coords[2])
    
    return (None, None, "Could not parse location: {}".format(location_str))


def great_circle_distance(lat1, lon1, lat2, lon2):
    """
    Calculate great circle distance between two points.
    
    Uses Haversine formula.
    
    Args:
        lat1, lon1: First point in decimal degrees
        lat2, lon2: Second point in decimal degrees
        
    Returns:
        Distance in kilometers
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return EARTH_RADIUS_KM * c


def bearing(lat1, lon1, lat2, lon2):
    """
    Calculate initial bearing from point 1 to point 2.
    
    Args:
        lat1, lon1: Starting point in decimal degrees
        lat2, lon2: Ending point in decimal degrees
        
    Returns:
        Bearing in degrees (0-360)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
    
    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)
    
    return (bearing_deg + 360) % 360


def midpoint(lat1, lon1, lat2, lon2):
    """
    Calculate midpoint of great circle path.
    
    Args:
        lat1, lon1: Starting point in decimal degrees
        lat2, lon2: Ending point in decimal degrees
        
    Returns:
        Tuple (lat, lon) of midpoint
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    delta_lon = math.radians(lon2 - lon1)
    
    bx = math.cos(lat2_rad) * math.cos(delta_lon)
    by = math.cos(lat2_rad) * math.sin(delta_lon)
    
    lat_mid = math.atan2(
        math.sin(lat1_rad) + math.sin(lat2_rad),
        math.sqrt((math.cos(lat1_rad) + bx) ** 2 + by ** 2)
    )
    lon_mid = lon1_rad + math.atan2(by, math.cos(lat1_rad) + bx)
    
    return (math.degrees(lat_mid), math.degrees(lon_mid))


def lookup_region(name):
    """
    Look up state or country centroid by name.
    
    Args:
        name: State name/abbrev or country name
        
    Returns:
        Tuple (lat, lon, description) or None
    """
    name_lower = name.lower().strip()
    
    # Load regions data
    regions_path = os.path.join(os.path.dirname(__file__), 'regions.json')
    try:
        with open(regions_path, 'r') as f:
            regions = json.load(f)
    except (IOError, ValueError):
        return None
    
    # Check US states (by name or abbreviation)
    for state in regions.get('us_states', []):
        if (name_lower == state.get('name', '').lower() or
            name_lower == state.get('abbrev', '').lower()):
            return (state['lat'], state['lon'], 
                    "{} ({})".format(state['name'], state['abbrev']))
    
    # Check countries
    for country in regions.get('countries', []):
        if name_lower == country.get('name', '').lower():
            return (country['lat'], country['lon'], country['name'])
        # Also check common abbreviations
        if name_lower == country.get('abbrev', '').lower():
            return (country['lat'], country['lon'], country['name'])
    
    return None


def validate_grid(grid):
    """
    Validate Maidenhead grid square format.
    
    Args:
        grid: Grid square string
        
    Returns:
        True if valid, False otherwise
    """
    if not grid or len(grid) < 4:
        return False
    return bool(GRID_REGEX.match(grid.strip()))


def format_bearing(deg):
    """
    Format bearing with cardinal direction.
    
    Args:
        deg: Bearing in degrees
        
    Returns:
        String like "225° (SW)"
    """
    cardinals = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    idx = int((deg + 11.25) / 22.5) % 16
    return "{:.0f} ({})".format(deg, cardinals[idx])


def format_distance(km):
    """
    Format distance with appropriate unit.
    
    Args:
        km: Distance in kilometers
        
    Returns:
        String like "680 km" or "4,200 km"
    """
    if km >= 1000:
        return "{:,.0f} km".format(km)
    return "{:.0f} km".format(km)
