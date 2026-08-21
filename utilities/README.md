# BPQ Utilities

Sysop tools for network mapping, maintenance, and service installation.

## Table of Contents

- [Quick Start](#quick-start)
- [install-dxspider.sh - DX Spider Cluster Installer](#install-dxspidersh---dx-spider-cluster-installer)
- [nodemap.py - Network Topology Mapper](#nodemappy---network-topology-mapper)
  - [Data Quality](#data-quality)
- [nodemap-tui.py - Full-Screen Front End](#nodemap-tuipy---full-screen-front-end)
- [nodemap-html.py - Interactive Map Generator](#nodemap-htmlpy---interactive-map-generator)
- [mailroute.py - Mail Forwarding Route Analyzer](#mailroutepy---mail-forwarding-route-analyzer)

## Quick Start

```bash
# Create utilities directory (outside linbpq to avoid update conflicts)
mkdir -p ~/utilities
cd ~/utilities

# Download scripts
for f in nodemap.py nodemap-html.py nodemap-tui.py map_boundaries.py; do 
  wget -O "$f" "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/$f"
done
chmod +x nodemap.py nodemap-html.py nodemap-tui.py

# Basic crawl (5 hops from local node)
./nodemap.py 5

# Generate maps
./nodemap-html.py -a

# Or drive all of the above from a menu
./nodemap-tui.py
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

Crawls packet radio nodes via RF to discover network topology. Creates comprehensive maps by analyzing routing tables, MHEARD lists, and node information.

Supported node firmware:
- **BPQ32/LinBPQ** (G8BPQ) - Full support
- **Kantronics KPC-3 Plus** (X1J4 firmware) - MHEARD columnar format, ALIAS:CALL routes
- **FBB** (F6FBB) - Basic support
- **JNOS** - Basic support

### Usage

```bash
./nodemap.py [MAX_HOPS] [START_NODE] [OPTIONS]
```

**Common Options:**
- `-h`, `--help`, `/?` - Show all options
- `-y`, `--yes` - Silent mode for cron (requires `-u` and `-p`)
- `-c`, `--callsign CALL-SSID` - Force connection to specific SSID (single node)
- `--force-ssid BASE FULL` - Force SSID mapping (multiple, resolves ties)
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
- `-H`, `--hf[:audit|:crawl]` - HF ports (VARA/ARDOP/PACTOR); bare form audits
- `-I`, `--ip[:audit|:crawl]` - IP ports (AXIP/Telnet); bare form audits
- `-t`, `--timeout SECONDS` - Override per-node operation timeout (default: 360 + hop_count×240). Increase for nodes with huge ROUTES tables (e.g., `-t 1800` for 30 min)
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

**Resolve SSID conflicts (tied votes):**
```bash
# Single conflict: use --force-ssid
./nodemap.py 4 AB1KI-15 --force-ssid W1DTX W1DTX-7 --verbose

# Multiple conflicts: chain --force-ssid arguments
./nodemap.py 4 AB1KI-15 \
    --force-ssid W1DTX W1DTX-7 \
    --force-ssid N1LJK N1LJK-5 \
    --force-ssid WD1F WD1F-1 \
    --verbose

# Legacy: Force connection to single node
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
- **nodemap-overrides.json** - Sysop-entered data a crawl will never overwrite:
  gridsquares, the ignore list, and confirmed-real callsigns. Safe to edit by hand.
- **nodemap-geocache.json** - Cached location lookups, so repeat crawls make no
  HTTP requests and an offline node still resolves what it resolved before.
- **telnet.log** - Command/response traffic with timestamps (use `-l`)
- **debug.log** - Verbose crawl diagnostics (use `-D`)
- **exclusions.txt** - Optional blocklist, still honoured via `-x`

Corrupted callsigns no longer need to be listed by hand - see Data Quality below.

### Data Quality

**Corrupt callsign detection.** MHEARD is the only discovery source that arrives
as bare AX.25 UI frames, with no error correction, so a share of the "stations"
it reports are corrupted copies of real ones. ROUTES and the NODES table arrive
inside an acked NET/ROM session and have already survived a CRC, so they are
treated as corroboration while MHEARD is treated only as a lead.

A callsign is quarantined when it shows one of the known corruption signatures:

| Signature | Example | Why |
|---|---|---|
| `case_anomaly` | `KX1nMA` | AX.25 cannot carry a lowercase callsign |
| `unallocated_prefix` | `Q1QFY` | Q is reserved for Q signals, never issued |
| `bit_error:CALL` | `N1QYY` from `N1QFY` | Same length, one or two flipped characters |
| `truncated:CALL` | `N1Q` from `N1QFY` | Frame cut short mid-address |
| `bad_ssid` | `W1ABC-99` | AX.25 SSIDs are 4 bits, 0-15 |
| `reserved_word` | `NODES`, `BEACON` | A protocol word, not a station |

Length matters: the AX.25 address field is a fixed 7 bytes, so real corruption
substitutes characters rather than inserting or deleting them. Matching on
substitution distance instead of full edit distance is what keeps genuine
callsigns such as `W1ZE` and `N1EP` out of the quarantine.

**Proof of contact always wins.** A station the crawler has actually connected
to and read commands from can never be quarantined or deleted, and a stale
ignore entry for it is cleared automatically. WD1F is a real Maine BBS whose
callsign sits one character from WD1O, a real node; this is what keeps that
coincidence from erasing it.

A callsign-registry lookup was tried as a second net and deliberately removed.
It is the wrong tool: it rescued KC1JMF, a definite bad copy of KC1JMH that
happens to be an issued callsign, and the only free FCC source covers US
callsigns only - so it would bias toward keeping ghosts everywhere and do
nothing at all outside the US. Contact is the only authenticity check that
holds regardless of region.

Quarantined callsigns are removed from the map, added to the ignore list, and
skipped by every later crawl - each one avoided is minutes of 1200-baud air
time. Nothing is deleted: the reasoning is kept in `suspect_callsigns` in
nodemap.json, and any decision can be reversed.

```bash
./nodemap.py --list-ignored              # what is being skipped, and why
./nodemap.py --confirm-call W1ZE         # real station, crawl it again
./nodemap.py --ignore-call N8QFQ         # never crawl this again
./nodemap.py --no-auto-ignore            # flag corruption but keep retrying
```

**Node status.** Every node carries `first_seen`, `last_seen`, `last_crawled`,
`crawl_attempts`, `crawl_successes`, `consecutive_failures` and a `status`:

- `online` - reached this run, or heard on RF within 24 hours
- `recent` - seen within the last week, but no fresh evidence this run
- `stale` - nothing has confirmed it for over a week
- `offline` - three or more consecutive failed connections
- `unreachable` - not present in any ROUTES table

Links carry the same treatment: `first_seen`, `last_seen`, `observed_count`,
`stale`, and `asymmetric` (A hears B but B never hears A - a real property of
an RF path, and worth drawing differently).

**Location resolution.** Missing gridsquares are filled from the first source
that answers, most trustworthy first:

1. Sysop override in `nodemap-overrides.json`
2. A gridsquare stated in the node's INFO text
3. Lat/lon in INFO, converted to a locator
4. A place name in INFO - including hilltops such as "on Streaked Mtn" -
   geocoded via OpenStreetMap
5. Callsign lookup via Callook, then HamDB, then QRZ

QRZ credentials are read from the `qrz3.py` config (`apps/config.py`) if it is
installed; no credentials are stored in this script. Note that a callsign
lookup returns the *license address*, not the node site, which is why it sits
at the bottom of the ladder - WS1EC's licence is in Scarborough while the node
is on the air from Windham.

Every lookup is cached and every one is optional. `--no-lookup` keeps a crawl
entirely off the internet, and a failed uplink simply disables further lookups
rather than stalling the crawl - the emergency in which the map matters most is
the one where the internet is down.

**Gridsquares are remembered.** Anything entered by hand goes to
`nodemap-overrides.json` and outranks whatever a later crawl parses. Previously
a hand-entered grid survived only until the next crawl of that node re-exported
it as empty.

```bash
./nodemap.py --set-grid NG1P FN43vp      # persists across crawls
```

After a crawl, the script offers to look up every node still missing a grid,
then to take the rest by hand.

### How It Works

**SSID Selection Priority** (connects to node port, not BBS/RMS/CHAT):
1. CLI override (`--force-ssid BASE FULL` or `--callsign CALL-SSID`) - user knows best
2. ROUTES consensus - aggregated from all nodes' routing tables
3. MHEARD data - fallback for new discoveries

SSIDs like `-2` (BBS), `-10` (RMS), `-4` (CHAT) vary by sysop. When crawl encounters tied votes (e.g., W1DTX-4, W1DTX-7, W1DTX-15), use `--force-ssid W1DTX W1DTX-7` to break the tie and complete the crawl. The script uses ROUTES tables from neighboring nodes to find the actual node SSID.

**Port Filtering:**

VHF/UHF (RF) ports are always fully crawled. HF and IP ports are each a
tri-state, off by default:

- `--hf` or `--hf:audit` (and `-H`) - list what MHEARD reports on VARA/ARDOP/
  PACTOR ports without ever connecting to it. Good for awareness and mapping
  ("what's reachable over HF from here") at no air-time cost beyond one MHEARD
  query per port.
- `--hf:crawl` - also connect and fully crawl over HF. Slow at 300 baud; only
  worth it if you actually want HF nodes' own INFO/ROUTES/neighbours.
- `--ip` / `--ip:audit` / `--ip:crawl` (and `-I`) - the same three states for
  AXIP/Telnet ports.
- Omit the flag entirely to skip that port type completely, as before.

Audited stations are recorded under each node's `port_audit` field - the port,
its description, and who was heard there - kept separate from `neighbors` and
`connections` since we never actually spoke to them: no INFO, no ROUTES, no
confirmation the callsign is even a node rather than a user station. A station
only becomes part of the mapped topology once something actually connects to
it, either over RF or via `:crawl`.

**Crawl Modes:**
- `update` (default) - Skip nodes nodemap.json already has good data for,
  but still grow the map using their previously recorded unexplored neighbours
  (so it works even if the local node can't currently reach them live). The
  node you crawl from is always re-crawled fresh, regardless of mode.
- `reaudit` - Re-crawl every reachable node from scratch, verifying it is
  actually still there. Slower; needs a live connection to discover anything,
  since it does not use recorded stubs.
- `new-only` - Load nodemap.json and queue only its unexplored neighbours,
  with no live walk from the start node at all. The fastest option when you
  just want to fill in gaps.

### Requirements

- Python 3.5.3+ (3.6+ recommended)
- Python 3.13+: `pip install telnetlib3` to crawl. Everything that does not
  open a connection (`--set-grid`, `--list-ignored`, `--display`) works without it.
- Internet access is optional; used only for location lookups
- Access to BPQ telnet port (default: 8010)
- Readable `bpq32.cfg`

---


## nodemap-tui.py - Full-Screen Front End

A menu-driven front end for `nodemap.py`, for when the option list is more than
you want to assemble by hand. Built on stdlib `curses` - nothing to install, and
it runs on the Python 3.5 that ships with older Raspbian.

```bash
wget -O nodemap-tui.py \
  https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/nodemap-tui.py
chmod +x nodemap-tui.py
./nodemap-tui.py
```

### Screens

- **Crawl** - every crawl option as a labelled field, with a one-line
  explanation of whichever is highlighted and a live preview of the command it
  builds. Press `r` to run it. The preview is generated from the same objects
  the form edits, so it cannot drift, and it doubles as a way to learn the CLI.
- **Nodes and status** - every node sorted worst-status first, with gridsquare,
  days since last seen and neighbour count. Enter queries one node.
- **Gridsquares** - which nodes have a locator and where it came from, with
  the missing ones flagged. Enter sets one by hand.
- **Ignored callsigns** - the quarantine list with the reason for each. Enter
  restores a callsign that is really a station.

### Keys

`up`/`down` or `j`/`k` move, `enter` selects or edits, `space` toggles,
`left`/`right` cycle a choice, `q` or `Escape` goes back, `g` regenerates the
HTML and SVG maps.

Needs `nodemap.py` in the same directory, and a terminal of at least 60x16.
It is a front end only - every action shells out to `nodemap.py`, so anything
done here can still be done from the shell, and nothing depends on the TUI
being installed.

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
- Node marker colors:
  - Red: VHF/UHF node
  - Gray: HF gateway (has VARA/ARDOP/PACTOR port)
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

## mailroute.py - Mail Forwarding Route Analyzer

Reads network topology from `nodemap.json` and generates BBS mail forwarding configuration recommendations. Helps sysops set up inter-BBS message routing with connect scripts, hierarchical addresses, bulletin distribution, and NTS traffic routing.

### Features

- Auto-detects all BBS nodes from crawled NetRom alias data
- Extracts hierarchical addresses from node info text
- Computes shortest RF paths via BFS on the topology graph
- **Bulletin distribution tree**: BFS spanning tree showing which BBSes forward bulletins to which neighbors, preventing duplicate flood traffic over 1200 baud
- **Forwarding roles**: Classifies each BBS as BULLETIN + PERSONAL (direct neighbor, full forwarding) or PERSONAL ONLY (remote, personal mail via multi-hop scripts)
- **HRoutes/HRoutesP recommendations**: Hierarchical routes for flood bulletins and personal/directed mail per partner
- **HF gateway detection**: Identifies BBSes with VARA/ARDOP/PACTOR ports for wider network access
- **NTS traffic routing guide**: Addressing conventions, FWDAliases, traffic flow, and radiogram format
- Generates connect scripts with BBS NetRom alias (primary) and explicit hop-by-hop ELSE fallbacks
- Outputs BPQ32 web UI field values (TO, AT, HRoutes, HRoutesP, Connect Script, BBS HA, settings)
- Optional linmail.cfg-compatible snippets (`-c` flag)

### Usage

```bash
# Full analysis from auto-detected home node
./mailroute.py

# From a specific home node
./mailroute.py -n WS1EC

# Show routing for one BBS only
./mailroute.py -t KC1JMH

# Bulletin strategy and NTS guide only
./mailroute.py -b

# Generate linmail.cfg snippets
./mailroute.py -c > forwarding.cfg

# Network summary only
./mailroute.py -s

# Use specific JSON file
./mailroute.py -j /path/to/nodemap.json
```

### Options

| Flag | Description |
|------|-------------|
| `-j, --json FILE` | Path to nodemap.json (default: nodemap.json) |
| `-n, --node CALL` | Home node callsign (default: auto-detect) |
| `-t, --target CALL` | Show routing for specific BBS only |
| `-c, --config` | Output linmail.cfg format snippets |
| `-s, --summary` | Show network summary only |
| `-b, --bulletin` | Show bulletin strategy and NTS guide only |
| `-h, --help, /?` | Show help |

### Output

For each reachable BBS in the network:
- BBS identity (callsign, alias, hierarchical address, location)
- Forwarding role: BULLETIN + PERSONAL or PERSONAL ONLY
- Shortest RF path from home node with alternate routes
- HRoutes (flood bulletins) and HRoutesP (personal/directed) recommendations
- Connect script: primary via BBS NetRom alias + ELSE explicit hops
- Recommended forwarding settings (B1 protocol, intervals, etc.)

Network-wide sections:
- Bulletin distribution tree showing relay topology
- NTS addressing conventions and FWDAliases
- HF gateway identification for interstate traffic

### Prerequisites

Requires `nodemap.json` generated by `nodemap.py`. Run a crawl first:
```bash
./nodemap.py 5
./mailroute.py
```

