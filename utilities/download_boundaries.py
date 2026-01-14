#!/usr/bin/env python3
"""
Download and Convert Natural Earth Boundary Data
------------------------------------------------
Downloads state and county boundaries from Natural Earth Data
and converts them to Python format for offline SVG map rendering.

Natural Earth Data: https://www.naturalearthdata.com/
License: Public Domain
Resolution: 1:10m (most detailed)

Usage:
  python3 download_boundaries.py
  
Output:
  map_boundaries.py - Updated with accurate boundary data
"""

import urllib.request
import zipfile
import json
import os
import sys

def download_file(url, filename):
    """Download a file with progress indication."""
    print("Downloading {}...".format(filename))
    try:
        urllib.request.urlretrieve(url, filename)
        print("  Downloaded: {}".format(filename))
        return True
    except Exception as e:
        print("  Error downloading: {}".format(e))
        return False

def extract_zip(zip_path, extract_to='.'):
    """Extract a zip file."""
    print("Extracting {}...".format(zip_path))
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print("  Extracted to: {}".format(extract_to))
        return True
    except Exception as e:
        print("  Error extracting: {}".format(e))
        return False

def simplify_coords(coords, tolerance=0.01):
    """
    Simplify coordinate list using Douglas-Peucker algorithm.
    Reduces point count while maintaining shape.
    
    Args:
        coords: List of [lon, lat] coordinate pairs
        tolerance: Simplification tolerance (degrees)
    
    Returns:
        Simplified coordinate list
    """
    if len(coords) <= 2:
        return coords
    
    # Find point with maximum distance from line between first and last
    first = coords[0]
    last = coords[-1]
    max_dist = 0
    max_idx = 0
    
    for i in range(1, len(coords) - 1):
        point = coords[i]
        # Calculate perpendicular distance from point to line
        dx = last[0] - first[0]
        dy = last[1] - first[1]
        denom = dx*dx + dy*dy
        
        if denom == 0:
            # First and last points are the same
            dist = ((point[0] - first[0])**2 + (point[1] - first[1])**2)**0.5
        else:
            dist = abs(dy * point[0] - dx * point[1] + 
                      last[0] * first[1] - last[1] * first[0]) / denom**0.5
        
        if dist > max_dist:
            max_dist = dist
            max_idx = i
    
    # If max distance is greater than tolerance, recursively simplify
    if max_dist > tolerance:
        # Simplify left and right segments
        left = simplify_coords(coords[:max_idx+1], tolerance)
        right = simplify_coords(coords[max_idx:], tolerance)
        # Combine (remove duplicate middle point)
        return left[:-1] + right
    else:
        # Return just endpoints
        return [first, last]

def process_geojson(geojson_path, name_field='name', simplify=True, country_filter=None):
    """
    Process GeoJSON file and extract boundary coordinates.
    
    Args:
        geojson_path: Path to GeoJSON file
        name_field: Field name containing region name
        simplify: Whether to simplify coordinates
        country_filter: ISO country code to filter by (e.g., 'US')
    
    Returns:
        Dictionary of {code: {name, coords}} or None on error
    """
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        boundaries = {}
        
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            
            # Filter by country if specified
            if country_filter:
                iso_a2 = props.get('iso_a2') or props.get('gu_a3', '')[:2]
                if iso_a2 != country_filter:
                    continue
            
            # Get name from properties
            name = props.get(name_field) or props.get('NAME') or props.get('name')
            if not name:
                continue
            
            # Extract coordinates based on geometry type
            coords = []
            if geom.get('type') == 'Polygon':
                # Use first (outer) ring
                coords = geom.get('coordinates', [[]])[0]
            elif geom.get('type') == 'MultiPolygon':
                # Use first polygon's outer ring
                coords = geom.get('coordinates', [[[]]]) [0][0]
            
            if not coords:
                continue
            
            # Simplify if requested
            if simplify:
                coords = simplify_coords(coords, tolerance=0.005)
            
            # Round to 2 decimal places
            coords = [[round(lon, 2), round(lat, 2)] for lon, lat in coords]
            
            # Generate code (state abbreviation or county name)
            code = props.get('postal') or props.get('STUSPS') or name.upper().replace(' ', '_')
            
            boundaries[code] = {
                'name': name,
                'coords': coords
            }
            
            print("  Processed: {} ({} points)".format(name, len(coords)))
        
        return boundaries
    
    except Exception as e:
        print("  Error processing GeoJSON: {}".format(e))
        return None

