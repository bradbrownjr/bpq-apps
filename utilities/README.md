# BPQ Utilities

Sysop tools for BBS management, network mapping, and maintenance tasks.

**Installation**: See [docs/INSTALLATION.md#utilities-installation](../docs/INSTALLATION.md#utilities-installation) for setup instructions and directory layout.

## nodemap.py - Network Topology Mapper

Advanced packet radio network discovery tool that crawls through BPQ nodes via RF connections to map topology, applications, and connectivity. Creates comprehensive network maps by analyzing routing tables, MHEARD lists, and node information.

### Quick Install

Download all nodemap scripts:
```bash
cd ~/utilities
wget https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/nodemap.py
wget https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/nodemap-html.py
wget https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/map_boundaries.py
chmod +x nodemap.py nodemap-html.py
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
2. **MHEARD data** (fallback) - What was heard on RF, may include apps/operators
3. **NODES aliases** (ignored for connections) - Often contain app SSIDs like BBS (-2), RMS (-10)

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
- `MAX_HOPS` - Maximum RF hops to traverse (default: 10)
- `START_NODE` - Callsign to start from (default: local node from bpq32.cfg)

**Options:**
- `--overwrite` or `-o` - Replace existing data (default: merge mode)
- `--resume` or `-r` - Continue from unexplored nodes in existing data
- `--mode MODE` - Crawl mode: `update` (default), `reaudit`, `new-only`
  - `update`: Skip already-visited nodes in current session (fastest)
  - `reaudit`: Re-crawl all nodes to verify/update data
  - `new-only`: Auto-load nodemap.json, queue only unexplored neighbors
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
