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

**SSID Selection Standard** (Critical - determines which SSID to connect to):
1. **CLI-forced SSIDs** (`--callsign CALL-SSID`) - highest priority, user override
2. **ROUTES consensus** - aggregate SSIDs from ALL nodes' ROUTES tables (most authoritative)
3. **own_aliases primary** - node's own alias matching ROUTES-consensus SSID
4. **own_aliases fallback** - scan own_aliases for base_call match with valid SSID (1-15)
5. **MHEARD data** - lowest priority, includes transient/port-specific SSIDs

**Important**: Never assume SSID by number convention (BBS=-2, RMS=-10, CHAT=-4, etc.) - these vary by sysop. The ROUTES tables from neighboring nodes are the authoritative source.

**SSID Tracking:**
- Tracks source of each SSID: ROUTES (authoritative), MHEARD (RF observed), or CLI (user-forced)
- ROUTES always wins, aggregated across all nodes for consensus
- Prevents incorrect connections to BBS/RMS/CHAT SSIDs instead of node SSIDs
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
- Focuses on RF connectivity for true packet radio topology
- **Default**: Skips HF ports (VARA/ARDOP/PACTOR, 300 baud too slow) and IP ports (Telnet/AXIP, not RF)
- Use `--hf` to include HF digital modes (for predominantly HF networks)
- Use `--ip` to include Internet-based connections (AXIP reflectors, Telnet routing)
- Maps real over-the-air VHF/UHF packet radio network structure by default

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
- `--exclude CALLS` or `-x CALLS` - Exclude callsigns from crawling
  - Accepts comma-separated list: `--exclude AB1KI,N1REX,K1NYY`
  - Accepts filename: `--exclude blocklist.txt`
  - Use `-x` alone to load default `exclusions.txt`
  - File format: one callsign per line or comma-separated, # for comments
  - Useful for filtering corrupted callsigns from AX.25 routing table pollution
- `--hf` - Include HF ports in crawling
  - Default: Skip HF ports (VARA, ARDOP, PACTOR, 300 baud) - too slow for efficient crawling
  - HF ports detected by: Keywords (VARA, ARDOP, PACTOR, WINMOR), frequency <30 MHz, or speed ≤300 baud
  - Enable for networks with primarily HF connectivity or when specifically exploring HF links
  - Example: `./nodemap.py 5 --hf` (crawl including HF ports)
- `--ip` - Include IP/Internet ports in crawling
  - Default: Skip IP ports (AXIP, TCP, Telnet) - not RF, may be transient Internet links
  - IP ports detected by: Keywords (TELNET, TCP, IP, UDP, AX/IP, AXIP, AXUDP)
  - Enable to map Internet-based connectivity (AXIP reflectors, Telnet connections)
  - Example: `./nodemap.py 5 --ip` (crawl including IP ports)
- `--merge FILE` - Combine data from another operator's nodemap.json
- `--verbose` or `-v` - Show detailed command/response output
- `--notify URL` - Send progress notifications to webhook
- `--log FILE` or `-l FILE` - Log all telnet traffic for debugging (default: telnet.log)
- `--debug-log FILE` or `-D FILE` - Log verbose debug output (implies -v, default: debug.log)
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
./nodemap.py 5 -x blocklist.txt          # Load exclusions from file
./nodemap.py 5 -x                        # Use default exclusions.txt
./nodemap.py 10 --mode new-only -x       # Combine with other options

# Port type filtering (advanced)
./nodemap.py 5 --hf                      # Include HF ports (VARA, ARDOP, PACTOR, etc.)
./nodemap.py 5 --ip                      # Include IP ports (AXIP, Telnet reflectors)
./nodemap.py 5 --hf --ip                 # Include both HF and IP ports (maximum coverage)

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
- Connections between nodes with frequency/port data
- SSID mappings and routing quality scores
- Metadata (timestamp, mode, total counts)

**nodemap.csv** - Connection list with:
- From/To callsigns
- Port numbers
- Quality scores
- Grid squares
- Node types