def generate_python_file(state_boundaries, county_boundaries, output_file='map_boundaries.py'):
    """Generate Python module with boundary data."""
    print("\nGenerating {}...".format(output_file))
    
    lines = []
    lines.append('# -*- coding: utf-8 -*-')
    lines.append('"""')
    lines.append('US State and County Boundaries for Offline Maps')
    lines.append('------------------------------------------------')
    lines.append('Accurate boundary data from Natural Earth Data (Public Domain)')
    lines.append('https://www.naturalearthdata.com/')
    lines.append('')
    lines.append('Resolution: 1:10m (most detailed)')
    lines.append('Coordinates: [lon, lat] pairs (GeoJSON convention)')
    lines.append('Simplified using Douglas-Peucker algorithm for reasonable file size')
    lines.append('"""')
    lines.append('')
    lines.append('# State boundary polygons (lon, lat pairs)')
    lines.append('STATE_BOUNDARIES = {')
    
    for code in sorted(state_boundaries.keys()):
        state = state_boundaries[code]
        lines.append("    '{}': {{".format(code))
        lines.append("        'name': '{}',".format(state['name']))
        lines.append("        'coords': [")
        
        # Format coordinates (4 per line)
        coords = state['coords']
        for i in range(0, len(coords), 4):
            chunk = coords[i:i+4]
            coord_strs = ["[{}, {}]".format(lon, lat) for lon, lat in chunk]
            lines.append("            " + ", ".join(coord_strs) + ("," if i + 4 < len(coords) else ""))
        
        lines.append("        ]")
        lines.append("    },")
    
    lines.append('}')
    lines.append('')
    lines.append('# Maine county boundaries (lon, lat pairs)')
    lines.append('MAINE_COUNTIES = {')
    
    for code in sorted(county_boundaries.keys()):
        county = county_boundaries[code]
        lines.append("    '{}': {{".format(code))
        lines.append("        'name': '{}',".format(county['name']))
        lines.append("        'coords': [")
        
        # Format coordinates (4 per line)
        coords = county['coords']
        for i in range(0, len(coords), 4):
            chunk = coords[i:i+4]
            coord_strs = ["[{}, {}]".format(lon, lat) for lon, lat in chunk]
            lines.append("            " + ", ".join(coord_strs) + ("," if i + 4 < len(coords) else ""))
        
        lines.append("        ]")
        lines.append("    },")
    
    lines.append('}')
    lines.append('')
    lines.append('def get_state_boundaries():')
    lines.append('    """Return all state boundary data."""')
    lines.append('    return STATE_BOUNDARIES')
    lines.append('')
    lines.append('def get_maine_counties():')
    lines.append('    """Return Maine county boundary data."""')
    lines.append('    return MAINE_COUNTIES')
    lines.append('')
    lines.append('def get_states_in_bounds(min_lat, max_lat, min_lon, max_lon):')
    lines.append('    """')
    lines.append('    Return list of state codes that overlap with given bounds.')
    lines.append('    ')
    lines.append('    Args:')
    lines.append('        min_lat, max_lat: Latitude range')
    lines.append('        min_lon, max_lon: Longitude range')
    lines.append('    ')
    lines.append('    Returns:')
    lines.append('        List of state codes (e.g., [\'ME\', \'NH\', \'VT\'])')
    lines.append('    """')
    lines.append('    visible_states = []')
    lines.append('    ')
    lines.append('    for code, state in STATE_BOUNDARIES.items():')
    lines.append('        # Check if any coordinate is within bounds')
    lines.append('        for lon, lat in state[\'coords\']:')
    lines.append('            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:')
    lines.append('                visible_states.append(code)')
    lines.append('                break')
    lines.append('    ')
    lines.append('    return visible_states')
    lines.append('')
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("  Wrote: {}".format(output_file))
        return True
    except Exception as e:
        print("  Error writing file: {}".format(e))
        return False

def main():
    """Main entry point."""
    print("Natural Earth Boundary Data Downloader")
    print("=" * 50)
    print("")
    
    # URLs for Natural Earth 1:10m data (most detailed) - GeoJSON format
    state_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson"
    
    # Note: Natural Earth doesn't have US county data at 1:10m
    # We'll need to use a different source for counties or skip them
    print("NOTE: Will download US state boundaries.")
    print("County data may need separate processing from Census TIGER/Line files.")
    print("")
    
    # Download states
    state_file = "ne_10m_admin_1_states_provinces.geojson"
    if not os.path.exists(state_file):
        if not download_file(state_url, state_file):
            print("\nFailed to download state boundaries.")
            return 1
    
    # No extraction needed - already GeoJSON
    geojson_file = state_file
    
    if not os.path.exists(geojson_file):
        print("\nError: Could not find GeoJSON file after extraction.")
        print("Available files:")
        for f in os.listdir('.'):
            if 'admin_1' in f.lower():
                print("  - {}".format(f))
        return 1
    
    print("\nProcessing state boundaries...")
    all_states = process_geojson(geojson_file, name_field='name', country_filter='US')
    
    if not all_states:
        print("\nFailed to process state boundaries.")
        return 1
    
    # Filter to only US states we care about (Northeast + nearby)
    us_states = {}
    keep_states = ['ME', 'NH', 'VT', 'MA', 'CT', 'RI', 'NY', 'PA', 'NJ', 'MD', 'DE', 'VA', 'WV', 'DC']
    
    for code, data in all_states.items():
        if code in keep_states:
            us_states[code] = data
    
    print("\nKept {} relevant northeastern US states.".format(len(us_states)))
    
    # For now, use empty counties (will need separate processing)
    maine_counties = {}
    print("\nNote: County boundaries need separate processing from Census data.")
    
    # Generate Python file
    if not generate_python_file(us_states, maine_counties):
        print("\nFailed to generate map_boundaries.py")
        return 1
    
    print("\nSuccess! map_boundaries.py has been updated with accurate boundary data.")
    print("File size: {} KB".format(os.path.getsize('map_boundaries.py') // 1024))
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
