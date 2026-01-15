#!/usr/bin/env python3
"""
Node Map HTML Generator for BPQ Packet Radio Networks
------------------------------------------------------
Generates interactive HTML map and static SVG from nodemap.json data.

Outputs:
  nodemap.html - Interactive Leaflet map (requires internet for tiles)
  nodemap.svg  - Static vector map (fully offline with state/county boundaries)

For BPQ Web Server:
  Copy nodemap.html to your BPQ HTML directory and add menu link.
  See --help for BPQ configuration instructions.

Author: Brad Brown (KC1JMH)
Date: January 2026
Version: 1.4.1
"""

__version__ = '1.4.1'

import sys
import json
import os
import math
import re


class Colors:
    """ANSI color codes for console output."""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RESET = '\033[0m'


def colored_print(message, color=None):
    """Print message with color if stdout is a terminal."""
    if color and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        print("{}{}{}".format(color, message, Colors.RESET))
    else:
        print(message)


# Try to import boundary data (optional)
try:
    from map_boundaries import get_state_boundaries, get_maine_counties, get_states_in_bounds
    HAS_BOUNDARIES = True
except ImportError:
    HAS_BOUNDARIES = False

# Check Python version
if sys.version_info < (3, 5):
    colored_print("Error: This script requires Python 3.5 or later.", Colors.RED)
    sys.exit(1)


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
    if not re.match(r'^[A-R]{2}[0-9]{2}([A-X]{2})?$', grid):
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


def get_band_color(frequency):
    """
    Get color for amateur radio band based on frequency (MHz).
    
    Returns CSS color string.
    """
    if frequency is None:
        return '#888888'  # Gray for unknown
    
    freq = float(frequency)
    
    if 144.0 <= freq <= 148.0:
        return '#2196F3'  # Blue - 2m
    elif 222.0 <= freq <= 225.0:
        return '#9C27B0'  # Purple - 1.25m
    elif 420.0 <= freq <= 450.0:
        return '#FF9800'  # Orange - 70cm
    elif 902.0 <= freq <= 928.0:
        return '#E91E63'  # Pink - 33cm
    elif 1240.0 <= freq <= 1300.0:
        return '#00BCD4'  # Cyan - 23cm
    elif 50.0 <= freq <= 54.0:
        return '#4CAF50'  # Green - 6m
    elif 28.0 <= freq <= 29.7:
        return '#FFEB3B'  # Yellow - 10m
    else:
        return '#888888'  # Gray - other


def get_band_name(frequency):
    """Get band name from frequency (MHz)."""
    if frequency is None:
        return 'Unknown'
    
    freq = float(frequency)
    
    if 144.0 <= freq <= 148.0:
        return '2m'
    elif 222.0 <= freq <= 225.0:
        return '1.25m'
    elif 420.0 <= freq <= 450.0:
        return '70cm'
    elif 902.0 <= freq <= 928.0:
        return '33cm'
    elif 1240.0 <= freq <= 1300.0:
        return '23cm'
    elif 50.0 <= freq <= 54.0:
        return '6m'
    elif 28.0 <= freq <= 29.7:
        return '10m'
    else:
        return 'Other'


