#!/usr/bin/env python3
"""
Node Map Crawler for BPQ Packet Radio Networks
-----------------------------------------------
Automatically crawls through packet radio nodes to discover network topology.
Connects to nodes, retrieves MHEARD lists and INFO, and builds a map of
node connectivity for visualization.

Features:
- Discovers nodes via MHEARD lists on RF ports
- Extracts location data from INFO command
- Traverses network breadth-first to avoid loops
- Uses ROUTES command to find optimal paths
- Handles BPQ, FBB, and JNOS nodes
- Exports to JSON and CSV formats
- Reads BPQ telnet port from bpq32.cfg automatically
- Skips IP-based ports (focuses on RF connectivity)

Network Resources:
- Maine Packet Network: https://www.mainepacketradio.org/
- Network Map: https://n1xp.com/HAM/content/pkt/MEPktNtMap.pdf
- Station Map: https://n1xp.com/HAM/content/pkt/MEPktStMap.pdf
- BPQ Commands: https://cheatography.com/gcremerius/cheat-sheets/bpq-user-and-sysop-commands/

Author: Brad Brown KC1JMH
Date: January 2026
Version: 1.1.2
"""

__version__ = '1.1.2'

import sys
import telnetlib
import time
import json
import csv
import re
import os
from collections import deque

# Check Python version
if sys.version_info < (3, 5):
    print("Error: This script requires Python 3.5 or later.")
    print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ))
    sys.exit(1)