**nodemap_partial_[CALLSIGN].json/csv** - Created on Ctrl+C interrupt

**exclusions.txt** - Optional blocklist file for `-x` option:
```
# Corrupted callsigns from AX.25 routing pollution
KX1nMA
KM1JMH
KX1KMA

# Can also use commas
W1ZE, VE1YAR

# Offline or problematic nodes
AB1KI  # inline comments work too
```

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

Converts nodemap.json data into visual maps: interactive HTML with Leaflet.js and static SVG. Shows node locations, RF connections by frequency band, and network topology.

### Features

- **Dual Output Formats**: Interactive HTML map AND static SVG
- **Multi-Band Connection Lines**: Separate colored lines for each frequency band
  - 🔵 Blue: 2m (144-148 MHz) - solid
  - 🟠 Orange: 70cm (420-450 MHz) - solid
  - 🟣 Purple: 1.25m/220 MHz (222-225 MHz) - solid
  - 🟢 Green: 6m (50-54 MHz) - solid
  - ⚫ Gray: Unknown/Other - solid
  - 🟨 Yellow: HF ports (VARA, ARDOP, PACTOR) - dashed
  - 🔵 Cyan: IP ports (AXIP, TCP, Telnet) - dotted
- **Link Type Indicators**: Visual distinction between RF, HF digital modes, and Internet connectivity
- **RF Connection Detection**: Uses MHEARD port data to determine actual frequencies
- **Node Markers**: Color-coded by primary operating frequency
- **Info Popups**: Callsign, location, ports, frequencies, applications, neighbors
- **SVG Labels**: Positioned below nodes to prevent overlap blocking
- **Boundary Support**: Optional state/county boundaries overlay (requires map_boundaries.py)
- **Standalone HTML**: Single-file output, works offline after initial load
- **Mobile Friendly**: Responsive design works on phones/tablets

### Usage

```bash
./nodemap-html.py [OPTIONS]
```

**Options:**
- `--html FILE` - Generate interactive HTML map (default: nodemap.html)
- `--svg FILE` - Generate static SVG map (default: nodemap.svg)
- `--input FILE` - Input JSON file (default: nodemap.json)
- `--output-dir DIR` - Save files to directory (prompts for BPQ HTML dir)
- `--all` - Generate both HTML and SVG formats
- `--help, -h, /?` - Show help message

**Examples:**
```bash
# Generate both formats (recommended)
./nodemap-html.py --all

# Generate only HTML
./nodemap-html.py --html

# Generate only SVG
./nodemap-html.py --svg

# Custom filenames
./nodemap-html.py --html network.html --svg network.svg

# From different input file
./nodemap-html.py --all --input other_network.json

# Save directly to BPQ web directory
./nodemap-html.py --all --output-dir ~/linbpq/HTML/
```

### Output

**nodemap.html** - Interactive Leaflet map:
- OpenStreetMap base layer (requires internet for tiles)
- Clickable node markers with detailed popups
- Multi-band connection lines (separate line per frequency)
- Hover tooltips on connections showing frequency
- Pan/zoom controls
- Legend showing band colors

**nodemap.svg** - Static vector map:
- Fully offline - no external dependencies
- State/county boundaries (if map_boundaries.py available)
- Hover tooltips on nodes
- Labels positioned below nodes (prevents overlap blocking)
- Can be embedded in HTML pages or documents
- Suitable for printing

### BPQ Web Server Integration

1. **Copy files to BPQ HTML directory:**
   ```bash
   cp nodemap.html nodemap.svg ~/linbpq/HTML/
   ```

2. **Add link in your BPQ web interface index.html:**
   ```html
   <a href="nodemap.html">Network Map (Interactive)</a>
   <a href="nodemap.svg">Network Map (Static)</a>
   ```

3. **Or add custom page in bpq32.cfg (HTML section):**
   ```
   FILE=/HTML/nodemap.html,nodemap.html
   ```

### Requirements

- Python 3.5.3+
- nodemap.json from nodemap.py
- Modern web browser for viewing HTML output
- Optional: map_boundaries.py for state/county boundaries in SVG
