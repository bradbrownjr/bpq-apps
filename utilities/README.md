# BPQ Utilities

Sysop tools for BBS management, network mapping, and maintenance tasks.

## Installation

### Recommended Layout

Scripts should be placed in `~/utilities/` or `~/apps/` adjacent to `~/linbpq/`:

```
/home/pi/               (or /home/ect/)
├── apps/               # User-facing BPQ applications
├── utilities/          # Sysop tools (nodemap.py, etc.)
├── linbpq/
│   └── bpq32.cfg       # Auto-detected by scripts
└── ...
```

The scripts auto-detect `bpq32.cfg` from:
1. `../linbpq/bpq32.cfg` (script in utilities/ or apps/, config in linbpq/)
2. `/home/pi/linbpq/bpq32.cfg`
3. `/home/ect/linbpq/bpq32.cfg`
4. Same directory as script
5. `linbpq/bpq32.cfg` (script in parent)

### Setup

```bash
# Create utilities directory
mkdir -p /home/pi/utilities
cd /home/pi/utilities

# Clone repo (or copy utilities/)
git clone https://github.com/bradbrownjr/bpq-apps.git
cd bpq-apps/utilities

# Make scripts executable
chmod +x *.py
```

## nodemap.py - Network Topology Mapper

Automatically crawls packet radio network via RF connections to discover nodes, ports, applications, and connectivity.

### Usage

```bash
./nodemap.py [MAX_HOPS] [START_NODE] [--overwrite]
```

**Parameters:**
- `MAX_HOPS` - Maximum hops to traverse (default: 10)
- `START_NODE` - Callsign to start from (default: local node from bpq32.cfg)
- `--overwrite` or `-o` - Overwrite existing data (default: merge mode)

### Data Storage

**Default mode (merge):**
- Loads existing `nodemap.json`
- Updates nodes with new data (overwrites if callsign exists)
- Preserves historical data from previous crawls
- Ideal for incremental network discovery and resuming after interruptions

**Overwrite mode (`--overwrite`):**
- Completely replaces `nodemap.json` and `nodemap.csv` each run
- Use for fresh network scans or when data needs reset

### Examples

```bash
# Crawl 5 hops from local node (merge with existing)
./nodemap.py 5

# Crawl 10 hops starting from WS1EC (merge mode)
./nodemap.py 10 WS1EC

# Crawl and completely replace existing data
./nodemap.py 5 --overwrite

# Resume from where connection was lost (merge mode)
./nodemap.py 10 KC1JMH
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

Commands scale timeouts based on hop count:
- **Command timeout:** 5s + 10s per hop (max 60s)
- **Operation timeout:** 5min + 2min per hop
- Prevents hangs on poor RF conditions or unresponsive nodes

### Requirements

- Python 3.5.3+
- Access to BPQ telnet port (default: 8010)
- `bpq32.cfg` readable by script
