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
Version: 1.3.1
"""

__version__ = '1.3.61'

import sys
import telnetlib
import socket
import time
import json
import csv
import glob
import re
import os
from collections import deque


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
    
    def __init__(self, host='localhost', port=None, callsign=None, max_hops=10, username=None, password=None, verbose=False, notify_url=None, log_file=None, resume=False):
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
            log_file: File to log all telnet traffic to (default: None)
            resume: Resume from unexplored nodes in existing nodemap.json (default: False)
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
        self.resume = resume
        self.resume_file = None  # Set externally if specific file needed
        self.visited = set()  # Nodes we've already crawled
        self.failed = set()  # Nodes that failed connection
        self.nodes = {}  # Node data: {callsign: {info, neighbors, location, type}}
        self.connections = []  # List of [node1, node2, port] connections
        self.routes = {}  # Best routes to nodes: {callsign: [path]}
        self.route_ports = {}  # Port numbers for direct neighbors: {callsign: port_number}
        self.shortest_paths = {}  # Shortest discovered path to each node: {callsign: [path]}
        self.netrom_ssid_map = {}  # Global NetRom SSID mapping: {base_callsign: 'CALLSIGN-SSID'}
        self.alias_to_call = {}  # Global alias->callsign-SSID mapping: {'CHABUR': 'KS1R-13'}
        self.call_to_alias = {}  # Reverse lookup: {'KS1R': 'CHABUR'}
        self.last_heard = {}  # MHEARD timestamps: {callsign: seconds_ago}
        self.intermittent_links = {}  # Failed connections: {(from, to): [attempts]}
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
                print("Warning: Could not open log file {}: {}".format(self.log_file, e))
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
                print("    Notification failed: {}".format(e))
    
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
            
            # Connect through nodes in path (for multi-hop or direct connections from local node)
            for i, callsign in enumerate(path):
                # Strategy: Prefer direct connection (C PORT CALL-SSID) when we have port info
                # This bypasses NetRom routing and is faster for direct neighbors
                # Fallback to NetRom alias (C ALIAS) if no port info available
                
                # Extract base callsign for lookups (route_ports and netrom_ssid_map are keyed by base call)
                lookup_call = callsign.split('-')[0] if '-' in callsign else callsign
                
                port_num = self.route_ports.get(lookup_call)
                full_callsign = self.netrom_ssid_map.get(lookup_call, callsign)
                
                if port_num and full_callsign:
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
                        
                        # Update global mappings
                        for alias, full_call in all_aliases.items():
                            base_call = full_call.split('-')[0]
                            if base_call not in self.call_to_alias:
                                self.call_to_alias[base_call] = alias
                                self.alias_to_call[alias] = full_call
                        
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
                # Base 20s + 20s per hop, max 2 minutes
                conn_timeout = min(20 + (i * 20), 120)
                start_time = time.time()
                connected = False
                response = ""
                
                if self.verbose:
                    print("    Waiting for connection (timeout: {}s)...".format(conn_timeout))
                
                # Set socket timeout to prevent read_some() from blocking forever
                # Use short timeout so we can check elapsed time in the loop
                tn.sock.settimeout(2.0)
                
                while time.time() - start_time < conn_timeout:
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
                        
                        time.sleep(0.5)
                        
                    except socket.timeout:
                        # Socket read timed out, but we're still within conn_timeout
                        # Just continue waiting for more data
                        pass
                    except EOFError:
                        print("  Connection lost to {}".format(callsign))
                        tn.close()
                        return None
                
                if not connected:
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
                        
                        # Wait for connection with same timeout
                        start_time = time.time()
                        connected = False
                        response = ""
                        
                        if self.verbose:
                            print("    Waiting for NetRom connection (timeout: {}s)...".format(conn_timeout))
                        
                        while time.time() - start_time < conn_timeout:
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
                    prompt_data = tn.read_until(b'} ', timeout=10)
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
                    time.sleep(0.5)  # Give any trailing data time to arrive
                    extra_data = tn.read_very_eager()
                    if extra_data:
                        self._log('RECV', extra_data)
                        if self.verbose:
                            print("    Cleared {} bytes of buffered data".format(len(extra_data)))
                except:
                    # If no prompt received, just consume whatever is buffered
                    buffered = tn.read_very_eager()
                    self._log('RECV', buffered)
                    if self.verbose:
                        print("    No clear prompt, consumed {} bytes".format(len(buffered)))
            
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
            response = b''
            read_attempts = 0
            max_attempts = 3  # Try multiple times to get complete response
            last_response_len = 0
            
            while read_attempts < max_attempts:
                read_attempts += 1
                
                try:
                    # Try to read until prompt
                    chunk = tn.read_until(b'} ', timeout=timeout)
                    self._log('RECV', chunk)
                    response += chunk
                    
                    # Try to get second prompt (actual response follows first prompt)
                    chunk2 = tn.read_until(b'} ', timeout=timeout)
                    self._log('RECV', chunk2)
                    response += chunk2
                except:
                    pass
                
                # Consume any extra buffered data
                time.sleep(0.5)  # Give time for trailing data to arrive
                try:
                    extra = tn.read_very_eager()
                    if extra:
                        self._log('RECV', extra)
                        response += extra
                except:
                    pass
                
                # Check if we have enough data (response stopped growing)
                if len(response) > 0 and len(response) == last_response_len:
                    break
                last_response_len = len(response)
                
                # If we have expected content, check for it
                decoded_check = response.decode('ascii', errors='ignore')
                if expect_content and expect_content.lower() in decoded_check.lower():
                    break  # Found what we're looking for
                
                # Small delay before retry
                if read_attempts < max_attempts:
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
            print("Warning: Could not load {}: {}".format(filename, e))
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
        for callsign, node_data in nodes_data.items():
            # Restore netrom_ssids from each node's discovered SSID data
            node_ssids = node_data.get('netrom_ssids', {})
            for base_call, full_call in node_ssids.items():
                if base_call not in self.netrom_ssid_map:
                    self.netrom_ssid_map[base_call] = full_call
                    if self.verbose:
                        print("Restored SSID mapping: {} = {}".format(base_call, full_call))
            
            # Also restore route_ports from heard_on_ports data (MHEARD port information)
            heard_on_ports = node_data.get('heard_on_ports', [])
            for call, port in heard_on_ports:
                if port is not None and call not in self.route_ports:
                    self.route_ports[call] = port
                    if self.verbose:
                        print("Restored MHEARD port: {} on port {}".format(call, port))
            
            # Also restore route_ports from routes data (for any additional entries)
            routes = node_data.get('routes', {})
            for neighbor, quality in routes.items():
                if neighbor not in self.route_ports and quality > 0:
                    # Use port 1 as fallback if no MHEARD data available
                    self.route_ports[neighbor] = 1
                    if self.verbose:
                        print("Restored route port (fallback): {} on port 1".format(neighbor))
        
        if self.verbose and self.netrom_ssid_map:
            print("Restored {} SSID mappings from previous crawl".format(len(self.netrom_ssid_map)))
        if self.verbose and self.route_ports:
            print("Restored {} route ports from previous crawl".format(len(self.route_ports)))
        
        # Find unexplored neighbors from each visited node
        for callsign, node_data in nodes_data.items():
            unexplored_neighbors = node_data.get('unexplored_neighbors', [])
            if self.verbose and unexplored_neighbors:
                print("Node {} has {} unexplored neighbors: {}".format(callsign, len(unexplored_neighbors), ', '.join(unexplored_neighbors)))
            
            # Also check neighbors that were never visited
            all_neighbors = node_data.get('neighbors', [])
            for neighbor in all_neighbors:
                if neighbor not in self.visited and neighbor not in [u for u, _ in unexplored]:
                    # Calculate path to this neighbor through the visited node
                    # We need to reconstruct the path to reach the parent node first
                    hop_distance = node_data.get('hop_distance', 0)
                    if hop_distance == 0:
                        # Parent is local node, direct connection
                        path = []
                    else:
                        # For now, use direct path through parent
                        # Could be optimized by finding shortest path
                        path = [callsign]
                    
                    unexplored.append((neighbor, path))
        
        # Remove duplicates (same callsign might appear as neighbor of multiple nodes)
        seen = set()
        unique_unexplored = []
        for call, path in unexplored:
            if call not in seen:
                seen.add(call)
                unique_unexplored.append((call, path))
        
        print("Found {} unexplored neighbors".format(len(unique_unexplored)))
        return unique_unexplored
    
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
            # Look for patterns like "433.300 MHz", "145.050 MHz", "144.930 MHz"
            frequency = None
            freq_match = re.search(r'(\d+\.\d+)\s*MHz', rest, re.IGNORECASE)
            if freq_match:
                frequency = float(freq_match.group(1))
            
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
        standard_commands = [
            # BPQ User Commands
            'BYE', 'CONNECT', 'C', 'DISCONNECT', 'D', 'INFO', 'I', 'NODES', 'N',
            'PORTS', 'ROUTES', 'USERS', 'U', 'MHEARD', 'MH', 'LINKS', 'L',
            'SESSION', 'S', 'YAPP', 'UNPROTO', 'VERSION', 'V', 'HOME', 'CQ',
            # BPQ Sysop Commands
            'SYSOP', 'ATTACH', 'DETACH', 'RECONNECT', 'RESPTIME', 'FRACK',
            'FRACKS', 'PACLEN', 'MAXFRAME', 'RETRIES', 'RESET',
            # JNOS Commands
            'ARP', 'DIALER', 'DOMAIN', 'EXIT', 'FINGER', 'FTP', 'HELP',
            'HOPCHECK', 'IFCONFIG', 'IP', 'KICK', 'LOG', 'NETROM', 'PING',
            'PPP', 'RECORD', 'REMOTE', 'RESET', 'ROUTE', 'SMTP', 'START',
            'STOP', 'TCP', 'TRACE', 'UDP', 'UPLOAD',
            # FBB Commands
            'ABORT', 'CHECK', 'DIR', 'EXPERT', 'HELP', 'KILL', 'LIST',
            'READ', 'REPLY', 'SEND', 'STATS', 'TALK', 'VERBOSE', 'WHO'
        ]
        
        # Built-in BPQ applications that should be counted as apps
        builtin_apps = ['BBS', 'CHAT', 'RMS', 'APRS']
        
        # Filter: include if NOT in standard commands OR if in builtin apps
        applications = [cmd for cmd in commands 
                       if cmd.upper() not in standard_commands or cmd.upper() in builtin_apps]
        
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
        
        colored_print("Crawling {}{}".format(callsign, path_desc), Colors.CYAN)
        
        self.visited.add(callsign)
        
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
        # 3 minutes base + 2 minutes per hop (was 2min + 1min/hop)
        # This gives more time for processing routes, mheard, and neighbor analysis
        operation_deadline = time.time() + 180 + (hop_count * 120)
        
        try:
            # Helper to check if we've exceeded deadline
            def check_deadline():
                if time.time() > operation_deadline:
                    colored_print("  Operation timeout for {} ({} hops)".format(callsign, hop_count), Colors.YELLOW)
                    return True
                return False
            
            # Inter-command delay scales with hop count
            # Over multi-hop RF, need time for responses to fully arrive
            inter_cmd_delay = 0.5 + (hop_count * 0.5)  # 0.5s base + 0.5s per hop
            
            # Get PORTS to identify RF ports
            if check_deadline():
                return
            ports_output = self._send_command(tn, 'PORTS', timeout=cmd_timeout, expect_content='Port')
            ports_list = self._parse_ports(ports_output)
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
            for alias, full_call in other_aliases.items():
                base_call = full_call.split('-')[0]
                
                # Store alias mapping for documentation
                if base_call not in self.call_to_alias:
                    self.call_to_alias[base_call] = alias
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
            # Update global route_ports with direct neighbor port info from this node
            self.route_ports.update(route_ports)
            
            # ROUTES SSIDs are AUTHORITATIVE for node connections
            # These are the actual node SSIDs (e.g., K1NYY-15), not app SSIDs (K1NYY-2 BBS, K1NYY-10 RMS)
            for call, ssid in routes_ssids.items():
                if call not in self.netrom_ssid_map or call in routes_ssids:
                    # Always prefer ROUTES SSID - it's the definitive node SSID
                    self.netrom_ssid_map[call] = ssid
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
                                mheard_ssids[base_call] = full_callsign
                                if self.verbose:
                                    if has_ssid:
                                        print("    MHEARD SSID for {}: {} (not in ROUTES table)".format(base_call, full_callsign))
                                    else:
                                        print("    MHEARD {} (no SSID - not a node, skipping)".format(full_callsign))
                            elif self.verbose and has_ssid:
                                # Already have SSID, ignore subsequent entries
                                print("    Ignoring {} (already have {})".format(full_callsign, mheard_ssids[base_call]))
                            
                            # Only add to neighbor list if it has an SSID (is a node)
                            # Stations without SSIDs can't be crawled
                            if has_ssid:
                                mheard_neighbors.append(base_call)
                                
                                # Store port info
                                if base_call not in mheard_ports:
                                    mheard_ports[base_call] = port_num
            
            # Update global netrom_ssid_map with MHEARD data
            # Priority: 1) ROUTES (already stored above - authoritative for direct neighbors)
            #           2) MHEARD (only if not already mapped from ROUTES)
            # Don't overwrite existing entries - ROUTES already has correct node SSIDs
            for call, ssid in mheard_ssids.items():
                if call not in self.netrom_ssid_map:
                    # Not in ROUTES, use MHEARD SSID (may be app/operator)
                    self.netrom_ssid_map[call] = ssid
            
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
            
            self.nodes[callsign] = {
                'info': info_output.strip(),
                'neighbors': all_neighbors,  # Direct RF neighbors from MHEARD (with SSIDs only)
                'explored_neighbors': explored_neighbors,  # Neighbors that were/will be visited
                'unexplored_neighbors': unexplored_neighbors,  # Neighbors skipped (hop limit)
                'intermittent_neighbors': intermittent_neighbors,  # Neighbors with failed connections
                'hop_distance': hop_count,  # RF hops from start node
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
            
            # Record connections
            for neighbor in all_neighbors:
                link_key = (callsign, neighbor)
                is_intermittent = link_key in self.intermittent_links
                
                self.connections.append({
                    'from': callsign,
                    'to': neighbor,
                    'port': None,
                    'quality': routes.get(neighbor, 0),
                    'intermittent': is_intermittent  # Mark unreliable/failed connections
                })
                
                # Add unvisited neighbors to queue with shortest path optimization
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
                    
                    # Check if this is a shorter path than previously discovered
                    if neighbor not in self.shortest_paths or len(new_path) < len(self.shortest_paths[neighbor]):
                        self.shortest_paths[neighbor] = new_path
                        
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
                        
                        # Only queue if this is a new or shorter path
                        self.queue.append((neighbor, new_path))
            
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
        # Resume mode: load unexplored nodes from existing data
        if self.resume:
            resume_filename = self.resume_file if self.resume_file else 'nodemap.json'
            print("Resume mode: Loading unexplored nodes from {}...".format(resume_filename))
            unexplored = self._load_unexplored_nodes(resume_filename)
            
            if not unexplored:
                print("No unexplored nodes found.")
                if len(self.visited) > 0:
                    print("All {} previously crawled nodes have been fully explored.".format(len(self.visited)))
                    colored_print("Use normal mode to start a fresh crawl or increase max hops.", Colors.YELLOW)
                else:
                    colored_print("No previous crawl data found. Use normal mode to start a fresh crawl.", Colors.RED)
                return
            
            # Queue all unexplored nodes
            for callsign, path in unexplored:
                self.queue.append((callsign, path))
            
            colored_print("Queued {} unexplored nodes for crawling".format(len(unexplored)), Colors.GREEN)
            self._send_notification("Resume crawl: {} unexplored nodes".format(len(unexplored)))
            
            # In resume mode, we don't have a single starting callsign
            starting_callsign = None
            
            # Skip the normal start node logic
            print("BPQ node: {}:{}".format(self.host, self.port))
            print("Max hops: {}".format(self.max_hops))
            print("-" * 50)
        else:
            # Normal mode: start from specified or local node
            # Determine starting node
            starting_path = []  # Path to reach the starting node
            
            if start_node:
                # Validate provided callsign
                if not self._is_valid_callsign(start_node):
                    print("Error: Invalid callsign format: {}".format(start_node))
                    return
                starting_callsign = start_node.upper()
                print("Starting network crawl from: {}...".format(starting_callsign))
                
                # Pre-load route information from existing nodemap.json if available
                # This ensures we have port numbers and SSIDs for connecting to the start node
                existing = self._load_existing_data('nodemap.json')
                
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
                        
                        # Restore netrom_ssids (for connection commands)
                        for base_call, full_call in node_info.get('netrom_ssids', {}).items():
                            # For the node itself, always use its own SSID (authoritative)
                            # For others, only if not already set
                            if base_call == node_call or base_call not in self.netrom_ssid_map:
                                self.netrom_ssid_map[base_call] = full_call
                        
                        # Restore route_ports (port numbers for neighbors)
                        for neighbor_call, port_num in node_info.get('heard_on_ports', []):
                            if port_num is not None and neighbor_call not in self.route_ports:
                                self.route_ports[neighbor_call] = port_num
                        
                        # Restore call_to_alias mappings (for NetRom routing)
                        for alias, full_call in node_info.get('seen_aliases', {}).items():
                            base_call = full_call.split('-')[0]
                            if base_call not in self.call_to_alias:
                                self.call_to_alias[base_call] = alias
                                self.alias_to_call[alias] = full_call
                    
                    if self.route_ports:
                        if self.verbose:
                            print("Loaded {} port mappings from existing nodemap.json".format(len(self.route_ports)))
                    
                    if self.call_to_alias:
                        if self.verbose:
                            print("Loaded {} NetRom aliases from existing nodemap.json".format(len(self.call_to_alias)))
                    
                    # Find path to remote start node through existing network
                    # Look for a node that has the start_node as a neighbor
                    if starting_callsign != self.callsign:
                        # Not the local node - need to find how to reach it
                        target_base = starting_callsign.split('-')[0] if '-' in starting_callsign else starting_callsign
                        
                        if self.verbose:
                            print("Looking for path to {} among known neighbors...".format(target_base))
                        
                        found_path = False
                        for node_call, node_info in nodes_data.items():
                            neighbors = node_info.get('neighbors', [])
                            if self.verbose:
                                print("  {} has neighbors: {}".format(node_call, ', '.join(neighbors) if neighbors else 'none'))
                            
                            # Check if this node has the target as a neighbor
                            if target_base in neighbors:
                                # Found a node that can reach the target
                                if node_call == self.callsign:
                                    # Target is direct neighbor of local node
                                    starting_path = []
                                    if self.verbose:
                                        print("Found {} as direct neighbor of local node {}".format(target_base, self.callsign))
                                else:
                                    # Target is neighbor of another node - route through that node
                                    starting_path = [node_call]
                                    if self.verbose:
                                        print("Found {} reachable via {}".format(target_base, node_call))
                                found_path = True
                                break
                        
                        if not found_path:
                            if self.verbose:
                                print("Warning: {} not found in any known node's neighbor list".format(target_base))
                            # Fallback: Check if we have a NetRom alias for direct connection
                            if target_base in self.call_to_alias:
                                if self.verbose:
                                    print("Found NetRom alias for {}: {}".format(target_base, self.call_to_alias[target_base]))
                                # Leave starting_path=[] for direct NetRom connection
                            else:
                                if self.verbose:
                                    print("No NetRom alias found for {}, will try direct fallback".format(target_base))
                else:
                    if self.verbose:
                        print("No existing nodemap.json found or no nodes in it")
                        print("Will attempt NetRom discovery when connecting to local node")
            else:
                if not self.callsign:
                    print("Error: Could not determine local node callsign from bpq32.cfg.")
                    print("Please ensure NODECALL is set in your bpq32.cfg file.")
                    print("Or provide a starting callsign: {} [MAX_HOPS] [START_NODE]".format(sys.argv[0]))
                    return
                starting_callsign = self.callsign
                colored_print("Starting network crawl from local node: {}...".format(starting_callsign), Colors.GREEN)
            
            print("BPQ node: {}:{}".format(self.host, self.port))
            print("Max hops: {}".format(self.max_hops))
            print("-" * 50)
            
            # Start with specified or local node (with path if remote)
            # path contains intermediate hops only (not the target node itself)
            queue_entry = (starting_callsign, starting_path if start_node else [])
            if self.verbose and start_node:
                print("Queuing {} with path: {}".format(starting_callsign, starting_path if starting_path else "(direct)"))
            self.queue.append(queue_entry)
        
        # BFS traversal with priority sorting by MHEARD recency
        while self.queue:
            # Sort queue by last_heard timestamp (most recent first)
            # Nodes not in last_heard go to end (never heard, likely stale)
            queue_list = list(self.queue)
            queue_list.sort(key=lambda x: self.last_heard.get(x[0], 999999))
            self.queue = deque(queue_list)
            
            callsign, path = self.queue.popleft()
            
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
        
        # Load existing data if merge mode
        if merge:
            existing = self._load_existing_data(filename)
            if existing and 'nodes' in existing:
                nodes_data = existing['nodes']
                print("Merging with {} existing nodes...".format(len(nodes_data)))
        
        # Update with current crawl data (overwrites duplicates)
        for callsign, node_data in self.nodes.items():
            nodes_data[callsign] = node_data
        
        # Convert intermittent_links keys to strings for JSON serialization
        intermittent_serialized = {}
        for (from_call, to_call), attempts in self.intermittent_links.items():
            key = "{}>{}".format(from_call, to_call)
            intermittent_serialized[key] = attempts
        
        data = {
            'nodes': nodes_data,
            'connections': self.connections,
            'intermittent_links': intermittent_serialized,  # Failed/unreliable connections
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
                print("Error: Invalid or missing nodemap data in {}".format(filename))
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
            print("Error merging {}: {}".format(filename, e))
            return -1


def main():
    """Main entry point."""
    # Check for help flag first
    if '-h' in sys.argv or '--help' in sys.argv or '/?' in sys.argv:
        print("BPQ Node Map Crawler v{}".format(__version__))
        print("=" * 50)
        print("\nAutomatically crawls packet radio network to discover topology.")
        print("\nUsage: {} [MAX_HOPS] [START_NODE] [OPTIONS]".format(sys.argv[0]))
        print("\nArguments:")
        print("  MAX_HOPS         Maximum RF hops from start (default: 10)")
        print("                   0=local only, 1=direct neighbors, 2=neighbors+their neighbors")
        print("  START_NODE       Callsign to begin crawl (default: local node)")
        print("\nOptions:")
        print("  --overwrite, -o  Overwrite existing data (default: merge)")
        print("  --resume, -r     Resume from unexplored nodes in nodemap.json")
        print("                   Automatically finds nodemap_partial*.json if nodemap.json missing")
        print("  --resume FILE    Resume from specific JSON file")
        print("  --merge FILE, -m Merge another nodemap.json file into current data")
        print("                   Supports wildcards: --merge *.json")
        print("  --user USERNAME  Telnet login username (default: prompt if needed)")
        print("  --pass PASSWORD  Telnet login password (default: prompt if needed)")
        print("  --notify URL     Send notifications to webhook URL")
        print("  --verbose, -v    Show detailed command/response output")
        print("  --log FILE, -l   Log all telnet traffic to file")
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
    
    print("BPQ Node Map Crawler v{}".format(__version__))
    print("=" * 50)
    
    # Parse command line args
    max_hops = 10
    start_node = None
    username = None
    password = None
    notify_url = None
    log_file = None
    merge_files = []  # List of files to merge
    resume_file = None  # File to resume from (None = auto-detect)
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    resume = '--resume' in sys.argv or '-r' in sys.argv
    
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
        elif (arg == '--notify' or arg == '-n') and i + 1 < len(sys.argv):
            notify_url = sys.argv[i + 1]
            i += 2
        elif (arg == '--log' or arg == '-l') and i + 1 < len(sys.argv):
            log_file = sys.argv[i + 1]
            i += 2
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
                        print("Warning: Wildcard pattern '{}' matched no usable files (output file excluded)".format(pattern))
                else:
                    print("Warning: Wildcard pattern '{}' matched no files".format(pattern))
            else:
                # For explicit filenames, also check if it's the output file
                if pattern != 'nodemap.json':
                    merge_files.append(pattern)
                else:
                    print("Warning: Skipping '{}' - cannot merge output file into itself".format(pattern))
            i += 2
        else:
            i += 1
    
    # Merge mode is default; use --overwrite to disable
    merge_mode = '--overwrite' not in sys.argv and '-o' not in sys.argv
    
    # Create crawler
    crawler = NodeCrawler(max_hops=max_hops, username=username, password=password, verbose=verbose, notify_url=notify_url, log_file=log_file, resume=resume)
    
    # Set resume file if specified
    if resume_file:
        crawler.resume_file = resume_file
    
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
    
    if resume:
        print("Mode: Resume (crawling unexplored nodes from nodemap.json)")
    elif merge_mode:
        print("Mode: Merge (updating existing nodemap.json)")
    else:
        print("Mode: Overwrite (replacing all data)")
    
    # Crawl network
    try:
        crawler.crawl_network(start_node=start_node)
        
        # Export results
        crawler.export_json(merge=merge_mode)
        crawler.export_csv()
        
        # Merge additional files if specified
        if merge_files:
            print("\\nMerging additional data files...")
            for merge_file in merge_files:
                result = crawler.merge_external_data(merge_file)
                if result > 0:
                    print("Successfully merged {} nodes from {}".format(result, merge_file))
            
            # Re-export with merged data
            crawler.export_json(merge=merge_mode)
            crawler.export_csv()
            print("Final merged data exported.")
        
        print("\nNetwork map complete!")
        print("Nodes discovered: {}".format(len(crawler.nodes)))
        print("Connections found: {}".format(len(crawler.connections)))
        
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