def load_nodemap(filename='nodemap.json'):
    """Load nodemap.json and return full data dict (nodes, connections)."""
    if not os.path.exists(filename):
        colored_print("Error: {} not found".format(filename), Colors.RED)
        print("Run nodemap.py first to generate network data.")
        return None
    
    # Use utf-8-sig to handle BOM if present
    with open(filename, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    return data


def extract_sponsor(info_text):
    """Extract sponsoring agency from INFO text if present."""
    if not info_text:
        return None
    
    # Common patterns for sponsoring organizations
    patterns = [
        r'maintained by[:\s]+(.+?)(?:\.|$)',
        r'operated by[:\s]+(.+?)(?:\.|$)',
        r'sponsored by[:\s]+(.+?)(?:\.|$)',
        r'owned by[:\s]+(.+?)(?:\.|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, info_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:50]  # Limit length
    
    return None


def generate_html_map(nodes, connections, output_file='nodemap.html'):
    """
    Generate interactive Leaflet HTML map.
    
    Note: Requires internet connection to load map tiles and Leaflet library.
    """
    # Build node data with coordinates
    map_nodes = []
    map_connections = []
    
    for callsign, node_data in nodes.items():
        location = node_data.get('location', {})
        grid = location.get('grid', '')
        
        coords = grid_to_latlon(grid)
        if not coords:
            continue
        
        lat, lon = coords
        
        # Extract node info for popup
        info_text = node_data.get('info', '')
        sponsor = extract_sponsor(info_text)
        city = location.get('city', '')
        state = location.get('state', '')
        node_type = node_data.get('type', 'Unknown')
        
        # Split applications into NetRom access and other apps
        all_apps = node_data.get('applications', [])
        netrom_access = []
        applications = []
        for app in all_apps:
            # NetRom entries contain ":" (like "CCEMA:WS1EC-15}") or "}" (prompt)
            # These are aliases, not applications
            if ':' in app or '}' in app:
                # This is a NetRom alias
                netrom_access.append(app)
            else:
                # This is an actual application (BBS, CHAT, GOPHER, EANHUB, etc.)
                applications.append(app)
        
        # Get frequencies from ports (with band color)
        frequencies = []
        for port in node_data.get('ports', []):
            if port.get('is_rf') and port.get('frequency'):
                freq = port['frequency']
                band = get_band_name(freq)
                color = get_band_color(freq)
                frequencies.append({
                    'text': "{} MHz ({})".format(freq, band),
                    'color': color
                })
        
        # Get SSIDs (only node's own service SSIDs from own_aliases)
        ssids = []
        for alias in node_data.get('own_aliases', []):
            if ':' in alias:
                ssid = alias.split(':')[1]
                if ssid not in ssids:
                    ssids.append(ssid)
        
        # Extract base callsign for display (without SSID)
        display_call = callsign.split('-')[0] if '-' in callsign else callsign
        
        # Calculate RF/IP neighbor counts for this node (from ROUTES only)
        routes = node_data.get('routes', {})
        heard_on_ports = node_data.get('heard_on_ports', [])
        ports = node_data.get('ports', [])
        
        # Build set of neighbors heard on RF ports
        rf_heard = set()
        for entry in heard_on_ports:
            if len(entry) == 2:
                neighbor, port_num = entry
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                for port in ports:
                    if port.get('number') == port_num and port.get('is_rf'):
                        rf_heard.add(neighbor_base)
                        break
        
        # Count routes: RF if heard on RF port, otherwise IP
        rf_neighbor_count = 0
        ip_neighbor_count = 0
        for neighbor_base, quality in routes.items():
            if quality > 0:
                if neighbor_base in rf_heard:
                    rf_neighbor_count += 1
                else:
                    ip_neighbor_count += 1
        
        map_nodes.append({
            'callsign': callsign,
            'display_call': display_call,  # Base callsign for map labels
            'lat': lat,
            'lon': lon,
            'grid': grid,
            'city': city,
            'state': state,
            'type': node_type,
            'sponsor': sponsor,
            'netrom_access': netrom_access,
            'applications': applications,
            'frequencies': frequencies,
            'ssids': ssids,
            'rf_neighbors': rf_neighbor_count,
            'ip_neighbors': ip_neighbor_count
        })
    
    # Build map connections from routes tables (quality > 0)
    # Connections display base callsigns but connect nodes via their SSIDs
    node_coords = {}
    for node in map_nodes:
        node_coords[node['callsign']] = (node['lat'], node['lon'])
    
    seen_connections = set()
    
    for callsign, node_data in nodes.items():
        # Skip nodes without coordinates
        if callsign not in node_coords:
            continue
        
        from_lat, from_lon = node_coords[callsign]
        routes = node_data.get('routes', {})
        
        # Iterate through routes table (ROUTES-validated neighbors)
        for neighbor_base, quality in routes.items():
            if quality == 0:
                continue  # Skip zeroed routes
            
            # Find neighbor in nodes dict - could be keyed as base or with SSID
            neighbor_key = None
            if neighbor_base in nodes:
                neighbor_key = neighbor_base
            else:
                # Try to find with SSID suffix
                for node_key in nodes.keys():
                    if node_key.startswith(neighbor_base + '-'):
                        neighbor_key = node_key
                        break
            
            # Skip if neighbor not in topology or has no coordinates
            if not neighbor_key or neighbor_key not in node_coords:
                continue
            
            to_lat, to_lon = node_coords[neighbor_key]
            
            # Deduplicate bidirectional connections (A-B same as B-A)
            conn_key = tuple(sorted([callsign, neighbor_key]))
            if conn_key in seen_connections:
                continue
            seen_connections.add(conn_key)
            
            # Get frequency for color coding (from source node's ports)
            conn_freq = None
            for port in node_data.get('ports', []):
                if port.get('is_rf') and port.get('frequency'):
                    conn_freq = port['frequency']
                    break
            
            map_connections.append({
                'from': callsign,
                'to': neighbor_key,
                'from_lat': from_lat,
                'from_lon': from_lon,
                'to_lat': to_lat,
                'to_lon': to_lon,
                'color': get_band_color(conn_freq),
                'frequency': conn_freq
            })
    
    if not map_nodes:
        colored_print("Error: No nodes with valid grid squares found.", Colors.RED)
        return False
    
    # Calculate neighbor statistics
    # RF neighbors: in ROUTES and heard on RF port
    # IP neighbors: in ROUTES but NOT heard on RF port (AXIP/telnet only)
    total_rf_neighbors = 0
    total_ip_neighbors = 0
    
    for callsign, node_data in nodes.items():
        routes = node_data.get('routes', {})
        heard_on_ports = node_data.get('heard_on_ports', [])
        ports = node_data.get('ports', [])
        
        # Build set of neighbors heard on RF ports
        rf_heard = set()
        for entry in heard_on_ports:
            if len(entry) == 2:
                neighbor, port_num = entry
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                
                # Check if this port is RF
                for port in ports:
                    if port.get('number') == port_num and port.get('is_rf'):
                        rf_heard.add(neighbor_base)
                        break
        
        # Count routes: RF if heard on RF port, otherwise IP
        rf_neighbors = set()
        ip_neighbors = set()
        
        for neighbor_base, quality in routes.items():
            if quality > 0:
                if neighbor_base in rf_heard:
                    rf_neighbors.add(neighbor_base)
                else:
                    ip_neighbors.add(neighbor_base)
        
        total_rf_neighbors += len(rf_neighbors)
        total_ip_neighbors += len(ip_neighbors)
    
    # Build list of unmapped nodes (no valid gridsquare)
    # Deduplicate by base callsign to avoid showing NG1P and NG1P-4 separately
    unmapped_nodes = []
    seen_base_calls = set()
    for callsign, node_data in nodes.items():
        location = node_data.get('location', {})
        grid = location.get('grid', '')
        if not grid_to_latlon(grid):
            # Extract base callsign (without SSID) for deduplication
            base_call = callsign.split('-')[0] if '-' in callsign else callsign
            if base_call not in seen_base_calls:
                unmapped_nodes.append(base_call)  # Show base callsign only
                seen_base_calls.add(base_call)
    unmapped_nodes.sort()
    
    if unmapped_nodes:
        colored_print("Nodes without gridsquare: {}".format(', '.join(unmapped_nodes)), Colors.YELLOW)
    
    # Calculate map center
    avg_lat = sum(n['lat'] for n in map_nodes) / len(map_nodes)
    avg_lon = sum(n['lon'] for n in map_nodes) / len(map_nodes)
    
    # Generate HTML
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Packet Radio Network Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        #map { height: 100vh; width: 100%; }
        .legend {
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            line-height: 1.6;
        }
        .legend-item { display: flex; align-items: center; margin: 3px 0; }
        .legend-color { width: 20px; height: 3px; margin-right: 8px; }
        .popup-content h3 { margin: 0 0 8px 0; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .popup-content p { margin: 4px 0; font-size: 13px; }
        .popup-content .label { font-weight: bold; color: #666; }
        .popup-content .apps { color: #2196F3; }
        .popup-content .freqs { color: #FF9800; }
        .info-box {
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        // Node data
        var nodes = ''' + json.dumps(map_nodes) + ''';
        var connections = ''' + json.dumps(map_connections) + ''';
        
        // Initialize map
        var map = L.map('map').setView([''' + str(avg_lat) + ''', ''' + str(avg_lon) + '''], 8);
        
        // Add tile layer (OpenStreetMap)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors | Packet Network Map'
        }).addTo(map);
        
        // Draw connections first (so they're under markers)
        var drawnConnections = new Set();
        connections.forEach(function(conn) {
            // Deduplicate bidirectional connections
            var key = [conn.from, conn.to].sort().join('-');
            if (drawnConnections.has(key)) return;
            drawnConnections.add(key);
            
            var line = L.polyline([
                [conn.from_lat, conn.from_lon],
                [conn.to_lat, conn.to_lon]
            ], {
                color: conn.color,
                weight: 2,
                opacity: 0.7
            }).addTo(map);
            
            var freq = conn.frequency ? conn.frequency + ' MHz' : 'Unknown';
            line.bindTooltip(conn.from + ' ↔ ' + conn.to + '<br>' + freq);
        });
        
        // Add node markers
        nodes.forEach(function(node) {
            var marker = L.circleMarker([node.lat, node.lon], {
                radius: 8,
                fillColor: '#e53935',
                color: '#b71c1c',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            }).addTo(map);
            
            // Build popup content
            var popup = '<div class="popup-content">';
            popup += '<h3>' + node.callsign + '</h3>';
            
            if (node.city || node.state) {
                popup += '<p><span class="label">Location:</span> ' + 
                         (node.city ? node.city + ', ' : '') + (node.state || '') + '</p>';
            }
            popup += '<p><span class="label">Grid:</span> ' + node.grid + '</p>';
            popup += '<p><span class="label">Type:</span> ' + node.type + '</p>';
            
            if (node.sponsor) {
                popup += '<p><span class="label">Sponsor:</span> ' + node.sponsor + '</p>';
            }
            
            if (node.ssids && node.ssids.length > 0) {
                popup += '<p><span class="label">SSIDs:</span> ' + node.ssids.join(', ') + '</p>';
            }
            
            if (node.frequencies && node.frequencies.length > 0) {
                popup += '<p><span class="label">Frequencies:</span><br>';
                node.frequencies.forEach(function(freq) {
                    popup += '<span class="freqs" style="color:' + freq.color + ';">' + 
                             freq.text + '</span><br>';
                });
                popup += '</p>';
            }
            
            if (node.netrom_access && node.netrom_access.length > 0) {
                popup += '<p><span class="label">NetRom Access:</span><br>' + 
                         '<span class="apps">' + node.netrom_access.join(', ') + '</span></p>';
            }
            
            if (node.applications && node.applications.length > 0) {
                var apps = node.applications.slice(0, 10);  // Limit display
                popup += '<p><span class="label">Applications:</span><br>' + 
                         '<span class="apps">' + apps.join(', ') + '</span></p>';
            }
            
            popup += '<p><span class="label">RF Neighbors:</span> ' + node.rf_neighbors + '<br>' +
                     '<span class="label">IP Neighbors:</span> ' + node.ip_neighbors + '</p>';
            popup += '</div>';
            
            marker.bindPopup(popup, { maxWidth: 300 });
            marker.bindTooltip(node.display_call, { permanent: false, direction: 'top' });
        });
        
        // Add legend
        var legend = L.control({ position: 'bottomright' });
        legend.onAdd = function(map) {
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<strong>Band Colors</strong><br>' +
                '<div class="legend-item"><div class="legend-color" style="background:#2196F3"></div>2m (144-148 MHz)</div>' +
                '<div class="legend-item"><div class="legend-color" style="background:#FF9800"></div>70cm (420-450 MHz)</div>' +
                '<div class="legend-item"><div class="legend-color" style="background:#9C27B0"></div>1.25m (222-225 MHz)</div>' +
                '<div class="legend-item"><div class="legend-color" style="background:#4CAF50"></div>6m (50-54 MHz)</div>' +
                '<div class="legend-item"><div class="legend-color" style="background:#888888"></div>Other/Unknown</div>';
            return div;
        };
        legend.addTo(map);
        
        // Add info box with unmapped nodes
        var unmappedNodes = ''' + json.dumps(unmapped_nodes) + ''';
        var rfNeighbors = ''' + str(total_rf_neighbors) + ''';
        var ipNeighbors = ''' + str(total_ip_neighbors) + ''';
        var info = L.control({ position: 'topright' });
        info.onAdd = function(map) {
            var div = L.DomUtil.create('div', 'info-box');
            var unmappedHtml = '';
            if (unmappedNodes.length > 0) {
                unmappedHtml = '<hr style="margin:8px 0">' +
                    '<strong style="color:#ff9800">Unmapped Nodes</strong><br>' +
                    '<small>(no gridsquare data)</small><br>' +
                    '<span style="color:#666">' + unmappedNodes.join(', ') + '</span>';
            }
            div.innerHTML = '<strong>Packet Radio Network</strong><br>' +
                'Nodes: ' + nodes.length + '<br>' +
                'Connections: ' + connections.length + '<br>' +
                'RF Neighbors: ' + rfNeighbors + '<br>' +
                'IP Neighbors: ' + ipNeighbors + '<br>' +
                '<small>Generated by nodemap-html.py</small>' +
                unmappedHtml;
            return div;
        };
        info.addTo(map);
        
        // Fit bounds to show all nodes
        if (nodes.length > 1) {
            var bounds = L.latLngBounds(nodes.map(function(n) { return [n.lat, n.lon]; }));
            map.fitBounds(bounds, { padding: [20, 20] });
        }
    </script>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Count unique connections (deduplicated)
    unique_connections = set()
    for conn in map_connections:
        key = tuple(sorted([conn['from'], conn['to']]))
        unique_connections.add(key)
    
    print("Generated {} ({} nodes, {} connections)".format(output_file, len(map_nodes), len(unique_connections)))
    return True


def generate_svg_map(nodes, connections, output_file='nodemap.svg'):
    """
    Generate static SVG map (fully offline, no external dependencies).
    
    Uses simple coordinate projection for regional coverage.
    """
    # Build node data with coordinates
    map_nodes = []
    map_connections = []
    
    for callsign, node_data in nodes.items():
        location = node_data.get('location', {})
        grid = location.get('grid', '')
        
        coords = grid_to_latlon(grid)
        if not coords:
            continue
        
        lat, lon = coords
        
        # Get primary frequency for node color
        primary_freq = None
        for port in node_data.get('ports', []):
            if port.get('is_rf') and port.get('frequency'):
                primary_freq = port['frequency']
                break
        
        # Build frequency list for tooltip
        freq_list = []
        for port in node_data.get('ports', []):
            if port.get('is_rf') and port.get('frequency'):
                freq_list.append("{} MHz".format(port['frequency']))
        
        # Extract base callsign for display (without SSID)
        display_call = callsign.split('-')[0] if '-' in callsign else callsign
        
        # Calculate RF/IP neighbor counts for this node (from ROUTES only)
        routes = node_data.get('routes', {})
        heard_on_ports = node_data.get('heard_on_ports', [])
        ports_data = node_data.get('ports', [])
        
        # Build set of neighbors heard on RF ports
        rf_heard = set()
        for entry in heard_on_ports:
            if len(entry) == 2:
                neighbor, port_num = entry
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                for port in ports_data:
                    if port.get('number') == port_num and port.get('is_rf'):
                        rf_heard.add(neighbor_base)
                        break
        
        # Count routes: RF if heard on RF port, otherwise IP
        rf_neighbor_count = 0
        ip_neighbor_count = 0
        for neighbor_base, quality in routes.items():
            if quality > 0:
                if neighbor_base in rf_heard:
                    rf_neighbor_count += 1
                else:
                    ip_neighbor_count += 1
        
        map_nodes.append({
            'callsign': callsign,
            'display_call': display_call,  # Base callsign for SVG labels
            'lat': lat,
            'lon': lon,
            'grid': grid,
            'frequency': primary_freq,
            'frequencies': freq_list,
            'type': node_data.get('type', 'Unknown'),
            'rf_neighbors': rf_neighbor_count,
            'ip_neighbors': ip_neighbor_count
        })
    
    # Build map connections from routes tables (quality > 0)
    node_coords = {}
    for node in map_nodes:
        node_coords[node['callsign']] = (node['lat'], node['lon'])
    
    seen_connections = set()
    
    for callsign, node_data in nodes.items():
        if callsign not in node_coords:
            continue
        
        from_lat, from_lon = node_coords[callsign]
        routes = node_data.get('routes', {})
        
        for neighbor_base, quality in routes.items():
            if quality == 0:
                continue
            
            # Find neighbor in nodes dict - could be keyed as base or with SSID
            neighbor_key = None
            if neighbor_base in nodes:
                neighbor_key = neighbor_base
            else:
                for node_key in nodes.keys():
                    if node_key.startswith(neighbor_base + '-'):
                        neighbor_key = node_key
                        break
            
            if not neighbor_key or neighbor_key not in node_coords:
                continue
            
            to_lat, to_lon = node_coords[neighbor_key]
            
            conn_key = tuple(sorted([callsign, neighbor_key]))
            if conn_key in seen_connections:
                continue
            seen_connections.add(conn_key)
            
            conn_freq = None
            for port in node_data.get('ports', []):
                if port.get('is_rf') and port.get('frequency'):
                    conn_freq = port['frequency']
                    break
            
            map_connections.append({
                'from': callsign,
                'to': neighbor_key,
                'from_lat': from_lat,
                'from_lon': from_lon,
                'to_lat': to_lat,
                'to_lon': to_lon,
                'color': get_band_color(conn_freq),
                'frequency': conn_freq
            })
    
    if not map_nodes:
        colored_print("Error: No nodes with valid grid squares found.", Colors.RED)
        return False
    
    # Calculate bounds from nodes
    min_lat = min(n['lat'] for n in map_nodes)
    max_lat = max(n['lat'] for n in map_nodes)
    min_lon = min(n['lon'] for n in map_nodes)
    max_lon = max(n['lon'] for n in map_nodes)
    
    # Add generous padding for context (show surrounding area)
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    lat_padding = max(lat_range * 0.3, 0.5)  # At least 0.5 degrees
    lon_padding = max(lon_range * 0.3, 0.5)
    min_lat -= lat_padding
    max_lat += lat_padding
    min_lon -= lon_padding
    max_lon += lon_padding
    
    # SVG dimensions
    width = 800
    height = 600
    
    def project(lat, lon):
        """Simple Mercator-like projection to SVG coordinates."""
        x = (lon - min_lon) / (max_lon - min_lon) * (width - 100) + 50
        y = (max_lat - lat) / (max_lat - min_lat) * (height - 100) + 50
        return (x, y)
    
    def coords_to_path(coords):
        """Convert list of [lon, lat] coords to SVG path."""
        if not coords:
            return ""
        points = []
        for lon, lat in coords:
            x, y = project(lat, lon)
            points.append("{:.1f},{:.1f}".format(x, y))
        return "M " + " L ".join(points) + " Z"
    
    # Generate SVG
    svg_lines = []
    svg_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    svg_lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}" width="{}" height="{}">'.format(width, height, width, height))
    svg_lines.append('  <style>')
    svg_lines.append('    .node { cursor: pointer; }')
    svg_lines.append('    .node:hover circle { r: 10; }')
    svg_lines.append('    .node text { font-family: sans-serif; font-size: 10px; }')
    svg_lines.append('    .connection { stroke-opacity: 0.6; transition: stroke-opacity 0.2s, stroke-width 0.2s; }')
    svg_lines.append('    .connection:hover { stroke-opacity: 1.0; stroke-width: 4; }')
    svg_lines.append('    .connection.highlighted { stroke-opacity: 1.0; stroke-width: 4; }')
    svg_lines.append('    .connection.dimmed { stroke-opacity: 0.15; }')
    svg_lines.append('    .legend text { font-family: sans-serif; font-size: 11px; }')
    svg_lines.append('    .title { font-family: sans-serif; font-size: 16px; font-weight: bold; }')
    svg_lines.append('    .state { fill: #e8e8e8; stroke: #999; stroke-width: 1; }')
    svg_lines.append('    .county { fill: none; stroke: #bbb; stroke-width: 0.5; stroke-dasharray: 2,2; }')
    svg_lines.append('    .state-label { font-family: sans-serif; font-size: 12px; fill: #666; }')
    svg_lines.append('  </style>')
    svg_lines.append('  <script><![CDATA[')
    svg_lines.append('    function highlightNode(callsign) {')
    svg_lines.append('      // Dim all connections')
    svg_lines.append('      var connections = document.querySelectorAll(".connection");')
    svg_lines.append('      connections.forEach(function(conn) {')
    svg_lines.append('        conn.classList.add("dimmed");')
    svg_lines.append('        conn.classList.remove("highlighted");')
    svg_lines.append('      });')
    svg_lines.append('      // Highlight connections for this node')
    svg_lines.append('      var nodeConns = document.querySelectorAll(".connection[data-from=\'" + callsign + "\'], .connection[data-to=\'" + callsign + "\']");')
    svg_lines.append('      nodeConns.forEach(function(conn) {')
    svg_lines.append('        conn.classList.remove("dimmed");')
    svg_lines.append('        conn.classList.add("highlighted");')
    svg_lines.append('      });')
    svg_lines.append('    }')
    svg_lines.append('    function unhighlightAll() {')
    svg_lines.append('      var connections = document.querySelectorAll(".connection");')
    svg_lines.append('      connections.forEach(function(conn) {')
    svg_lines.append('        conn.classList.remove("dimmed", "highlighted");')
    svg_lines.append('      });')
    svg_lines.append('    }')
    svg_lines.append('  ]]></script>')
    
    # Background
    svg_lines.append('  <rect width="100%" height="100%" fill="#f5f5f5"/>')
    
    # Define clip path to constrain boundary drawing to visible area
    svg_lines.append('  <defs>')
    svg_lines.append('    <clipPath id="map-clip">')
    svg_lines.append('      <rect x="50" y="50" width="{}" height="{}"/>'.format(width - 100, height - 100))
    svg_lines.append('    </clipPath>')
    svg_lines.append('  </defs>')
    
    # Draw state boundaries if available
    if HAS_BOUNDARIES:
        svg_lines.append('  <!-- State boundaries -->')
        svg_lines.append('  <g class="boundaries" clip-path="url(#map-clip)">')
        
        # Get states that overlap with our map bounds
        visible_states = get_states_in_bounds(min_lat, max_lat, min_lon, max_lon)
        state_data = get_state_boundaries()
        
        for state_code in visible_states:
            if state_code in state_data:
                state = state_data[state_code]
                path_d = coords_to_path(state['coords'])
                if path_d:
                    svg_lines.append('    <path class="state" d="{}">'.format(path_d))
                    svg_lines.append('      <title>{}</title>'.format(state['name']))
                    svg_lines.append('    </path>')
        
        # Draw Maine counties if Maine is visible and we're zoomed in enough
        if 'ME' in visible_states:
            lat_range = max_lat - min_lat
            if lat_range < 5:  # Only show counties when zoomed in
                county_data = get_maine_counties()
                for county_name, county in county_data.items():
                    path_d = coords_to_path(county['coords'])
                    if path_d:
                        svg_lines.append('    <path class="county" d="{}">'.format(path_d))
                        svg_lines.append('      <title>{} County</title>'.format(county_name))
                        svg_lines.append('    </path>')
        
        svg_lines.append('  </g>')
    
    # Title
    svg_lines.append('  <text x="{}" y="25" class="title" text-anchor="middle">Packet Radio Network Map</text>'.format(width/2))
    
    # Draw connections
    svg_lines.append('  <g class="connections">')
    drawn_connections = set()
    for conn in map_connections:
        # Avoid duplicate lines (A-B and B-A)
        key = tuple(sorted([conn['from'], conn['to']]))
        if key in drawn_connections:
            continue
        drawn_connections.add(key)
        
        x1, y1 = project(conn['from_lat'], conn['from_lon'])
        x2, y2 = project(conn['to_lat'], conn['to_lon'])
        freq_label = "{} MHz".format(conn['frequency']) if conn.get('frequency') else "Unknown"
        svg_lines.append('    <line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="2" class="connection" data-from="{}" data-to="{}">'.format(
            x1, y1, x2, y2, conn['color'], conn['from'], conn['to']))
        svg_lines.append('      <title>{} ↔ {} ({})</title>'.format(conn['from'], conn['to'], freq_label))
        svg_lines.append('    </line>')
    svg_lines.append('  </g>')
    
    # Draw nodes
    svg_lines.append('  <g class="nodes">')
    for node in map_nodes:
        x, y = project(node['lat'], node['lon'])
        color = get_band_color(node['frequency'])
        
        # Build tooltip with same structure as HTML popups
        tooltip_lines = []
        tooltip_lines.append("{} ({})".format(node['callsign'], node['grid']))
        if node['type']:
            tooltip_lines.append("Type: {}".format(node['type']))
        if node['frequencies']:
            tooltip_lines.append("Frequencies: {}".format(", ".join(node['frequencies'])))
        tooltip_lines.append("RF Neighbors: {}".format(node['rf_neighbors']))
        tooltip_lines.append("IP Neighbors: {}".format(node['ip_neighbors']))
        tooltip = "&#10;".join(tooltip_lines)  # &#10; is XML newline
        
        svg_lines.append('    <g class="node" transform="translate({:.1f},{:.1f})" onmouseenter="highlightNode(\'{}\');" onmouseleave="unhighlightAll();">'.format(x, y, node['callsign']))
        svg_lines.append('      <circle r="6" fill="{}" stroke="#333" stroke-width="1.5">'.format(color))
        svg_lines.append('        <title>{}</title>'.format(tooltip.replace('"', '&quot;')))
        svg_lines.append('      </circle>')
        svg_lines.append('      <text x="8" y="4">{}</text>'.format(node['display_call']))
        svg_lines.append('    </g>')
    svg_lines.append('  </g>')
    
    # Legend
    legend_x = width - 150
    legend_y = height - 140
    svg_lines.append('  <g class="legend" transform="translate({},{})">'.format(legend_x, legend_y))
    svg_lines.append('    <rect x="-5" y="-15" width="140" height="130" fill="white" stroke="#ccc" rx="5"/>')
    svg_lines.append('    <text y="0" font-weight="bold">Band Colors</text>')
    
    bands = [
        ('#2196F3', '2m (144-148 MHz)'),
        ('#FF9800', '70cm (420-450 MHz)'),
        ('#9C27B0', '1.25m (222-225 MHz)'),
        ('#4CAF50', '6m (50-54 MHz)'),
        ('#888888', 'Other/Unknown'),
    ]
    for i, (color, label) in enumerate(bands):
        y_offset = 20 + i * 20
        svg_lines.append('    <line x1="0" y1="{}" x2="20" y2="{}" stroke="{}" stroke-width="3"/>'.format(y_offset, y_offset, color))
        svg_lines.append('    <text x="25" y="{}">{}</text>'.format(y_offset + 4, label))
    svg_lines.append('  </g>')
    
    # Stats
    svg_lines.append('  <text x="10" y="{}" font-family="sans-serif" font-size="10" fill="#666">'.format(height - 10))
    svg_lines.append('    Nodes: {} | Connections: {} | Generated by nodemap-html.py'.format(len(map_nodes), len(drawn_connections)))
    svg_lines.append('  </text>')
    
    svg_lines.append('</svg>')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg_lines))
    
    print("Generated {} ({} nodes, {} connections)".format(output_file, len(map_nodes), len(drawn_connections)))
    return True


def show_help():
    """Display help information."""
    print("Node Map HTML Generator v{}".format(__version__))
    print("=" * 50)
    print("")
    print("Generates visual maps from nodemap.json data.")
    print("")
    print("Usage: {} [OPTIONS]".format(sys.argv[0]))
    print("")
    print("Options:")
    print("  --html FILE       Generate interactive HTML map (default: nodemap.html)")
    print("  --svg FILE        Generate static SVG map (default: nodemap.svg)")
    print("  --input FILE      Input JSON file (default: nodemap.json)")
    print("  --output-dir DIR  Save files to directory (prompts for ../linbpq/HTML)")
    print("  --all             Generate both HTML and SVG")
    print("  --help, -h, /?    Show this help message")
    print("")
    print("Examples:")
    print("  {} --all                    # Generate both formats".format(sys.argv[0]))
    print("  {} --html network.html      # Custom HTML filename".format(sys.argv[0]))
    print("  {} --svg --input data.json  # SVG from custom input".format(sys.argv[0]))
    print("")
    print("Output Files:")
    print("  nodemap.html - Interactive Leaflet map")
    print("                 REQUIRES INTERNET for map tiles")
    print("                 Click nodes for detailed info")
    print("                 Color-coded by frequency band")
    print("")
    print("  nodemap.svg  - Static vector map")
    print("                 FULLY OFFLINE - no dependencies")
    print("                 Hover nodes for basic info")
    print("                 Can be embedded in HTML pages")
    print("")
    print("BPQ Web Server Setup:")
    print("  1. Copy nodemap.html to your BPQ HTML directory:")
    print("     cp nodemap.html ~/linbpq/HTML/")
    print("")
    print("  2. Add link in your BPQ web interface index.html:")
    print('     <a href="nodemap.html">Network Map</a>')
    print("")
    print("  3. Or add custom page in bpq32.cfg (HTML section):")
    print("     FILE=/HTML/nodemap.html,nodemap.html")
    print("")
    print("Note on Offline Use:")
    print("  The HTML map requires internet to load OpenStreetMap tiles.")
    print("  For fully offline operation, use the SVG output instead.")
    print("  The SVG can be viewed in any web browser without connectivity.")


def main():
    """Main entry point."""
    # Parse arguments first to check for help
    args = sys.argv[1:]
    
    if not args or '--help' in args or '-h' in args or '/?' in args:
        show_help()
        return
    
    # Show version for actual runs
    print("")
    print("Node Map HTML Generator v{}".format(__version__))
    print("")
    
    input_file = 'nodemap.json'
    html_file = None
    svg_file = None
    output_dir = None
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg == '--input' and i + 1 < len(args):
            input_file = args[i + 1]
            i += 2
        elif arg == '--output-dir' and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif arg == '--html':
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                html_file = args[i + 1]
                i += 2
            else:
                html_file = 'nodemap.html'
                i += 1
        elif arg == '--svg':
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                svg_file = args[i + 1]
                i += 2
            else:
                svg_file = 'nodemap.svg'
                i += 1
        elif arg == '--all':
            html_file = 'nodemap.html'
            svg_file = 'nodemap.svg'
            i += 1
        else:
            i += 1
    
    # Default to --all if no output specified
    if html_file is None and svg_file is None:
        html_file = 'nodemap.html'
        svg_file = 'nodemap.svg'
    
    # Check for linbpq HTML directory and prompt user
    if output_dir is None:
        linbpq_html = os.path.join('..', 'linbpq', 'HTML')
        if os.path.isdir(linbpq_html):
            print("")
            print("Found linbpq HTML directory: {}".format(os.path.abspath(linbpq_html)))
            try:
                response = input("Save files there? (Y/n): ").strip().lower()
                if response == '' or response == 'y' or response == 'yes':
                    output_dir = linbpq_html
                    print("Files will be saved to {}".format(os.path.abspath(output_dir)))
            except (KeyboardInterrupt, EOFError):
                print("")
                print("Using current directory")
    
    # Prepend output directory to filenames if specified
    if output_dir:
        if html_file:
            html_file = os.path.join(output_dir, os.path.basename(html_file))
        if svg_file:
            svg_file = os.path.join(output_dir, os.path.basename(svg_file))
    
    # Load data
    data = load_nodemap(input_file)
    if not data:
        return
    
    nodes = data.get('nodes', {})
    connections = data.get('connections', [])
    
    print("Loaded {} nodes and {} connections from {}".format(len(nodes), len(connections), input_file))
    
    # Count nodes with grid squares
    nodes_with_grid = sum(1 for n in nodes.values() if n.get('location', {}).get('grid'))
    print("Nodes with grid squares: {}".format(nodes_with_grid))
    
    if nodes_with_grid == 0:
        print("")
        colored_print("Warning: No nodes have grid square data.", Colors.YELLOW)
        print("Grid squares are extracted from node INFO text.")
        print("Nodes without grid squares cannot be mapped.")
        return
    
    print("")
    
    # Generate outputs
    if html_file:
        generate_html_map(nodes, connections, html_file)
    
    if svg_file:
        generate_svg_map(nodes, connections, svg_file)
    
    print("")
    print("Map generation complete!")
    
    # Only show deployment reminder if not already saved to linbpq
    if output_dir is None or 'linbpq' not in output_dir.lower():
        print("")
        print("To deploy to BPQ Web Server:")
        print("  cp nodemap.html nodemap.svg ../linbpq/HTML/")
        print("  (or manually copy files to your linbpq HTML directory)")


if __name__ == '__main__':
    main()
