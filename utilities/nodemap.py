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
- BPQ Node Commands: https://www.cantab.net/users/john.wiseman/Documents/NodeCommands.html

Author: Brad Brown, KC1JMH
Date: January 2026
Version: 1.7.19
"""

__version__ = '1.7.19'

import sys
import socket
import time
import json
import csv
import glob
import re
import os
from collections import deque

# Telnet library import with future-proofing for Python 3.13+
# Note: telnetlib was deprecated in Python 3.11 and removed in 3.13
# For Python 3.13+, install telnetlib3: pip install telnetlib3
# Then use: from telnetlib3.telnetlib import Telnet (drop-in replacement)
try:
    import telnetlib
except ImportError:
    # Python 3.13+ - telnetlib removed from stdlib
    try:
        from telnetlib3.telnetlib import Telnet as telnetlib
        print("Note: Using telnetlib3 (telnetlib not available in Python 3.13+)")
    except ImportError:
        print("Error: telnetlib not available. For Python 3.13+, install: pip install telnetlib3")
        sys.exit(1)


class Colors:
    """ANSI color codes for console output."""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def colored_print(message, color=None):
    """Print message with color if stdout is a terminal."""
    if color and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        print("{}{}{}".format(color, message, Colors.RESET))
    else:
        print(message)


# Check Python version
if sys.version_info < (3, 5):
    colored_print("Error: This script requires Python 3.5 or later.", Colors.RED)
    colored_print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ), Colors.YELLOW)
    sys.exit(1)


class NodeCrawler:
    """Crawls BPQ packet radio network to discover topology."""
    
    # Valid amateur radio callsign pattern: 1-2 prefix chars, digit, 1-3 suffix chars, optional -SSID
    CALLSIGN_PATTERN = re.compile(r'^[A-Z]{1,2}\d[A-Z]{1,3}(?:-\d{1,2})?$', re.IGNORECASE)
    
    def __init__(self, host='localhost', port=None, callsign=None, max_hops=10, username=None, password=None, verbose=False, notify_url=None, log_file=None, debug_log=None, resume=False, crawl_mode='update', exclude=None):
        """
        Initialize crawler.
        
        Args:
            host: BPQ node hostname (default: localhost)
            port: BPQ telnet port (auto-detected if None)
            callsign: Your callsign for login (auto-detected if None)
            max_hops: Maximum hops to traverse (default: 10)
            username: Telnet login username (default: None, prompts when needed)
            password: Telnet login password (default: None, prompts when needed)
            verbose: Enable verbose output (default: False)
            notify_url: URL to POST notifications to (default: None)
            log_file: File to log telnet traffic (default: None)
            debug_log: File to log verbose debug output (default: None)
            resume: Resume from unexplored nodes in existing nodemap.json (default: False)
            crawl_mode: How to handle existing nodes: 'update' (skip known), 'reaudit' (re-crawl all), 'new-only' (only new nodes)
            exclude: Set of callsigns to exclude from crawling (default: None)
        """
        self.host = host
        self.port = port if port else self._find_bpq_port()
        self.callsign = callsign if callsign else self._find_callsign()
        self.max_hops = max_hops
        self.username = username  # None means prompt when needed
        self.password = password  # None means prompt when needed
        self.verbose = verbose
        self.notify_url = notify_url
        self.log_file = log_file
        self.log_handle = None
        self.debug_log = debug_log
        self.debug_handle = None
        self.resume = resume
        self.resume_file = None  # Set externally if specific file needed
        self.crawl_mode = crawl_mode  # 'update', 'reaudit', or 'new-only'
        self.exclude = exclude if exclude else set()  # Nodes to skip
        self.visited = set()  # Nodes we've already crawled
        self.failed = set()  # Nodes that failed connection
        self.nodes = {}  # Node data: {callsign: {info, neighbors, location, type}}
        self.connections = []  # List of [node1, node2, port] connections
        self.routes = {}  # Best routes to nodes: {callsign: [path]}
        self.route_ports = {}  # Port numbers for direct neighbors: {callsign: port_number}
        self.shortest_paths = {}  # Shortest discovered path to each node: {callsign: [path]}
        self.netrom_ssid_map = {}  # Global NetRom SSID mapping: {base_callsign: 'CALLSIGN-SSID'}
        self.ssid_source = {}  # Track SSID source: {base_callsign: ('routes'|'mheard', timestamp)}
        self.alias_to_call = {}  # Global alias->callsign-SSID mapping: {'CHABUR': 'KS1R-13'}
        self.call_to_alias = {}  # Reverse lookup: {'KS1R': 'CHABUR'}
        self.last_heard = {}  # MHEARD timestamps: {callsign: seconds_ago}
        self.intermittent_links = {}  # Failed connections: {(from, to): [attempts]}
        self.queue = deque()  # BFS queue for crawling: entries are (callsign, path, quality)
        self.queued_paths = set()  # Track queued paths to avoid duplicates: {(callsign, tuple(path))}
        self.timeout = 10  # Telnet timeout in seconds
        self.cli_forced_ssids = {}  # SSIDs forced via --callsign CLI option: {base_call: full_ssid}
    
    def _vprint(self, message):
        """Print verbose message to console and debug log (if --debug-log set)."""
        if self.verbose:
            print(message)
            if self.debug_log:
                # Open debug log on first use
                if self.debug_handle is None:
                    try:
                        self.debug_handle = open(self.debug_log, 'a')
                    except Exception as e:
                        colored_print("Warning: Could not open debug log {}: {}".format(self.debug_log, e), Colors.YELLOW)
                        self.debug_log = None
                        return
                
                try:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    self.debug_handle.write("[{}] {}\n".format(timestamp, message))
                    self.debug_handle.flush()
                except Exception as e:
                    if self.verbose:
                        print("    Debug log write failed: {}".format(e))
        
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
    
    def _log(self, direction, data):
        """Log telnet traffic to file if logging enabled.
        
        Args:
            direction: 'SEND' or 'RECV'
            data: Bytes or string to log
        """
        if not self.log_file:
            return
        
        # Open log file on first use
        if self.log_handle is None:
            try:
                self.log_handle = open(self.log_file, 'a')
            except Exception as e:
                colored_print("Warning: Could not open log file {}: {}".format(self.log_file, e), Colors.YELLOW)
                self.log_file = None
                return
        
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(data, bytes):
                data_str = data.decode('ascii', errors='replace')
            else:
                data_str = data
            self.log_handle.write("[{}] {}: {}\n".format(timestamp, direction, repr(data_str)))
            self.log_handle.flush()
        except Exception as e:
            if self.verbose:
                print("    Log write failed: {}".format(e))
    
    def _send_notification(self, message):
        """Send notification to webhook URL if configured."""
        if not self.notify_url:
            return
        
        try:
            # Python 3.x
            if sys.version_info[0] >= 3:
                import urllib.request
                data = message.encode('utf-8')
                req = urllib.request.Request(self.notify_url, data=data, method='POST')
                urllib.request.urlopen(req, timeout=5)
            else:
                # Python 2.x fallback
                import urllib2
                urllib2.urlopen(self.notify_url, data=message, timeout=5)
        except Exception as e:
            if self.verbose:
                colored_print("Notification failed: {}".format(e), Colors.RED)
    
    def _calculate_connection_timeout(self, hop_count):
        """
        Calculate connection timeout based on number of hops.
        At 1200 baud simplex RF: ~45s per hop for connection establishment.
        Simplex means each packet must be ACKed before next can be sent.
        
        Args:
            hop_count: Number of hops in the path
            
        Returns:
            Timeout in seconds (base 45s + 45s per hop, max 240s)
        """
        return min(45 + (hop_count * 45), 240)
    
    def _verify_netrom_route(self, tn, target):
        """
        Verify NetRom route to target using NRR command.
        
        Args:
            tn: Active telnet connection
            target: Target callsign or alias
            
        Returns:
            Tuple of (route_exists, hop_count, route_path)
            route_path is list of callsigns in route, or None if not found
        """
        try:
            # Try NRR command (NetRom Route Request)
            # Response format: "NRR Response: CALL1 CALL2* CALL3" where * marks destination
            cmd = "NRR {}".format(target)
            response = self._send_command(tn, cmd, timeout=10, expect_content='Response')
            
            # Check for "Not found" or "Ok" response
            if 'not found' in response.lower():
                return (False, 0, None)
            
            # Parse route response: "NRR Response: CALL1 CALL2* CALL3"
            # The * marks the destination node
            match = re.search(r'NRR Response:\s*(.+)', response, re.IGNORECASE)
            if match:
                route_str = match.group(1).strip()
                # Split by whitespace and remove the * marker
                route_calls = [c.replace('*', '') for c in route_str.split()]
                # Hop count is number of intermediate nodes (exclude source and destination)
                hop_count = max(0, len(route_calls) - 2)
                return (True, hop_count, route_calls)
            
            return (False, 0, None)
            
        except Exception as e:
            if self.verbose:
                print("    NRR command failed: {}".format(e))
            return (False, 0, None)
    
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
            
            # Set socket-level timeout for ALL subsequent read operations
            # Without this, read_some() blocks indefinitely
            # Use 5s socket timeout - the outer loop handles per-hop timing
            tn.sock.settimeout(5)
            
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
            
            # Verify NetRom route to first hop before attempting connection
            # Only check NRR if we don't have direct port info
            # NRR only works for nodes in NetRom routing table, not direct neighbors
            if len(path) > 0 and self.verbose:
                first_hop = path[0]
                lookup_call = first_hop.split('-')[0] if '-' in first_hop else first_hop
                
                # Skip NRR check if we have port info (direct neighbor)
                port_num = self.route_ports.get(lookup_call)
                if not port_num and lookup_call in self.call_to_alias:
                    # Only verify NetRom routes when we need NetRom routing
                    target_for_nrr = self.call_to_alias.get(lookup_call)
                    
                    print("  Verifying NetRom route to {} (using NRR {})...".format(first_hop, target_for_nrr))
                    route_exists, verified_hops, route_path = self._verify_netrom_route(tn, target_for_nrr)
                    
                    if route_exists and route_path:
                        print("  Route found: {} ({} hop{})".format(' -> '.join(route_path), verified_hops, 's' if verified_hops != 1 else ''))
                        if verified_hops > len(path):
                            print("  Note: Actual route has {} hops (expected {})".format(verified_hops, len(path)))
                    elif not route_exists:
                        print("  Warning: NRR reports no route to {}".format(target_for_nrr))
                elif port_num:
                    print("  Using direct port connection to {} on port {}".format(first_hop, port_num))
            
            # Connect through nodes in path (for multi-hop or direct connections from local node)
            for i, callsign in enumerate(path):
                # Strategy: Prefer direct connection (C PORT CALL-SSID) when we have port info
                # This bypasses NetRom routing and is faster for direct neighbors
                # Fallback to NetRom alias (C ALIAS) if no port info available
                
                # Extract base callsign for lookups (route_ports and netrom_ssid_map are keyed by base call)
                lookup_call = callsign.split('-')[0] if '-' in callsign else callsign
                
                port_num = self.route_ports.get(lookup_call)
                # CLI-forced SSIDs always take precedence over discovered SSIDs
                full_callsign = self.cli_forced_ssids.get(lookup_call) or self.netrom_ssid_map.get(lookup_call, callsign)
                
                # Direct port connection (C PORT CALL) only for first hop from localhost
                # Subsequent hops MUST use NetRom routing (already connected via AX.25)
                if i == 0 and port_num and full_callsign:
                    # Direct neighbor with known port and SSID: C PORT CALLSIGN-SSID
                    # Fastest method - goes straight to neighbor, no NetRom routing
                    cmd = "C {} {}\r".format(port_num, full_callsign).encode('ascii')
                    connect_target = "{} {} (port {}, direct)".format(port_num, full_callsign, port_num)
                    if self.verbose:
                        print("    Issuing command: C {} {} (direct port connection, hop {}/{})".format(port_num, full_callsign, i+1, len(path)))
                elif self.call_to_alias.get(lookup_call):
                    # NetRom alias available: C ALIAS
                    # Uses NetRom routing - slower but works for non-direct neighbors
                    alias = self.call_to_alias.get(lookup_call)
                    cmd = "C {}\r".format(alias).encode('ascii')
                    connect_target = alias
                    if self.verbose:
                        full_call = self.alias_to_call.get(alias, 'unknown')
                        print("    Issuing command: C {} (NetRom alias for {}, hop {}/{})".format(alias, full_call, i+1, len(path)))
                elif i == 0:  # Only try NetRom discovery for first hop
                    # No known path - try NetRom discovery from local node
                    if self.verbose:
                        print("    No known route to {} - attempting NetRom discovery...".format(callsign))
                    
                    # Get NODES command to discover aliases
                    try:
                        nodes_output = self._send_command(tn, 'NODES', timeout=10, expect_content=':')
                        all_aliases, discovered_ssids, _ = self._parse_nodes_aliases(nodes_output)
                        
                        # Update global mappings, preferring node aliases over service aliases
                        for alias, full_call in all_aliases.items():
                            base_call = full_call.split('-')[0]
                            is_service = self._is_likely_node_ssid(full_call)
                            
                            # Add or update mapping, preferring likely node SSIDs
                            if base_call not in self.call_to_alias:
                                # New entry - add it
                                self.call_to_alias[base_call] = alias
                                self.alias_to_call[alias] = full_call
                            elif is_service:
                                # Likely node SSID - replace existing
                                self.call_to_alias[base_call] = alias
                                self.alias_to_call[alias] = full_call
                            # else: suspicious SSID and we already have a mapping - skip
                        
                        # Update SSID mappings
                        for base_call, full_call in discovered_ssids.items():
                            if base_call not in self.netrom_ssid_map:
                                self.netrom_ssid_map[base_call] = full_call
                        
                        # Try again with discovered aliases
                        if lookup_call in self.call_to_alias:
                            alias = self.call_to_alias[lookup_call]
                            cmd = "C {}\r".format(alias).encode('ascii')
                            connect_target = alias
                            if self.verbose:
                                print("    Found NetRom alias: {} -> {}".format(lookup_call, alias))
                                print("    Issuing command: C {} (discovered NetRom alias, hop {}/{})".format(alias, i+1, len(path)))
                        else:
                            # Still no alias found - try connecting to known nodes to discover more
                            if self.verbose:
                                print("    {} not in local NetRom table - trying known nodes...".format(lookup_call))
                            
                            # Try connecting to known nodes to expand NetRom discovery
                            found_via_neighbor = False
                            for alias, full_call in all_aliases.items():
                                neighbor_base = full_call.split('-')[0]
                                if neighbor_base != self.callsign:  # Skip self
                                    try:
                                        if self.verbose:
                                            print("    Trying {} ({}) for expanded NetRom discovery...".format(alias, full_call))
                                        
                                        # Connect to neighbor
                                        neighbor_cmd = "C {}\r".format(alias).encode('ascii')
                                        tn.write(neighbor_cmd)
                                        time.sleep(1)
                                        
                                        # Look for CONNECTED response
                                        response = ""
                                        start_time = time.time()
                                        while time.time() - start_time < 10:  # Short timeout
                                            try:
                                                chunk = tn.read_some()
                                                response += chunk.decode('ascii', errors='ignore')
                                                if 'CONNECTED' in response.upper():
                                                    if self.verbose:
                                                        print("    Connected to {} - getting NODES...".format(alias))
                                                    
                                                    # Wait for prompt and get NODES
                                                    tn.read_until(b'} ', timeout=5)
                                                    neighbor_nodes = self._send_command(tn, 'NODES', timeout=10, expect_content=':')
                                                    neighbor_aliases, neighbor_ssids, _ = self._parse_nodes_aliases(neighbor_nodes)
                                                    
                                                    # Check if our target is in this node's table
                                                    for n_alias, n_full_call in neighbor_aliases.items():
                                                        n_base = n_full_call.split('-')[0]
                                                        if n_base == lookup_call:
                                                            if self.verbose:
                                                                print("    Found {} via {}: {} -> {}".format(lookup_call, alias, n_alias, n_full_call))
                                                            # Disconnect from neighbor and use its alias
                                                            tn.write(b'BYE\r')
                                                            time.sleep(0.5)
                                                            tn.read_very_eager()  # Clear response
                                                            
                                                            # Now connect using the discovered alias
                                                            cmd = "C {}\r".format(n_alias).encode('ascii')
                                                            connect_target = "{} (via {})".format(n_alias, alias)
                                                            found_via_neighbor = True
                                                            if self.verbose:
                                                                print("    Issuing command: C {} (found via {}, hop {}/{})".format(n_alias, alias, i+1, len(path)))
                                                            break
                                                    
                                                    if found_via_neighbor:
                                                        break
                                                    else:
                                                        # Target not found, disconnect
                                                        tn.write(b'BYE\r')
                                                        time.sleep(0.5)
                                                        tn.read_very_eager()
                                                        break
                                                
                                            except socket.timeout:
                                                pass
                                            except EOFError:
                                                break
                                        
                                        if found_via_neighbor:
                                            break
                                            
                                    except Exception as e:
                                        if self.verbose:
                                            print("    Failed to query {}: {}".format(alias, e))
                                        continue
                            
                            if not found_via_neighbor:
                                # Still no route - final fallback
                                full_callsign = self.netrom_ssid_map.get(lookup_call, callsign)
                                cmd = "C {}\r".format(full_callsign).encode('ascii')
                                connect_target = "{} (no route found - will fail)".format(full_callsign)
                                if self.verbose:
                                    print("    No route found after expanded search")
                                    print("    Issuing command: C {} (final fallback - will likely fail, hop {}/{})".format(full_callsign, i+1, len(path)))
                    
                    except Exception as e:
                        if self.verbose:
                            print("    NetRom discovery failed: {}".format(e))
                        # Fall back to basic connection attempt
                        full_callsign = callsign
                        cmd = "C {}\r".format(full_callsign).encode('ascii')
                        connect_target = "{} (discovery failed)".format(full_callsign)
                        if self.verbose:
                            print("    Issuing command: C {} (discovery failed, hop {}/{})".format(full_callsign, i+1, len(path)))
                else:
                    # Fallback: use callsign-SSID without port
                    # May fail if not a direct neighbor
                    if not full_callsign:
                        full_callsign = callsign  # Use base callsign
                        if self.verbose:
                            print("    No NetRom SSID found for {}, using base callsign".format(callsign))
                    
                    # IMPORTANT: Don't use "C CALLSIGN-SSID" without port - BPQ requires port number
                    # Instead, suggest user find NetRom alias or add to existing network data
                    if self.verbose:
                        print("    Warning: No port or NetRom alias for {} - connection will likely fail".format(callsign))
                        print("    Suggestion: Connect to a known node first, get NODES list to find aliases")
                    
                    cmd = "C {}\r".format(full_callsign).encode('ascii')
                    connect_target = "{} (no port - likely to fail)".format(full_callsign)
                    if self.verbose:
                        print("    Issuing command: C {} (fallback without port - BPQ may reject, hop {}/{})".format(full_callsign, i+1, len(path)))
                
                # Set socket timeout before write to prevent blocking on dead connections
                # TCP write() can block if remote end's receive buffer is full
                tn.sock.settimeout(10.0)
                
                try:
                    tn.write(cmd)
                except socket.timeout:
                    print("  Connection to {} timed out (write blocked)".format(callsign))
                    tn.close()
                    return None
                
                # Wait for connection response (scale timeout with hop count)
                # At 1200 baud RF: ~20s per hop for connection establishment
                # Calculate timeout based on total path length (this hop + remaining hops)
                remaining_hops = len(path) - i
                conn_timeout = self._calculate_connection_timeout(remaining_hops)
                connection_start_time = time.time()
                connected = False
                response = ""
                
                if self.verbose:
                    print("    Waiting for connection (timeout: {}s for {} hop{})...".format(
                        conn_timeout, remaining_hops, 's' if remaining_hops != 1 else ''))
                
                # Set socket timeout to prevent read_some() from blocking forever
                # Use short timeout so we can check elapsed time in the loop
                try:
                    if tn.sock:
                        tn.sock.settimeout(2.0)
                except:
                    pass
                
                while time.time() - connection_start_time < conn_timeout:
                    # Check timeout FIRST before any I/O operations
                    elapsed = time.time() - connection_start_time
                    if elapsed >= conn_timeout:
                        break
                    
                    try:
                        # Use read_very_eager() instead of read_some() - it's non-blocking
                        chunk = tn.read_very_eager()
                        if chunk:
                            response += chunk.decode('ascii', errors='ignore')
                        
                        # Check for connection success
                        if 'CONNECTED' in response.upper():
                            connected = True
                            print("  Connected to {}".format(callsign))
                            break
                        
                        # Check for failure patterns
                        if any(x in response.upper() for x in ['BUSY', 'FAILED', 'NO ROUTE', 
                                                                 'TIMEOUT', 'DISCONNECTED',
                                                                 'NOT HEARD', 'NO ANSWER',
                                                                 'NOT IN TABLES', 'NO ROUTE TO']):
                            # Extract last meaningful line for error message
                            error_line = response.strip().split('\n')[-1] if response.strip() else 'Unknown error'
                            colored_print("  Connection to {} (via {}) failed: {}".format(
                                callsign, 
                                connect_target,
                                error_line
                            ), Colors.RED)
                            tn.close()
                            return None
                        
                        # Sleep between checks to avoid busy-waiting
                        # Sleep between checks to avoid busy-waiting
                        time.sleep(0.5)
                        
                    except EOFError:
                        print("  Connection lost to {}".format(callsign))
                        tn.close()
                        return None
                    except Exception as e:
                        # Any other exception during read
                        if self.verbose:
                            print("  Read error: {}".format(e))
                        # Check if we've exceeded timeout
                        if time.time() - connection_start_time >= conn_timeout:
                            break
                        time.sleep(0.5)
                
                if not connected:
                    elapsed = time.time() - connection_start_time
                    if self.verbose:
                        print("  Connection to {} (via {}) timed out after {:.1f}s (expected timeout: {}s)".format(
                            callsign, connect_target, elapsed, conn_timeout))
                    else:
                        print("  Connection to {} (via {}) timed out (no CONNECTED response)".format(callsign, connect_target))
                    
                    # If direct port connection failed, try NetRom alias as fallback
                    if port_num and self.call_to_alias.get(lookup_call):
                        alias = self.call_to_alias.get(lookup_call)
                        if self.verbose:
                            print("    Direct port connection failed - trying NetRom alias: {}".format(alias))
                        
                        # Clear any buffered data
                        try:
                            tn.read_very_eager()
                        except:
                            pass
                        
                        # Try NetRom connection
                        cmd = "C {}\r".format(alias).encode('ascii')
                        try:
                            tn.write(cmd)
                        except:
                            tn.close()
                            return None
                        
                        # Calculate remaining timeout from original start time
                        elapsed = time.time() - connection_start_time
                        remaining_timeout = max(5, conn_timeout - elapsed)  # At least 5s for fallback
                        connected = False
                        response = ""
                        
                        if self.verbose:
                            print("    Waiting for NetRom connection (timeout: {}s remaining)...".format(int(remaining_timeout)))
                        
                        while time.time() - connection_start_time < conn_timeout:
                            # Check timeout FIRST before any I/O operations
                            elapsed = time.time() - connection_start_time
                            if elapsed >= conn_timeout:
                                break
                            
                            try:
                                chunk = tn.read_some()
                                response += chunk.decode('ascii', errors='ignore')
                                
                                if 'CONNECTED' in response.upper():
                                    connected = True
                                    print("  Connected to {} via NetRom alias {}".format(callsign, alias))
                                    break
                                
                                if any(x in response.upper() for x in ['BUSY', 'FAILED', 'NO ROUTE', 
                                                                         'TIMEOUT', 'DISCONNECTED',
                                                                         'NOT HEARD', 'NO ANSWER']):
                                    break
                                
                                time.sleep(0.5)
                            except socket.timeout:
                                # Check if total timeout exceeded
                                if time.time() - connection_start_time >= conn_timeout:
                                    break
                                pass
                            except EOFError:
                                break
                    
                    if not connected:
                        tn.close()
                        return None
                
                # Wait for remote node prompt after connection
                # BPQ remote nodes use "ALIAS:CALLSIGN-SSID} " prompt format
                # Banner/info is sent immediately after CONNECTED, followed by prompt
                # This tells us the actual node SSID in use
                try:
                    # Look for BPQ remote prompt: "} " at end of banner
                    # Allow 30s for banner at 1200 baud over RF hops
                    if self.verbose:
                        print("    Waiting for remote node prompt (30s timeout)...")
                    prompt_data = tn.read_until(b'} ', timeout=30)
                    self._log('RECV', prompt_data)
                    prompt_text = prompt_data.decode('ascii', errors='replace')
                    
                    # Extract actual node SSID from prompt: "ALIAS:CALL-SSID} "
                    # Example: "WINFLD:N1QFY-4} " means node is N1QFY-4
                    prompt_match = re.search(r'(\w+):(\w+(?:-\d+)?)\}\s*$', prompt_text)
                    if prompt_match:
                        prompt_alias = prompt_match.group(1)
                        prompt_callsign = prompt_match.group(2)
                        base_call = prompt_callsign.split('-')[0]
                        
                        # Store the ACTUAL node SSID we're connected to
                        self.netrom_ssid_map[base_call] = prompt_callsign
                        self.alias_to_call[prompt_alias] = prompt_callsign
                        self.call_to_alias[base_call] = prompt_alias
                        
                        if self.verbose:
                            print("    Connected to node: {} ({}) - stored for routing".format(prompt_callsign, prompt_alias))
                    elif self.verbose:
                        print("    Received remote prompt: {}...".format(prompt_data[-20:].decode('ascii', errors='replace').strip()))
                    
                    # Always consume any remaining buffered data after prompt
                    # This prevents leftover banner/info text from contaminating first command response
                    time.sleep(1.5)  # Give trailing data time to arrive over 1200 baud RF
                    extra_data = tn.read_very_eager()
                    if extra_data:
                        self._log('RECV', extra_data)
                        if self.verbose:
                            print("    Cleared {} bytes of buffered data".format(len(extra_data)))
                except socket.timeout:
                    if self.verbose:
                        print("    Timeout waiting for prompt - node may be slow or connection unstable")
                    # Consume whatever is buffered
                    buffered = tn.read_very_eager()
                    self._log('RECV', buffered)
                    if self.verbose:
                        print("    Consumed {} bytes of buffered data".format(len(buffered)))
                except Exception as e:
                    # If no prompt received, just consume whatever is buffered
                    if self.verbose:
                        print("    Error reading prompt: {}".format(e))
                    buffered = tn.read_very_eager()
                    self._log('RECV', buffered)
                    if self.verbose:
                        print("    Consumed {} bytes".format(len(buffered)))
            
            return tn
            
        except Exception as e:
            colored_print("Error connecting: {}".format(e), Colors.RED)
            return None
    
    def _send_command(self, tn, command, wait_for=b'>', timeout=5, expect_content=None):
        """Send command and read response with timeout protection.
        
        Args:
            tn: Telnet connection
            command: Command to send
            wait_for: Prompt to wait for (default: >)
            timeout: Read timeout in seconds
            expect_content: Optional string that should appear in response for validation
        
        Returns:
            Decoded response string
        """
        try:
            if self.verbose:
                print("    Sending command: {}".format(command))
            cmd_bytes = "{}\r".format(command).encode('ascii')
            tn.write(cmd_bytes)
            self._log('SEND', cmd_bytes)
            
            # Wait for command echo before reading response
            # This helps synchronize on slow multi-hop RF links
            time.sleep(0.3)
            
            # Read all available data with retries
            # Over RF, responses arrive in chunks with gaps
            # For large responses (NODES, ROUTES), use short per-read timeout to avoid blocking
            # and calculate attempts based on overall timeout
            response = b''
            read_attempts = 0
            # Per-read timeout: scale with overall timeout for long commands (MHEARD, INFO)
            # Use 5s for short commands, up to 8s for long commands over multi-hop RF
            per_read_timeout = min(8, max(3, timeout / 2))
            max_attempts = max(8, int(timeout / 2))  # More attempts for reliability
            last_response_len = 0
            stable_count = 0  # Count consecutive attempts with no growth
            
            while read_attempts < max_attempts:
                read_attempts += 1
                
                try:
                    # Try to read until prompt (use short timeout to avoid blocking on large output)
                    chunk = tn.read_until(b'} ', timeout=per_read_timeout)
                    self._log('RECV', chunk)
                    response += chunk
                    
                    # Try to get second prompt (actual response follows first prompt)
                    chunk2 = tn.read_until(b'} ', timeout=per_read_timeout)
                    self._log('RECV', chunk2)
                    response += chunk2
                except:
                    pass
                
                # Consume any extra buffered data
                time.sleep(1.0)  # Give more time for trailing data to arrive over RF
                try:
                    extra = tn.read_very_eager()
                    if extra:
                        self._log('RECV', extra)
                        response += extra
                except:
                    pass
                
                # Check if response stopped growing
                if len(response) > 0 and len(response) == last_response_len:
                    stable_count += 1
                    # Need 3 consecutive stable readings for multi-hop RF (3-4 seconds with no data)
                    # This prevents premature termination of long MHEARD/INFO outputs
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0  # Reset if we got more data
                last_response_len = len(response)
                
                # If we have expected content, check for it
                decoded_check = response.decode('ascii', errors='ignore')
                if expect_content and expect_content.lower() in decoded_check.lower():
                    # Still wait for stable response even if we found expected content
                    # (there might be more data after it)
                    if stable_count >= 2:  # Can exit with 2 stable if we found expected content
                        break
                
                # Delay before retry (already did 1.0s above)
                if read_attempts < max_attempts and stable_count == 0:
                    time.sleep(0.5)
            
            decoded = response.decode('ascii', errors='ignore')
            
            # Validate response content if expected
            if expect_content and expect_content.lower() not in decoded.lower():
                if self.verbose:
                    print("    Warning: Expected '{}' not found in response".format(expect_content))
            
            if self.verbose:
                print("    Response ({} bytes):".format(len(decoded)))
                # Show more of response for debugging
                display = decoded[:300] if len(decoded) > 300 else decoded
                print("    {}".format(display.replace('\r\n', '\n    ')))
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
    
    def _parse_mheard(self, output, port_num=None):
        """
        Parse MHEARD output to extract callsigns, timestamps, and port numbers.
        
        MHEARD output format:
            Heard List for Port N
            CALLSIGN-SSID  DD:HH:MM:SS (days:hours:mins:secs since last heard)
        
        Args:
            output: MHEARD command output
            port_num: Port number if known (from command context)
        
        Returns:
            If port_num provided: List of base callsigns (without SSID)
            If port_num None: List of (callsign, port) tuples
            Also updates self.last_heard dict with timestamps
        """
        heard = []
        lines = output.split('\n')
        
        # Try to extract port from header if not provided
        detected_port = port_num
        if detected_port is None:
            for line in lines:
                if 'Heard List for Port' in line:
                    match = re.search(r'Port\s+(\d+)', line)
                    if match:
                        detected_port = int(match.group(1))
                        break
        
        for line in lines:
            # Skip header lines
            if 'Heard List' in line or not line.strip():
                continue
            
            # Look for callsign and timestamp: "KC1JMH-15  00:00:00:03"
            # Match callsign with optional SSID, followed by timestamp
            match = re.match(r'^(\w+(?:-\d+)?)\s+(\d+):(\d+):(\d+):(\d+)', line)
            if match:
                full_callsign = match.group(1)
                callsign = full_callsign.split('-')[0]  # Strip SSID for base call
                
                # Validate callsign format
                if not self._is_valid_callsign(callsign):
                    continue
                
                # Parse timestamp (DD:HH:MM:SS) to total seconds
                days = int(match.group(2))
                hours = int(match.group(3))
                minutes = int(match.group(4))
                seconds = int(match.group(5))
                total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
                
                # Update last_heard with most recent time for this callsign
                if callsign not in self.last_heard or total_seconds < self.last_heard[callsign]:
                    self.last_heard[callsign] = total_seconds
                
                # If we have port info, return (callsign, port) tuple
                if detected_port is not None:
                    if callsign not in [h[0] if isinstance(h, tuple) else h for h in heard]:
                        if port_num is not None:
                            # Called with explicit port, return just callsigns
                            heard.append(callsign)
                        else:
                            # Called without explicit port, return tuples
                            heard.append((callsign, detected_port))
                else:
                    # No port info, just return callsigns
                    if callsign not in heard:
                        heard.append(callsign)
        
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
        
        Note: INFO is freeform text entered by sysop. Parsing is unreliable
        and should be given less weight than structured command output.
        
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
        
        Note: Detection from INFO text is unreliable (sysop-entered freeform).
        Prompt character detection (> or :) is more reliable fallback.
        
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
            colored_print("Warning: Could not load {}: {}".format(filename, e), Colors.YELLOW)
            return None
    
    def _find_path_to_node(self, target_callsign, nodes_data):
        """Find shortest path from local node to target node using BFS.
        
        Args:
            target_callsign: Target node to reach
            nodes_data: Dictionary of node data from nodemap.json
            
        Returns:
            List of intermediate callsigns (not including local or target), or None if not found
        """
        if not self.callsign:
            return None
        
        if target_callsign == self.callsign:
            return []
        
        # BFS to find shortest path
        queue = [(self.callsign, [])]  # (current_node, path_to_current)
        visited = {self.callsign}
        
        while queue:
            current, path = queue.pop(0)
            current_info = nodes_data.get(current, {})
            neighbors = current_info.get('neighbors', [])
            
            for neighbor in neighbors:
                if neighbor == target_callsign:
                    # Found target - path doesn't include local or target
                    return path
                
                if neighbor not in visited and neighbor in nodes_data:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        # Target not reachable through known neighbors
        return None
    
    def _load_unexplored_nodes(self, filename='nodemap.json'):
        """Load unexplored nodes from existing nodemap data.
        
        Returns:
            List of (callsign, path) tuples for unexplored neighbors
        """
        # Try multiple possible filenames if default doesn't exist
        possible_files = [filename]
        if filename == 'nodemap.json':
            # Also try partial files from interrupted crawls
            import glob
            partial_files = glob.glob('nodemap_partial*.json')
            if partial_files:
                # Use most recent partial file
                partial_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
                possible_files.extend(partial_files)
        
        existing = None
        used_file = None
        for try_file in possible_files:
            existing = self._load_existing_data(try_file)
            if existing and 'nodes' in existing:
                used_file = try_file
                break
        
        if not existing or 'nodes' not in existing:
            print("No existing nodemap data found. Starting fresh crawl.")
            print("Tried files: {}".format(', '.join(possible_files)))
            return []
        
        if used_file != filename:
            print("Using existing data from: {}".format(used_file))
        
        unexplored = []
        nodes_data = existing['nodes']
        
        # Mark all previously visited nodes
        for callsign in nodes_data.keys():
            self.visited.add(callsign)
        
        print("Loaded {} previously visited nodes".format(len(self.visited)))
        
        # Restore SSID mappings from previous crawl data
        # This is critical for resume functionality - connections need proper SSIDs
        # Priority: Aggregate from all nodes' ROUTES (most authoritative) > netrom_ssids (MHEARD)
        
        # First pass: Build SSID map from all nodes' ROUTES
        # When multiple nodes route to the same callsign, they reveal the node SSID
        ssid_candidates = {}  # {base_call: {full_ssid: count}}
        
        for callsign, node_data in nodes_data.items():
            routes = node_data.get('routes', {})
            for route_call in routes.keys():
                # Only process routes with SSIDs
                if '-' not in route_call:
                    continue
                # Skip suspicious SSIDs (out of range 1-15)
                if not self._is_likely_node_ssid(route_call):
                    continue
                base_call = route_call.split('-')[0]
                if base_call not in ssid_candidates:
                    ssid_candidates[base_call] = {}
                if route_call not in ssid_candidates[base_call]:
                    ssid_candidates[base_call][route_call] = 0
                ssid_candidates[base_call][route_call] += 1
        
        # Use the most common SSID for each base callsign (consensus from routes)
        for base_call, ssid_counts in ssid_candidates.items():
            if ssid_counts:
                # Pick the SSID that appears in the most routes (consensus)
                most_common_ssid = max(ssid_counts.items(), key=lambda x: x[1])[0]
                self.netrom_ssid_map[base_call] = most_common_ssid
        
        # Second pass: Fill in from each node's own netrom_ssids (MHEARD data)
        for callsign, node_data in nodes_data.items():
            node_ssids = node_data.get('netrom_ssids', {})
            for base_call, full_call in node_ssids.items():
                # Only use if not already set by routes consensus
                if base_call not in self.netrom_ssid_map:
                    # Skip suspicious SSIDs (out of valid range)
                    if self._is_likely_node_ssid(full_call):
                        self.netrom_ssid_map[base_call] = full_call
            
            # Also restore route_ports from heard_on_ports data (MHEARD port information)
            heard_on_ports = node_data.get('heard_on_ports', [])
            for call, port in heard_on_ports:
                if port is not None and call not in self.route_ports:
                    self.route_ports[call] = port
            
            # Also restore route_ports from routes data (for any additional entries)
            routes = node_data.get('routes', {})
            for neighbor, quality in routes.items():
                if neighbor not in self.route_ports and quality > 0:
                    # Use port 1 as fallback if no MHEARD data available
                    self.route_ports[neighbor] = 1
        
        # Restore CLI-forced SSIDs (these override anything from JSON)
        for base_call, forced_ssid in self.cli_forced_ssids.items():
            self.netrom_ssid_map[base_call] = forced_ssid
            self.ssid_source[base_call] = ('cli', time.time())
            if self.verbose:
                print("Restored CLI-forced SSID: {} = {}".format(base_call, forced_ssid))
        
        if self.netrom_ssid_map:
            print("Restored {} SSID mappings from previous crawl".format(len(self.netrom_ssid_map)))
        if self.route_ports:
            print("Restored {} route ports from previous crawl".format(len(self.route_ports)))
        
        # Find unexplored neighbors from each visited node
        for callsign, node_data in nodes_data.items():
            unexplored_neighbors = node_data.get('unexplored_neighbors', [])
            if unexplored_neighbors:
                print("  {} has {} unexplored: {}".format(callsign, len(unexplored_neighbors), ', '.join(sorted(unexplored_neighbors)[:5]) + ('...' if len(unexplored_neighbors) > 5 else '')))
            
            # Also check neighbors that were never visited
            all_neighbors = node_data.get('neighbors', [])
            for neighbor in all_neighbors:
                # Skip if already visited or excluded
                if neighbor in self.visited or neighbor in self.exclude:
                    continue
                
                # Check if THIS node (current parent) has a valid route to the neighbor
                # Don't queue via this parent if route is quality 0 (blocked) from this node
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                parent_routes = node_data.get('routes', {})
                
                # Find if parent has route to neighbor
                parent_has_route = False
                parent_route_quality = 0
                parent_route_ssid = None
                
                for route_call, quality in parent_routes.items():
                    route_base = route_call.split('-')[0] if '-' in route_call else route_call
                    if route_base == neighbor_base:
                        parent_has_route = True
                        parent_route_quality = quality
                        parent_route_ssid = route_call
                        break
                
                # Skip if parent doesn't have route or route is quality 0 (blocked)
                if not parent_has_route:
                    if self.verbose:
                        print("    Skipping {} from {} (no route in parent)".format(neighbor, callsign))
                    continue
                    
                if parent_route_quality == 0:
                    if self.verbose:
                        print("    Skipping {} from {} (quality 0 - parent has blocked route)".format(neighbor, callsign))
                    continue
                
                # Use the node SSID from parent's routes (authoritative)
                neighbor_to_queue = parent_route_ssid
                
                # Calculate path to this neighbor
                # Priority:
                # 1. If neighbor was previously visited successfully, use its own successful_path
                # 2. Otherwise, use parent's successful_path + parent callsign
                # 3. Fallback to BFS reconstruction
                neighbor_node_data = nodes_data.get(neighbor_to_queue)
                if neighbor_node_data and 'successful_path' in neighbor_node_data:
                    # Use the neighbor's own proven successful path (highest priority)
                    path = neighbor_node_data['successful_path']
                    if self.verbose:
                        print("    Using proven path for {}: {}".format(neighbor_to_queue, ' > '.join(path) if path else '(direct)'))
                else:
                    # Reconstruct path via parent node
                    parent_successful_path = node_data.get('successful_path')
                    if parent_successful_path is not None:
                        # Use the proven successful path from previous crawl
                        if callsign == self.callsign:
                            # Parent is local node
                            path = []
                        else:
                            # Path to neighbor = proven path to parent + parent itself
                            path = parent_successful_path + [callsign]
                    else:
                        # Fallback to BFS reconstruction
                        hop_distance = node_data.get('hop_distance', 0)
                        if hop_distance == 0:
                            # Parent is local node, direct connection to neighbor
                            path = []
                        else:
                            # Use BFS to find path from local node to parent node
                            # Then neighbor is reached via parent
                            parent_path = self._find_path_to_node(callsign, nodes_data)
                            if parent_path is not None:
                                # Path to neighbor = path to parent + parent itself
                                path = parent_path + [callsign]
                            else:
                                # Fallback: assume direct connection to parent
                                path = [callsign]
                
                unexplored.append((neighbor_to_queue, path))
        
        # Sort by multiple criteria to try best paths first:
        # 1. Hop count (fewer hops = more reliable)
        # 2. Node callsign (for deterministic ordering)
        # This allows multiple attempts to same node via different paths
        unexplored.sort(key=lambda x: (len(x[1]), x[0]))
        
        print("Found {} path(s) to {} unique neighbor(s)".format(len(unexplored), len(set(call for call, _ in unexplored))))
        return unexplored
    
    def _is_likely_node_ssid(self, full_callsign):
        """
        Check if a callsign-SSID looks like a node SSID (used for routing).
        
        Node SSIDs are typically -15, but vary by sysop. We can't rely on specific numbers.
        Instead, we use heuristics: SSIDs in valid range (1-15) are potentially nodes.
        
        This is ONLY used to decide connection preference when multiple SSIDs exist.
        All SSIDs are preserved in maps for visualization.
        
        Args:
            full_callsign: Full callsign with SSID (e.g., 'KS1R-13')
            
        Returns:
            True if valid SSID range (1-15), False if suspicious (0, >15, or invalid)
        """
        if '-' not in full_callsign:
            return True  # Base callsign without SSID is valid
        
        try:
            ssid = int(full_callsign.rsplit('-', 1)[1])
            # Valid SSID range is 0-15, but 0 and >15 are suspicious
            return 1 <= ssid <= 15
        except (ValueError, IndexError):
            return False
    
    def _parse_ports(self, output):
        """
        Parse PORTS output to extract port details.
        
        Expected format:
            Ports
              1 433.300 MHz 1200 BAUD
              2 145.050 MHz @ 1200 b/s
              8 AX/IP/UDP
              9 Telnet Server
        
        Returns:
            List of port dictionaries with number, frequency, speed, type
        """
        ports = []
        lines = output.split('\n')
        
        for line in lines:
            # Skip empty lines and header
            line = line.strip()
            if not line or line.lower() == 'ports':
                continue
            
            # Pattern: port_num followed by description
            # Examples: "1 433.300 MHz 1200 BAUD", "9 Telnet Server", "8 AX/IP/UDP"
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if not match:
                continue
            
            port_num = int(match.group(1))
            rest = match.group(2).strip()
            
            # Try to extract speed (baud rate) from description
            # Look for patterns like "1200 BAUD", "@ 1200 b/s", "1200 Baud"
            speed = None
            speed_match = re.search(r'@?\s*(\d+)\s*(?:b/s|baud|BAUD)', rest, re.IGNORECASE)
            if speed_match:
                speed = int(speed_match.group(1))
            
            # Try to extract frequency from description
            # Look for patterns like "433.300 MHz", "145.050 MHz", "144.930 MHz", "144.990" (MHz implied)
            frequency = None
            freq_match = re.search(r'(\d+\.\d+)\s*(?:MHz)?', rest, re.IGNORECASE)
            if freq_match:
                freq_str = freq_match.group(1)
                # Only parse if it looks like a frequency (30-3000 MHz range for amateur radio)
                freq_val = float(freq_str)
                if 30.0 <= freq_val <= 3000.0:
                    frequency = freq_val
            
            # Full description is everything after port number
            description = rest
            
            # Determine if it's RF or IP-based
            desc_upper = description.upper()
            is_rf = not any(x in desc_upper for x in ['TELNET', 'TCP', 'IP', 'UDP', 'AX/IP'])
            
            ports.append({
                'number': port_num,
                'description': description,
                'frequency': frequency,  # MHz as float (433.3, 145.05, etc.)
                'speed': speed,
                'is_rf': is_rf
            })
        
        return ports
    
    def _parse_nodes_aliases(self, output):
        """
        Parse NODES output to get alias/SSID mappings and neighbor callsigns.
        
        NODES output contains two types of entries:
        1. Aliased: "CCEBBS:WS1EC-2" (alias:callsign-ssid)
        2. Non-aliased: "N1LJK-15" (just callsign-ssid, no alias)
        
        Both types indicate entries in the routing table (crawlable nodes).
        Non-aliased entries are common for nodes that only advertise their
        node SSID without application aliases.
        
        Returns:
            Tuple of (aliases dict, netrom_ssids dict, neighbors list)
            - aliases: Maps alias to full callsign-SSID
            - netrom_ssids: Maps base callsign to NetRom SSID for connections
            - neighbors: List of base callsigns (without SSID)
        """
        aliases = {}
        netrom_ssids = {}
        neighbors = []
        
        # First pass: Look for aliased entries like "CCEBBS:WS1EC-2"
        matches = re.findall(r'(\w+):(\w+(?:-\d+)?)', output)
        for alias, callsign in matches:
            # Validate callsign format
            if self._is_valid_callsign(callsign):
                aliases[alias] = callsign
                # Extract base callsign and SSID
                if '-' in callsign:
                    base_call, ssid = callsign.rsplit('-', 1)
                    netrom_ssids[base_call] = callsign
                else:
                    base_call = callsign
                    netrom_ssids[base_call] = callsign
                
                if base_call not in neighbors:
                    neighbors.append(base_call)
        
        # Second pass: Look for non-aliased entries like "N1LJK-15"
        # These are callsign-SSID patterns NOT preceded by a colon (not part of alias)
        # Pattern: word boundary, callsign-SSID, whitespace or end
        # Exclude entries already found via aliases
        non_aliased = re.findall(r'\b([A-Z]{1,2}\d[A-Z]{1,3}-\d{1,2})\b', output)
        for full_callsign in non_aliased:
            base_call = full_callsign.rsplit('-', 1)[0]
            # Skip if we already have this from aliased entries
            if base_call in netrom_ssids:
                continue
            # Validate callsign format
            if self._is_valid_callsign(full_callsign):
                netrom_ssids[base_call] = full_callsign
                if base_call not in neighbors:
                    neighbors.append(base_call)
        
        return aliases, netrom_ssids, neighbors
        
        return aliases, netrom_ssids, neighbors
    
    def _parse_applications(self, info_output):
        """
        Extract application list from INFO output.
        
        Note: INFO is freeform text entered by sysop. Application list format
        and content varies widely and should be considered unreliable.
        
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
            Tuple of (commands list, applications list)
            - commands: All available commands
            - applications: Subset that are actual applications (BBS, CHAT, RMS, etc.)
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
        
        # Identify actual applications (interactive services)
        # Exclude standard BPQ/JNOS/FBB commands - only keep user-facing applications
        # Standard commands that are NOT applications:
        standard_commands = {
            # BPQ User Commands
            'BYE', 'CONNECT', 'C', 'DISCONNECT', 'D', 'INFO', 'I', 'NODES', 'N',
            'PORTS', 'ROUTES', 'USERS', 'U', 'MHEARD', 'MH', 'LINKS', 'L',
            'SESSION', 'S', 'YAPP', 'UNPROTO', 'VERSION', 'V', 'HOME', 'CQ',
            # BPQ Sysop Commands (uppercase only - avoids filtering 'Sysop' as text)
            'SYSOP', 'ATTACH', 'DETACH', 'RECONNECT', 'RESPTIME', 'FRACK',
            'FRACKS', 'PACLEN', 'MAXFRAME', 'RETRIES', 'RESET',
            # JNOS Commands
            'ARP', 'DIALER', 'DOMAIN', 'EXIT', 'FINGER', 'FTP', 'HELP',
            'HOPCHECK', 'IFCONFIG', 'IP', 'KICK', 'LOG', 'NETROM', 'PING',
            'PPP', 'RECORD', 'REMOTE', 'ROUTE', 'SMTP', 'START',
            'STOP', 'TCP', 'TRACE', 'UDP', 'UPLOAD',
            # FBB Commands
            'ABORT', 'CHECK', 'DIR', 'EXPERT', 'HELP', 'KILL', 'LIST',
            'READ', 'REPLY', 'SEND', 'STATS', 'TALK', 'VERBOSE', 'WHO'
        }
        
        # Built-in BPQ applications that should ALWAYS be counted as apps
        builtin_apps = {'BBS', 'CHAT', 'RMS', 'APRS', 'CHATSVR', 'MAIL'}
        
        # Filter applications: Include if:
        # 1. In builtin_apps (BBS, CHAT, RMS, etc.)
        # 2. Not in standard_commands (custom apps like GOPHER, EANHUB, TEST, FORMS, etc.)
        applications = []
        for cmd in commands:
            cmd_upper = cmd.upper()
            # Always include builtins
            if cmd_upper in builtin_apps:
                applications.append(cmd)
            # Include if not a standard command
            elif cmd_upper not in standard_commands:
                # Exclude node prompts (contain ':' or '}' like "CCEMA:WS1EC-15}")
                if ':' not in cmd and '}' not in cmd:
                    applications.append(cmd)
        
        return commands, applications
    
    def _parse_routes(self, output):
        """
        Parse ROUTES output to find best paths to destinations.
        
        ROUTES is the AUTHORITATIVE source for node SSIDs!
        Direct neighbor entries (lines starting with >) show the actual node SSID,
        not application SSIDs like BBS (-2), RMS (-10), or CHAT (-13).
        
        Example:
            > 1 K1NYY-15  200 13!   <- K1NYY-15 is the NODE (not K1NYY-2 BBS or K1NYY-10 RMS)
            > 1 KS1R-15   200 20!   <- KS1R-15 is the NODE (not KS1R-13 CHAT)
        
        Returns:
            Tuple of (routes dict, ports dict, ssids dict)
            - routes: {callsign: quality} for all routes
            - ports: {callsign: port_number} for direct neighbors only
            - ssids: {base_callsign: full_callsign-ssid} for direct neighbors (AUTHORITATIVE)
        """
        routes = {}
        ports = {}
        ssids = {}  # NEW: Store authoritative node SSIDs from ROUTES
        lines = output.split('\n')
        
        for line in lines:
            # Look for direct neighbor routes (start with >)
            # Format: "> PORT CALLSIGN-SSID QUALITY METRIC"
            # Example: "> 1 WS1EC-15  200 4!"
            if line.strip().startswith('>'):
                match = re.search(r'>\s+(\d+)\s+(\w+(?:-\d+)?)\s+(\d+)', line)
                if match:
                    port_num = int(match.group(1))
                    full_call = match.group(2)
                    quality = int(match.group(3))
                    base_call = full_call.split('-')[0]
                    
                    # Validate callsign format
                    if self._is_valid_callsign(base_call):
                        routes[base_call] = quality
                        ports[base_call] = port_num  # Store port for direct neighbors
                        ssids[base_call] = full_call  # AUTHORITATIVE node SSID
                        continue
            
            # Look for other route lines (non-direct neighbors)
            # Format: "  PORT CALLSIGN-SSID QUALITY METRIC"
            # Example: "  1 K1NYY-15  200 0!" (reachable via intermediate hop)
            # Skip routes with quality 0 (blocked/poor paths that sysop disabled)
            match = re.search(r'^\s+(\d+)\s+(\w+(?:-\d+)?)\s+(\d+)', line)
            if match:
                port_num = int(match.group(1))
                full_call = match.group(2)
                quality = int(match.group(3))
                base_call = full_call.split('-')[0]
                
                # Validate callsign format and skip quality 0 (blocked routes)
                if self._is_valid_callsign(base_call):
                    if quality > 0:
                        if base_call not in routes:  # Don't overwrite direct neighbor entries
                            routes[base_call] = quality
                            ssids[base_call] = full_call  # AUTHORITATIVE node SSID from ROUTES
                    elif self.verbose:
                        print("    Ignoring {} (quality 0 - sysop blocked route)".format(full_call))
        
        return routes, ports, ssids
    
    def crawl_node(self, callsign, path=[]):
        """
        Crawl a single node to discover neighbors.
        
        Args:
            callsign: Node callsign to crawl
            path: Connection path to reach this node
        """
        # Check if node is excluded
        if callsign in self.exclude:
            if self.verbose:
                print("  Skipping {} (excluded via --exclude)".format(callsign))
            return
        
        # Check if already visited based on crawl mode
        if callsign in self.visited:
            if self.crawl_mode == 'reaudit':
                # Re-audit mode: allow re-crawling known nodes
                if self.verbose:
                    print("  Re-auditing {} (reaudit mode)".format(callsign))
                self.visited.remove(callsign)  # Remove so we can re-crawl
            else:
                # Update or new-only mode: skip already visited
                return
        
        # In new-only mode, also skip nodes already in self.nodes (from nodemap.json)
        if self.crawl_mode == 'new-only' and callsign in self.nodes:
            if self.verbose:
                print("  Skipping {} (already in nodemap.json, new-only mode)".format(callsign))
            return
        
        # Build readable path description
        if not path:
            if callsign == self.callsign:
                path_desc = " (local node)"
            else:
                path_desc = " (direct connection)"
        else:
            path_desc = " (via {})".format(' > '.join(path))
        
        colored_print("Crawling {}{}".format(callsign, path_desc), Colors.CYAN)
        
        # Don't add to visited yet - only after successful connection
        # This allows retrying via alternate paths if this path fails
        
        # Calculate command timeout based on path length
        # At 1200 baud simplex: ~10s per hop for command/response cycle
        # Base timeout 5s + 10s per hop, max 60s
        # hop_count = number of RF jumps from start node
        # path=[] means 0 hops (local node), path=[KC1JMH] means 1 hop, etc.
        hop_count = len(path) if path else (0 if callsign == self.callsign else 1)
        cmd_timeout = min(5 + (hop_count * 10), 60)
        
        # Notify about connection attempt before connecting
        if not path:
            if callsign != self.callsign:
                notify_msg = "Connecting to {}".format(callsign)
            else:
                notify_msg = "Connecting to {}".format(callsign)
        else:
            notify_msg = "{} connecting to {}".format(path[-1], callsign)
        self._send_notification(notify_msg)
        
        # Connect to node
        # path contains intermediate hops only (not target)
        # For local node: path=[] (no intermediate hops)
        # For direct neighbor: callsign=KC1JMH, path=[] -> connect with C KC1JMH-15
        # For multi-hop: callsign=KS1R, path=[KC1JMH] -> C KC1JMH-15, then C KS1R-15
        connect_path = path + [callsign] if path else ([callsign] if callsign != self.callsign else [])
        
        tn = self._connect_to_node(connect_path)
        
        # Send 'Starting crawl' notification after successful connection to local node
        if tn and not path and callsign == self.callsign:
            self._send_notification("Starting crawl from {}".format(callsign))
        if not tn:
            colored_print("  Skipping {} (connection failed)".format(callsign), Colors.YELLOW)
            
            # Track this as an intermittent/unreliable link
            # Don't add to self.failed - node may be reachable from other paths
            if path:
                # Multi-hop: track connection from last hop
                link_key = (path[-1], callsign)
            else:
                # Direct: track from local node
                link_key = (self.callsign if self.callsign else 'LOCAL', callsign)
            
            if link_key not in self.intermittent_links:
                self.intermittent_links[link_key] = []
            self.intermittent_links[link_key].append(time.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Show who failed to reach whom
            if not path:
                fail_msg = "Failed: {} unreachable".format(callsign)
            else:
                fail_msg = "{} failed to reach {}".format(path[-1], callsign)
            self._send_notification(fail_msg)
            
            # Note: NOT adding to self.failed - node can still be explored from other neighbors
            # This allows mapping intermittent/poor connections while still discovering the node
            return
        
        # Set overall operation timeout (commands + processing)
        # Allow more generous timeout for nodes with many neighbors
        # 6 minutes base + 4 minutes per hop (was 4min + 3min/hop)
        # RF at 1200 baud is slow; need patience for multi-hop responses
        operation_deadline = time.time() + 360 + (hop_count * 240)
        
        # Track partial crawl data in case of timeout
        partial_data = {
            'callsign': callsign,
            'path': path,
            'hop_distance': hop_count,
            'successful_path': path if path else ([] if callsign == self.callsign else [callsign]),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'partial': True  # Mark as incomplete
        }
        
        try:
            # Helper to check if we've exceeded deadline
            def check_deadline():
                if time.time() > operation_deadline:
                    colored_print("  Operation timeout for {} ({} hops)".format(callsign, hop_count), Colors.YELLOW)
                    # Save partial data before timeout
                    if partial_data.get('info') or partial_data.get('ports') or partial_data.get('neighbors'):
                        colored_print("  Saving partial crawl data for {}...".format(callsign), Colors.YELLOW)
                        self.nodes[callsign] = partial_data
                        self.visited.add(callsign)  # Mark as visited to avoid re-crawl loops
                    return True
                return False
            
            # Inter-command delay scales with hop count
            # Over multi-hop RF, need time for responses to fully arrive
            inter_cmd_delay = 1.0 + (hop_count * 0.5)  # 1s base + 0.5s per hop
            
            # First, try ? to discover available commands
            # Some nodes may not support standard BPQ commands
            if check_deadline():
                return
            try:
                help_output = self._send_command(tn, '?', timeout=cmd_timeout, expect_content=None)
                if self.verbose:
                    print("  Available commands: {}".format(' '.join(help_output.split()[:20])))  # Show first 20 words
                time.sleep(inter_cmd_delay)
            except Exception as e:
                if self.verbose:
                    print("  Note: ? command not available or failed: {}".format(e))
            
            # Get PORTS to identify RF ports
            if check_deadline():
                return
            ports_output = self._send_command(tn, 'PORTS', timeout=cmd_timeout, expect_content='Port')
            ports_list = self._parse_ports(ports_output)
            partial_data['ports'] = ports_list  # Save partial
            time.sleep(inter_cmd_delay)
            
            # Get NODES for alias mappings only (not for neighbor discovery)
            # NODES shows routing table (all reachable nodes), not RF neighbors
            if check_deadline():
                return
            nodes_output = self._send_command(tn, 'NODES', timeout=cmd_timeout, expect_content=':')
            all_aliases, netrom_ssids_from_nodes, _ = self._parse_nodes_aliases(nodes_output)
            # Discard neighbors_from_nodes - NODES is routing table, not neighbor list
            time.sleep(inter_cmd_delay)
            
            # Base callsign without SSID (for filtering self from neighbors)
            # e.g., when on KC1JMH-15, base_callsign = KC1JMH
            base_callsign = callsign.split('-')[0] if '-' in callsign else callsign
            
            # Separate this node's own aliases from other nodes' aliases
            # Own aliases: entries where the callsign matches current node's base callsign
            # Example: On WS1EC, own aliases are CCEMA:WS1EC-15, CCEBBS:WS1EC-2, etc.
            own_aliases = {}
            other_aliases = {}
            for alias, full_call in all_aliases.items():
                alias_base = full_call.split('-')[0]
                if alias_base == base_callsign:
                    own_aliases[alias] = full_call
                else:
                    other_aliases[alias] = full_call
            
            # Update global alias mappings from NODES (routing table)
            # These are useful for routing to other nodes
            # Prefer node aliases over service aliases (BBS, RMS, CHAT)
            for alias, full_call in other_aliases.items():
                base_call = full_call.split('-')[0]
                is_likely_node = self._is_likely_node_ssid(full_call)
                
                # Store alias mapping for documentation
                if base_call not in self.call_to_alias:
                    # New entry - add it
                    self.call_to_alias[base_call] = alias
                elif is_likely_node:
                    # Likely node SSID - replace existing suspicious SSID
                    self.call_to_alias[base_call] = alias
                # else: suspicious SSID and we already have a mapping - skip
                
                if alias not in self.alias_to_call:
                    self.alias_to_call[alias] = full_call
            
            # NOTE: Do NOT pre-populate netrom_ssid_map from NODES aliases here!
            # NODES aliases include BBS (-2), RMS (-10), CHAT (-13) etc.
            # These are APPLICATION SSIDs, not NODE SSIDs.
            # ROUTES is the authoritative source for node SSIDs (see below).
            
            # Get ROUTES for path optimization (BPQ only)
            # ROUTES is AUTHORITATIVE for node SSIDs - direct neighbor entries show actual node SSID
            if check_deadline():
                return
            routes_output = self._send_command(tn, 'ROUTES', timeout=cmd_timeout)
            routes, route_ports, routes_ssids = self._parse_routes(routes_output)
            partial_data['routes'] = routes  # Save partial
            # Update global route_ports with direct neighbor port info from this node
            self.route_ports.update(route_ports)
            
            # ROUTES SSIDs are AUTHORITATIVE for node connections
            # These are the actual node SSIDs (e.g., K1NYY-15), not app SSIDs (K1NYY-2 BBS, K1NYY-10 RMS)
            for call, ssid in routes_ssids.items():
                # Always update from ROUTES - it's authoritative
                self.netrom_ssid_map[call] = ssid
                self.ssid_source[call] = ('routes', time.time())
                if self.verbose:
                    print("    Node SSID from ROUTES: {} = {} (authoritative)".format(call, ssid))
            time.sleep(inter_cmd_delay)
            
            # Get MHEARD from each RF port to find actual RF neighbors
            # MHEARD shows stations recently heard on RF - actual connectivity
            # Also extract port numbers for each neighbor AND their SSIDs (for connections)
            # 
            # SSID Selection Priority:
            # 1. ROUTES (authoritative for direct neighbors - shows actual node SSID)
            # 2. MHEARD (fallback - what was heard on RF, may include apps/operators)
            # 
            # Do NOT use NODES aliases for SSIDs - they include app SSIDs like BBS, RMS, CHAT
            mheard_neighbors = []
            mheard_ports = {}  # {callsign: port_num}
            mheard_ssids = {}  # {base_callsign: 'CALLSIGN-SSID'} - from actual RF
            for port_info in ports_list:
                if port_info['is_rf']:
                    if check_deadline():
                        return
                    port_num = port_info['number']
                    mheard_output = self._send_command(tn, 'MHEARD {}'.format(port_num), timeout=cmd_timeout, expect_content='Heard')
                    time.sleep(inter_cmd_delay)
                    
                    # Parse MHEARD with full callsign-SSID info
                    lines = mheard_output.split('\n')
                    for line in lines:
                        # Skip header lines
                        if 'Heard List' in line or not line.strip():
                            continue
                        
                        # Look for callsign with SSID: "KC1JMH-15  00:00:00:03"
                        match = re.match(r'^(\w+(?:-\d+)?)\s+(\d+):(\d+):(\d+):(\d+)', line)
                        if match:
                            full_callsign = match.group(1)
                            base_call = full_callsign.split('-')[0]
                            
                            # Validate callsign format
                            if not self._is_valid_callsign(base_call):
                                continue
                            
                            # Check if this has a node SSID (contains -number)
                            # Stations without SSID are likely user stations or digipeaters
                            # They can't be crawled as nodes (no BPQ commands)
                            has_ssid = '-' in full_callsign
                            
                            # SSID Selection: Prefer ROUTES over MHEARD
                            # ROUTES shows actual node SSIDs; MHEARD may include apps/operators
                            if base_call in routes_ssids:
                                # Already have authoritative SSID from ROUTES - use it
                                if base_call not in mheard_ssids:
                                    mheard_ssids[base_call] = routes_ssids[base_call]
                                    if self.verbose:
                                        print("    {} in ROUTES as {} (authoritative)".format(base_call, routes_ssids[base_call]))
                            elif base_call in routes and routes[base_call] == 0:
                                # Station is in ROUTES but with quality 0 (sysop blocked)
                                if self.verbose and has_ssid:
                                    print("    Skipping {} (quality 0 in ROUTES - sysop blocked route)".format(full_callsign))
                                # Don't add to mheard_ssids or neighbors - skip this station
                                continue
                            elif base_call not in mheard_ssids:
                                # First MHEARD entry for this callsign, not in ROUTES
                                if has_ssid:
                                    mheard_ssids[base_call] = full_callsign
                                    if self.verbose:
                                        print("    MHEARD SSID for {}: {} (not in ROUTES table)".format(base_call, full_callsign))
                                else:
                                    # No SSID - likely user station, skip it
                                    if self.verbose:
                                        print("    MHEARD {} (no SSID - not a node, skipping)".format(full_callsign))
                                    continue
                            elif self.verbose and has_ssid:
                                # Already have SSID for this base call
                                existing = mheard_ssids[base_call]
                                existing_has_ssid = '-' in existing
                                # If we already have a no-SSID entry, replace with SSID entry
                                if not existing_has_ssid and has_ssid:
                                    mheard_ssids[base_call] = full_callsign
                                    print("    Upgraded {} to {} (found SSID)".format(existing, full_callsign))
                                else:
                                    print("    Ignoring {} (already have {})".format(full_callsign, existing))
                            
                            # Only add to neighbor list if it has an SSID (is a node)
                            # Stations without SSIDs can't be crawled
                            if has_ssid:
                                mheard_neighbors.append(base_call)
                                
                                # Store port info
                                if base_call not in mheard_ports:
                                    mheard_ports[base_call] = port_num
            
            # Update global netrom_ssid_map with MHEARD data
            # Priority: 1) ROUTES (already stored above - authoritative)
            #           2) Newer MHEARD (can overwrite older MHEARD, but not ROUTES)
            for call, ssid in mheard_ssids.items():
                source, timestamp = self.ssid_source.get(call, (None, 0))
                # Update if: no existing SSID, OR existing is from MHEARD and this is newer
                if call not in self.netrom_ssid_map or (source == 'mheard' and time.time() > timestamp + 3600):
                    self.netrom_ssid_map[call] = ssid
                    self.ssid_source[call] = ('mheard', time.time())
                    if self.verbose and call in self.netrom_ssid_map:
                        print("    Updated SSID from newer MHEARD: {} = {}".format(call, ssid))
            
            # Use MHEARD exclusively for neighbors (stations actually heard on RF with SSIDs)
            # Remove duplicates and exclude self (all SSIDs)
            all_neighbors = list(set([n for n in mheard_neighbors if n != base_callsign]))
            
            # Update global route_ports with MHEARD port info
            # Combine with ROUTES data (ROUTES takes precedence if both exist)
            for call, port in mheard_ports.items():
                if call not in self.route_ports:
                    self.route_ports[call] = port
                    if self.verbose:
                        print("    Port info from MHEARD: {} on port {}".format(call, port))
            
            # Mark which neighbors will be explored vs skipped
            # A neighbor is explored if: visited or failed (actual exploration attempt made)
            # A neighbor is unexplored if: not visited, not failed, but either exceeds hop limit or will be queued
            explored_neighbors = []
            unexplored_neighbors = []
            for neighbor in all_neighbors:
                if neighbor in self.visited or neighbor in self.failed:
                    # Actually visited or connection attempt failed
                    explored_neighbors.append(neighbor)
                elif hop_count + 1 > self.max_hops:
                    # Beyond hop limit, won't be visited
                    unexplored_neighbors.append(neighbor)
                else:
                    # Within hop limit, will be queued for future exploration
                    unexplored_neighbors.append(neighbor)
            
            # Get INFO
            if check_deadline():
                return
            info_output = self._send_command(tn, 'INFO', timeout=cmd_timeout)
            location = self._parse_info(info_output)
            time.sleep(inter_cmd_delay)
            
            # Get available commands (? command)
            if check_deadline():
                return
            commands_output = self._send_command(tn, '?', timeout=cmd_timeout)
            commands, applications = self._parse_commands(commands_output)
            
            # Detect node type
            node_type = self._detect_node_type(info_output, '>:')
            
            # Store node data
            # Note: INFO-derived data (location, applications, type from keywords) is marked
            # with 'source' to indicate reliability. Structured command data is preferred.
            
            # Find which neighbors are intermittent (failed connections from this node)
            intermittent_neighbors = []
            for neighbor in all_neighbors:
                link_key = (callsign, neighbor)
                if link_key in self.intermittent_links:
                    intermittent_neighbors.append(neighbor)
            
            # Extract top-level fields for convenience
            primary_alias = list(own_aliases.keys())[0] if own_aliases else None
            gridsquare = location.get('grid', None)
            
            # Get successful connection path from shortest_paths (if available)
            successful_path = self.shortest_paths.get(callsign, path)
            
            self.nodes[callsign] = {
                'info': info_output.strip(),
                'alias': primary_alias,  # Primary NetRom alias (extracted from own_aliases)
                'gridsquare': gridsquare,  # Maidenhead locator (extracted from location)
                'neighbors': all_neighbors,  # Direct RF neighbors from MHEARD (with SSIDs only)
                'explored_neighbors': explored_neighbors,  # Neighbors that were/will be visited
                'unexplored_neighbors': unexplored_neighbors,  # Neighbors skipped (hop limit)
                'intermittent_neighbors': intermittent_neighbors,  # Neighbors with failed connections
                'hop_distance': hop_count,  # RF hops from start node
                'successful_path': successful_path,  # Intermediate nodes used to reach this node
                'location': location,  # From INFO (unreliable, sysop-entered)
                'location_source': 'info',  # Mark as low-confidence
                'ports': ports_list,  # From PORTS (reliable)
                'heard_on_ports': [(call, mheard_ports.get(call)) for call in all_neighbors],
                'type': node_type,  # From INFO or prompt (low/medium confidence)
                'type_source': 'info' if 'BPQ' in info_output.upper() or 'FBB' in info_output.upper() else 'prompt',
                'routes': routes,  # From ROUTES (reliable)
                'own_aliases': own_aliases,  # This node's aliases (CCEMA:WS1EC-15, etc.)
                'seen_aliases': other_aliases,  # Other nodes' aliases seen in NODES
                'netrom_ssids': mheard_ssids,  # From MHEARD (actual RF transmissions)
                'applications': applications,  # From ? command (BBS, CHAT, RMS, etc.)
                'commands': commands  # From ? command (all available commands)
            }
            
            # If this node was crawled with a CLI-forced SSID, update its netrom_ssids entry
            # This ensures the corrected SSID persists in the JSON for future crawls
            base_call = callsign.split('-')[0] if '-' in callsign else callsign
            if base_call in self.cli_forced_ssids:
                forced_ssid = self.cli_forced_ssids[base_call]
                self.nodes[callsign]['netrom_ssids'][base_call] = forced_ssid
                if self.verbose:
                    print("  Updated netrom_ssids: {} = {} (CLI-forced)".format(base_call, forced_ssid))
            
            # Record connections - only for neighbors in ROUTES with non-zero quality
            # MHEARD shows all stations heard on RF, but ROUTES shows actual routing neighbors
            for neighbor in all_neighbors:
                # Check if neighbor is in ROUTES (has a route entry)
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                if neighbor_base not in routes:
                    continue  # Skip neighbors not in ROUTES (not routing nodes)
                
                quality = routes.get(neighbor_base, 0)
                if quality == 0:
                    continue  # Skip quality 0 routes (sysop blocked)
                
                link_key = (callsign, neighbor)
                is_intermittent = link_key in self.intermittent_links
                
                self.connections.append({
                    'from': callsign,
                    'to': neighbor,
                    'port': None,
                    'quality': quality,
                    'intermittent': is_intermittent  # Mark unreliable/failed connections
                })
                
                # Add unvisited neighbors to queue - allow multiple paths per node
                # Queue all valid paths, prioritized by route quality from current node
                # Only queue if within hop limit (next hop would be hop_count + 1)
                # Note: We don't check self.failed here - nodes with intermittent connections
                # can still be explored from other neighbors (better paths)
                if neighbor not in self.visited and hop_count + 1 <= self.max_hops:
                    # Determine path to this neighbor (intermediate hops only, not target)
                    # If we're at local node WS1EC (path=[], callsign==self.callsign), queue KC1JMH with path=[]
                    #   (direct connection from local, no intermediate hops)
                    # If we're at KC1JMH (path=[], callsign!=self.callsign), queue KS1R with path=[KC1JMH]
                    #   (go through KC1JMH to reach KS1R)
                    # If we're at KS1R (path=[KC1JMH]), queue N1XP with path=[KC1JMH, KS1R]
                    #   (go through KC1JMH, then KS1R, to reach N1XP)
                    if path:
                        # We're not at local node, path contains route to current node
                        # Current node becomes an intermediate hop to reach neighbor
                        new_path = path + [callsign]
                    elif callsign == self.callsign:
                        # We're at the actual local node, direct connection to neighbor (no intermediate hops)
                        new_path = []
                    else:
                        # We're at a direct neighbor of local node (path=[] but not local node)
                        # Need to route through this node to reach its neighbors
                        new_path = [callsign]
                    
                    # Skip if neighbor is already in the path (prevents routing loops)
                    # Example: At KS1R via KC1JMH, don't route back through KC1JMH to reach KC1JMH
                    if neighbor in new_path or neighbor == self.callsign:
                        if self.verbose:
                            print("    Skipping {} (already in path: {})".format(neighbor, ' > '.join(new_path) if new_path else 'local'))
                        continue
                    
                    # Track shortest path for reference (but queue all paths)
                    if neighbor not in self.shortest_paths or len(new_path) < len(self.shortest_paths[neighbor]):
                        self.shortest_paths[neighbor] = new_path
                    
                    # Get route quality from current node to this neighbor
                    route_quality = routes.get(neighbor, 0)
                    
                    # Skip quality 0 routes (sysop-blocked/poor paths)
                    if route_quality == 0:
                        if self.verbose:
                            print("    Skipping {} via {} (route quality 0)".format(neighbor, callsign))
                        continue
                    
                    # Check if we've already queued this exact path
                    path_key = (neighbor, tuple(new_path))
                    if path_key in self.queued_paths:
                        if self.verbose:
                            print("    Skipping duplicate path to {} via {}".format(neighbor, ' > '.join(new_path) if new_path else 'direct'))
                        continue
                    
                    # Skip nodes that haven't been heard in over 24 hours (likely offline)
                    # 86400 seconds = 24 hours
                    stale_threshold = 86400
                    neighbor_age = self.last_heard.get(neighbor, 0)
                    
                    if neighbor_age > stale_threshold:
                        if self.verbose:
                            days = neighbor_age // 86400
                            hours = (neighbor_age % 86400) // 3600
                            print("    Skipping {} (stale: {}d {}h ago)".format(neighbor, days, hours))
                        continue
                    
                    # Queue this path with quality (for prioritization)
                    self.queue.append((neighbor, new_path, route_quality))
                    self.queued_paths.add(path_key)
            
            print("  Found {} neighbors: {}".format(
                len(all_neighbors),
                ', '.join(all_neighbors)
            ))
            print("  Node type: {}".format(node_type))
            print("  RF Ports: {}".format(len([p for p in ports_list if p['is_rf']])))
            print("  Applications: {} ({})".format(len(applications), ', '.join(applications) if applications else 'none'))
            print("  Commands: {}".format(len(commands)))
            if own_aliases:
                print("  Own Aliases: {}".format(len(own_aliases)))
            
            # Notify after successful crawl
            if not path:
                if callsign == self.callsign:
                    notify_msg = "{}: {} neighbors".format(callsign, len(all_neighbors))
                else:
                    notify_msg = "{}: {} neighbors".format(callsign, len(all_neighbors))
            else:
                notify_msg = "{}: {} neighbors".format(callsign, len(all_neighbors))
            self._send_notification(notify_msg)
            
            # Mark as successfully visited after crawl completes
            self.visited.add(callsign)
            
        finally:
            # Disconnect
            try:
                tn.write(b'BYE\r')
                time.sleep(0.5)
            except:
                pass
            tn.close()
    
    def crawl_network(self, start_node=None, forced_target=None):
        """
        Crawl entire network starting from specified or local node.
        
        Args:
            start_node: Callsign to start crawl from (default: local node)
        """
        # Resume mode OR new-only mode: load unexplored nodes from existing data
        if self.resume or self.crawl_mode == 'new-only':
            resume_filename = self.resume_file if self.resume_file else 'nodemap.json'
            mode_name = "Resume" if self.resume else "New-only"
            print("{} mode: Loading unexplored nodes from {}...".format(mode_name, resume_filename))
            unexplored = self._load_unexplored_nodes(resume_filename)
            
            if not unexplored:
                print("No unexplored nodes found.")
                if len(self.visited) > 0:
                    print("All {} previously crawled nodes have been fully explored.".format(len(self.visited)))
                    colored_print("Use normal mode to start a fresh crawl or increase max hops.", Colors.YELLOW)
                else:
                    colored_print("No previous crawl data found. Use normal mode to start a fresh crawl.", Colors.RED)
                return
            
            # Queue all unexplored nodes (with default quality for resume)
            for callsign, path in unexplored:
                self.queue.append((callsign, path, 255))  # Default high quality for resume paths
            
            colored_print("Queued {} unexplored nodes for crawling".format(len(unexplored)), Colors.GREEN)
            mode_name = "Resume" if self.resume else "New-only"
            self._send_notification("{} crawl: {} unexplored nodes".format(mode_name, len(unexplored)))
            
            # In resume/new-only mode, we don't have a single starting callsign
            starting_callsign = None
            
            # Skip the normal start node logic
            print("BPQ node: {}:{}".format(self.host, self.port))
            print("Max hops: {}".format(self.max_hops))
            print("-" * 50)
        else:
            # Normal mode: start from specified or local node
            # Determine starting node
            starting_path = []  # Path to reach the starting node
            
            # Pre-load route information from existing nodemap.json if available
            # Needed for both start_node and forced_target path-finding
            existing = self._load_existing_data('nodemap.json')
            
            if start_node:
                # Validate provided callsign
                if not self._is_valid_callsign(start_node):
                    colored_print("Error: Invalid callsign format: {}".format(start_node), Colors.RED)
                    return
                starting_callsign = start_node.upper()
                print("Starting network crawl from: {}...".format(starting_callsign))
                
                if existing and 'nodes' in existing:
                    nodes_data = existing['nodes']
                    
                    if self.verbose:
                        print("Loaded existing data with {} nodes: {}".format(
                            len(nodes_data), 
                            ', '.join(sorted(nodes_data.keys()))))
                    
                    # Restore SSID mappings and route ports from all nodes
                    # Process in two passes: first nodes themselves (authoritative), then neighbors' observations
                    node_calls_sorted = sorted(nodes_data.keys(), 
                                              key=lambda k: (nodes_data[k].get('hop_distance', 999), k))
                    
                    for node_call in node_calls_sorted:
                        node_info = nodes_data[node_call]
                        
                        # Get node's own SSID from own_aliases (most authoritative)
                        # Prefer the primary node alias (matches node's alias field)
                        own_aliases = node_info.get('own_aliases', {})
                        node_alias_name = node_info.get('alias', '')  # Primary alias name
                        node_ssid = None
                        
                        # First try: use the SSID from the primary node alias
                        if node_alias_name and node_alias_name in own_aliases:
                            node_ssid = own_aliases[node_alias_name]
                        
                        # Fallback: find any alias where base matches node call and SSID is in valid range
                        if not node_ssid:
                            for alias, full_call in own_aliases.items():
                                base = full_call.split('-')[0] if '-' in full_call else full_call
                                if base == node_call and self._is_likely_node_ssid(full_call):
                                    node_ssid = full_call
                                    break
                        
                        # Store node's own SSID first (authoritative)
                        if node_ssid:
                            self.netrom_ssid_map[node_call] = node_ssid
                        
                        # Restore netrom_ssids (for connection commands)
                        for base_call, full_call in node_info.get('netrom_ssids', {}).items():
                            # Only set if not already set (node's own SSID takes precedence)
                            # And only if it's a likely node SSID (filter port-specific SSIDs)
                            if base_call not in self.netrom_ssid_map and self._is_likely_node_ssid(full_call):
                                self.netrom_ssid_map[base_call] = full_call
                        
                        # Restore route_ports (port numbers for neighbors)
                        for neighbor_call, port_num in node_info.get('heard_on_ports', []):
                            if port_num is not None and neighbor_call not in self.route_ports:
                                self.route_ports[neighbor_call] = port_num
                        
                        # Restore call_to_alias mappings (for NetRom routing)
                        # Prefer node aliases over service aliases
                        for alias, full_call in node_info.get('seen_aliases', {}).items():
                            base_call = full_call.split('-')[0]
                            is_likely_node = self._is_likely_node_ssid(full_call)
                            
                            if base_call not in self.call_to_alias:
                                # New entry - add it
                                self.call_to_alias[base_call] = alias
                                self.alias_to_call[alias] = full_call
                            elif is_likely_node:
                                # Likely node SSID - replace existing suspicious SSID
                                self.call_to_alias[base_call] = alias
                                self.alias_to_call[alias] = full_call
                            # else: suspicious SSID and we already have a mapping - skip
                    
                    if self.route_ports:
                        if self.verbose:
                            print("Loaded {} port mappings from existing nodemap.json".format(len(self.route_ports)))
                    
                    if self.call_to_alias:
                        if self.verbose:
                            print("Loaded {} NetRom aliases from existing nodemap.json".format(len(self.call_to_alias)))
                    
                    # Find path to remote start node through existing network
                    # Use BFS to find shortest path from local node to target
                    if starting_callsign != self.callsign:
                        # Not the local node - need to find how to reach it
                        target_base = starting_callsign.split('-')[0] if '-' in starting_callsign else starting_callsign
                        
                        # If user provided base callsign, look up the node SSID
                        # CLI-forced SSIDs take precedence over discovered SSIDs
                        if '-' not in starting_callsign:
                            resolved_ssid = self.cli_forced_ssids.get(target_base) or self.netrom_ssid_map.get(target_base)
                            if resolved_ssid and '-' in resolved_ssid:
                                starting_callsign = resolved_ssid
                                if self.verbose:
                                    source = "CLI-forced" if target_base in self.cli_forced_ssids else "discovered"
                                    print("Resolved {} to node SSID: {} ({})".format(target_base, resolved_ssid, source))
                        
                        # User can force specific SSID via netrom_ssid_map (pre-populated by --callsign)
                        # This overrides any discovered SSID
                        
                        # Check if target is actually a node (has SSID) vs user station
                        # CLI-forced SSIDs take precedence
                        target_ssid = self.cli_forced_ssids.get(target_base) or self.netrom_ssid_map.get(target_base)
                        if not target_ssid or '-' not in target_ssid:
                            # No SSID means it's a user station, not a node
                            colored_print("Error: {} appears to be a user station, not a node (no SSID in network data)".format(target_base), Colors.RED)
                            colored_print("User stations don't run BPQ node software and can't be crawled.", Colors.YELLOW)
                            
                            # Suggest other unexplored neighbors that ARE nodes
                            other_unexplored = []
                            for node_call, node_info in nodes_data.items():
                                for neighbor in node_info.get('unexplored_neighbors', []):
                                    neighbor_ssid = self.netrom_ssid_map.get(neighbor)
                                    if neighbor != target_base and neighbor_ssid and '-' in neighbor_ssid:
                                        if neighbor not in other_unexplored:
                                            other_unexplored.append(neighbor)
                            
                            if other_unexplored:
                                colored_print("Try one of these unexplored nodes instead: {}".format(', '.join(sorted(other_unexplored)[:10])), Colors.CYAN)
                            return
                        
                        if self.verbose:
                            print("Looking for path to {} among known neighbors...".format(target_base))
                        
                        # BFS to find shortest path
                        queue = [(self.callsign, [])]  # (current_node, path_to_current)
                        visited = {self.callsign}
                        found_path = False
                        
                        while queue and not found_path:
                            current, path = queue.pop(0)
                            current_info = nodes_data.get(current, {})
                            neighbors = current_info.get('neighbors', [])
                            
                            if self.verbose and neighbors:
                                print("  {} has neighbors: {}".format(current, ', '.join(neighbors)))
                            
                            for neighbor in neighbors:
                                if neighbor in visited:
                                    continue
                                visited.add(neighbor)
                                
                                # Build path to this neighbor
                                new_path = path + [neighbor]
                                
                                # Check if this neighbor is the target
                                if neighbor == target_base:
                                    # Found target - use path excluding target itself
                                    starting_path = path if path else []
                                    if self.verbose:
                                        if starting_path:
                                            print("Found {} reachable via: {}".format(target_base, ' -> '.join(starting_path)))
                                        else:
                                            print("Found {} as direct neighbor of local node {}".format(target_base, self.callsign))
                                    found_path = True
                                    break
                                
                                # Check if this neighbor node has the target as ITS neighbor
                                neighbor_info = nodes_data.get(neighbor, {})
                                neighbor_neighbors = neighbor_info.get('neighbors', [])
                                if self.verbose:
                                    print("    Checking {} neighbors: {} (looking for {})".format(neighbor, neighbor_neighbors[:5] if len(neighbor_neighbors) > 5 else neighbor_neighbors, target_base))
                                if target_base in neighbor_neighbors:
                                    # Target is neighbor of this node - path goes through this node
                                    starting_path = new_path
                                    if self.verbose:
                                        print("Found {} reachable via: {}".format(target_base, ' -> '.join(starting_path)))
                                    found_path = True
                                    break
                                
                                # Add to queue for further exploration
                                queue.append((neighbor, new_path))
                        
                        if not found_path:
                            # Target not found in neighbor lists - check direct neighbors from local node
                            local_node_info = nodes_data.get(self.callsign, {})
                            local_neighbors = local_node_info.get('neighbors', [])
                            local_routes = local_node_info.get('routes', {})
                            
                            # Find which direct neighbors have heard the target
                            direct_nodes_that_heard = []
                            for neighbor in local_neighbors:
                                neighbor_info = nodes_data.get(neighbor, {})
                                neighbor_neighbors = neighbor_info.get('neighbors', [])
                                if target_base in neighbor_neighbors:
                                    # Get route quality from local node to this neighbor
                                    quality = local_routes.get(neighbor, 0)
                                    direct_nodes_that_heard.append((neighbor, quality))
                            
                            if direct_nodes_that_heard:
                                if self.verbose:
                                    colored_print("Warning: {} not found in any known node's neighbor list".format(target_base), Colors.YELLOW)
                                
                                # Sort by route quality (best first), then alphabetically
                                sorted_nodes = sorted(direct_nodes_that_heard, key=lambda x: (-x[1], x[0]))
                                
                                print("")
                                print("{} has been heard by these direct neighbors:".format(target_base))
                                for i, (node, quality) in enumerate(sorted_nodes, 1):
                                    node_info = nodes_data.get(node, {})
                                    grid = node_info.get('location', {}).get('grid', 'unknown')
                                    print("  {}) {} ({}, quality {})".format(i, node, grid, quality))
                                print("")
                                
                                # Prompt user to choose intermediate node
                                try:
                                    choice = input("Choose a node to connect through (1-{}, or blank to skip): ".format(len(sorted_nodes))).strip()
                                    
                                    if not choice:
                                        colored_print("Skipping {} - no path specified".format(target_base), Colors.YELLOW)
                                        return
                                    
                                    choice_idx = int(choice) - 1
                                    if choice_idx < 0 or choice_idx >= len(sorted_nodes):
                                        colored_print("Error: Invalid choice", Colors.RED)
                                        return
                                    
                                    intermediate_node = sorted_nodes[choice_idx][0]
                                    print("Selected: {} -> {}".format(intermediate_node, target_base))
                                    
                                    # Intermediate is a direct neighbor, so path is just [intermediate, target]
                                    starting_path = [intermediate_node, target_ssid]
                                    if self.verbose:
                                        print("Built path: {}".format(' -> '.join(starting_path)))
                                    found_path = True
                                        
                                except (ValueError, KeyboardInterrupt, EOFError):
                                    print("")
                                    colored_print("Cancelled", Colors.YELLOW)
                                    return
                            else:
                                # No direct neighbors have heard it - search all nodes
                                all_nodes_that_heard = []
                                for node_call, node_info in nodes_data.items():
                                    if node_call == self.callsign:
                                        continue  # Already checked direct neighbors above
                                    neighbor_neighbors = node_info.get('neighbors', [])
                                    if target_base in neighbor_neighbors:
                                        all_nodes_that_heard.append(node_call)
                                
                                if all_nodes_that_heard:
                                    # Calculate hop distances for sorting
                                    node_hop_quality = []
                                    for node in all_nodes_that_heard:
                                        queue_dist = [(self.callsign, [], 0)]
                                        visited_dist = {self.callsign}
                                        
                                        while queue_dist:
                                            current, path, hops = queue_dist.pop(0)
                                            
                                            if current == node:
                                                node_hop_quality.append((node, hops, path))
                                                break
                                            
                                            current_info = nodes_data.get(current, {})
                                            current_routes = current_info.get('routes', {})
                                            for neighbor in current_info.get('neighbors', []):
                                                if neighbor not in visited_dist:
                                                    visited_dist.add(neighbor)
                                                    new_path = path + [neighbor]
                                                    queue_dist.append((neighbor, new_path, hops + 1))
                                    
                                    # Sort by hop count (closest first), then alphabetically
                                    sorted_nodes = sorted(node_hop_quality, key=lambda x: (x[1], x[0]))
                                    
                                    if sorted_nodes:
                                        print("")
                                        print("{} has been heard by these nodes:".format(target_base))
                                        for i, (node, hops, path) in enumerate(sorted_nodes, 1):
                                            node_info = nodes_data.get(node, {})
                                            grid = node_info.get('location', {}).get('grid', 'unknown')
                                            hop_str = "{} hop{}".format(hops, '' if hops == 1 else 's')
                                            print("  {}) {} ({}, {})".format(i, node, grid, hop_str))
                                        print("")
                                        
                                        # Prompt user to choose intermediate node
                                        try:
                                            choice = input("Choose a node to connect through (1-{}, or blank to skip): ".format(len(sorted_nodes))).strip()
                                            
                                            if not choice:
                                                colored_print("Skipping {} - no path specified".format(target_base), Colors.YELLOW)
                                                return
                                            
                                            choice_idx = int(choice) - 1
                                            if choice_idx < 0 or choice_idx >= len(sorted_nodes):
                                                colored_print("Error: Invalid choice", Colors.RED)
                                                return
                                            
                                            intermediate_node, hops, intermediate_path = sorted_nodes[choice_idx]
                                            print("Selected: {} -> {}".format(intermediate_node, target_base))
                                            
                                            # Build complete path: intermediate_path + target
                                            starting_path = intermediate_path + [target_ssid]
                                            if self.verbose:
                                                print("Built path: {}".format(' -> '.join(starting_path)))
                                            found_path = True
                                                
                                        except (ValueError, KeyboardInterrupt, EOFError):
                                            print("")
                                            colored_print("Cancelled", Colors.YELLOW)
                                            return
                                    else:
                                        # No nodes heard it - continue to all-nodes fallback
                                        pass
                                else:
                                    # Truly unknown - not heard by anyone
                                    # Fall back to manual selection from all known nodes
                                    all_known_nodes = [(n, nodes_data.get(n, {}).get('location', {}).get('grid', 'unknown'), 
                                                       len(nodes_data.get(n, {}).get('neighbors', []))) 
                                                      for n in nodes_data.keys() if n != self.callsign and n != target_base]
                                    
                                    if all_known_nodes:
                                        colored_print("Warning: {} not found in any neighbor list in topology data".format(target_base), Colors.YELLOW)
                                        print("")
                                        print("Available nodes to route through:")
                                        # Sort by number of neighbors (most connected first)
                                        sorted_all = sorted(all_known_nodes, key=lambda x: (-x[2], x[0]))
                                        for i, (node, grid, num_neighbors) in enumerate(sorted_all, 1):
                                            print("  {}) {} ({}, {} neighbors)".format(i, node, grid, num_neighbors))
                                        print("")
                                        
                                        try:
                                            choice = input("Choose a node to connect through (1-{}, or blank to skip): ".format(len(sorted_all))).strip()
                                            
                                            if not choice:
                                                colored_print("Skipping {} - no path specified".format(target_base), Colors.YELLOW)
                                                return
                                            
                                            choice_idx = int(choice) - 1
                                            if choice_idx < 0 or choice_idx >= len(sorted_all):
                                                colored_print("Error: Invalid choice", Colors.RED)
                                                return
                                            
                                            intermediate_node = sorted_all[choice_idx][0]
                                            print("Selected: {} -> {}".format(intermediate_node, target_base))
                                            
                                            # Find path to intermediate
                                            queue_to_int = [(self.callsign, [])]
                                            visited_to_int = {self.callsign}
                                            path_to_int = None
                                            
                                            while queue_to_int:
                                                curr, path = queue_to_int.pop(0)
                                                if curr == intermediate_node:
                                                    path_to_int = path
                                                    break
                                                curr_info = nodes_data.get(curr, {})
                                                for nbr in curr_info.get('neighbors', []):
                                                    if nbr not in visited_to_int:
                                                        visited_to_int.add(nbr)
                                                        queue_to_int.append((nbr, path + [nbr]))
                                            
                                            if path_to_int is not None:
                                                # Build complete path
                                                starting_path = path_to_int + [target_ssid]
                                                if self.verbose:
                                                    print("Built path: {}".format(' -> '.join(starting_path)))
                                                found_path = True
                                            else:
                                                colored_print("Error: Cannot find path to {}".format(intermediate_node), Colors.RED)
                                                return
                                                
                                        except (ValueError, KeyboardInterrupt, EOFError):
                                            print("")
                                            colored_print("Cancelled", Colors.YELLOW)
                                            return
                                    else:
                                        colored_print("Error: No nodes in topology to route through", Colors.RED)
                                        colored_print("Try crawling more nodes first to build the network topology", Colors.YELLOW)
                                        return
                                    
                                    # If we got here and still no path, allow manual callsign entry
                                    if not found_path:
                                        print("")
                                        colored_print("Unable to find automatic path to {}".format(target_base), Colors.YELLOW)
                                        print("You can manually specify an intermediate node callsign.")
                                        print("")
                                        
                                        try:
                                            manual_node = input("Enter intermediate node callsign (or blank to cancel): ").strip().upper()
                                            
                                            if not manual_node:
                                                colored_print("Cancelled", Colors.YELLOW)
                                                return
                                            
                                            # Validate it's in the topology
                                            if manual_node not in nodes_data:
                                                colored_print("Error: {} not found in network topology".format(manual_node), Colors.RED)
                                                return
                                            
                                            print("Selected: {} -> {}".format(manual_node, target_base))
                                            
                                            # Find path to manual node
                                            queue_to_manual = [(self.callsign, [])]
                                            visited_to_manual = {self.callsign}
                                            path_to_manual = None
                                            
                                            while queue_to_manual:
                                                curr, path = queue_to_manual.pop(0)
                                                if curr == manual_node:
                                                    path_to_manual = path
                                                    break
                                                curr_info = nodes_data.get(curr, {})
                                                for nbr in curr_info.get('neighbors', []):
                                                    if nbr not in visited_to_manual:
                                                        visited_to_manual.add(nbr)
                                                        queue_to_manual.append((nbr, path + [nbr]))
                                            
                                            if path_to_manual is not None:
                                                starting_path = path_to_manual + [target_ssid]
                                                if self.verbose:
                                                    print("Built path: {}".format(' -> '.join(starting_path)))
                                                found_path = True
                                            else:
                                                colored_print("Error: Cannot find path to {}".format(manual_node), Colors.RED)
                                                return
                                                
                                        except (KeyboardInterrupt, EOFError):
                                            print("")
                                            colored_print("Cancelled", Colors.YELLOW)
                                            return
                else:
                    if self.verbose:
                        print("No existing nodemap.json found or no nodes in it")
                        print("Will attempt NetRom discovery when connecting to local node")
            else:
                if not self.callsign:
                    colored_print("Error: Could not determine local node callsign from bpq32.cfg.", Colors.RED)
                    colored_print("Please ensure NODECALL is set in your bpq32.cfg file.", Colors.RED)
                    colored_print("Or provide a starting callsign: {} [MAX_HOPS] [START_NODE]".format(sys.argv[0]), Colors.RED)
                    return
                starting_callsign = self.callsign
                colored_print("Starting network crawl from local node: {}...".format(starting_callsign), Colors.GREEN)
            
            # Handle forced_target (from --callsign flag)
            # This means we want to crawl TO a specific target node, not start FROM it
            if forced_target and not start_node:
                # Find path to forced target through existing topology
                target_base = forced_target
                target_ssid = self.cli_forced_ssids.get(target_base) or self.netrom_ssid_map.get(target_base)
                
                if not target_ssid:
                    colored_print("Error: No SSID found for {} in network data".format(target_base), Colors.RED)
                    return
                
                if self.verbose:
                    print("Finding path to forced target: {} ({})".format(target_base, target_ssid))
                
                # Use the same BFS path-finding logic from start_node handling
                nodes_data = existing.get('nodes', {}) if existing else {}
                if not nodes_data:
                    colored_print("Error: No topology data available for path finding", Colors.RED)
                    colored_print("Run a full crawl first to build network map", Colors.YELLOW)
                    return
                
                # Populate netrom_ssid_map and route_ports from topology data
                # Priority: 1) Node's own SSID (from routes where it's listed as direct neighbor)
                #           2) netrom_ssids from other nodes
                for node_call, node_info in nodes_data.items():
                    # First, store the node's own SSID (this is authoritative)
                    # The key in nodes_data IS the authoritative SSID (e.g., "KC1JMH-15")
                    base_node = node_call.split('-')[0] if '-' in node_call else node_call
                    if '-' in node_call and base_node not in self.netrom_ssid_map:
                        self.netrom_ssid_map[base_node] = node_call
                        self.ssid_source[base_node] = ('routes', time.time())
                    
                    # Then store SSIDs this node knows about (secondary)
                    for base_call, full_call in node_info.get('netrom_ssids', {}).items():
                        # Only set if we don't have an authoritative source already
                        if base_call not in self.netrom_ssid_map:
                            self.netrom_ssid_map[base_call] = full_call
                            self.ssid_source[base_call] = ('topology', time.time())
                    
                    # Store route ports (which port neighbors are heard on)
                    for neighbor_call, port_num in node_info.get('heard_on_ports', []):
                        if port_num is not None and neighbor_call not in self.route_ports:
                            self.route_ports[neighbor_call] = port_num
                
                if self.verbose:
                    print("Loaded {} SSID mappings and {} port mappings from topology".format(
                        len(self.netrom_ssid_map), len(self.route_ports)))
                
                # BFS to find shortest path
                queue = [(self.callsign, [])]
                visited = {self.callsign}
                found_path = False
                forced_path = []
                
                if self.verbose:
                    print("Starting BFS from {} (looking for {})".format(self.callsign, target_base))
                    print("Available nodes in topology: {}".format(', '.join(sorted(nodes_data.keys()))))
                
                while queue and not found_path:
                    current, path = queue.pop(0)
                    current_info = nodes_data.get(current, {})
                    neighbors = current_info.get('neighbors', [])
                    
                    if self.verbose and neighbors:
                        print("  Checking {} neighbors: {}".format(current, neighbors))
                    
                    for neighbor in neighbors:
                        if neighbor in visited:
                            continue
                        visited.add(neighbor)
                        new_path = path + [neighbor]
                        
                        if neighbor == target_base:
                            forced_path = path
                            found_path = True
                            if self.verbose:
                                if forced_path:
                                    print("Found {} reachable via: {}".format(target_base, ' -> '.join(forced_path)))
                                else:
                                    print("Found {} as direct neighbor".format(target_base))
                            break
                        
                        # Try to look up neighbor by name, or by resolved SSID if it's a base call
                        neighbor_info = nodes_data.get(neighbor, {})
                        if not neighbor_info and '-' not in neighbor:
                            # Neighbor is base call, try to resolve to SSID
                            neighbor_ssid = self.netrom_ssid_map.get(neighbor)
                            if neighbor_ssid:
                                neighbor_info = nodes_data.get(neighbor_ssid, {})
                                if self.verbose and neighbor_info:
                                    print("    Resolved {} to {}".format(neighbor, neighbor_ssid))
                        
                        neighbor_neighbors = neighbor_info.get('neighbors', [])
                        if self.verbose and neighbor_neighbors:
                            print("    {} has neighbors: {} (looking for {})".format(neighbor, neighbor_neighbors[:5] if len(neighbor_neighbors) > 5 else neighbor_neighbors, target_base))
                        if target_base in neighbor_neighbors:
                            forced_path = new_path
                            found_path = True
                            if self.verbose:
                                print("Found {} reachable via: {}".format(target_base, ' -> '.join(forced_path)))
                            break
                        
                        queue.append((neighbor, new_path))
                
                if found_path:
                    # Queue the target with found path
                    starting_callsign = target_ssid
                    starting_path = forced_path
                    if self.verbose:
                        print("Queuing {} with path: {}".format(target_ssid, ' -> '.join(forced_path) if forced_path else "(direct)"))
                else:
                    colored_print("Error: Cannot find path to {} in topology".format(target_base), Colors.RED)
                    return
            
            print("BPQ node: {}:{}".format(self.host, self.port))
            print("Max hops: {}".format(self.max_hops))
            print("-" * 50)
            
            # Start with specified or local node (with path if remote)
            # path contains intermediate hops only (not the target node itself)
            queue_entry = (starting_callsign, starting_path if start_node or forced_target else [], 255)  # Default high quality
            if self.verbose and (start_node or forced_target):
                print("Queuing {} with path: {}".format(starting_callsign, starting_path if starting_path else "(direct)"))
            self.queue.append(queue_entry)
        
        # BFS traversal with priority sorting:
        # 1. Route quality (higher = better, 0 = blocked)
        # 2. Hop count (fewer = faster/more reliable)
        # 3. MHEARD recency (more recent = likely still active)
        while self.queue:
            # Sort queue by quality (desc), then hop count (asc), then MHEARD recency (asc)
            # Quality 255 = excellent, 192 = good, 0 = blocked
            queue_list = list(self.queue)
            queue_list.sort(key=lambda x: (-x[2], len(x[1]), self.last_heard.get(x[0], 999999)))
            self.queue = deque(queue_list)
            
            callsign, path, quality = self.queue.popleft()
            
            # Limit depth to prevent excessive crawling from discovered neighbors
            # BUT: Don't apply limit to the initial starting node (even if remote)
            # max_hops means "explore neighbors to this depth FROM starting node"
            # not "can only reach nodes at this depth"
            # 
            # path contains intermediate hops, target node is not in path
            # Hop distance = path length + 1 (for the target node itself)
            # Example: WS1EC->KC1JMH->KS1R->W1LH: path=['KC1JMH','KS1R'], W1LH is at hop 3
            
            # Skip hop check for initial starting node (allow reaching it regardless of hops)
            is_starting_node = (starting_callsign is not None and 
                               callsign.split('-')[0] == starting_callsign.split('-')[0])
            
            if not is_starting_node:
                # Not the starting node - apply hop limit to neighbors discovered from it
                if starting_callsign is None:
                    # Resume mode: calculate from path length
                    if not path:
                        # Empty path: either local node (0 hops) or direct neighbor (1 hop)
                        hop_distance = 0 if callsign == self.callsign else 1
                    else:
                        # Path has intermediates: distance = path length + 1 for target
                        hop_distance = len(path) + 1
                else:
                    # Normal mode: compare with actual starting callsign
                    if not path:
                        hop_distance = 0 if callsign == starting_callsign else 1
                    else:
                        hop_distance = len(path) + 1
                
                if hop_distance > self.max_hops:
                    print("Skipping {} ({} hops > max {})".format(callsign, hop_distance, self.max_hops))
                    continue
            
            self.crawl_node(callsign, path)
            time.sleep(2)  # Be polite, don't hammer network
        
        print("-" * 50)
        colored_print("Crawl complete. Found {} nodes.".format(len(self.nodes)), Colors.GREEN)
        if self.failed:
            colored_print("Failed connections: {} nodes".format(len(self.failed)), Colors.YELLOW)
            print("  Failed: {}".format(', '.join(sorted(self.failed))))
        else:
            print("No failed connections.")
        
        # Notify crawl completion
        self._send_notification("Crawl complete: {} nodes, {} failed".format(len(self.nodes), len(self.failed)))
        
        # Display summary table
        if self.nodes:
            print("\n" + "=" * 96)
            print("NETWORK SUMMARY")
            print("=" * 96)
            print("{:<10} {:<4} {:<6} {:<5} {:<5} {:<6} {:<6} {:<10} {:<30}".format(
                "CALLSIGN", "HOPS", "PORTS", "APPS", "CMDS", "NBRS", "FAILED", "UNEXPLRD", "GRID/LOCATION"
            ))
            print("-" * 96)
            
            for callsign in sorted(self.nodes.keys()):
                node = self.nodes[callsign]
                hop_dist = node.get('hop_distance', 0)
                ports = len([p for p in node.get('ports', []) if p.get('is_rf')])
                apps = len(node.get('applications', []))  # Apps from ? command (BBS, CHAT, RMS, etc.)
                commands = len(node.get('commands', []))  # All commands from ? (reliable)
                neighbors = len(node.get('neighbors', []))
                
                # Recalculate failed connections from intermittent_links
                # Count links where this node (callsign) tried to reach neighbors
                failed = 0
                for (from_call, to_call) in self.intermittent_links.keys():
                    if from_call == callsign:
                        failed += 1
                
                unexplored = len(node.get('unexplored_neighbors', []))
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
                
                print("{:<10} {:<4} {:<6} {:<5} {:<5} {:<6} {:<6} {:<10} {:<30}".format(
                    callsign,
                    hop_dist,
                    ports,
                    apps,
                    commands,
                    neighbors,
                    failed if failed > 0 else '',
                    unexplored if unexplored > 0 else '',
                    loc_str[:30]
                ))
            
            print("=" * 96)
            print("Total: {} nodes, {} connections".format(
                len(self.nodes),
                len(self.connections)
            ))
            print("=" * 96)
    
    def export_json(self, filename='nodemap.json', merge=False):
        """Export network map to JSON.
        
        Args:
            filename: Output filename
            merge: If True, merge with existing data instead of overwrite
        """
        nodes_data = {}
        connections_data = []
        
        # Load existing data if merge mode
        if merge:
            existing = self._load_existing_data(filename)
            if existing and 'nodes' in existing:
                nodes_data = existing['nodes']
                print("Merging with {} existing nodes...".format(len(nodes_data)))
            
            # Load existing connections and filter out connections from re-crawled nodes
            if 'connections' in existing:
                crawled_nodes = set(self.nodes.keys())
                for conn in existing.get('connections', []):
                    # Keep connection if neither endpoint was re-crawled
                    if conn['from'] not in crawled_nodes and conn['to'] not in crawled_nodes:
                        connections_data.append(conn)
        
        # Add new connections from current crawl
        connections_data.extend(self.connections)
        
        # Deduplicate nodes before merge: check if base callsign exists with different SSID
        # If N1QFY exists and we're adding N1QFY-15 (or vice versa), merge to SSID version
        for callsign, node_data in self.nodes.items():
            base_call = callsign.split('-')[0] if '-' in callsign else callsign
            
            # Check if a different SSID variant already exists
            existing_key = None
            if callsign in nodes_data:
                # Exact match - will overwrite
                existing_key = callsign
            else:
                # Check for base or SSID variants
                for existing_call in list(nodes_data.keys()):
                    existing_base = existing_call.split('-')[0] if '-' in existing_call else existing_call
                    if existing_base == base_call:
                        # Found variant - prefer SSID version over base
                        if '-' in callsign and '-' not in existing_call:
                            # New has SSID, existing is base - use new, delete existing
                            if self.verbose:
                                print("  Deduplicating: {} replaces {}".format(callsign, existing_call))
                            del nodes_data[existing_call]
                            existing_key = None
                        elif '-' in existing_call and '-' not in callsign:
                            # Existing has SSID, new is base - keep existing, skip new
                            if self.verbose:
                                print("  Deduplicating: keeping {} over {}".format(existing_call, callsign))
                            existing_key = existing_call
                        else:
                            # Both have SSID or both base - overwrite
                            existing_key = existing_call
                        break
            
            # Add or update node
            if existing_key and existing_key != callsign:
                # Merge into existing SSID variant
                continue
            nodes_data[callsign] = node_data
        
        # Convert intermittent_links keys to strings for JSON serialization
        intermittent_serialized = {}
        for (from_call, to_call), attempts in self.intermittent_links.items():
            key = "{}>{}".format(from_call, to_call)
            intermittent_serialized[key] = attempts
        
        data = {
            'metadata': {
                'nodemap_version': __version__,
                'generated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'generator': 'nodemap.py'
            },
            'nodes': nodes_data,
            'connections': connections_data,
            'intermittent_links': intermittent_serialized,  # Failed/unreliable connections
            'crawl_info': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'start_node': self.callsign,
                'total_nodes': len(nodes_data),
                'total_connections': len(connections_data),
                'mode': 'merge' if merge else 'overwrite'
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        mode_str = "Merged into" if merge else "Exported to"
        print("{} {} ({} nodes)".format(mode_str, filename, len(nodes_data)))
    
    def export_csv(self, filename='nodemap.csv'):
        """Export connections to CSV with frequency information for network mapping."""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            # Enhanced header with frequency fields for network mapping
            writer.writerow(['From', 'To', 'Port', 'Quality', 'Intermittent', 'To_Explored', 
                           'From_Grid', 'To_Grid', 'From_Type', 'To_Type', 
                           'From_Frequencies', 'To_Frequencies', 'From_Ports'])
            
            for conn in self.connections:
                from_node = self.nodes.get(conn['from'], {})
                to_node = self.nodes.get(conn['to'], {})
                to_call = conn['to']
                
                # Determine if 'to' node was explored
                to_explored = 'Yes' if to_call in self.visited else 'No'
                
                # Extract RF frequencies from 'from' node for operators to know connection options
                from_frequencies = []
                from_ports = []
                for port in from_node.get('ports', []):
                    if port['is_rf'] and port.get('frequency'):
                        from_frequencies.append(str(port['frequency']))
                        from_ports.append(str(port['number']))
                
                # Extract RF frequencies from 'to' node
                to_frequencies = []
                for port in to_node.get('ports', []):
                    if port['is_rf'] and port.get('frequency'):
                        to_frequencies.append(str(port['frequency']))
                
                writer.writerow([
                    conn['from'],
                    conn['to'],
                    conn['port'],
                    conn.get('quality', 0),
                    'Yes' if conn.get('intermittent', False) else 'No',
                    to_explored,
                    from_node.get('location', {}).get('grid', ''),
                    to_node.get('location', {}).get('grid', ''),
                    from_node.get('type', 'Unknown'),
                    to_node.get('type', 'Unknown'),
                    ';'.join(from_frequencies),  # Semicolon-separated frequencies (e.g., "433.3;145.05")
                    ';'.join(to_frequencies),
                    ';'.join(from_ports)         # Corresponding port numbers for frequency reference
                ])
        
        print("Exported to {}".format(filename))
    
    def merge_external_data(self, filename):
        """Merge data from another nodemap.json file.
        
        Args:
            filename: Path to external nodemap.json file
            
        Returns:
            Number of nodes merged, or -1 on error
        """
        try:
            external_data = self._load_existing_data(filename)
            if not external_data or 'nodes' not in external_data:
                colored_print("Error: Invalid or missing nodemap data in {}".format(filename), Colors.RED)
                return -1
            
            external_nodes = external_data['nodes']
            merged_count = 0
            new_count = 0
            
            for callsign, node_data in external_nodes.items():
                if callsign in self.nodes:
                    # Node exists, merge data intelligently
                    existing = self.nodes[callsign]
                    
                    # Keep most recent timestamp for same data
                    # Merge neighbor lists (union)
                    existing_neighbors = set(existing.get('neighbors', []))
                    external_neighbors = set(node_data.get('neighbors', []))
                    merged_neighbors = list(existing_neighbors | external_neighbors)
                    
                    # Merge intermittent_neighbors
                    existing_intermittent = set(existing.get('intermittent_neighbors', []))
                    external_intermittent = set(node_data.get('intermittent_neighbors', []))
                    merged_intermittent = list(existing_intermittent | external_intermittent)
                    
                    # Use external data if it has more recent info or more details
                    external_timestamp = external_data.get('crawl_info', {}).get('timestamp', '')
                    
                    # Update with merged data
                    self.nodes[callsign]['neighbors'] = merged_neighbors
                    self.nodes[callsign]['intermittent_neighbors'] = merged_intermittent
                    
                    # Merge other fields if external has more info
                    if len(node_data.get('applications', [])) > len(existing.get('applications', [])):
                        self.nodes[callsign]['applications'] = node_data['applications']
                    
                    if node_data.get('location', {}).get('grid') and not existing.get('location', {}).get('grid'):
                        self.nodes[callsign]['location'] = node_data['location']
                    
                    merged_count += 1
                else:
                    # New node, add it
                    self.nodes[callsign] = node_data
                    new_count += 1
            
            # Merge connections
            if 'connections' in external_data:
                external_connections = external_data['connections']
                
                # Create set of existing connections for deduplication
                existing_conn_keys = set()
                for conn in self.connections:
                    key = (conn['from'], conn['to'])
                    existing_conn_keys.add(key)
                
                # Add new connections
                for conn in external_connections:
                    key = (conn['from'], conn['to'])
                    if key not in existing_conn_keys:
                        self.connections.append(conn)
            
            # Merge intermittent_links
            if 'intermittent_links' in external_data:
                external_intermittent = external_data['intermittent_links']
                for link_key, attempts in external_intermittent.items():
                    # Convert back to tuple key format
                    if '>' in link_key:
                        from_call, to_call = link_key.split('>', 1)
                        tuple_key = (from_call, to_call)
                        
                        if tuple_key in self.intermittent_links:
                            # Merge attempt lists
                            self.intermittent_links[tuple_key].extend(attempts)
                        else:
                            self.intermittent_links[tuple_key] = attempts
            
            print("Merged {} nodes from {} ({} new, {} updated)".format(
                len(external_nodes), filename, new_count, merged_count))
            return len(external_nodes)
            
        except Exception as e:
            colored_print("Error merging {}: {}".format(filename, e), Colors.RED)
            return -1


def main():
    """Main entry point."""
    # Check for set-grid mode first (fast exit)
    if '--set-grid' in sys.argv:
        set_grid_call = None
        set_grid_value = None
        for i, arg in enumerate(sys.argv):
            if arg == '--set-grid' and i + 2 < len(sys.argv):
                set_grid_call = sys.argv[i + 1].upper()
                set_grid_value = sys.argv[i + 2]
                break
        
        if not set_grid_call or not set_grid_value:
            colored_print("Error: --set-grid requires CALLSIGN and GRIDSQUARE", Colors.RED)
            print("Example: {} --set-grid NG1P FN43vp".format(sys.argv[0]))
            sys.exit(1)
        
        # Validate gridsquare format (basic check)
        if not re.match(r'^[A-R]{2}[0-9]{2}[a-x]{2}$', set_grid_value, re.IGNORECASE):
            colored_print("Warning: Gridsquare '{}' doesn't match standard format (e.g., FN43vp)".format(set_grid_value), Colors.YELLOW)
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                sys.exit(0)
        
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            colored_print("Run a crawl first to generate network data", Colors.RED)
            sys.exit(1)
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            base_call = set_grid_call.split('-')[0] if '-' in set_grid_call else set_grid_call
            
            # Find node by base callsign or exact match
            node_key = None
            if set_grid_call in nodes_data:
                node_key = set_grid_call
            else:
                # Try finding by base callsign
                matches = [k for k in nodes_data.keys() if k.split('-')[0] == base_call]
                if not matches:
                    colored_print("Node {} not found in nodemap.json".format(set_grid_call), Colors.RED)
                    colored_print("Available nodes: {}".format(', '.join(sorted(nodes_data.keys()))), Colors.YELLOW)
                    sys.exit(1)
                elif len(matches) > 1:
                    colored_print("Multiple SSIDs found for {}: {}".format(base_call, ', '.join(matches)), Colors.YELLOW)
                    response = input("Update all variants? (Y/n): ").strip().lower()
                    if response in ['', 'y', 'yes']:
                        # Update all variants
                        for match in matches:
                            if 'location' not in nodes_data[match]:
                                nodes_data[match]['location'] = {}
                            nodes_data[match]['location']['grid'] = set_grid_value
                            nodes_data[match]['gridsquare'] = set_grid_value
                            print("Updated gridsquare for {}: {}".format(match, set_grid_value))
                        
                        # Save back to file
                        with open('nodemap.json', 'w') as f:
                            json.dump(data, f, indent=2)
                        colored_print("\nSaved to nodemap.json", Colors.GREEN)
                        sys.exit(0)
                    else:
                        node_key = matches[0]
                        print("Updating only: {}".format(node_key))
                else:
                    node_key = matches[0]
            
            # Update the node's gridsquare
            if 'location' not in nodes_data[node_key]:
                nodes_data[node_key]['location'] = {}
            
            old_grid = nodes_data[node_key]['location'].get('grid', 'N/A')
            nodes_data[node_key]['location']['grid'] = set_grid_value
            nodes_data[node_key]['gridsquare'] = set_grid_value
            
            print("Updated gridsquare for {}: {} -> {}".format(node_key, old_grid, set_grid_value))
            
            # Save back to file
            with open('nodemap.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            colored_print("Saved to nodemap.json", Colors.GREEN)
            
            # Offer to regenerate maps
            response = input("\nRegenerate maps? (Y/n): ").strip().lower()
            if response in ['', 'y', 'yes']:
                print("\nGenerating maps...")
                html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
                try:
                    import subprocess
                    result = subprocess.call(['python3', html_script, '--all'])
                    if result == 0:
                        colored_print("Maps generated successfully!", Colors.GREEN)
                    else:
                        colored_print("Warning: Map generation exited with code {}".format(result), Colors.YELLOW)
                except Exception as e:
                    colored_print("Error generating maps: {}".format(e), Colors.RED)
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error updating nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        
        sys.exit(0)
    
    # Check for cleanup mode (nodes, connections, or all)
    if '--cleanup' in sys.argv:
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            sys.exit(1)
        
        # Determine what to clean up
        cleanup_target = 'all'  # default
        for i, arg in enumerate(sys.argv):
            if arg == '--cleanup' and i + 1 < len(sys.argv):
                next_arg = sys.argv[i + 1].lower()
                if next_arg in ['nodes', 'connections', 'all']:
                    cleanup_target = next_arg
                    break
        
        print("BPQ Node Map Cleanup v{} - {}".format(__version__, cleanup_target))
        print("=" * 50)
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            connections = data.get('connections', [])
            changes_made = False
            
            # CONNECTIONS CLEANUP
            if cleanup_target in ['connections', 'all']:
                print("\nCleaning up connections...")
                if not connections:
                    print("  No connections to clean")
                else:
                    valid_connections = []
                    invalid_connections = []
                    
                    for conn in connections:
                        from_call = conn['from']
                        to_call = conn['to']
                        to_base = to_call.split('-')[0] if '-' in to_call else to_call
                        
                        from_node = nodes_data.get(from_call, {})
                        routes = from_node.get('routes', {})
                        
                        # Check if destination is in routes with non-zero quality
                        if to_base in routes and routes[to_base] > 0:
                            valid_connections.append(conn)
                        else:
                            invalid_connections.append(conn)
                    
                    if invalid_connections:
                        print("  Found {} invalid connections:".format(len(invalid_connections)))
                        for conn in invalid_connections[:5]:
                            print("    {} -> {} (quality: {})".format(conn['from'], conn['to'], conn.get('quality', 0)))
                        if len(invalid_connections) > 5:
                            print("    ... and {} more".format(len(invalid_connections) - 5))
                        
                        data['connections'] = valid_connections
                        changes_made = True
                        colored_print("  Removed {} invalid connections".format(len(invalid_connections)), Colors.YELLOW)
                        colored_print("  Kept {} valid connections".format(len(valid_connections)), Colors.GREEN)
                    else:
                        print("  All {} connections are valid".format(len(connections)))
            
            # NODES CLEANUP
            if cleanup_target in ['nodes', 'all']:
                print("\nCleaning up nodes...")
                removed = []
                
                # Find base callsigns with multiple SSID entries
                base_calls = {}
                for call in nodes_data.keys():
                    base = call.split('-')[0]
                    if base not in base_calls:
                        base_calls[base] = []
                    base_calls[base].append(call)
                
                # For each base call with duplicates, keep the best one
                for base, variants in base_calls.items():
                    if len(variants) > 1:
                        print("  Found duplicate entries for {}: {}".format(base, ', '.join(variants)))
                        
                        # Score each variant: neighbors count + (has_location ? 100 : 0) + (has_apps ? 50 : 0)
                        scored = []
                        for variant in variants:
                            node = nodes_data[variant]
                            score = len(node.get('neighbors', []))
                            if node.get('location', {}).get('grid'):
                                score += 100
                            if node.get('applications', []):
                                score += 50
                            scored.append((variant, score, node))
                        
                        # Sort by score (highest first)
                        scored.sort(key=lambda x: -x[1])
                        keep = scored[0][0]
                        
                        print("    Keeping: {} (score: {})".format(keep, scored[0][1]))
                        
                        for variant, score, node in scored[1:]:
                            print("    Removing: {} (score: {})".format(variant, score))
                            removed.append(variant)
                
                # Remove empty/incomplete nodes (no neighbors, no location, no apps)
                for call, node in list(nodes_data.items()):
                    if call in removed:
                        continue
                    neighbors = node.get('neighbors', [])
                    location = node.get('location', {})
                    apps = node.get('applications', [])
                    
                    if len(neighbors) == 0 and not location.get('grid') and len(apps) == 0:
                        print("  Removing incomplete: {} (no data)".format(call))
                        removed.append(call)
                
                if removed:
                    # Remove nodes
                    for call in removed:
                        del nodes_data[call]
                    data['nodes'] = nodes_data
                    changes_made = True
                    colored_print("  Removed {} duplicate/incomplete nodes".format(len(removed)), Colors.YELLOW)
                else:
                    print("  No duplicate or incomplete nodes found")
            
            if not changes_made:
                print("\nNo cleanup needed!")
                sys.exit(0)
            
            # Save changes
            with open('nodemap.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            colored_print("\nSaved cleaned data to nodemap.json", Colors.GREEN)
            
            # Offer to regenerate maps
            response = input("\nRegenerate maps? (Y/n): ").strip().lower()
            if response in ['', 'y', 'yes']:
                print("\nGenerating maps...")
                html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
                try:
                    import subprocess
                    result = subprocess.call(['python3', html_script, '--all'])
                    if result == 0:
                        colored_print("Maps generated successfully!", Colors.GREEN)
                    else:
                        colored_print("Warning: Map generation exited with code {}".format(result), Colors.YELLOW)
                except Exception as e:
                    colored_print("Error generating maps: {}".format(e), Colors.RED)
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error cleaning up nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        
        sys.exit(0)
    
    # Check for help flag first
    if '-h' in sys.argv or '--help' in sys.argv or '/?' in sys.argv:
        print("BPQ Node Map Crawler v{}".format(__version__))
        print("=" * 50)
        print("\nAutomatically crawls packet radio network to discover topology.")
        print("\nUsage: {} [MAX_HOPS] [START_NODE] [OPTIONS]".format(sys.argv[0]))
        print("\nArguments:")
        print("  MAX_HOPS         Maximum RF hops from start (default: 4, 0 with --callsign)")
        print("                   0=local only, 1=direct neighbors, 2=neighbors+their neighbors")
        print("  START_NODE       Callsign to begin crawl (default: local node)")
        print("\nOptions:")
        print("  --overwrite, -o  Overwrite existing data (default: merge)")
        print("  --resume, -r     Resume from unexplored nodes in nodemap.json")
        print("                   Automatically finds nodemap_partial*.json if nodemap.json missing")
        print("  --resume FILE    Resume from specific JSON file")
        print("  --merge FILE, -m Merge another nodemap.json file into current data")
        print("                   Supports wildcards: --merge *.json")
        print("  --mode MODE      Crawl mode: update (default), reaudit, new-only")
        print("                   update: skip already-visited nodes (fastest)")
        print("                   reaudit: re-crawl all nodes to verify/update data")
        print("                   new-only: auto-load nodemap.json, queue unexplored neighbors")
        print("  --exclude CALLS, -x CALLS  Exclude comma-separated callsigns from crawling")
        print("                   Example: --exclude AB1KI,N1REX,K1NYY")
        print("  --display-nodes, -d  Display nodes table from nodemap.json and exit")
        print("  --user USERNAME  Telnet login username (default: prompt if needed)")
        print("  --pass PASSWORD  Telnet login password (default: prompt if needed)")
        print("  --callsign CALL  Force specific SSID for start node (e.g., --callsign NG1P-4)")
        print("  --set-grid CALL GRID  Set gridsquare for callsign (e.g., --set-grid NG1P FN43vp)")
        print("  --query CALL, -q Query info about node (neighbors, apps, best route)")
        print("  --cleanup [TARGET]  Clean up nodemap.json (nodes, connections, or all)")
        print("                      TARGET: nodes (duplicates/incomplete), connections (invalid),")
        print("                              all (both, default if TARGET omitted)")
        print("  --notify URL     Send notifications to webhook URL")
        print("  --verbose, -v    Show detailed command/response output")
        print("  --log [FILE], -l [FILE]  Log telnet traffic (default: telnet.log)")
        print("  --debug-log [FILE], -D [FILE]  Log verbose debug output (implies -v, default: debug.log)")
        print("  --help, -h, /?   Show this help message")
        print("Examples:")
        print("  {} 5              # Crawl 5 hops, merge with existing".format(sys.argv[0]))
        print("  {} 10 WS1EC       # Crawl from WS1EC, merge results".format(sys.argv[0]))
        print("  {} 5 --overwrite  # Crawl and completely replace data".format(sys.argv[0]))
        print("  {} --resume       # Continue from unexplored nodes".format(sys.argv[0]))
        print("  {} --resume nodemap_partial.json  # Resume from specific file".format(sys.argv[0]))
        print("  {} --merge remote_nodemap.json  # Merge data from another node's perspective".format(sys.argv[0]))
        print("  {} -m *.json      # Merge all JSON files in current directory".format(sys.argv[0]))
        print("  {} 10 --user KC1JMH --pass ****  # With authentication".format(sys.argv[0]))
        print("  {} --notify https://example.com/webhook  # Send progress notifications".format(sys.argv[0]))
        print("  {} --callsign NG1P-4  # Force connection to specific SSID".format(sys.argv[0]))
        print("  {} --set-grid NG1P FN43vp  # Add gridsquare for node".format(sys.argv[0]))
        print("  {} -q NG1P  # Query what we know about NG1P".format(sys.argv[0]))
        print("\nData Storage:")
        print("  Merge mode (default): Updates existing nodemap.json, preserves old data")
        print("  Overwrite mode: Completely replaces nodemap.json and nodemap.csv")
        print("  Merge file mode: Combines data from multiple node perspectives")
        print("\nMulti-Node Mapping:")
        print("  1. Run script from different nodes: nodemap.py 10 > node1_map.json")
        print("  2. Share JSON files between operators")
        print("  3. Merge perspectives: nodemap.py --merge node2_map.json --merge node3_map.json")
        print("  4. Result: Combined network view from all vantage points")
        print("\nOutput Files:")
        print("  nodemap.json      Complete network topology and node information")
        print("  nodemap.csv       Connection list for spreadsheet analysis")
        print("\nInstallation:")
        print("  Place in ~/utilities/ or ~/apps/ adjacent to ~/linbpq/")
        print("  Reads NODECALL and TCPPORT from ../linbpq/bpq32.cfg")
        print("\nTimeout Protection:")
        print("  Commands scale with hop count (5s + 10s/hop, max 60s)")
        print("  Connection timeout: 20s + 20s/hop (max 2min)")
        print("  Operation timeout: 2min + 1min/hop (max ~12min for 10 hops)")
        print("  Staleness filter: Skips nodes not heard in >24 hours")
        sys.exit(0)
    
        sys.exit(0)
    
    # Check for display-nodes mode first (fast exit)
    if '--display-nodes' in sys.argv or '-d' in sys.argv:
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            colored_print("Run a crawl first to generate network data", Colors.RED)
            sys.exit(1)
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            netrom_data = data.get('netrom_nodes', {})
            if not nodes_data:
                print("No nodes found in nodemap.json")
                sys.exit(0)
            
            # Build set of explored nodes
            explored = set(nodes_data.keys())
            
            # Build set of all mentioned neighbors
            all_neighbors = set()
            for node in nodes_data.values():
                all_neighbors.update(node.get('neighbors', []))
            
            # Unexplored = neighbors not in explored nodes
            unexplored = all_neighbors - explored
            
            # Print nodes table
            print("\nNodes in nodemap.json ({} total):\n".format(len(nodes_data)))
            print("{:<12} {:<6} {:<10} {:<12} {:<25} {:<25}".format(
                "Callsign", "Hops", "Alias", "Gridsquare", "Neighbors", "Unexplored"))
            print("-" * 105)
            
            # Sort by callsign for consistent display
            for callsign in sorted(nodes_data.keys()):
                node = nodes_data[callsign]
                
                # Get alias - prefer top-level field, fallback to own_aliases or netrom data
                alias = node.get('alias', '')
                if not alias:
                    own_aliases = node.get('own_aliases', {})
                    alias = list(own_aliases.keys())[0] if own_aliases else ''
                if not alias:
                    alias = netrom_data.get(callsign, {}).get('alias', '')
                
                hops = node.get('hop_distance', '')
                
                # Get gridsquare - prefer top-level field, fallback to location dict or netrom data
                grid = node.get('gridsquare', '')
                if not grid:
                    location = node.get('location', {})
                    grid = location.get('grid', '')
                if not grid:
                    grid = netrom_data.get(callsign, {}).get('gridsquare', '')
                
                neighbors = node.get('neighbors', [])
                
                # Find unexplored neighbors
                unexplored_neighbors = [n for n in neighbors if n in unexplored]
                
                # Format neighbors list (first 2, then count)
                if len(neighbors) == 0:
                    neighbor_str = '-'
                elif len(neighbors) <= 2:
                    neighbor_str = ', '.join(neighbors)
                else:
                    neighbor_str = '{} (+{})'.format(
                        ', '.join(neighbors[:2]),
                        len(neighbors) - 2
                    )
                
                # Format unexplored list (first 2, then count)
                if len(unexplored_neighbors) == 0:
                    unexplored_str = '-'
                elif len(unexplored_neighbors) <= 2:
                    unexplored_str = ', '.join(unexplored_neighbors)
                else:
                    unexplored_str = '{} (+{})'.format(
                        ', '.join(unexplored_neighbors[:2]),
                        len(unexplored_neighbors) - 2
                    )
                
                print("{:<12} {:<6} {:<10} {:<12} {:<25} {:<25}".format(
                    callsign,
                    str(hops) if hops != '' else '-',
                    alias[:10],
                    grid[:12],
                    neighbor_str[:25],
                    unexplored_str[:25]
                ))
            
            print("\nTotal nodes: {}".format(len(nodes_data)))
            print("Unexplored neighbors: {}".format(len(unexplored)))
            if unexplored:
                print("Unexplored: {}".format(', '.join(sorted(unexplored))))
            print("Total connections: {}".format(len(data.get('connections', []))))
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error reading nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        
        sys.exit(0)
    
    # Check for query mode first (fast exit)
    if '--query' in sys.argv or '-q' in sys.argv:
        query_call = None
        for i, arg in enumerate(sys.argv):
            if (arg == '--query' or arg == '-q') and i + 1 < len(sys.argv):
                query_call = sys.argv[i + 1].upper()
                break
        
        if not query_call:
            colored_print("Error: --query requires a callsign", Colors.RED)
            sys.exit(1)
        
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            colored_print("Run a crawl first to generate network data", Colors.RED)
            sys.exit(1)
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            base_call = query_call.split('-')[0] if '-' in query_call else query_call
            
            # Find node by base callsign or exact match
            node_data = nodes_data.get(query_call)
            if not node_data:
                # Try base callsign
                matches = [k for k in nodes_data.keys() if k.split('-')[0] == base_call]
                if not matches:
                    colored_print("Node {} not found in nodemap.json".format(query_call), Colors.RED)
                    colored_print("Hint: Run crawl with --callsign {}-SSID to force specific SSID".format(base_call), Colors.YELLOW)
                    sys.exit(1)
                elif len(matches) > 1:
                    colored_print("Multiple SSIDs found for {}: {}".format(base_call, ', '.join(matches)), Colors.YELLOW)
                    query_call = matches[0]
                    node_data = nodes_data[query_call]
                    print("Showing: {}".format(query_call))
                else:
                    query_call = matches[0]
                    node_data = nodes_data[query_call]
            
            # Display node info
            print("\n" + "=" * 60)
            print("Node: {}".format(query_call))
            print("=" * 60)
            
            # Basic info
            alias = node_data.get('alias', 'N/A')
            node_type = node_data.get('type', 'Unknown')
            hop_distance = node_data.get('hop_distance', '?')
            print("Alias: {}".format(alias))
            print("Type: {}".format(node_type))
            print("Hop Distance: {}".format(hop_distance))
            
            # Location
            location = node_data.get('location', {})
            if location:
                grid = location.get('grid', 'N/A')
                city = location.get('city', '')
                state = location.get('state', '')
                print("Grid Square: {}".format(grid))
                if city or state:
                    print("Location: {}{}".format(city, ', ' + state if state else ''))
            
            # Best route
            successful_path = node_data.get('successful_path')
            if successful_path:
                if successful_path:
                    print("Best Route: {}".format(' > '.join(successful_path + [query_call])))
                else:
                    print("Best Route: Direct")
            
            # Applications
            applications = node_data.get('applications', [])
            if applications:
                # Filter out NetRom aliases
                apps = [a for a in applications if ':' not in a and '}' not in a]
                if apps:
                    print("\nApplications ({}):\n  {}".format(len(apps), ', '.join(apps)))
            
            # Neighbors
            neighbors = node_data.get('neighbors', [])
            explored = node_data.get('explored_neighbors', [])
            unexplored = node_data.get('unexplored_neighbors', [])
            
            print("\nNeighbors ({} total):".format(len(neighbors)))
            if explored:
                print("  Explored: {}".format(', '.join(sorted(explored))))
            if unexplored:
                print("  Unexplored: {}".format(', '.join(sorted(unexplored))))
            
            # Routes with quality
            routes = node_data.get('routes', {})
            if routes:
                print("\nRoutes ({} reachable nodes):".format(len(routes)))
                # Show top 10 by quality
                sorted_routes = sorted(routes.items(), key=lambda x: (-x[1], x[0]))[:10]
                for route_call, quality in sorted_routes:
                    print("  {:<15} quality: {}".format(route_call, quality))
                if len(routes) > 10:
                    print("  ... ({} more)".format(len(routes) - 10))
            
            # Ports
            ports = node_data.get('ports', [])
            rf_ports = [p for p in ports if p.get('is_rf')]
            if rf_ports:
                print("\nRF Ports ({}):".format(len(rf_ports)))
                for port in rf_ports:
                    freq = port.get('frequency', 'Unknown')
                    print("  Port {}: {} MHz".format(port.get('port_num'), freq))
            
            # Known SSIDs - helps decide which SSID to use for recrawl
            print("\nKnown SSIDs for {}:".format(base_call))
            ssid_sources = {}
            
            # 1. Current node's SSID (what we crawled)
            if '-' in query_call:
                ssid = query_call.split('-')[1]
                ssid_sources[query_call] = ['Current node (crawled)']
            
            # 2. SSIDs from this node's own netrom_ssids (MHEARD data)
            netrom_ssids = node_data.get('netrom_ssids', {})
            if base_call in netrom_ssids:
                self_ssid = netrom_ssids[base_call]
                if self_ssid not in ssid_sources:
                    ssid_sources[self_ssid] = []
                ssid_sources[self_ssid].append('Own MHEARD')
            
            # 3. SSIDs other nodes use to refer to this node
            for other_call, other_data in nodes_data.items():
                if other_call == query_call:
                    continue
                
                # Check other node's netrom_ssids
                other_netrom = other_data.get('netrom_ssids', {})
                if base_call in other_netrom:
                    found_ssid = other_netrom[base_call]
                    if found_ssid not in ssid_sources:
                        ssid_sources[found_ssid] = []
                    ssid_sources[found_ssid].append('MHEARD by {}'.format(other_call))
                
                # Check other node's routes (most authoritative)
                other_routes = other_data.get('routes', {})
                for route_call, quality in other_routes.items():
                    if route_call == base_call or (route_call.startswith(base_call) and 
                                                    (len(route_call) == len(base_call) or 
                                                     route_call[len(base_call)] == '-')):
                        # Found this callsign in routes
                        if route_call not in ssid_sources:
                            ssid_sources[route_call] = []
                        ssid_sources[route_call].append('ROUTES in {} (q={})'.format(other_call, quality))
            
            if ssid_sources:
                # Sort by: 1) SSIDs with base only, 2) SSIDs by number
                sorted_ssids = sorted(ssid_sources.items(), 
                                     key=lambda x: (0 if '-' not in x[0] else 1, x[0]))
                for ssid_call, sources in sorted_ssids:
                    # Deduplicate and limit sources shown
                    unique_sources = []
                    source_types = {}
                    for src in sources:
                        src_type = src.split()[0]  # "ROUTES", "MHEARD", "Current", "Own"
                        if src_type not in source_types:
                            source_types[src_type] = []
                        source_types[src_type].append(src)
                    
                    # Show summary
                    for src_type, src_list in sorted(source_types.items()):
                        if src_type == 'ROUTES':
                            # Show which nodes have this in ROUTES
                            nodes = [s.split('in ')[1].split()[0] for s in src_list if 'in ' in s]
                            unique_sources.append('ROUTES in {} nodes'.format(len(set(nodes))))
                        elif src_type == 'MHEARD':
                            nodes = [s.split('by ')[1] for s in src_list if 'by ' in s]
                            if len(nodes) <= 3:
                                unique_sources.append('MHEARD by {}'.format(', '.join(nodes)))
                            else:
                                unique_sources.append('MHEARD by {} nodes'.format(len(set(nodes))))
                        else:
                            unique_sources.append(src_list[0])
                    
                    print("  {:<15} ({})".format(ssid_call, '; '.join(unique_sources)))
                
                print("\nHint: Use --callsign {} to force recrawl with specific SSID".format(
                    sorted_ssids[0][0] if sorted_ssids else base_call))
            else:
                print("  No SSIDs found")
                print("\nHint: Use --callsign {}-SSID to force recrawl".format(base_call))
            
            print("=" * 60)
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error reading nodemap.json: {}".format(e), Colors.RED)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        sys.exit(0)
    
    # Print header for normal operation (after fast-exit modes)
    print("BPQ Node Map Crawler v{}".format(__version__))
    print("=" * 50)
    
    # Parse command line args
    max_hops = 4  # Default reduced from 10 to 4 (realistic for 1200 baud RF)
    max_hops_explicit = False  # Track if user explicitly set max_hops
    start_node = None
    forced_ssid = None  # User-specified SSID to override discovery
    username = None
    password = None
    notify_url = None
    log_file = None
    debug_log = None
    crawl_mode = 'update'  # Default to 'update' mode
    exclude_nodes = set()  # Nodes to exclude from crawling
    merge_files = []  # List of files to merge
    resume_file = None  # File to resume from (None = auto-detect)
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    resume = '--resume' in sys.argv or '-r' in sys.argv
    generate_maps = False  # Will be set by user prompt
    
    # Parse positional and optional arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith('-'):
            break
        if i == 1:
            if arg.isdigit():
                max_hops = int(arg)
                max_hops_explicit = True  # User explicitly set max_hops
            else:
                # First positional arg is not a digit, treat as START_NODE
                start_node = arg.upper()
        elif i == 2:
            start_node = arg.upper()
        i += 1
    
    # Parse options
    i = 1
    unknown_args = []
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--user' and i + 1 < len(sys.argv):
            username = sys.argv[i + 1]
            i += 2
        elif arg == '--pass' and i + 1 < len(sys.argv):
            password = sys.argv[i + 1]
            i += 2
        elif (arg == '--notify' or arg == '-n') and i + 1 < len(sys.argv):
            notify_url = sys.argv[i + 1]
            i += 2
        elif (arg == '--log' or arg == '-l'):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                log_file = sys.argv[i + 1]
                i += 2
            else:
                log_file = 'telnet.log'
                i += 1
        elif arg == '--debug-log' or arg == '-D':
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                debug_log = sys.argv[i + 1]
                i += 2
            else:
                debug_log = 'debug.log'
                i += 1
            # Debug mode automatically enables verbose output
            verbose = True
        elif (arg == '--exclude' or arg == '-x') and i + 1 < len(sys.argv):
            # Parse comma-separated list of callsigns to exclude
            exclude_str = sys.argv[i + 1]
            for call in exclude_str.split(','):
                call = call.strip().upper()
                if call:
                    exclude_nodes.add(call)
            i += 2
        elif arg == '--mode' and i + 1 < len(sys.argv):
            mode_arg = sys.argv[i + 1].lower()
            if mode_arg in ['update', 'reaudit', 'new-only']:
                crawl_mode = mode_arg
                i += 2
            else:
                colored_print("Error: Invalid mode '{}'. Must be 'update', 'reaudit', or 'new-only'.".format(sys.argv[i + 1]), Colors.RED)
                print("Run '{} --help' for usage information.".format(sys.argv[0]))
                sys.exit(1)
        elif (arg == '--resume' or arg == '-r'):
            resume = True
            # Check if next arg is a filename (not another option)
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                resume_file = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        elif (arg == '--merge' or arg == '-m') and i + 1 < len(sys.argv):
            pattern = sys.argv[i + 1]
            # Handle wildcard patterns like *.json
            if '*' in pattern or '?' in pattern:
                matched_files = glob.glob(pattern)
                if matched_files:
                    # Filter out the default output file to avoid self-merge
                    filtered_files = [f for f in matched_files if f != 'nodemap.json']
                    if len(filtered_files) != len(matched_files):
                        excluded = [f for f in matched_files if f == 'nodemap.json']
                        print("Wildcard '{}' matched {} files, excluding output file: {}".format(
                            pattern, len(matched_files), ', '.join(excluded)))
                    merge_files.extend(filtered_files)
                    if filtered_files:
                        print("Wildcard '{}' matched {} files: {}".format(pattern, len(filtered_files), ', '.join(filtered_files)))
                    else:
                        colored_print("Warning: Wildcard pattern '{}' matched no usable files (output file excluded)".format(pattern), Colors.YELLOW)
                else:
                    colored_print("Warning: Wildcard pattern '{}' matched no files".format(pattern), Colors.YELLOW)
            else:
                # For explicit filenames, also check if it's the output file
                if pattern != 'nodemap.json':
                    merge_files.append(pattern)
                else:
                    colored_print("Warning: Skipping '{}' - cannot merge output file into itself".format(pattern), Colors.YELLOW)
            i += 2
        elif arg == '--callsign' and i + 1 < len(sys.argv):
            forced_ssid = sys.argv[i + 1].upper()
            # Validate format: CALL-SSID
            if '-' not in forced_ssid:
                colored_print("Error: --callsign requires SSID (e.g., NG1P-4)", Colors.RED)
                sys.exit(1)
            # If max_hops wasn't explicitly set, default to 0 for --callsign (correction mode)
            # --callsign is a correction tool to fix one node's SSID, not a full crawl
            if not max_hops_explicit:
                max_hops = 0
            i += 2
        elif arg in ['--verbose', '-v', '--overwrite', '-o', '--display-nodes', '-d']:
            # Known flags without arguments
            i += 1
        elif arg.startswith('-') and not arg.isdigit():
            # Unknown option
            unknown_args.append(arg)
            i += 1
        else:
            i += 1
    
    # Check for unknown arguments
    if unknown_args:
        colored_print("Error: Unknown argument(s): {}".format(', '.join(unknown_args)), Colors.RED)
        print("Run '{} --help' for usage information.".format(sys.argv[0]))
        sys.exit(1)
    
    # Merge mode is default; use --overwrite to disable
    merge_mode = '--overwrite' not in sys.argv and '-o' not in sys.argv
    
    # Create crawler with specified crawl mode and exclusions
    crawler = NodeCrawler(max_hops=max_hops, username=username, password=password, verbose=verbose, notify_url=notify_url, log_file=log_file, debug_log=debug_log, resume=resume, crawl_mode=crawl_mode, exclude=exclude_nodes)
    
    # Set resume file if specified
    if resume_file:
        crawler.resume_file = resume_file
    
    # Display excluded nodes if any
    if exclude_nodes:
        print("Excluding nodes: {}".format(', '.join(sorted(exclude_nodes))))
    
    # Display logging status
    if log_file or debug_log:
        log_status = []
        if log_file:
            log_status.append("telnet -> {}".format(log_file))
        if debug_log:
            log_status.append("debug -> {}".format(debug_log))
        print("Logging: {}".format(", ".join(log_status)))
    
    # Handle merge-only mode (no crawling, just merge files)
    if merge_files and not resume and not start_node and max_hops == 10:
        print("Merge mode: Combining data from {} file(s)".format(len(merge_files)))
        
        # Load existing data if available
        if merge_mode:
            existing = crawler._load_existing_data('nodemap.json')
            if existing and 'nodes' in existing:
                crawler.nodes = existing['nodes']
                crawler.connections = existing.get('connections', [])
                # Reload intermittent_links from serialized format
                intermittent_serialized = existing.get('intermittent_links', {})
                for key_str, attempts in intermittent_serialized.items():
                    if '>' in key_str:
                        from_call, to_call = key_str.split('>', 1)
                        crawler.intermittent_links[(from_call, to_call)] = attempts
                print("Loaded {} existing nodes".format(len(crawler.nodes)))
        
        # Merge each file
        total_merged = 0
        for merge_file in merge_files:
            result = crawler.merge_external_data(merge_file)
            if result > 0:
                total_merged += result
        
        if total_merged > 0:
            # Export merged results
            crawler.export_json(merge=merge_mode)
            crawler.export_csv()
            print("\nMerge complete! Combined data from {} files.".format(len(merge_files)))
            print("Total nodes: {}".format(len(crawler.nodes)))
            print("Total connections: {}".format(len(crawler.connections)))
        else:
            print("No data was merged.")
        
        return
    
    # Only require local callsign if no start_node provided and not in resume mode
    if not start_node and not crawler.callsign and not resume:
        print("\nError: Could not determine local node callsign.")
        print("Ensure NODECALL is set in bpq32.cfg or provide a starting callsign.")
        print("\nUsage: {} [MAX_HOPS] [START_NODE] [OPTIONS]".format(sys.argv[0]))
        print("  MAX_HOPS: Maximum traversal depth (default: 4, auto-set to 0 with --callsign)")
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
    
    if resume:
        print("Mode: Resume (crawling unexplored nodes from nodemap.json)")
    elif merge_mode:
        print("Mode: Merge (updating existing nodemap.json)")
    else:
        print("Mode: Overwrite (replacing all data)")
    
    # Display crawl mode
    mode_descriptions = {
        'update': 'Update (skip visited nodes)',
        'reaudit': 'Reaudit (re-crawl all nodes)',
        'new-only': 'New-Only (queue unexplored neighbors from nodemap.json)'
    }
    print("Crawl Mode: {}".format(mode_descriptions.get(crawl_mode, crawl_mode)))
    
    # Crawl network
    try:
        # If user forced a specific SSID, pre-populate the map
        # Save it to restore after resume (which rebuilds map from JSON)
        cli_forced_ssids = {}
        forced_target = None  # Target node to crawl (for --callsign)
        if forced_ssid:
            base_call = forced_ssid.split('-')[0]
            crawler.netrom_ssid_map[base_call] = forced_ssid
            crawler.ssid_source[base_call] = ('cli', time.time())
            cli_forced_ssids[base_call] = forced_ssid
            colored_print("Forcing SSID: {} (will update SSID map for future crawls)".format(forced_ssid), Colors.GREEN)
            # --callsign means crawl TO this node, not start FROM it
            # Store as target, don't set start_node
            if not start_node:
                forced_target = base_call
        
        # Pass CLI-forced SSIDs to crawler so they survive resume
        crawler.cli_forced_ssids = cli_forced_ssids
        
        crawler.crawl_network(start_node=start_node, forced_target=forced_target)
        
        # Export results
        crawler.export_json(merge=merge_mode)
        crawler.export_csv()
        
        # Merge additional files if specified
        if merge_files:
            print("\\nMerging additional data files...")
            for merge_file in merge_files:
                result = crawler.merge_external_data(merge_file)
                if result > 0:
                    colored_print("Successfully merged {} nodes from {}".format(result, merge_file), Colors.GREEN)
            
            # Re-export with merged data
            crawler.export_json(merge=merge_mode)
            crawler.export_csv()
            print("Final merged data exported.")
        
        print("\nNetwork map complete!")
        print("Nodes discovered: {}".format(len(crawler.nodes)))
        print("Connections found: {}".format(len(crawler.connections)))
        
        # Prompt to generate maps (after seeing results)
        html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
        if os.path.isfile(html_script):
            print("")
            try:
                response = input("Generate HTML/SVG maps? (Y/n): ").strip().lower()
                if response == '' or response == 'y' or response == 'yes':
                    generate_maps = True
            except (KeyboardInterrupt, EOFError):
                print("")
                print("Skipping map generation")
        
        # Prompt for missing gridsquares
        missing_grids = []
        for callsign, node_data in crawler.nodes.items():
            location = node_data.get('location', {})
            grid = location.get('grid', '')
            if not grid:
                missing_grids.append(callsign)
        
        if missing_grids and not crawler.resume:
            print("\n{} node(s) missing gridsquare data: {}".format(
                len(missing_grids), ', '.join(sorted(missing_grids))))
            response = input("Set gridsquares now? (y/N): ").strip().lower()
            
            if response in ['y', 'yes']:
                updated_count = 0
                for callsign in sorted(missing_grids):
                    node_data = crawler.nodes[callsign]
                    location_info = node_data.get('location', {})
                    city = location_info.get('city', '')
                    state = location_info.get('state', '')
                    
                    # Show context
                    if city or state:
                        prompt = "Gridsquare for {} ({}{}): ".format(
                            callsign, city, ', ' + state if state else '')
                    else:
                        prompt = "Gridsquare for {}: ".format(callsign)
                    
                    grid_input = input(prompt).strip()
                    
                    # Skip if blank
                    if not grid_input:
                        continue
                    
                    # Validate format (warn but allow)
                    if not re.match(r'^[A-R]{2}[0-9]{2}[a-x]{2}$', grid_input, re.IGNORECASE):
                        print("  Warning: '{}' doesn't match standard gridsquare format".format(grid_input))
                        confirm = input("  Use it anyway? (y/N): ").strip().lower()
                        if confirm not in ['y', 'yes']:
                            continue
                    
                    # Update the node data
                    if 'location' not in crawler.nodes[callsign]:
                        crawler.nodes[callsign]['location'] = {}
                    crawler.nodes[callsign]['location']['grid'] = grid_input
                    crawler.nodes[callsign]['gridsquare'] = grid_input
                    updated_count += 1
                    print("  Set {} = {}".format(callsign, grid_input))
                
                if updated_count > 0:
                    print("\nUpdated {} gridsquare(s), re-exporting...".format(updated_count))
                    crawler.export_json(merge=merge_mode)
                    crawler.export_csv()
        
        # Generate HTML/SVG maps if user opted in
        if generate_maps:
            print("\nGenerating maps...")
            html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
            try:
                import subprocess
                result = subprocess.call(['python3', html_script, '--all'])
                if result == 0:
                    colored_print("Maps generated successfully!", Colors.GREEN)
                else:
                    colored_print("Warning: Map generation exited with code {}".format(result), Colors.YELLOW)
            except Exception as e:
                colored_print("Error generating maps: {}".format(e), Colors.RED)
        
        # Notify successful completion
        crawler._send_notification("Successfully crawled {} nodes!".format(len(crawler.nodes)))
        
        # Close log file if open
        if crawler.log_handle:
            crawler.log_handle.close()
        
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
        
        # Close log file if open
        if crawler.log_handle:
            crawler.log_handle.close()


if __name__ == '__main__':
    main()
