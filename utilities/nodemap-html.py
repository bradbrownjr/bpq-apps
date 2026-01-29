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
Version: 1.4.13
"""

__version__ = '1.4.13'

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
    # Build inbound neighbor map for incomplete crawls
    # Count who has routes TO each node (for nodes with empty routes table)
    inbound_neighbors = {}
    for node_call, node_data in nodes.items():
        routes = node_data.get('routes', {})
        heard_on_ports = node_data.get('heard_on_ports', [])
        ports = node_data.get('ports', [])
        
        # Build set of neighbors heard on RF ports from this node's perspective
        rf_heard = set()
        for entry in heard_on_ports:
            if len(entry) == 2:
                neighbor, port_num = entry
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                for port in ports:
                    if port.get('number') == port_num and port.get('is_rf'):
                        rf_heard.add(neighbor_base)
                        break
        
        # For each route, track inbound connection TO the neighbor
        for neighbor_base, quality in routes.items():
            if quality > 0:
                # Find neighbor's key in nodes dict
                neighbor_key = None
                if neighbor_base in nodes:
                    neighbor_key = neighbor_base
                else:
                    for node_key in nodes.keys():
                        if node_key.startswith(neighbor_base + '-'):
                            neighbor_key = node_key
                            break
                
                if neighbor_key:
                    if neighbor_key not in inbound_neighbors:
                        inbound_neighbors[neighbor_key] = {'rf': set(), 'ip': set()}
                    
                    # Inbound TO neighbor_key FROM node_call
                    node_call_base = node_call.split('-')[0] if '-' in node_call else node_call
                    if neighbor_base in rf_heard:
                        inbound_neighbors[neighbor_key]['rf'].add(node_call_base)
                    else:
                        inbound_neighbors[neighbor_key]['ip'].add(node_call_base)
    
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
        # For incomplete crawls, applications may contain OTHER nodes' aliases (from NODES output)
        # Filter to show only this node's own aliases
        all_apps = node_data.get('applications', [])
        own_aliases_dict = node_data.get('own_aliases', {})
        
        # Get this node's actual NetRom aliases (own_aliases is authoritative)
        # Sort to put primary alias (matching node alias field) first
        primary_alias = node_data.get('alias', '')
        netrom_access = []
        if own_aliases_dict:
            # Show primary alias first (bold), then others sorted
            primary_entry = None
            other_entries = []
            
            for alias, full_call in sorted(own_aliases_dict.items()):
                entry = "{}:{}}}".format(alias, full_call)
                if alias == primary_alias:
                    primary_entry = entry
                else:
                    other_entries.append(entry)
            
            # Primary first (will be bolded in display)
            if primary_entry:
                netrom_access.append(primary_entry)
            netrom_access.extend(other_entries)
        else:
            # Fallback: extract from applications (may include other nodes' aliases)
            for app in all_apps:
                if ':' in app or '}' in app:
                    netrom_access.append(app)
        
        # Applications: filter out NetRom aliases
        applications = []
        for app in all_apps:
            # Skip NetRom entries (contain ":" or "}")
            # Skip call-SSID patterns (like "2PGN-11")
            if ':' not in app and '}' not in app and '-' not in app:
                applications.append(app)
        
        # Get frequencies from ports (with band color)
        frequencies = []
        hf_ports = []  # Track HF port descriptions
        for port in node_data.get('ports', []):
            port_type = port.get('port_type', 'rf' if port.get('is_rf') else 'ip')
            if port_type == 'hf':
                # HF port - track description even without frequency
                desc = port.get('description', '')
                if desc and desc not in hf_ports:
                    hf_ports.append(desc)
            elif port.get('is_rf') and port.get('frequency'):
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
        
        # Calculate RF/IP neighbor counts for this node
        routes = node_data.get('routes', {})
        
        # Check if this is an incomplete crawl (empty routes)
        if not routes:
            # Use inbound neighbors (who has routes TO this node)
            if callsign in inbound_neighbors:
                rf_neighbor_count = len(inbound_neighbors[callsign]['rf'])
                ip_neighbor_count = len(inbound_neighbors[callsign]['ip'])
                incomplete_crawl = True
            else:
                rf_neighbor_count = 0
                ip_neighbor_count = 0
                incomplete_crawl = False
        else:
            # Normal: use this node's routes table
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
            incomplete_crawl = False
        
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
            'note': node_data.get('note', ''),  # Sysop-added note
            'netrom_access': netrom_access,
            'applications': applications,
            'frequencies': frequencies,
            'hf_ports': hf_ports,  # HF access methods (VARA, ARDOP, etc.)
            'ssids': ssids,
            'rf_neighbors': rf_neighbor_count,
            'ip_neighbors': ip_neighbor_count,
            'incomplete_crawl': incomplete_crawl
        })
    
    # Build map connections from routes tables (quality > 0)
    # Connections display base callsigns but connect nodes via their SSIDs
    # Draw separate lines for each band nodes connect on
    node_coords = {}
    for node in map_nodes:
        node_coords[node['callsign']] = (node['lat'], node['lon'])
    
    # Build port->info lookup for each node (frequency and port_type)
    node_port_info = {}  # {callsign: {port_num: {'frequency': MHz, 'port_type': 'rf'|'hf'|'ip'}}}
    for callsign, node_data in nodes.items():
        node_port_info[callsign] = {}
        for port in node_data.get('ports', []):
            port_num = port.get('number')
            if port_num is not None:
                node_port_info[callsign][port_num] = {
                    'frequency': port.get('frequency'),
                    'port_type': port.get('port_type', 'rf' if port.get('is_rf') else 'ip'),
                    'is_rf': port.get('is_rf', False)
                }
    
    # Legacy lookup for backward compatibility
    node_port_freqs = {}  # {callsign: {port_num: frequency}}
    for callsign, node_data in nodes.items():
        node_port_freqs[callsign] = {}
        for port in node_data.get('ports', []):
            if port.get('is_rf') and port.get('frequency'):
                node_port_freqs[callsign][port.get('number')] = port['frequency']
    
    # Build heard_on_ports lookup: {callsign: {neighbor_base: [port_nums]}}
    node_heard_ports = {}
    for callsign, node_data in nodes.items():
        node_heard_ports[callsign] = {}
        for entry in node_data.get('heard_on_ports', []):
            if len(entry) == 2:
                neighbor, port_num = entry
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                if neighbor_base not in node_heard_ports[callsign]:
                    node_heard_ports[callsign][neighbor_base] = []
                if port_num not in node_heard_ports[callsign][neighbor_base]:
                    node_heard_ports[callsign][neighbor_base].append(port_num)
    
    # Track connections by node pair AND band to draw multiple lines
    # Store tuples of (frequency, port_type) for each connection
    seen_connections = {}  # {(from, to): set of (frequency, port_type) tuples}
    
    for callsign, node_data in nodes.items():
        # Skip nodes without coordinates
        if callsign not in node_coords:
            continue
        
        from_lat, from_lon = node_coords[callsign]
        routes = node_data.get('routes', {})
        callsign_base = callsign.split('-')[0] if '-' in callsign else callsign
        
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
            
            # Check reciprocal route - neighbor must also have quality > 0 route back
            # This prevents drawing connections where one sysop has blocked the route
            neighbor_routes = nodes[neighbor_key].get('routes', {})
            if callsign_base not in neighbor_routes or neighbor_routes[callsign_base] == 0:
                continue  # Skip if neighbor has no route back or has blocked it
            
            to_lat, to_lon = node_coords[neighbor_key]
            
            # Connection key for deduplication (sorted pair)
            conn_key = tuple(sorted([callsign, neighbor_key]))
            if conn_key not in seen_connections:
                seen_connections[conn_key] = set()
            
            # Get port info from BOTH directions (A heard B on port X, B heard A on port Y)
            # This node's view: what port did we hear neighbor on?
            heard_ports_this = node_heard_ports.get(callsign, {}).get(neighbor_base, [])
            # Neighbor's view: what port did neighbor hear us on?
            neighbor_base_key = neighbor_key.split('-')[0] if '-' in neighbor_key else neighbor_key
            heard_ports_neighbor = node_heard_ports.get(neighbor_key, {}).get(callsign_base, [])
            
            # Collect (frequency, port_type) tuples from both directions
            links_found = set()
            for port_num in heard_ports_this:
                port_info = node_port_info.get(callsign, {}).get(port_num, {})
                freq = port_info.get('frequency')
                port_type = port_info.get('port_type', 'rf')
                if freq:
                    links_found.add((freq, port_type))
                elif port_type == 'ip':
                    # IP link without frequency - still record it
                    links_found.add((None, 'ip'))
                elif port_type == 'hf':
                    # HF link without frequency (VARA/ARDOP/PACTOR) - record it
                    links_found.add((None, 'hf'))
            for port_num in heard_ports_neighbor:
                port_info = node_port_info.get(neighbor_key, {}).get(port_num, {})
                freq = port_info.get('frequency')
                port_type = port_info.get('port_type', 'rf')
                if freq:
                    links_found.add((freq, port_type))
                elif port_type == 'ip':
                    links_found.add((None, 'ip'))
                elif port_type == 'hf':
                    links_found.add((None, 'hf'))
            
            # If no MHEARD port info, fall back to first RF port (legacy behavior)
            if not links_found:
                for port in node_data.get('ports', []):
                    if port.get('is_rf') and port.get('frequency'):
                        port_type = port.get('port_type', 'rf')
                        links_found.add((port['frequency'], port_type))
                        break
            
            # Add new links we haven't drawn yet for this pair
            for link_info in links_found:
                if link_info not in seen_connections[conn_key]:
                    seen_connections[conn_key].add(link_info)
    
    # Now build map_connections from seen_connections
    for conn_key, link_infos in seen_connections.items():
        from_call, to_call = conn_key
        if from_call not in node_coords or to_call not in node_coords:
            continue
        
        from_lat, from_lon = node_coords[from_call]
        to_lat, to_lon = node_coords[to_call]
        
        for freq, port_type in link_infos:
            # Determine color based on link type
            if port_type == 'ip':
                color = '#00BCD4'  # Cyan for IP links
            elif port_type == 'hf':
                color = '#FFEB3B'  # Yellow for HF links
            else:
                color = get_band_color(freq)  # Normal band color for RF
            
            map_connections.append({
                'from': from_call,
                'to': to_call,
                'from_lat': from_lat,
                'from_lon': from_lon,
                'to_lat': to_lat,
                'to_lon': to_lon,
                'color': color,
                'frequency': freq,
                'link_type': port_type  # 'rf', 'hf', or 'ip'
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
        .popup-content .hf-access { color: #FFC107; font-weight: 500; }
        .popup-content .note { background: #fff3cd; padding: 6px 8px; border-radius: 4px; margin: 8px 0; font-style: italic; color: #856404; border-left: 3px solid #ffc107; }
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
            
            // Line style based on link type
            var lineStyle = {
                color: conn.color,
                weight: 2,
                opacity: 0.7
            };
            
            // IP links: dotted cyan line
            if (conn.link_type === 'ip') {
                lineStyle.dashArray = '5, 5';
                lineStyle.opacity = 0.6;
            }
            // HF links: dashed line
            else if (conn.link_type === 'hf') {
                lineStyle.dashArray = '10, 5';
            }
            
            var line = L.polyline([
                [conn.from_lat, conn.from_lon],
                [conn.to_lat, conn.to_lon]
            ], lineStyle).addTo(map);
            
            var freq = conn.frequency ? conn.frequency + ' MHz' : (conn.link_type === 'ip' ? 'Internet' : 'Unknown');
            var linkType = conn.link_type ? ' (' + conn.link_type.toUpperCase() + ')' : '';
            line.bindTooltip(conn.from + ' ↔ ' + conn.to + '<br>' + freq + linkType);
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
            
            // Show note first if present (important info)
            if (node.note) {
                popup += '<div class="note">' + node.note + '</div>';
            }
            
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
            
            if (node.hf_ports && node.hf_ports.length > 0) {
                popup += '<p><span class="label">HF Access:</span><br>';
                popup += '<span class="hf-access">' + node.hf_ports.join(', ') + '</span></p>';
            }
            
            if (node.netrom_access && node.netrom_access.length > 0) {
                popup += '<p><span class="label">NetRom Access:</span><br>';
                // First entry is primary alias (bold)
                if (node.netrom_access.length > 0) {
                    popup += '<span class="apps"><strong>' + node.netrom_access[0] + '</strong>';
                    if (node.netrom_access.length > 1) {
                        popup += ', ' + node.netrom_access.slice(1).join(', ');
                    }
                    popup += '</span></p>';
                }
            }
            
            if (node.applications && node.applications.length > 0) {
                var apps = node.applications.slice(0, 10);  // Limit display
                popup += '<p><span class="label">Applications:</span><br>' + 
                         '<span class="apps">' + apps.join(', ') + '</span></p>';
            }
            
            var neighborLabel = node.incomplete_crawl ? ' (from network)' : '';
            popup += '<p><span class="label">RF Neighbors:</span> ' + node.rf_neighbors + neighborLabel + '<br>' +
                     '<span class="label">IP Neighbors:</span> ' + node.ip_neighbors + neighborLabel + '</p>';
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
    # Build inbound neighbor map for incomplete crawls (nodes with empty routes tables)
    inbound_neighbors = {}
    for node_call, node_data in nodes.items():
        routes = node_data.get('routes', {})
        heard_on_ports = node_data.get('heard_on_ports', [])
        ports_data = node_data.get('ports', [])
        
        # Build set of neighbors heard on RF ports for this node
        rf_heard = set()
        for entry in heard_on_ports:
            if len(entry) == 2:
                neighbor, port_num = entry
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                for port in ports_data:
                    if port.get('number') == port_num and port.get('is_rf'):
                        rf_heard.add(neighbor_base)
                        break
        
        # For each route FROM this node, track it as inbound TO neighbor
        for neighbor_base, quality in routes.items():
            if quality > 0:
                # Find neighbor key - could be base or with SSID
                neighbor_key = None
                if neighbor_base in nodes:
                    neighbor_key = neighbor_base
                else:
                    for node_key in nodes.keys():
                        if node_key.startswith(neighbor_base + '-'):
                            neighbor_key = node_key
                            break
                
                if neighbor_key:
                    if neighbor_key not in inbound_neighbors:
                        inbound_neighbors[neighbor_key] = {'rf': set(), 'ip': set()}
                    
                    # Categorize as RF (heard on RF port) or IP
                    if neighbor_base in rf_heard:
                        inbound_neighbors[neighbor_key]['rf'].add(node_call)
                    else:
                        inbound_neighbors[neighbor_key]['ip'].add(node_call)
    
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
        hf_ports = []  # Track HF port descriptions
        for port in node_data.get('ports', []):
            port_type = port.get('port_type', 'rf' if port.get('is_rf') else 'ip')
            if port_type == 'hf':
                # HF port - track description
                desc = port.get('description', '')
                if desc and desc not in hf_ports:
                    hf_ports.append(desc)
            elif port.get('is_rf') and port.get('frequency'):
                freq_list.append("{} MHz".format(port['frequency']))
        
        # Extract base callsign for display (without SSID)
        display_call = callsign.split('-')[0] if '-' in callsign else callsign
        
        # Calculate RF/IP neighbor counts for this node (from ROUTES only)
        routes = node_data.get('routes', {})
        heard_on_ports = node_data.get('heard_on_ports', [])
        ports_data = node_data.get('ports', [])
        
        # Check for incomplete crawl (empty routes table)
        incomplete_crawl = False
        if not routes:
            # Use inbound neighbor counts (who has routes TO this node)
            if callsign in inbound_neighbors:
                rf_neighbor_count = len(inbound_neighbors[callsign]['rf'])
                ip_neighbor_count = len(inbound_neighbors[callsign]['ip'])
                incomplete_crawl = True
            else:
                # No routes TO or FROM this node
                rf_neighbor_count = 0
                ip_neighbor_count = 0
                incomplete_crawl = True
        else:
            # Normal: use this node's routes table
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
            'hf_ports': hf_ports,  # HF access methods
            'type': node_data.get('type', 'Unknown'),
            'note': node_data.get('note', ''),  # Sysop-added note
            'rf_neighbors': rf_neighbor_count,
            'ip_neighbors': ip_neighbor_count,
            'incomplete_crawl': incomplete_crawl
        })
    
    # Build map connections from routes tables (quality > 0)
    # Draw separate lines for each band nodes connect on
    node_coords = {}
    for node in map_nodes:
        node_coords[node['callsign']] = (node['lat'], node['lon'])
    
    # Build port->frequency lookup for each node
    node_port_freqs = {}  # {callsign: {port_num: frequency}}
    for callsign, node_data in nodes.items():
        node_port_freqs[callsign] = {}
        for port in node_data.get('ports', []):
            if port.get('is_rf') and port.get('frequency'):
                node_port_freqs[callsign][port.get('number')] = port['frequency']
    
    # Build heard_on_ports lookup: {callsign: {neighbor_base: [port_nums]}}
    node_heard_ports = {}
    for callsign, node_data in nodes.items():
        node_heard_ports[callsign] = {}
        for entry in node_data.get('heard_on_ports', []):
            if len(entry) == 2:
                neighbor, port_num = entry
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                if neighbor_base not in node_heard_ports[callsign]:
                    node_heard_ports[callsign][neighbor_base] = []
                if port_num not in node_heard_ports[callsign][neighbor_base]:
                    node_heard_ports[callsign][neighbor_base].append(port_num)
    
    # Track connections by node pair AND band
    seen_connections = {}  # {(from, to): set of frequencies}
    
    for callsign, node_data in nodes.items():
        if callsign not in node_coords:
            continue
        
        from_lat, from_lon = node_coords[callsign]
        routes = node_data.get('routes', {})
        callsign_base = callsign.split('-')[0] if '-' in callsign else callsign
        
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
            
            # Check reciprocal route - neighbor must also have quality > 0 route back
            # This prevents drawing connections where one sysop has blocked the route
            neighbor_routes = nodes[neighbor_key].get('routes', {})
            if callsign_base not in neighbor_routes or neighbor_routes[callsign_base] == 0:
                continue  # Skip if neighbor has no route back or has blocked it
            
            to_lat, to_lon = node_coords[neighbor_key]
            
            conn_key = tuple(sorted([callsign, neighbor_key]))
            if conn_key not in seen_connections:
                seen_connections[conn_key] = set()
            
            # Get frequencies from BOTH directions
            heard_ports_this = node_heard_ports.get(callsign, {}).get(neighbor_base, [])
            neighbor_base_key = neighbor_key.split('-')[0] if '-' in neighbor_key else neighbor_key
            heard_ports_neighbor = node_heard_ports.get(neighbor_key, {}).get(callsign_base, [])
            
            freqs_found = set()
            for port_num in heard_ports_this:
                freq = node_port_freqs.get(callsign, {}).get(port_num)
                if freq:
                    freqs_found.add(freq)
            for port_num in heard_ports_neighbor:
                freq = node_port_freqs.get(neighbor_key, {}).get(port_num)
                if freq:
                    freqs_found.add(freq)
            
            # Fallback to first RF port if no MHEARD port info
            if not freqs_found:
                for port in node_data.get('ports', []):
                    if port.get('is_rf') and port.get('frequency'):
                        freqs_found.add(port['frequency'])
                        break
            
            for freq in freqs_found:
                if freq not in seen_connections[conn_key]:
                    seen_connections[conn_key].add(freq)
    
    # Build map_connections from seen_connections
    for conn_key, frequencies in seen_connections.items():
        from_call, to_call = conn_key
        if from_call not in node_coords or to_call not in node_coords:
            continue
        
        from_lat, from_lon = node_coords[from_call]
        to_lat, to_lon = node_coords[to_call]
        
        for freq in frequencies:
            map_connections.append({
                'from': from_call,
                'to': to_call,
                'from_lat': from_lat,
                'from_lon': from_lon,
                'to_lat': to_lat,
                'to_lon': to_lon,
                'color': get_band_color(freq),
                'frequency': freq
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
    svg_lines.append('    .connection { stroke-opacity: 0.6; transition: stroke-opacity 0.2s, stroke-width 0.2s; cursor: help; }')
    svg_lines.append('    .connection:hover { stroke-opacity: 1.0; stroke-width: 4; }')
    svg_lines.append('    .connection.highlighted { stroke-opacity: 1.0; stroke-width: 4; }')
    svg_lines.append('    .connection.dimmed { stroke-opacity: 0.15; }')
    svg_lines.append('    .legend text { font-family: sans-serif; font-size: 11px; }')
    svg_lines.append('    .title { font-family: sans-serif; font-size: 16px; font-weight: bold; }')
    svg_lines.append('    .state { fill: #e8e8e8; stroke: #999; stroke-width: 1; }')
    svg_lines.append('    .county { fill: none; stroke: #bbb; stroke-width: 0.5; stroke-dasharray: 2,2; }')
    svg_lines.append('    .state-label { font-family: sans-serif; font-size: 12px; fill: #666; }')
    svg_lines.append('    #tooltip { position: fixed; background: rgba(0,0,0,0.75); color: #fff; padding: 8px 12px; border-radius: 4px; font-size: 12px; z-index: 1000; white-space: pre-wrap; max-width: 250px; pointer-events: none; display: none; }')
    svg_lines.append('  </style>')
    svg_lines.append('  <script><![CDATA[')
    svg_lines.append('    var tooltip = null;')
    svg_lines.append('    function showTooltip(e, text) {')
    svg_lines.append('      if (!tooltip) { tooltip = document.createElement("div"); tooltip.id = "tooltip"; document.body.appendChild(tooltip); }')
    svg_lines.append('      tooltip.innerHTML = text.split("\\\\n").join("<br>");')
    svg_lines.append('      tooltip.style.left = (e.clientX + 10) + "px";')
    svg_lines.append('      tooltip.style.top = (e.clientY + 10) + "px";')
    svg_lines.append('      tooltip.style.display = "block";')
    svg_lines.append('    }')
    svg_lines.append('    function hideTooltip() { if (tooltip) tooltip.style.display = "none"; }')
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
        link_type = conn.get('link_type', 'rf')
        
        # Line style based on link type
        style_attrs = 'stroke="{}" stroke-width="2"'.format(conn['color'])
        if link_type == 'ip':
            style_attrs += ' stroke-dasharray="5,5"'  # Dotted for IP
            freq_label = "Internet (IP)"
        elif link_type == 'hf':
            style_attrs += ' stroke-dasharray="10,5"'  # Dashed for HF
            freq_label = "{} MHz (HF)".format(conn['frequency']) if conn.get('frequency') else "HF"
        else:
            freq_label = "{} MHz".format(conn['frequency']) if conn.get('frequency') else "Unknown"
        
        tooltip_text = "{} ↔ {}\\n{}".format(conn['from'], conn['to'], freq_label)
        svg_lines.append('    <line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" {} class="connection" data-from="{}" data-to="{}" onmousemove="showTooltip(event, {});" onmouseleave="hideTooltip();">'.format(
            x1, y1, x2, y2, style_attrs, conn['from'], conn['to'], repr(tooltip_text)))
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
        if node.get('hf_ports'):
            tooltip_lines.append("HF Access: {}".format(", ".join(node['hf_ports'])))
        
        # Add neighbor counts with label if from network (incomplete crawl)
        neighbor_label = ' (from network)' if node.get('incomplete_crawl', False) else ''
        tooltip_lines.append("RF Neighbors: {}{}".format(node['rf_neighbors'], neighbor_label))
        tooltip_lines.append("IP Neighbors: {}{}".format(node['ip_neighbors'], neighbor_label))
        
        # Add note if present
        if node.get('note'):
            tooltip_lines.append("Note: {}".format(node['note']))
        
        tooltip = "&#10;".join(tooltip_lines)  # &#10; is XML newline
        
        # Convert tooltip lines to string for JavaScript
        tooltip_str = "\\n".join(tooltip_lines)
        svg_lines.append('    <g class="node" transform="translate({:.1f},{:.1f})" onmouseenter="highlightNode(\'{}\');" onmousemove="showTooltip(event, {});" onmouseleave="unhighlightAll(); hideTooltip();">'.format(x, y, node['callsign'], repr(tooltip_str)))
        svg_lines.append('      <circle r="6" fill="{}" stroke="#333" stroke-width="1.5">'.format(color))
        svg_lines.append('      </circle>')
        svg_lines.append('      <text x="0" y="18" text-anchor="middle">{}</text>'.format(node['display_call']))
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
    """Display help information in man page format."""
    print("NAME")
    print("       nodemap-html - Generate visual maps from nodemap.json")
    print("")
    print("SYNOPSIS")
    print("       nodemap-html.py [OPTIONS]")
    print("")
    print("VERSION")
    print("       {}".format(__version__))
    print("")
    print("DESCRIPTION")
    print("       Generates interactive HTML and static SVG maps from nodemap.json")
    print("       data produced by nodemap.py. HTML maps require internet for tiles;")
    print("       SVG maps are fully offline with state/county boundaries.")
    print("")
    print("OPTIONS")
    print("       -a, --all")
    print("              Generate both HTML and SVG maps. This is the default if no")
    print("              output format is specified.")
    print("")
    print("       -t, --html [FILE]")
    print("              Generate interactive HTML map. Default: nodemap.html.")
    print("")
    print("       -s, --svg [FILE]")
    print("              Generate static SVG map. Default: nodemap.svg.")
    print("")
    print("       -i, --input FILE")
    print("              Input JSON file. Default: nodemap.json.")
    print("")
    print("       -o, --output-dir DIR")
    print("              Save files to directory. Prompts for ../linbpq/HTML if found.")
    print("")
    print("       -h, --help, /?")
    print("              Show this help message.")
    print("")
    print("EXAMPLES")
    print("       nodemap-html.py -a")
    print("              Generate both HTML and SVG maps.")
    print("")
    print("       nodemap-html.py -t network.html")
    print("              Generate HTML map with custom filename.")
    print("")
    print("       nodemap-html.py -s -i data.json")
    print("              Generate SVG from custom input file.")
    print("")
    print("OUTPUT FILES")
    print("       nodemap.html")
    print("              Interactive Leaflet map. REQUIRES INTERNET for map tiles.")
    print("              Click nodes for detailed info. Color-coded by frequency band.")
    print("")
    print("       nodemap.svg")
    print("              Static vector map. FULLY OFFLINE - no dependencies.")
    print("              Hover nodes for basic info. Can be embedded in HTML pages.")
    print("")
    print("BPQ WEB SERVER SETUP")
    print("       1. Copy nodemap.html to your BPQ HTML directory:")
    print("          cp nodemap.html ~/linbpq/HTML/")
    print("")
    print("       2. Add link in your BPQ web interface index.html:")
    print('          <a href="nodemap.html">Network Map</a>')
    print("")
    print("       3. Or add custom page in bpq32.cfg (HTML section):")
    print("          FILE=/HTML/nodemap.html,nodemap.html")
    print("")
    print("SEE ALSO")
    print("       nodemap.py - BPQ packet radio network topology crawler")


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
        
        if (arg == '--input' or arg == '-i') and i + 1 < len(args):
            input_file = args[i + 1]
            i += 2
        elif (arg == '--output-dir' or arg == '-o') and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif arg == '--html' or arg == '-t':
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                html_file = args[i + 1]
                i += 2
            else:
                html_file = 'nodemap.html'
                i += 1
        elif arg == '--svg' or arg == '-s':
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                svg_file = args[i + 1]
                i += 2
            else:
                svg_file = 'nodemap.svg'
                i += 1
        elif arg == '--all' or arg == '-a':
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
