# BPQ Utilities

Sysop tools for network mapping, maintenance, and service installation.

## Table of Contents

- [Quick Start](#quick-start)
- [install-dxspider.sh - DX Spider Cluster Installer](#install-dxspidersh---dx-spider-cluster-installer)
- [nodemap.py - Network Topology Mapper](#nodemappy---network-topology-mapper)
- [nodemap-html.py - Interactive Map Generator](#nodemap-htmlpy---interactive-map-generator)

## Quick Start

```bash
# Create utilities directory (outside linbpq to avoid update conflicts)
mkdir -p ~/utilities
cd ~/utilities

# Download scripts
for f in nodemap.py nodemap-html.py map_boundaries.py; do 
  wget -O "$f" "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/$f"
done
chmod +x nodemap.py nodemap-html.py

# Basic crawl (5 hops from local node)
./nodemap.py 5

# Generate maps
./nodemap-html.py -a
```

**Full installation guide**: See [docs/INSTALLATION.md#utilities-installation](../docs/INSTALLATION.md#utilities-installation)

---

## install-dxspider.sh - DX Spider Cluster Installer

Automated DX Spider cluster installation script for LinBPQ nodes. Installs DX Spider as an isolated Perl service with dedicated `sysop` user, integrating with linbpq via telnet.

### Features

- Validates root/sudo before proceeding
- Installs Perl dependencies via apt (no CPAN)
- Creates isolated `sysop` user and `spider` group
- Configures upstream cluster connectivity for spot sharing
- Creates systemd service for auto-start
- Appends to /etc/services and /etc/inetd.conf automatically
- Outputs BPQ32 configuration snippet for manual merge

### Usage

```bash
sudo ./install-dxspider.sh
```

### Configuration

Edit variables at top of script before running:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLUSTER_CALL` | WS1EC-6 | Cluster callsign (choose available SSID) |
| `SYSOP_CALL` | KC1JMH | Primary sysop callsign |
| `SYSOP_NAME` | Brad | Sysop first name |
| `LOCATOR` | FN43SR | Maidenhead grid square |
| `QTH` | Windham, ME | Location description |
| `UPSTREAM_1` | dxc.nc7j.com | Primary upstream cluster |
| `UPSTREAM_2` | w3lpl.net | Backup upstream cluster |
| `SPIDER_PORT` | 7300 | DX Spider telnet port |

### Post-Installation

Add to `bpq32.cfg`:

```
; Update CMDPORT line (add 7300 at position 16)
CMDPORT 63000 63010 63020 63030 63040 63050 63060 63070 63080 63090 63100 63110 63120 63130 63140 63160 7300

; Add APPLICATION line
APPLICATION 20,DX,C 9 HOST 16 S,WS1EC-6,CCEDX,255

; Update INFOMSG Applications section to include:
; DX      DX Cluster (WS1EC-6)
```

Then restart linbpq:
```bash
sudo systemctl restart linbpq
```

### Common Spider Commands

| Command | Description |
|---------|-------------|
| `sh/dx` | Show recent DX spots |
| `sh/dx/20` | Show last 20 spots |
| `sh/dx on 20m` | Show 20m band spots |
| `sh/links` | Show upstream connections |
| `connect NODE` | Connect to upstream cluster |
| `set/filter` | Configure spot filters |
| `bye` | Disconnect |

### Service Management

```bash
sudo systemctl status dxspider    # Check status
sudo systemctl restart dxspider   # Restart service
journalctl -u dxspider -f         # View logs
su - sysop -c '/spider/perl/console.pl'  # Spider console
```

---

## nodemap.py - Network Topology Mapper

Crawls BPQ nodes via RF to discover network topology. Creates comprehensive maps by analyzing routing tables, MHEARD lists, and node information.

### Usage

```bash
./nodemap.py [MAX_HOPS] [START_NODE] [OPTIONS]
```

**Common Options:**
- `-h`, `--help`, `/?` - Show all options
- `-y`, `--yes` - Silent mode for cron (requires `-u` and `-p`)
- `-c`, `--callsign CALL-SSID` - Force specific node SSID
- `-q`, `--query CALL` - Query node info without crawling
- `-d`, `--display-nodes` - Show nodes table and exit
- `-x`, `--exclude [FILE|CALLS]` - Skip callsigns (file or comma-separated)
- `-v`, `--verbose` - Show detailed output
- `-l`, `--log [FILE]` - Log telnet traffic (default: telnet.log)

**Data Management:**
- `-o`, `--overwrite` - Replace data (default: merge mode)
- `-r`, `--resume [FILE]` - Continue from unexplored nodes
- `-m`, `--merge FILE` - Combine data from another nodemap.json
- `-M`, `--mode MODE` - Crawl mode: `update`, `reaudit`, `new-only`
- `-C`, `--cleanup [TARGET]` - Clean nodemap.json: `nodes`, `connections`, `all`

**Advanced:**
- `-H`, `--hf` - Include HF ports (VARA/ARDOP/PACTOR)
- `-I`, `--ip` - Include IP ports (AXIP/Telnet)
- `-g`, `--set-grid CALL GRID` - Set gridsquare for node
- `-N`, `--note CALL [TEXT]` - Add/update/remove note

### Common Tasks

**First-time crawl:**
```bash
./nodemap.py 5                    # 5 hops from local node
./nodemap-html.py -a              # Generate HTML + SVG maps
```

**Daily maintenance (cron):**
```bash
# Discover new nodes only (saves bandwidth)
./nodemap.py 10 -y -u USER -p PASS --mode new-only

# Full network refresh weekly
0 2 * * 0 cd ~/nodemap && ./nodemap.py 15 -y -u USER -p PASS --mode reaudit
```

**Fix bad SSID:**
```bash
./nodemap.py --callsign NG1P-4    # Corrects SSID, updates JSON
```

**Query node without crawling:**
```bash
./nodemap.py -q NG1P              # Show neighbors, apps, routes
```

**Multi-operator mapping:**
```bash
# Each operator crawls their region
./nodemap.py 15 > my_crawl.log

# Share nodemap.json files, then merge
./nodemap.py --merge north.json --merge south.json
./nodemap-html.py -a
```

**Clean up corrupted data:**
```bash
./nodemap.py --cleanup            # Remove bad entries
./nodemap.py -d -x                # Display with exclusions
```


### Output Files

- **nodemap.json** - Complete network data (nodes, connections, SSIDs, quality scores)
- **nodemap.csv** - Connection list (from, to, port, quality, gridsquares)
- **telnet.log** - Command/response traffic with timestamps (use `-l`)
- **debug.log** - Verbose crawl diagnostics (use `-D`)
- **exclusions.txt** - Optional blocklist for corrupted callsigns

Example exclusions.txt:
```
# Corrupted callsigns from packet loss
KX1nMA
KM1JMH

# Offline nodes
AB1KI, N1REX  # commas work too
```

### How It Works

**SSID Selection** (connects to node port, not BBS/RMS/CHAT):
1. CLI override (`--callsign CALL-SSID`) - user knows best
2. ROUTES consensus - aggregated from all nodes' routing tables
3. MHEARD data - fallback for new discoveries

SSIDs like `-2` (BBS), `-10` (RMS), `-4` (CHAT) vary by sysop. The script uses ROUTES tables from neighboring nodes to find the actual node SSID.

**Port Filtering:**
- Default: VHF/UHF packet only (skips HF and IP)
- Use `--hf` for VARA/ARDOP/PACTOR networks
- Use `--ip` for AXIP/Telnet connectivity

**Crawl Modes:**
- `update` (default) - Skip visited nodes this session
- `reaudit` - Re-crawl all nodes to refresh data
- `new-only` - Only discover unexplored neighbors (minimal bandwidth)

### Requirements

- Python 3.5.3+ (3.6+ recommended)
- Python 3.13+: `pip install telnetlib3`
- Access to BPQ telnet port (default: 8010)
- Readable `bpq32.cfg`

---


## nodemap-html.py - Interactive Map Generator

Converts nodemap.json to visual maps: interactive HTML with Leaflet.js and static SVG.

### Usage

```bash
./nodemap-html.py [OPTIONS]
```

**Options:**
- `-a`, `--all` - Generate both HTML and SVG (default)
- `-t`, `--html [FILE]` - Generate HTML map (default: nodemap.html)
- `-s`, `--svg [FILE]` - Generate SVG map (default: nodemap.svg)
- `-i`, `--input FILE` - Input file (default: nodemap.json)
- `-o`, `--output-dir DIR` - Save to directory
- `-h`, `--help`, `/?` - Show help

**Examples:**
```bash
./nodemap-html.py -a                           # Generate both formats
./nodemap-html.py -t network.html -s map.svg   # Custom names
./nodemap-html.py -a -o ~/linbpq/HTML/         # Save to BPQ web dir
```

### Features

**Interactive HTML:**
- OpenStreetMap base layer
- Clickable nodes with detailed popups
- Color-coded connections by frequency band:
  - Blue: 2m (144-148 MHz)
  - Orange: 70cm (420-450 MHz)
  - Purple: 1.25m (222-225 MHz)
  - Green: 6m (50-54 MHz)
  - Yellow (dashed): HF (VARA/ARDOP/PACTOR)
  - Cyan (dotted): IP (AXIP/Telnet)
  - Gray: Unknown
- Pan/zoom controls, legend

**Static SVG:**
- Fully offline (no external dependencies)
- State/county boundaries (if map_boundaries.py available)
- Hover tooltips
- Suitable for printing/embedding

### BPQ Web Server

Copy files to `~/linbpq/HTML/` and add links:
```html
<a href="nodemap.html">Network Map</a>
```

Or in bpq32.cfg:
```
FILE=/HTML/nodemap.html,nodemap.html
```


