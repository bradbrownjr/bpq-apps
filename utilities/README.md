# BPQ Utilities

Sysop tools for BBS management, network mapping, and maintenance tasks.

**Installation**: See [docs/INSTALLATION.md#utilities-installation](../docs/INSTALLATION.md#utilities-installation) for setup instructions and directory layout.

## Table of Contents

- [nodemap.py - Network Topology Mapper](#nodemappy---network-topology-mapper)
  - [Quick Install](#quick-install)
  - [Key Features](#key-features)
  - [Network Assumptions](#network-assumptions)
  - [Usage](#usage)
  - [Multi-Node Mapping Workflow](#multi-node-mapping-workflow)
  - [Data Storage Modes](#data-storage-modes)
  - [Examples](#examples)
  - [Output Files](#output-files)
  - [Captured Data](#captured-data)
  - [Timeout Protection](#timeout-protection)
  - [Crawl Modes](#crawl-modes)
  - [Requirements](#requirements)
- [nodemap-html.py - Interactive Map Generator](#nodemap-htmlpy---interactive-map-generator)
  - [Features](#features)
  - [Usage](#usage-1)
  - [Output](#output)

## nodemap.py - Network Topology Mapper

Advanced packet radio network discovery tool that crawls through BPQ nodes via RF connections to map topology, applications, and connectivity. Creates comprehensive network maps by analyzing routing tables, MHEARD lists, and node information.

### Quick Install

Download all nodemap scripts:
```bash
for f in nodemap.py nodemap-html.py map_boundaries.py; do wget -O "$f" "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/$f"; done && chmod +x nodemap.py nodemap-html.py
```

### Key Features

- **RF-Only Discovery**: Uses actual RF connections, ignoring IP/Telnet ports
- **Intelligent SSID Selection**: Distinguishes node SSIDs from application SSIDs (BBS, RMS, CHAT)
- **Quality-Based Routing**: Respects sysop quality settings, skips blocked routes (quality 0)
- **Multi-Perspective Mapping**: Combines data from multiple operators' viewpoints
- **Resume Capability**: Continues interrupted crawls from unexplored nodes
- **Timeout Protection**: Handles slow RF links with adaptive timeouts
- **Data Preservation**: Merge mode preserves historical data across runs

### Network Assumptions

**Node Discovery:**
- Uses MHEARD lists from RF ports to find actual neighbors
- Only crawls stations with SSIDs (assumes they run node software)
- Validates callsign format before attempting connections

**SSID Selection Priority:**
1. **ROUTES command** (authoritative) - Shows actual node SSIDs for connections
2. **Newer MHEARD data** (can update old MHEARD) - What was heard on RF within 1 hour
3. **Older MHEARD data** (fallback) - Stale RF observations
4. **NODES aliases** (ignored for connections) - Often contain app SSIDs like BBS (-2), RMS (-10)

**SSID Tracking:**
- Tracks source of each SSID: ROUTES (authoritative), MHEARD (RF observed), or CLI (user-forced)
- ROUTES always wins, newer MHEARD (>1hr) can update older MHEARD
- Prevents stale SSID discovery from causing incorrect connections
- Use `--callsign CALL-SSID` to force correct SSID when known
- CLI-forced SSIDs persist through disconnects/reconnections and update JSON permanently

**Correcting Bad SSID Data:**
If nodemap.json has incorrect SSID (e.g., connected to BBS instead of node):
1. Use `--callsign` flag alone: `./nodemap.py --callsign NG1P-4` (auto: max_hops=0, start_node=NG1P)
2. Script connects to correct SSID for all attempts (initial + reconnects)
3. Upon successful crawl, updates node's `netrom_ssids` in JSON
4. Future crawls use corrected SSID automatically (no flag needed)

**Path Quality:**
- **Quality > 0**: Route is available and usable
- **Quality 0**: Sysop has blocked this route (poor RF, policy, etc.)
- **Not in ROUTES**: Node not reachable from current vantage point

**RF vs IP Separation:**
- Focuses exclusively on RF connectivity for actual packet radio topology
- Ignores Telnet/TCP ports to avoid Internet-based connections
- Maps real over-the-air packet radio network structure

### Usage

```bash
./nodemap.py [MAX_HOPS] [START_NODE] [OPTIONS]
```

**Parameters:**
- `MAX_HOPS` - Maximum RF hops to traverse (default: 4, auto-set to 0 with --callsign)
- `START_NODE` - Callsign to start from (default: local node from bpq32.cfg)

**Options:**
- `--overwrite` or `-o` - Replace existing data (default: merge mode)
- `--resume` or `-r` - Continue from unexplored nodes in existing data
- `--callsign CALL-SSID` - Force specific node SSID (e.g., `--callsign NG1P-4`)
  - **Correction mode**: Automatically sets max_hops=0 and start_node when used alone
  - Use to fix bad SSID data without crawling entire network
  - Example: `./nodemap.py --callsign NG1P-4` (crawls only NG1P-4, 0 neighbors)
  - Override with explicit max_hops: `./nodemap.py 5 --callsign NG1P-4` (crawls NG1P-4 + 5 hops)
  - Overrides auto-discovered SSID for all connection attempts (including reconnects)
  - Updates node's `netrom_ssids` in JSON to correct bad data permanently
  - Forced SSID persists for future crawls even without the flag
- `--query CALL` or `-q CALL` - Query node info without crawling
  - Shows neighbors (explored/unexplored), apps, routes, best path
  - Use to check nodes from nodemap-html.py "unmapped nodes" list
  - Fast lookup: `./nodemap.py -q NG1P`
- `--cleanup [TARGET]` - Clean up nodemap.json data
  - `nodes`: Remove duplicate SSID entries and incomplete nodes (no neighbors/location/apps)
  - `connections`: Remove invalid connections (not in ROUTES or quality 0)
  - `all`: Both nodes and connections cleanup (default if TARGET omitted)
  - Automatically creates backup before making changes
  - Examples: `./nodemap.py --cleanup`, `./nodemap.py --cleanup connections`
- `--set-grid CALL GRID` - Set gridsquare for node (e.g., `--set-grid NG1P FN43vp`)
  - Updates location data for nodes without gridsquare in INFO
  - Validates gridsquare format (warns if non-standard)
  - Offers to regenerate maps after update
- `--display-nodes` or `-d` - Display nodes table from nodemap.json and exit
- `--mode MODE` - Crawl mode: `update` (default), `reaudit`, `new-only`
  - `update`: Skip already-visited nodes in current session (fastest)
  - `reaudit`: Re-crawl all nodes to verify/update data
  - `new-only`: Auto-load nodemap.json, queue only unexplored neighbors
- `--exclude CALLS` or `-x CALLS` - Exclude callsigns from crawling (comma-separated)
  - Example: `--exclude AB1KI,N1REX,K1NYY`
  - Useful for skipping offline or problematic nodes
- `--merge FILE` - Combine data from another operator's nodemap.json
- `--verbose` or `-v` - Show detailed command/response output
- `--notify URL` - Send progress notifications to webhook
- `--log FILE` - Log all telnet traffic for debugging
- `--user USERNAME` - Telnet login username (default: prompt if needed)
- `--pass PASSWORD` - Telnet login password (default: prompt if needed)

### Multi-Node Mapping Workflow

For comprehensive network coverage, coordinate with other operators:

1. **Each operator runs from their perspective:**
   ```bash
   # Operator 1 (Southern region)
   ./nodemap.py 15 > south_network.log
   
   # Operator 2 (Northern region)  
   ./nodemap.py 12 > north_network.log
   
   # Operator 3 (Western region)
   ./nodemap.py 10 > west_network.log
   ```

2. **Share the resulting nodemap.json files** via email, BBS, or file transfer

3. **One operator combines all perspectives:**
   ```bash
   ./nodemap.py --merge north_nodemap.json --merge west_nodemap.json
   ```

4. **Result**: Comprehensive network map showing connectivity from all vantage points

### Data Storage Modes

**Default mode (merge):**
- Loads existing `nodemap.json`
- Updates nodes with new data (overwrites if callsign exists)
- Preserves historical data from previous crawls
- Ideal for incremental discovery and building comprehensive maps

**Overwrite mode (`--overwrite`):**
- Completely replaces `nodemap.json` and `nodemap.csv` each run
- Use for fresh network scans or when data needs reset

**Merge mode (`--merge`):**
- Combines data from external nodemap.json files
- Intelligently merges neighbor lists (union of all neighbors)
- Preserves most detailed application and location data
- Handles duplicate connections and intermittent links

### Examples

```bash
# Basic crawling
./nodemap.py 5                    # Crawl 5 hops from local node
./nodemap.py 10 WS1EC            # Crawl 10 hops starting from WS1EC
./nodemap.py 5 --overwrite       # Crawl and replace existing data

# Crawl modes (bandwidth optimization)
./nodemap.py 5 --mode new-only    # Only discover new nodes (saves RF bandwidth)
./nodemap.py 10 --mode reaudit    # Re-verify all nodes (update existing data)
./nodemap.py 3 --mode update      # Default: skip visited nodes in this session

# Excluding problematic nodes
./nodemap.py 5 --exclude AB1KI           # Skip one node
./nodemap.py 5 -x AB1KI,N1REX,K1NYY      # Skip multiple nodes (comma-separated)
./nodemap.py 10 --mode new-only -x AB1KI # Combine with other options

# Resume interrupted crawls
./nodemap.py --resume             # Continue from unexplored nodes
./nodemap.py 15 KC1JMH           # Resume/expand from previous crawl

# Multi-operator mapping
./nodemap.py --merge remote_map.json              # Merge one file
./nodemap.py --merge map1.json --merge map2.json  # Merge multiple files
./nodemap.py 10 --merge other_perspective.json    # Crawl AND merge

# Advanced options
./nodemap.py 10 --verbose --log debug.txt         # Detailed logging
./nodemap.py 5 --notify https://my.webhook.com    # Progress notifications
./nodemap.py 10 --user KC1JMH --pass mypass       # With authentication

# Force specific SSID (when node has multiple)
./nodemap.py --callsign NG1P-4                    # Correction mode: crawls only NG1P-4 (0 hops)
./nodemap.py 5 --callsign NG1P-4                  # Crawl NG1P-4 + 5 hops (explicit override)
./nodemap.py 10 WS1EC --callsign WS1EC-15         # Start at WS1EC, force node port SSID

# Data maintenance
./nodemap.py --cleanup                            # Clean all (nodes + connections)
./nodemap.py --cleanup nodes                      # Remove duplicates and incomplete nodes only
./nodemap.py --cleanup connections                # Remove invalid connections only
./nodemap.py --set-grid NG1P FN43vp               # Add gridsquare for node
./nodemap.py -d                                   # Display nodes table

# Query node information
./nodemap.py -q NG1P                              # Show what we know about NG1P
./nodemap.py --query KC1JMH                       # Neighbors, apps, routes, best path
```

### Output Files

**nodemap.json** - Complete network data including:
- Node information (location, type, ports, applications)
- Connections between nodes
- Metadata (timestamp, mode, total counts)

**nodemap.csv** - Connection list with:
- From/To callsigns
- Port numbers
- Quality scores
- Grid squares
- Node types

**nodemap_partial_[CALLSIGN].json/csv** - Created on Ctrl+C interrupt

### Captured Data

For each node:
- **Neighbors** - Nodes heard on RF ports
- **Location** - Grid square, lat/lon, city/state
- **Ports** - Numbers, frequencies, speeds, RF vs IP
- **Aliases** - SSID mappings (e.g., CCEBBS:WS1EC-2)
- **Applications** - BBS, Chat, RMS, etc. with SSIDs
- **Commands** - Available commands from `?` output
- **Type** - BPQ, FBB, or JNOS
- **Routes** - Path quality scores

### Timeout Protection

Adaptive timeouts for 1200 baud simplex RF:
- **Connection timeout:** 30s + 30s per hop (max 180s)
- **Command timeout:** 5s + 10s per hop (max 60s)
- **Operation timeout:** 5min + 2min per hop
- **Prompt wait:** 30s (allows multi-hop banner data)
- Prevents hangs on poor RF conditions or unresponsive nodes

### Crawl Modes

**Update mode** (default):
- Skips nodes already visited in current session
- Fastest for normal crawling
- Best for initial network discovery

**Reaudit mode** (`--mode reaudit`):
- Re-crawls all reachable nodes
- Updates/verifies existing data
- Use periodically to refresh network map

**New-only mode** (`--mode new-only`):
- Auto-loads nodemap.json
- Queues only unexplored neighbors
- Skips all known nodes
- Minimal RF bandwidth usage
- Perfect for 1200 baud simplex networks

### Requirements

- Python 3.5.3+
- Access to BPQ telnet port (default: 8010)
- `bpq32.cfg` readable by script

---

## nodemap-html.py - Interactive Map Generator

Converts nodemap.json data into an interactive HTML map with Leaflet.js visualization. Shows node locations, RF connections, and network topology on an OpenStreetMap base layer.

### Features

- **Interactive Map**: Pan, zoom, click nodes for details
- **RF Connection Lines**: Visual representation of network links
- **Node Markers**: Color-coded by type (BPQ, FBB, JNOS)
- **Info Popups**: Callsign, location, ports, frequencies, applications
- **Boundary Support**: Optional state/region boundaries overlay
- **Standalone HTML**: Single-file output, no server required
- **Mobile Friendly**: Responsive design works on phones/tablets

### Usage

```bash
./nodemap-html.py [OPTIONS]
```

**Options:**
- `--input FILE` or `-i FILE` - Input nodemap.json file (default: nodemap.json)
- `--output FILE` or `-o FILE` - Output HTML file (default: nodemap.html)
- `--boundaries FILE` or `-b FILE` - GeoJSON boundaries file (optional)
- `--title TEXT` - Map title (default: "Packet Radio Network Map")

**Examples:**
```bash
# Basic map generation
./nodemap-html.py

# Custom input/output files
./nodemap-html.py -i network_data.json -o map.html

# With state boundaries
./nodemap-html.py -b map_boundaries.py

# Custom title
./nodemap-html.py --title "Maine Packet Radio Network"
```

### Output

**nodemap.html** - Interactive map containing:
- OpenStreetMap base layer
- Node markers with callsigns
- RF connection lines between nodes
- Info popups with node details (click markers)
- Legend showing node types
- Optional state/region boundaries

**Viewing:**
- Open nodemap.html in any web browser
- No web server required (uses CDN for Leaflet.js)
- Works offline after initial load
- Share file via email, BBS, or web hosting

**Node Colors:**
- 🔵 Blue: BPQ nodes
- 🟢 Green: FBB nodes  
- 🟡 Yellow: JNOS nodes
- ⚫ Gray: Unknown type

**Connection Lines:**
- Solid lines: Active RF connections
- Thickness indicates connection quality (if available)

### Requirements

- Python 3.5.3+
- nodemap.json from nodemap.py
- Modern web browser for viewing output