class NodeCrawler:
    """Crawls BPQ packet radio network to discover topology."""
    
    # Valid amateur radio callsign pattern: 1-2 prefix chars, digit, 1-3 suffix chars, optional -SSID
    CALLSIGN_PATTERN = re.compile(r'^[A-Z]{1,2}\d[A-Z]{1,3}(?:-\d{1,2})?$', re.IGNORECASE)
    
    def __init__(self, host='localhost', port=None, callsign=None, max_hops=10, username=None, password=None, debug=False):
        """
        Initialize crawler.
        
        Args:
            host: BPQ node hostname (default: localhost)
            port: BPQ telnet port (auto-detected if None)
            callsign: Your callsign for login (auto-detected if None)
            max_hops: Maximum hops to traverse (default: 10)
            username: Telnet login username (default: None, prompts when needed)
            password: Telnet login password (default: None, prompts when needed)
            debug: Enable debug output (default: False)
        """
        self.host = host
        self.port = port if port else self._find_bpq_port()
        self.callsign = callsign if callsign else self._find_callsign()
        self.max_hops = max_hops
        self.username = username  # None means prompt when needed
        self.password = password  # None means prompt when needed
        self.debug = debug
        self.visited = set()  # Nodes we've already crawled
        self.failed = set()  # Nodes that failed connection
        self.nodes = {}  # Node data: {callsign: {info, neighbors, location, type}}
        self.connections = []  # List of [node1, node2, port] connections
        self.routes = {}  # Best routes to nodes: {callsign: [path]}
        self.shortest_paths = {}  # Shortest discovered path to each node: {callsign: [path]}
        self.netrom_ssid_map = {}  # Global NetRom SSID mapping: {base_callsign: 'CALLSIGN-SSID'}
        self.queue = deque()  # BFS queue for crawling
        self.timeout = 10  # Telnet timeout in seconds
        
    def _find_bpq_port(self):
        """Find BPQ telnet port from bpq32.cfg (Telnet Server port only)."""
        config_paths = [
            '../linbpq/bpq32.cfg',          # Script in utilities/ or apps/, cfg in linbpq/
            '/home/pi/linbpq/bpq32.cfg',    # Standard RPi location
            '/home/ect/linbpq/bpq32.cfg',   # Alternative user
            'bpq32.cfg',                    # Same directory as script
            'linbpq/bpq32.cfg'              # Script in parent, cfg in linbpq/
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        in_telnet_port = False
                        for line in f:
                            line_upper = line.upper()
                            # Start of Telnet port section
                            if 'DRIVER=TELNET' in line_upper or 'ID=TELNET SERVER' in line_upper:
                                in_telnet_port = True
                            # End of port section
                            elif 'ENDPORT' in line_upper:
                                in_telnet_port = False
                            # Look for TCPPORT only in Telnet port section
                            elif in_telnet_port:
                                match = re.search(r'TCPPORT\s*=\s*(\d+)', line, re.IGNORECASE)
                                if match:
                                    port = int(match.group(1))
                                    print("Found BPQ telnet port: {}".format(port))
                                    return port
                except Exception as e:
                    print("Error reading {}: {}".format(path, e))
        
        # Default to 8010 if not found
        print("BPQ port not found in config, using default: 8010")
        return 8010
    
    @staticmethod
    def _is_valid_callsign(callsign):
        """Validate callsign format: 1-2 prefix, digit, 1-3 suffix, optional -SSID."""
        if not callsign:
            return False
        return NodeCrawler.CALLSIGN_PATTERN.match(callsign.upper()) is not None
    
    def _find_callsign(self):
        """Extract callsign from bpq32.cfg."""
        config_paths = [
            '../linbpq/bpq32.cfg',          # Script in utilities/ or apps/, cfg in linbpq/
            '/home/pi/linbpq/bpq32.cfg',    # Standard RPi location
            '/home/ect/linbpq/bpq32.cfg',   # Alternative user
            'bpq32.cfg',                    # Same directory as script
            'linbpq/bpq32.cfg'              # Script in parent, cfg in linbpq/
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        for line in f:
                            # Look for NODECALL=WS1EC or similar
                            match = re.search(r'NODECALL\s*=\s*(\w+)', line, re.IGNORECASE)
                            if match:
                                call = match.group(1)
                                print("Found node callsign: {}".format(call))
                                return call
                except Exception as e:
                    print("Error reading {}: {}".format(path, e))
        
        return None
    
    def _connect_to_node(self, path=[]):
        """
        Connect to a node via telnet.
        
        Args:
            path: List of callsigns to connect through (empty for local node)
            
        Returns:
            telnetlib.Telnet object or None
        """
        try:
            # Show progress for local connections
            if not path:
                print("  Connecting to localhost:{}...".format(self.port))
            
            tn = telnetlib.Telnet(self.host, self.port, self.timeout)
            time.sleep(1)
            
            # Always handle authentication when connecting to localhost
            # Read initial response (may be login prompt or direct prompt)
            initial = tn.read_very_eager().decode('ascii', errors='ignore')
            
            # Check if login is required
            if 'user:' in initial.lower() or 'callsign:' in initial.lower():
                print("  Authentication required...")
                
                # Prompt for username if not provided
                if not self.username:
                    self.username = raw_input("    Username: ") if sys.version_info[0] < 3 else input("    Username: ")
                
                # Send username
                tn.write("{}\r".format(self.username).encode('ascii'))
                time.sleep(0.5)
                
                # Check for password prompt
                response = tn.read_very_eager().decode('ascii', errors='ignore')
                if 'password:' in response.lower():
                    # Prompt for password if not provided
                    if self.password is None:
                        import getpass
                        self.password = getpass.getpass("    Password: ")
                    
                    # Send password
                    tn.write("{}\r".format(self.password).encode('ascii'))
                    time.sleep(0.5)
            
            # Wait for command prompt
            print("  Waiting for node prompt...")
            tn.read_until(b'>', timeout=5)
            print("  Connected to local node")
            
            # If no path, just return (connecting to local node)
            if not path:
                return tn
            
            # Connect through nodes in path (for multi-hop or direct connections from local node)
            for i, callsign in enumerate(path):
                # Determine full callsign with NetRom SSID from global map
                full_callsign = self.netrom_ssid_map.get(callsign, callsign)
                
                # Get alias if available for better messages
                alias = None
                for node_data in self.nodes.values():
                    aliases = node_data.get('aliases', {})
                    for a, cs in aliases.items():
                        if cs.split('-')[0] == callsign:
                            alias = a
                            break
                    if alias:
                        break
                
                # Use NetRom CONNECT syntax: C CALLSIGN-SSID
                cmd = "C {}\r".format(full_callsign).encode('ascii')
                if self.debug:
                    if alias:
                        print("    DEBUG: Issuing command: C {} (alias: {}, hop {}/{})".format(full_callsign, alias, i+1, len(path)))
                    else:
                        print("    DEBUG: Issuing command: C {} (hop {}/{})".format(full_callsign, i+1, len(path)))
                tn.write(cmd)
                
                # Wait for connection response (up to 30 seconds for RF)
                start_time = time.time()
                connected = False
                response = ""
                
                while time.time() - start_time < 30:
                    try:
                        chunk = tn.read_some()
                        response += chunk.decode('ascii', errors='ignore')
                        
                        # Check for connection success
                        if 'CONNECTED' in response.upper():
                            connected = True
                            print("  Connected to {}".format(callsign))
                            break
                        
                        # Check for failure patterns
                        if any(x in response.upper() for x in ['BUSY', 'FAILED', 'NO ROUTE', 
                                                                 'TIMEOUT', 'DISCONNECTED',
                                                                 'NOT HEARD', 'NO ANSWER']):
                            print("  Connection to {} failed: {}".format(
                                callsign, 
                                response.strip().split('\n')[-1]
                            ))
                            tn.close()
                            return None
                        
                        time.sleep(0.5)
                        
                    except EOFError:
                        print("  Connection lost to {}".format(callsign))
                        tn.close()
                        return None
                
                if not connected:
                    print("  Connection to {} timed out (no CONNECTED response)".format(callsign))
                    tn.close()
                    return None
                
                # Wait for prompt after connection
                time.sleep(1)
            
            return tn
            
        except Exception as e:
            print("Error connecting: {}".format(e))
            return None
    
    def _send_command(self, tn, command, wait_for=b'>', timeout=5):
        """Send command and read response with timeout protection."""
        try:
            if self.debug:
                print("    DEBUG: Sending command: {}".format(command))
            tn.write("{}\r".format(command).encode('ascii'))
            # Short delay for command to be received
            time.sleep(0.5)
            response = tn.read_until(wait_for, timeout=timeout)
            decoded = response.decode('ascii', errors='ignore')
            if self.debug:
                print("    DEBUG: Response ({} bytes):".format(len(decoded)))
                print("    {}".format(decoded[:200] if len(decoded) > 200 else decoded))
            return decoded
        except EOFError:
            print("    Connection lost during {} command".format(command))
            return ""
        except:
            # Timeout or other error - try to get whatever is buffered
            try:
                buffered = tn.read_very_eager().decode('ascii', errors='ignore')
                if not buffered:
                    print("    Timeout on {} command ({}s)".format(command, timeout))
                return buffered
            except:
                return ""
    
    def _parse_mheard(self, output):
        """
        Parse MHEARD output to extract callsigns and ports.
        
        Returns:
            List of (callsign, port) tuples for RF ports only
        """
        heard = []
        lines = output.split('\n')
        
        for line in lines:
            # Look for lines like: "KC1JMH   Port 2  ..."
            match = re.search(r'(\w+(?:-\d+)?)\s+Port\s+(\d+)', line)
            if match:
                full_callsign = match.group(1)
                callsign = full_callsign.split('-')[0]  # Strip SSID for base call
                port = int(match.group(2))
                
                # Validate callsign format
                if not self._is_valid_callsign(callsign):
                    continue
                
                # Skip if already in list
                if callsign not in [c for c, p in heard]:
                    heard.append((callsign, port))
        
        return heard
    
    def _filter_rf_ports(self, heard_list, ports_output):
        """
        Filter heard list to only include RF ports (not Telnet/IP).
        
        Args:
            heard_list: List of (callsign, port) tuples
            ports_output: Output from PORTS command
            
        Returns:
            Filtered list of (callsign, port) tuples
        """
        # Parse PORTS to identify non-RF ports
        ip_ports = set()
        lines = ports_output.split('\n')
        
        for line in lines:
            # Look for Telnet, TCPIP, etc.
            if re.search(r'Port\s+(\d+).*(?:Telnet|TCPIP|IP)', line, re.IGNORECASE):
                match = re.search(r'Port\s+(\d+)', line)
                if match:
                    ip_ports.add(int(match.group(1)))
        
        # Filter out IP-based ports
        return [(call, port) for call, port in heard_list if port not in ip_ports]
    
    def _parse_info(self, output):
        """
        Extract location from INFO output.
        
        Returns:
            Dictionary with location data (lat, lon, grid, city, state)
        """
        location = {}
        
        # Look for common location patterns
        # Grid square: FN43xx
        grid_match = re.search(r'\b([A-R]{2}\d{2}[a-x]{2})\b', output, re.IGNORECASE)
        if grid_match:
            location['grid'] = grid_match.group(1).upper()
        
        # Lat/Lon patterns
        lat_match = re.search(r'(\d{2}[.\d]*)\s*[NnSs]', output)
        lon_match = re.search(r'(\d{2,3}[.\d]*)\s*[WwEe]', output)
        if lat_match and lon_match:
            location['lat'] = lat_match.group(0)
            location['lon'] = lon_match.group(0)
        
        # City, State pattern
        city_state = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+([A-Z]{2})', output)
        if city_state:
            location['city'] = city_state.group(1)
            location['state'] = city_state.group(2)
        
        return location
    
    def _detect_node_type(self, info_output, prompt_chars):
        """
        Detect node software type (BPQ, FBB, JNOS).
        
        Args:
            info_output: Output from INFO command
            prompt_chars: Last characters received (prompt indicators)
            
        Returns:
            String: 'BPQ', 'FBB', 'JNOS', or 'Unknown'
        """
        info_upper = info_output.upper()
        
        if 'BPQ' in info_upper or 'G8BPQ' in info_upper:
            return 'BPQ'
        elif 'FBB' in info_upper or 'F6FBB' in info_upper:
            return 'FBB'
        elif 'JNOS' in info_upper or 'NOS' in info_upper:
            return 'JNOS'
        elif '>' in prompt_chars:
            return 'BPQ'  # BPQ uses > prompt
        elif ':' in prompt_chars:
            return 'FBB'  # FBB uses : prompt
        
        return 'Unknown'
    
    def _load_existing_data(self, filename):
        """Load existing nodemap data if available."""
        if not os.path.exists(filename):
            return None
        
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print("Warning: Could not load {}: {}".format(filename, e))
            return None
    
    def _parse_ports(self, output):
        """
        Parse PORTS output to extract port details.
        
        Returns:
            List of port dictionaries with number, frequency, speed, type
        """
        ports = []
        lines = output.split('\n')
        
        for line in lines:
            # Look for lines like: "  1 433.300 MHz 1200 BAUD"
            # or "  8 AX/IP/UDP" or "  9 Telnet Server"
            match = re.search(r'^\s*(\d+)\s+(.+?)(?:\s+@\s+|\s+at\s+)?(\d+)?\s*(?:b/s|BAUD)?', line, re.IGNORECASE)
            if match:
                port_num = int(match.group(1))
                description = match.group(2).strip()
                speed = match.group(3) if match.group(3) else None
                
                # Determine if it's RF or IP-based
                is_rf = not any(x in description.upper() for x in ['TELNET', 'TCP', 'IP', 'UDP'])
                
                ports.append({
                    'number': port_num,
                    'description': description,
                    'speed': int(speed) if speed else None,
                    'is_rf': is_rf
                })
        
        return ports
    
    def _parse_nodes_aliases(self, output):
        """
        Parse NODES output to get alias/SSID mappings and neighbor callsigns.
        
        Returns:
            Tuple of (aliases dict, netrom_ssids dict, neighbors list)
            - aliases: Maps alias to full callsign-SSID
            - netrom_ssids: Maps base callsign to NetRom SSID for connections
            - neighbors: List of base callsigns (without SSID)
        """
        aliases = {}
        netrom_ssids = {}
        neighbors = []
        # Look for patterns like: "CCEBBS:WS1EC-2" or "CCEMA:WS1EC-15"
        matches = re.findall(r'(\w+):(\w+(?:-\d+)?)', output)
        for alias, callsign in matches:
            # Validate callsign format
            if self._is_valid_callsign(callsign):
                aliases[alias] = callsign
                # Extract base callsign and SSID
                if '-' in callsign:
                    base_call, ssid = callsign.rsplit('-', 1)
                    # Store NetRom SSID for this base callsign (typically highest SSID or -15)
                    netrom_ssids[base_call] = callsign
                else:
                    base_call = callsign
                    netrom_ssids[base_call] = callsign
                
                if base_call not in neighbors:
                    neighbors.append(base_call)
        
        return aliases, netrom_ssids, neighbors
    
    def _parse_applications(self, info_output):
        """
        Extract application list from INFO output.
        
        Returns:
            List of application dictionaries with name, description, ssid
        """
        apps = []
        lines = info_output.split('\n')
        in_apps_section = False
        
        for line in lines:
            # Look for "Applications" header
            if 'application' in line.lower() and ('---' in lines[lines.index(line) + 1] if lines.index(line) + 1 < len(lines) else False):
                in_apps_section = True
                continue
            
            # Stop at next section header (dashes or all caps words followed by dashes)
            if in_apps_section and ('---' in line or (line.isupper() and line.strip())):
                in_apps_section = False
                continue
            
            # Parse application lines like: "BBS     Inter-node Mail      WS1EC-2"
            if in_apps_section and line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    # Find SSID if present (callsign-number at end)
                    ssid = None
                    if len(parts) > 1 and re.match(r'\w+-\d+', parts[-1]):
                        ssid = parts[-1]
                        description = ' '.join(parts[1:-1])
                    else:
                        description = ' '.join(parts[1:])
                    
                    apps.append({
                        'name': name,
                        'description': description.strip(),
                        'ssid': ssid
                    })
        
        return apps
    
    def _parse_commands(self, output):
        """
        Parse ? command output to get list of available commands/applications.
        
        Returns:
            List of command names available on the node
        """
        commands = []
        lines = output.split('\n')
        
        for line in lines:
            # Skip header/separator lines
            if not line.strip() or '---' in line or 'Commands' in line:
                continue
            
            # Commands are typically listed in columns or one per line
            # Extract words that look like commands (uppercase, alphanumeric)
            words = line.split()
            for word in words:
                # Filter for likely command names (avoid help text)
                if word.isupper() or (word[0].isupper() and len(word) <= 10):
                    # Clean up any trailing punctuation
                    cmd = word.strip('.,;:')
                    if cmd and cmd not in commands:
                        commands.append(cmd)
        
        return commands
    
    def _parse_routes(self, output):
        """
        Parse ROUTES output to find best paths to destinations.
        
        Returns:
            Dictionary of {callsign: quality} for direct routes
        """
        routes = {}
        lines = output.split('\n')
        
        for line in lines:
            # Look for route lines with quality indicators
            # Format varies but usually: DEST VIA PORT QUALITY
            match = re.search(r'(\w+(?:-\d+)?)\s+.*?(\d+)', line)
            if match:
                dest = match.group(1).split('-')[0]
                # Validate callsign format
                if not self._is_valid_callsign(dest):
                    continue
                quality = int(match.group(2))
                routes[dest] = quality
        
        return routes
    
    def crawl_node(self, callsign, path=[]):
        """
        Crawl a single node to discover neighbors.
        
        Args:
            callsign: Node callsign to crawl
            path: Connection path to reach this node
        """
        if callsign in self.visited:
            return
        
        # Build readable path description
        if not path:
            if callsign == self.callsign:
                path_desc = " (local node)"
            else:
                path_desc = " (direct connection)"
        else:
            path_desc = " (via {})".format(' > '.join(path))
        
        print("Crawling {}{}".format(callsign, path_desc))
        
        self.visited.add(callsign)
        
        # Calculate command timeout based on path length
        # At 1200 baud simplex: ~10s per hop for command/response cycle
        # Base timeout 5s + 10s per hop, max 60s
        hop_count = len(path)
        cmd_timeout = min(5 + (hop_count * 10), 60)
        
        # Connect to node
        # path contains intermediate hops only (not target)
        # For local node: path=[] (no intermediate hops)
        # For direct neighbor: callsign=KC1JMH, path=[] -> connect with C KC1JMH-15
        # For multi-hop: callsign=KS1R, path=[KC1JMH] -> C KC1JMH-15, then C KS1R-15
        connect_path = path + [callsign] if path else ([callsign] if callsign != self.callsign else [])
        
        tn = self._connect_to_node(connect_path)
        if not tn:
            print("  Skipping {} (connection failed)".format(callsign))
            self.failed.add(callsign)
            return
        
        # Set overall operation timeout (commands + processing)
        # Allow 5 minutes base + 2 minutes per hop
        operation_deadline = time.time() + 300 + (hop_count * 120)
        
        try:
            # Helper to check if we've exceeded deadline
            def check_deadline():
                if time.time() > operation_deadline:
                    print("  Operation timeout for {} ({} hops)".format(callsign, hop_count))
                    return True
                return False
            
            # Get PORTS to identify RF ports
            if check_deadline():
                return
            ports_output = self._send_command(tn, 'PORTS', timeout=cmd_timeout)
            ports_list = self._parse_ports(ports_output)
            
            # Get NODES for alias mappings and neighbor list
            if check_deadline():
                return
            nodes_output = self._send_command(tn, 'NODES', timeout=cmd_timeout)
            aliases, netrom_ssids, neighbors_from_nodes = self._parse_nodes_aliases(nodes_output)
            
            # Update global NetRom SSID map with discovered SSIDs
            self.netrom_ssid_map.update(netrom_ssids)
            
            # Filter out the current node from neighbors (including different SSIDs of same callsign)
            # e.g., when on KC1JMH-15, don't list KC1JMH-2 or KC1JMH-10 as neighbors
            base_callsign = callsign.split('-')[0] if '-' in callsign else callsign
            neighbors_from_nodes = [n for n in neighbors_from_nodes if n != base_callsign]
            
            # Get ROUTES for path optimization (BPQ only)
            if check_deadline():
                return
            routes_output = self._send_command(tn, 'ROUTES', timeout=cmd_timeout)
            routes = self._parse_routes(routes_output)
            
            # Get MHEARD from each RF port for detailed heard info
            mheard_neighbors = []
            for port_info in ports_list:
                if port_info['is_rf']:
                    if check_deadline():
                        return
                    port_num = port_info['number']
                    mheard_output = self._send_command(tn, 'MHEARD {}'.format(port_num), timeout=cmd_timeout)
                    heard = self._parse_mheard(mheard_output)
                    mheard_neighbors.extend([call for call, p in heard])
            
            # Combine neighbors from NODES and MHEARD, exclude self (all SSIDs)
            all_neighbors = [n for n in list(set(neighbors_from_nodes + mheard_neighbors)) if n != base_callsign]
            
            # Get INFO
            if check_deadline():
                return
            info_output = self._send_command(tn, 'INFO', timeout=cmd_timeout)
            location = self._parse_info(info_output)
            applications = self._parse_applications(info_output)
            
            # Get available commands (? command)
            if check_deadline():
                return
            commands_output = self._send_command(tn, '?', timeout=cmd_timeout)
            commands = self._parse_commands(commands_output)
            
            # Detect node type
            node_type = self._detect_node_type(info_output, '>:')
            
            # Store node data
            self.nodes[callsign] = {
                'info': info_output.strip(),
                'neighbors': all_neighbors,
                'location': location,
                'ports': ports_list,
                'heard_on_ports': [(call, None) for call in all_neighbors],
                'type': node_type,
                'routes': routes,
                'aliases': aliases,
                'netrom_ssids': netrom_ssids,  # Store for connections
                'applications': applications,
                'commands': commands
            }
            
            # Record connections
            for neighbor in all_neighbors:
                self.connections.append({
                    'from': callsign,
                    'to': neighbor,
                    'port': None,
                    'quality': routes.get(neighbor, 0)
                })
                
                # Add unvisited neighbors to queue with shortest path optimization
                if neighbor not in self.visited and neighbor not in self.failed:
                    # Determine path to this neighbor (intermediate hops only, not target)
                    # If we're at local node WS1EC (path=[]), queue KC1JMH with path=[]
                    #   (direct connection from local, no intermediate hops)
                    # If we're at KC1JMH (path=[]), queue KS1R with path=[KC1JMH]
                    #   (go through KC1JMH to reach KS1R)
                    # If we're at KS1R (path=[KC1JMH]), queue N1XP with path=[KC1JMH, KS1R]
                    #   (go through KC1JMH, then KS1R, to reach N1XP)
                    if path:
                        # We're not at local node, path contains route to current node
                        # Current node becomes an intermediate hop to reach neighbor
                        new_path = path + [callsign]
                    else:
                        # We're at local node, direct connection to neighbor (no intermediate hops)
                        new_path = []
                    
                    # Check if this is a shorter path than previously discovered
                    if neighbor not in self.shortest_paths or len(new_path) < len(self.shortest_paths[neighbor]):
                        self.shortest_paths[neighbor] = new_path
                        # Only queue if this is a new or shorter path
                        self.queue.append((neighbor, new_path))
            
            print("  Found {} neighbors: {}".format(
                len(all_neighbors),
                ', '.join(all_neighbors)
            ))
            print("  Node type: {}".format(node_type))
            print("  RF Ports: {}".format(len([p for p in ports_list if p['is_rf']])))
            print("  Applications: {}".format(len(applications)))
            print("  Commands: {}".format(len(commands)))
            if aliases:
                print("  Aliases: {}".format(len(aliases)))
            
        finally:
            # Disconnect
            try:
                tn.write(b'BYE\r')
                time.sleep(0.5)
            except:
                pass
            tn.close()
    
    def crawl_network(self, start_node=None):
        """
        Crawl entire network starting from specified or local node.
        
        Args:
            start_node: Callsign to start crawl from (default: local node)
        """
        # Determine starting node
        if start_node:
            # Validate provided callsign
            if not self._is_valid_callsign(start_node):
                print("Error: Invalid callsign format: {}".format(start_node))
                return
            starting_callsign = start_node.upper()
            print("Starting network crawl from: {}...".format(starting_callsign))
        else:
            if not self.callsign:
                print("Error: Could not determine local node callsign from bpq32.cfg.")
                print("Please ensure NODECALL is set in your bpq32.cfg file.")
                print("Or provide a starting callsign: {} [MAX_HOPS] [START_NODE]".format(sys.argv[0]))
                return
            starting_callsign = self.callsign
            print("Starting network crawl from local node: {}...".format(starting_callsign))
        
        print("BPQ node: {}:{}".format(self.host, self.port))
        print("Max hops: {}".format(self.max_hops))
        print("-" * 50)
        
        # Start with specified or local node
        self.queue.append((starting_callsign, []))
        
        # BFS traversal
        while self.queue:
            callsign, path = self.queue.popleft()
            
            # Limit depth to prevent excessive crawling
            if len(path) > self.max_hops:
                print("Skipping {} (depth limit {} reached)".format(callsign, self.max_hops))
                continue
            
            self.crawl_node(callsign, path)
            time.sleep(2)  # Be polite, don't hammer network
        
        print("-" * 50)
        print("Crawl complete. Found {} nodes.".format(len(self.nodes)))
        print("Failed connections: {} nodes".format(len(self.failed)))
        if self.failed:
            print("  Failed: {}".format(', '.join(sorted(self.failed))))
        
        # Display summary table
        if self.nodes:
            print("\n" + "=" * 80)
            print("NETWORK SUMMARY")
            print("=" * 80)
            print("{:<10} {:<8} {:<6} {:<6} {:<10} {:<30}".format(
                "CALLSIGN", "TYPE", "PORTS", "APPS", "NEIGHBORS", "GRID/LOCATION"
            ))
            print("-" * 80)
            
            for callsign in sorted(self.nodes.keys()):
                node = self.nodes[callsign]
                node_type = node.get('type', 'Unknown')
                ports = len([p for p in node.get('ports', []) if p.get('is_rf')])
                apps = len(node.get('applications', []))
                neighbors = len(node.get('neighbors', []))
                location = node.get('location', {})
                grid = location.get('grid', '')
                city = location.get('city', '')
                state = location.get('state', '')
                
                # Build location string
                if grid:
                    loc_str = grid
                elif city and state:
                    loc_str = "{}, {}".format(city, state)
                else:
                    loc_str = ""
                
                print("{:<10} {:<8} {:<6} {:<6} {:<10} {:<30}".format(
                    callsign,
                    node_type,
                    ports,
                    apps,
                    neighbors,
                    loc_str[:30]
                ))
            
            print("=" * 80)
            print("Total: {} nodes, {} connections".format(
                len(self.nodes),
                len(self.connections)
            ))
            print("=" * 80)
    
    def export_json(self, filename='nodemap.json', merge=False):
        """Export network map to JSON.
        
        Args:
            filename: Output filename
            merge: If True, merge with existing data instead of overwrite
        """
        nodes_data = {}
        
        # Load existing data if merge mode
        if merge:
            existing = self._load_existing_data(filename)
            if existing and 'nodes' in existing:
                nodes_data = existing['nodes']
                print("Merging with {} existing nodes...".format(len(nodes_data)))
        
        # Update with current crawl data (overwrites duplicates)
        for callsign, node_data in self.nodes.items():
            nodes_data[callsign] = node_data
        
        data = {
            'nodes': nodes_data,
            'connections': self.connections,
            'crawl_info': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'start_node': self.callsign,
                'total_nodes': len(nodes_data),
                'total_connections': len(self.connections),
                'mode': 'merge' if merge else 'overwrite'
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        mode_str = "Merged into" if merge else "Exported to"
        print("{} {} ({} nodes)".format(mode_str, filename, len(nodes_data)))
    
    def export_csv(self, filename='nodemap.csv'):
        """Export connections to CSV."""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['From', 'To', 'Port', 'Quality', 'From_Grid', 'To_Grid', 'From_Type', 'To_Type'])
            
            for conn in self.connections:
                from_node = self.nodes.get(conn['from'], {})
                to_node = self.nodes.get(conn['to'], {})
                
                writer.writerow([
                    conn['from'],
                    conn['to'],
                    conn['port'],
                    conn.get('quality', 0),
                    from_node.get('location', {}).get('grid', ''),
                    to_node.get('location', {}).get('grid', ''),
                    from_node.get('type', 'Unknown'),
                    to_node.get('type', 'Unknown')
                ])
        
        print("Exported to {}".format(filename))


def main():
    """Main entry point."""
    # Check for help flag first
    if '-h' in sys.argv or '--help' in sys.argv or '/?' in sys.argv:
        print("BPQ Node Map Crawler v{}".format(__version__))
        print("=" * 50)
        print("\nAutomatically crawls packet radio network to discover topology.")
        print("\nUsage: {} [MAX_HOPS] [START_NODE] [OPTIONS]".format(sys.argv[0]))
        print("\nArguments:")
        print("  MAX_HOPS         Maximum traversal depth (default: 10)")
        print("  START_NODE       Callsign to begin crawl (default: local node)")
        print("\nOptions:")
        print("  --overwrite, -o  Overwrite existing data (default: merge)")
        print("  --user USERNAME  Telnet login username (default: prompt if needed)")
        print("  --pass PASSWORD  Telnet login password (default: prompt if needed)")
        print("  --debug          Show command/response details for troubleshooting")
        print("  --help, -h, /?   Show this help message")
        print("Examples:")
        print("  {} 5              # Crawl 5 hops, merge with existing".format(sys.argv[0]))
        print("  {} 10 WS1EC       # Crawl from WS1EC, merge results".format(sys.argv[0]))
        print("  {} 5 --overwrite  # Crawl and completely replace data".format(sys.argv[0]))
        print("  {} 10 --user KC1JMH --pass ****  # With authentication".format(sys.argv[0]))
        print("\nData Storage:")
        print("  Merge mode (default): Updates existing nodemap.json, preserves old data")
        print("  Overwrite mode: Completely replaces nodemap.json and nodemap.csv")
        print("\nOutput Files:")
        print("  nodemap.json      Complete network topology and node information")
        print("  nodemap.csv       Connection list for spreadsheet analysis")
        print("\nInstallation:")
        print("  Place in ~/utilities/ or ~/apps/ adjacent to ~/linbpq/")
        print("  Reads NODECALL and TCPPORT from ../linbpq/bpq32.cfg")
        print("\nTimeout Protection:")
        print("  Commands scale with hop count (5s + 10s/hop, max 60s)")
        print("  Overall operation timeout: 5min + 2min/hop")
        sys.exit(0)
    
    print("BPQ Node Map Crawler v{}".format(__version__))
    print("=" * 50)
    
    # Parse command line args
    max_hops = 10
    start_node = None
    username = None
    password = None
    debug = '--debug' in sys.argv
    
    # Parse positional and optional arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith('-'):
            break
        if i == 1 and arg.isdigit():
            max_hops = int(arg)
        elif i == 2:
            start_node = arg.upper()
        i += 1
    
    # Parse options
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--user' and i + 1 < len(sys.argv):
            username = sys.argv[i + 1]
            i += 2
        elif arg == '--pass' and i + 1 < len(sys.argv):
            password = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Merge mode is default; use --overwrite to disable
    merge_mode = '--overwrite' not in sys.argv and '-o' not in sys.argv
    
    # Create crawler
    crawler = NodeCrawler(max_hops=max_hops, username=username, password=password, debug=debug)
    
    # Only require local callsign if no start_node provided
    if not start_node and not crawler.callsign:
        print("\nError: Could not determine local node callsign.")
        print("Ensure NODECALL is set in bpq32.cfg or provide a starting callsign.")
        print("\nUsage: {} [MAX_HOPS] [START_NODE] [OPTIONS]".format(sys.argv[0]))
        print("  MAX_HOPS: Maximum traversal depth (default: 10)")
        print("  START_NODE: Callsign to begin crawl (default: local node)")
        print("  --overwrite, -o: Overwrite existing data (default: merge)")
        print("  --user USERNAME: Telnet login username (default: NODECALL)")
        print("  --pass PASSWORD: Telnet login password (default: empty)")
        print("\nExamples:")
        print("  {} 5              # Crawl 5 hops, merge with existing".format(sys.argv[0]))
        print("  {} 10 WS1EC       # Crawl from WS1EC, merge results".format(sys.argv[0]))
        print("  {} 5 --overwrite  # Crawl and completely replace data".format(sys.argv[0]))
        print("  {} 10 --user KC1JMH --pass ****  # With authentication".format(sys.argv[0]))
        print("\nInstallation:")
        print("  Place in ~/utilities/ or ~/apps/ adjacent to ~/linbpq/")
        sys.exit(1)
    
    if merge_mode:
        print("Mode: Merge (updating existing nodemap.json)")
    else:
        print("Mode: Overwrite (replacing all data)")
    
    # Crawl network
    try:
        crawler.crawl_network(start_node=start_node)
        
        # Export results
        crawler.export_json(merge=merge_mode)
        crawler.export_csv()
        
        print("\nNetwork map complete!")
        print("Nodes discovered: {}".format(len(crawler.nodes)))
        print("Connections found: {}".format(len(crawler.connections)))
        
    except KeyboardInterrupt:
        print("\n\nCrawl interrupted by user.")
        print("Partial results:")
        print("  Nodes: {}".format(len(crawler.nodes)))
        print("  Connections: {}".format(len(crawler.connections)))
        
        # Export partial results
        if crawler.nodes:
            partial_name = 'nodemap_partial_{}'.format(start_node) if start_node else 'nodemap_partial'
            crawler.export_json('{}.json'.format(partial_name))
            crawler.export_csv('{}.csv'.format(partial_name))


if __name__ == '__main__':
    main()
