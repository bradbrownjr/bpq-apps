# BPQ Utilities

Sysop tools for network mapping and maintenance.

## Table of Contents

- [Quick Start](#quick-start)
- [nodemap.py - Network Topology Mapper](#nodemappy---network-topology-mapper)
- [nodemap-html.py - Interactive Map Generator](#nodemap-htmlpy---interactive-map-generator)
- [wx-alert-update.sh - Weather Alert Beacon Text Generator](#wx-alert-updatesh---weather-alert-beacon-text-generator)
- [wx-beacon-daemon.py - BPQ Beacon Transmitter](#wx-beacon-daemonpy---bpq-beacon-transmitter)

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

---

## wx-alert-update.sh - Weather Alert Beacon Text Generator

Updates weather beacon text file for BPQ node. Includes alert count and SKYWARN spotter activation status. Run via cron to keep beacon current.

### Usage

```bash
./wx-alert-update.sh [output_file] [gridsquare]
```

**Arguments:**
- `output_file` - Path to output file (default: `~/linbpq/beacontext.txt`)
- `gridsquare` - Location to check (default: from bpq32.cfg LOCATOR)

**Examples:**
```bash
# Use defaults (local gridsquare, ~/linbpq/beacontext.txt)
./wx-alert-update.sh

# Custom location
./wx-alert-update.sh /home/ect/linbpq/beacontext.txt FN43hp

# Run in cron (every 15 minutes) - ALREADY INSTALLED
*/15 * * * * /home/ect/utilities/wx-alert-update.sh >/dev/null 2>&1
```

### Setup

**Cron job is already installed on WS1EC node.** To verify or modify:

```bash
crontab -l | grep wx-alert
```

### Output Format

Compact beacon message with alert count and SKYWARN status:
```
WS1EC-15: No active weather alerts. Connect to WX app for details.
WS1EC-15: 1 WEATHER ALERT! Connect to WX app for details.
WS1EC-15: 3 WEATHER ALERTS! SKYWARN SPOTTERS ACTIVATED. Connect to WX app for details.
```

**Features:**
- Uppercase "ALERT(S)" for severe/extreme alerts
- Lowercase "alert(s)" for moderate/minor
- **SKYWARN Detection**: Checks Hazardous Weather Outlook for spotter activation
  - Searches for "Weather spotters are encouraged to report" phrase
  - Based on code from [skywarn-activation-alerts](https://github.com/bradbrownjr/skywarn-activation-alerts)
- Directs users to WX app for full details

### How It Works

1. Calls `wx.py --beacon [GRIDSQUARE]`
2. wx.py fetches NWS alerts for location via API
3. wx.py checks HWO text file for SKYWARN activation phrase
4. Outputs compact beacon message
5. Script writes to file atomically (temp file + mv)
6. **wx-beacon-daemon.py reads file and transmits via BPQ**

### Requirements

- `wx.py` version 4.2 or later
- Internet connectivity (for NWS API and HWO text access)
- Writable `~/linbpq/` directory
- cron daemon running

---

## wx-beacon-daemon.py - BPQ Beacon Transmitter

Daemon that sends weather alert beacons via BPQ HOST interface. Reads beacon text from file and transmits as UI frames on VHF port.

**Why this approach?** BPQ32 has no native file inclusion mechanism for beacons. Instead of modifying bpq32.cfg (which requires restarting BPQ and disconnects active users), this daemon runs independently and sends beacons programmatically.

### Usage

```bash
./wx-beacon-daemon.py [OPTIONS]
```

**Options:**
- `-p`, `--port PORT` - BPQ HOST port (default: 8010)
- `--host ADDR` - BPQ HOST address (default: 127.0.0.1)
- `-i`, `--interval MINS` - Beacon interval in minutes (default: 15)
- `-c`, `--callsign CALL` - Beacon callsign (default: WS1EC-15)
- `-r`, `--radio-port NUM` - BPQ radio port number (default: 2)
- `-f`, `--file PATH` - Beacon text file (default: ~/linbpq/beacontext.txt)
- `-d`, `--daemon` - Run as daemon (background)
- `-v`, `--verbose` - Verbose logging
- `-h`, `--help` - Show help

**Examples:**
```bash
# Test in foreground with verbose output
./wx-beacon-daemon.py -v

# Run as background daemon
./wx-beacon-daemon.py -d

# Custom interval and callsign
./wx-beacon-daemon.py -i 30 -c WS1EC-4 -v

# Different BPQ HOST port
./wx-beacon-daemon.py -p 8011 -v
```

### Setup as systemd Service

**Install service:**
```bash
sudo cp docs/examples/etc/wx-beacon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wx-beacon
sudo systemctl start wx-beacon
```

**Check status:**
```bash
sudo systemctl status wx-beacon
```

**View logs:**
```bash
journalctl -u wx-beacon -f
```

**Restart service:**
```bash
sudo systemctl restart wx-beacon
```

### How It Works

1. Reads beacon text from `~/linbpq/beacontext.txt` every 15 minutes
2. Connects to BPQ HOST port (8010)
3. Authenticates with node callsign
4. Sends UI frame command: `U <port> BEACON <text>`
5. Multi-line beacons sent as separate UI frames (1-second spacing)
6. Repeats on schedule

### BPQ HOST Protocol

The daemon uses BPQ's HOST interface to send unproto/UI frames:
```
1. Connect to HOST port (8010)
2. Send: "WS1EC-15\r"           (authenticate)
3. Send: "U 2 BEACON <text>\r"  (send UI frame on port 2)
```

**UI Frame Format:**
- `U` - Unproto/UI frame command
- `2` - Port number (VHF port 2 = 145.050 MHz)
- `BEACON` - Destination address
- `<text>` - Beacon message

### Integration with wx-alert-update.sh

**Complete weather beacon system:**
1. `wx-alert-update.sh` runs every 15 minutes via cron
2. Updates `~/linbpq/beacontext.txt` with current alerts
3. `wx-beacon-daemon.py` reads file and transmits via BPQ
4. No BPQ restart needed - zero user disruption

### Requirements

- BPQ32/LinBPQ running with HOST port enabled (Port 9 in bpq32.cfg)
- Python 3.5.3+ (no external dependencies - stdlib only)
- Read access to beacon text file
- Network access to BPQ HOST port (localhost:8010)

### Troubleshooting

**Beacon not transmitting:**
- Check BPQ is running: `sudo systemctl status linbpq`
- Verify HOST port: `grep TCPPORT ~/linbpq/bpq32.cfg` (should be 8010)
- Test beacon file exists: `cat ~/linbpq/beacontext.txt`
- Check daemon logs: `journalctl -u wx-beacon -n 50`

**Permission denied:**
- Ensure user `ect` owns beacon file
- Check file permissions: `ls -la ~/linbpq/beacontext.txt`

**Beacons too frequent/infrequent:**
- Adjust interval: edit `/etc/systemd/system/wx-beacon.service`
- Change `ExecStart` line to include `-i <minutes>`
- Reload: `sudo systemctl daemon-reload && sudo systemctl restart wx-beacon`

