# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [nodemap 1.3.74] - 2026-01-13
### Fixed
- Increased timeouts for 1200 baud simplex RF: 30s base + 30s per hop (was 20s+20s)
- Simplex RF requires packet acknowledgment before next transmission (slower)
- Prompt wait timeout increased from 10s to 30s for multi-hop connections
- Post-connection delay increased to 1.5s to allow banner data arrival
- Added verbose timeout messages showing elapsed time vs expected timeout
- Better error messages when prompt read times out or fails

## [nodemap 1.3.73] - 2026-01-13
### Fixed
- Improved error message when target is user station (no SSID)
- Now suggests other unexplored nodes that ARE actually nodes
- Helps user pick valid crawl targets instead of user stations

## [nodemap 1.3.72] - 2026-01-13
### Fixed
- Auto-resolve base callsign to node SSID when available in network data
- User can now specify "wd1f" and script will find "WD1F-15" if known
- Matches behavior of unexplored neighbor list (shows base callsigns)

## [nodemap 1.3.71] - 2026-01-13
### Fixed
- Detect user stations (callsigns without SSID) and abort crawl with helpful error
- WD1F has no SSID in network data (sysop callsign, not node callsign)
- Prevents attempting to crawl non-node stations that can't respond to BPQ commands

## [nodemap 1.3.70] - 2026-01-13
### Fixed
- Use node SSID from own_aliases instead of netrom_ssids when loading existing data
- Prevents connecting to service SSIDs (e.g., KC1JMH-8) instead of node SSID (KC1JMH-15)
- Node's own_aliases contains authoritative SSID, netrom_ssids may have stale observations

## [nodemap 1.3.69] - 2026-01-13
### Fixed
- Path-finding now uses BFS to build multi-hop routes through network topology
- Previous logic only found single-hop paths, causing direct connection attempts to unreachable nodes
- Now properly routes through intermediate nodes (e.g., WS1EC → KC1JMH → KS1R → WD1F)
- Uses neighbor data from nodemap.json to calculate reachable paths

## [nodemap 1.3.68] - 2026-01-13
### Fixed
- Actually enforce timeout by checking elapsed time in socket.timeout exception handler
- Previous fix calculated timeout correctly but didn't break out of loop when socket kept timing out
- Now explicitly checks if total timeout exceeded when read_some() times out

## [nodemap 1.3.67] - 2026-01-13
### Fixed
- Skip NRR route verification for direct neighbors with known port numbers
- NRR only works for NetRom routing table entries, not direct RF connections
- Shows "Using direct port connection" message instead of misleading NRR warning

## [nodemap 1.3.66] - 2026-01-13
### Fixed
- Connection timeout now properly enforced - was using 2s socket timeout in loop but not checking total elapsed time correctly
- NetRom fallback path was resetting timer instead of using original start time, allowing connections to run indefinitely
- Timeout now calculated based on actual hop count: base 20s + 20s per remaining hop (max 120s)
- Verbose output shows expected timeout with hop count: "timeout: 40s for 2 hops"

### Added
- NetRom route verification using NRR command before attempting connections
- Prevents long waits for non-existent routes - warns if NRR reports "Not found"
- Shows actual route path and hop count from NRR response when available
- Helper method `_calculate_connection_timeout()` to standardize timeout calculations
- Helper method `_verify_netrom_route()` to check routes using NRR command

## [nodemap 1.3.65] - 2026-01-12
### Added
- Now extracts alias and gridsquare to top-level fields in node data
- Makes data more accessible without digging into nested dicts
- Display mode uses top-level fields with fallbacks to nested data

## [nodemap 1.3.64] - 2026-01-12
### Fixed
- Display mode now correctly extracts alias from own_aliases and gridsquare from location dict
- Was looking in wrong fields - alias is in own_aliases{}, gridsquare is in location{'grid'}

## [nodemap 1.3.63] - 2026-01-12
### Improved
- Display mode now shows unexplored neighbors column
- Pulls alias and gridsquare from netrom_nodes if missing from node data
- Lists all unexplored neighbors at bottom for easy target selection

## [nodemap 1.3.62] - 2026-01-12
### Added
- Display-only mode: `--display-nodes` / `-d` shows nodes table from nodemap.json
- Quick way to review discovered nodes without re-crawling

## [nodemap 1.3.61] - 2026-01-12
### Added
- NetRom alias fallback when direct port connection times out
- Automatically retries with C ALIAS if C PORT SSID fails to connect

## [nodemap 1.3.60] - 2026-01-22
### Fixed
- SSID priority: Node's own SSID now takes precedence over what neighbors heard on MHEARD
- Process nodes sorted by hop_distance to load authoritative data first
- Prevents using operator SSIDs (e.g., KC1JMH-8) instead of node SSIDs (KC1JMH-15)

## [nodemap 1.3.59] - 2026-01-22
### Added
- On-demand NetRom alias discovery when no existing data available
- NODES command executed from local node to find routing aliases
- Better error handling when BPQ rejects commands without port numbers

### Fixed
- "C COMMAND REQUIRES A PORT NUMBER" error by using NetRom aliases instead

## [nodemap 1.3.58] - 2026-01-22
### Added
- NetRom alias fallback for remote node connections
- Diagnostic output showing path finding process
- Restoration of call_to_alias mappings from nodemap.json

### Fixed
- Better handling when target node not found in neighbor lists

## [nodemap 1.3.57] - 2026-01-22
### Fixed
- Hop limit no longer prevents reaching remote start node
- max_hops now means "explore FROM start node to this depth", not "can only reach at this depth"
- Remote start nodes can be reached regardless of hop distance, hop limit applies only to neighbors discovered from start node

## [nodemap 1.3.56] - 2026-01-22
### Fixed
- Remote node start mode now finds proper path through existing network
- When starting from non-local node (e.g., `nodemap.py 1 N1REX`), searches existing nodemap.json for nodes that can reach the target
- Connects through intermediate hops instead of trying direct connection from local node

## [nodemap 1.3.55] - 2026-01-22
### Fixed
- Callsign-SSID normalization in port/alias lookups
- Extract base callsign (split on '-') before checking route_ports and call_to_alias maps
- Remote node crawls now properly use direct port connections instead of fallback mode

## [nodemap 1.3.54] - 2026-01-22
### Added
- Pre-load route info from existing nodemap.json when starting remote crawl
- Loads netrom_ssid_map and route_ports for remote node startup (no delays waiting for PORTS/NODES)

## [nodemap-html 1.1.0] - 2026-01-15
### Added
- State and county boundaries for offline SVG maps (New England region)
- New map_boundaries.py with simplified boundary coordinates
- SVG clipPath to constrain boundary rendering to visible area
- Maine county boundaries shown when zoomed in (lat range < 5 degrees)
- Hover tooltips on state and county boundaries

### Changed
- Increased SVG padding from 10% to 30% for better geographic context
- Updated output description: SVG now includes state/county boundaries

## [nodemap-html 1.0.0] - 2026-01-15
### Added
- New utility: nodemap-html.py for map visualization
- Interactive HTML map using Leaflet.js and OpenStreetMap tiles
- Static SVG map for fully offline viewing
- Band-based color coding (2m blue, 1.25m purple, 70cm orange, etc.)
- Grid square to lat/lon conversion (Maidenhead locator system)
- Connection lines between neighboring nodes
- Legend showing frequency bands and node count

## [1.3.54] - 2026-01-12
### Fixed
- Pre-load route information when starting crawl from remote node (not local)
- Now correctly retrieves port numbers and SSIDs from existing nodemap.json
- Fixes "C N1REX-15 (fallback)" error when starting with: nodemap.py 1 N1REX
- Remote node crawls now use direct connection: "C 1 N1REX-15" (with port) instead of fallback

## [1.3.53] - 2026-01-12
### Fixed
- Fixed hop count off-by-one error: nodes at max_hops+1 were incorrectly included
- Corrected hop distance calculation: now properly counts target node (len(path) + 1)
- With max_hops=2, now correctly stops at 2 hops instead of crawling to 3

## [1.3.52] - 2026-01-12
### Fixed
- Fixed infinite hang when tn.write() blocks on dead TCP connections during multi-hop
- Added 10s socket timeout before write operations to detect unresponsive remote nodes
- Fixes 23+ minute hangs when intermediate node (e.g. KS1R) stops responding before command sent

## [1.3.51] - 2026-01-12
### Fixed
- Fixed infinite hang during multi-hop connections when RF link goes silent
- Added socket timeout (2s) to read_some() loop to ensure conn_timeout is respected
- Prevents scenarios where script hangs indefinitely waiting for connection response

## [1.3.50] - 2026-01-15
### Added
- Frequency tracking for network mapping and mesh interconnection planning
- Enhanced CSV export with From_Frequencies, To_Frequencies, From_Ports columns
- Frequency extraction from PORTS command output (parses MHz values)
- Port-level frequency data in JSON output (nodes.ports[].frequency)

## [1.3.41] - 2026-01-12
### Fixed
- Reduced excessive operation timeout from 5min+2min/hop to 2min+1min/hop (max 12min vs 25min)
- Reduced connection timeout from 30s+30s/hop to 20s+20s/hop (max 2min vs 3min)
- Added staleness filter: skip nodes not heard in >24 hours (prevents long waits on offline nodes)
- Fixed W1LH-6 type scenarios where nodes with very old MHEARD timestamps cause extended hangs

### Changed
- Verbose output now shows when nodes are skipped due to staleness (e.g., "Skipping W1LH (stale: 2d 3h ago)")

## [1.3.40] - 2026-01-12
### Added
- Safety check to prevent merging output file (nodemap.json) into itself
- Automatic filtering of output file from wildcard patterns (*.json)
- Warning messages when output file merge attempts are blocked

### Changed
- Wildcard merge now shows count of excluded files for transparency

## [1.3.39] - 2026-01-12
### Added
- Support for -m as shorthand alias for --merge option
- Wildcard pattern support for merge files (e.g., -m *.json, --merge node*.json)
- Automatic expansion of glob patterns with informative matching output

## [1.3.38] - 2026-01-12
### Added
- Multi-perspective network mapping with --merge functionality
- Merge external nodemap.json files from other operators' viewpoints
- Intelligent node data merging (combines neighbors, preserves most detailed info)
- Merge-only mode for combining data without crawling
- Enhanced help documentation with multi-node mapping workflow

## [1.3.37] - 2026-01-12
### Changed
- Simplified SSID selection verbose messaging:
  - Removed unnecessary "may be app/operator SSID" text
  - Added explicit detection of quality 0 routes in MHEARD stations
  - Now shows "Skipping X (quality 0 in ROUTES - sysop blocked route)" for blocked stations
  - Cleaner "not in ROUTES table" message for truly unknown stations

## [1.3.36] - 2026-01-12
### Changed
- Improved verbose output clarity for SSID selection:
  - Added logging when quality 0 routes are ignored ("sysop blocked route")
  - Clarified "not in ROUTES table" vs quality-based filtering
  - Enhanced distinction between authoritative vs fallback SSID sources

## [1.3.35] - 2026-01-12

### Fixed
- nodemap.py: ROUTES parsing now includes non-direct neighbors with quality > 0
- nodemap.py: Nodes with quality 0 in ROUTES are skipped (sysop-blocked poor paths)
- nodemap.py: Removed overly strict 'Routes' content validation that caused parsing failures

### Changed  
- nodemap.py: All ROUTES entries with quality > 0 now provide authoritative node SSIDs
- nodemap.py: MHEARD nodes found in any ROUTES entry (not just direct >) are marked as authoritative

## [1.3.34] - 2025-06-25

### Fixed
- nodemap.py: SSID selection now uses ROUTES as authoritative source (not NODES aliases)
- nodemap.py: NODES aliases contain APP SSIDs (BBS -2, RMS -10, CHAT -13), not node SSIDs
- nodemap.py: ROUTES direct neighbor entries (> lines) show actual node SSIDs (e.g., K1NYY-15)

### Changed
- nodemap.py: _parse_routes now returns SSIDs dict in addition to routes and ports
- nodemap.py: Removed NODES alias pre-population of netrom_ssid_map (was using app SSIDs)
- nodemap.py: MHEARD SSID selection now defers to ROUTES (not NODES) for authoritative SSIDs

## [1.3.33] - 2025-06-25

### Fixed
- nodemap.py: Connection timeout now enforced (was hanging indefinitely on failed RF connections)
- nodemap.py: Socket-level timeout (5s) prevents read_some() blocking forever
- nodemap.py: SSID selection now uses NODES routing table as authoritative source
- nodemap.py: Non-aliased NODES entries (e.g., N1LJK-15) now parsed correctly
- nodemap.py: Removed incorrect "higher SSID is better" assumption

### Changed
- nodemap.py: _parse_nodes_aliases now captures both aliased (CCEBBS:WS1EC-2) and non-aliased (N1LJK-15) entries
- nodemap.py: MHEARD SSID selection defers to NODES routing table for known nodes
- nodemap.py: Entries only in MHEARD (not in NODES) marked as potentially operators

## [1.3.29] - 2025-06-25

### Changed
- nodemap.py: Skip non-node stations (no SSID) in MHEARD-based crawling
- nodemap.py: Stations without SSIDs (digipeaters, users) documented but not crawled
- nodemap.py: Separated own_aliases (current node) from nodes_aliases (routing table)
- nodemap.py: Summary now shows "Own Aliases" count instead of all nodes' aliases

### Fixed
- nodemap.py: WD1F hang - stations without SSIDs are not BPQ nodes, don't try to connect
- nodemap.py: Alias count was inflated by including all NODES entries

## [1.3.28] - 2025-06-25

### Changed
- nodemap.py: Complete rewrite of _send_command for multi-hop RF reliability
- nodemap.py: Added retry logic with content validation for command responses
- nodemap.py: Inter-command delays scaled by hop count (0.5s base + 0.5s per hop)
- nodemap.py: Connection timeout scales with hop count (30s base + 30s per hop, max 180s)

### Fixed
- nodemap.py: Command/response synchronization issues on multi-hop RF paths
- nodemap.py: PORTS regex now correctly extracts frequency information
- nodemap.py: Handles partial/malformed responses with automatic retry

### Added
- GitHub Copilot instructions file (`.github/copilot-instructions.md`)
- This changelog file to track project changes
- `docs/` directory for consolidated documentation and images
- `docs/images/` directory containing all screenshots and example outputs
- `docs/examples/` directory for configuration file examples
- `docs/INSTALLATION.md` - comprehensive installation and setup guide
- `games/` directory for interactive game applications
- `games/README.md` documenting game setup and configuration
- Comprehensive documentation in `docs/examples/etc/README.md` explaining service integration
- Complete app documentation in `apps/README.md` for all applications including:
  - callout.py (BPQ callsign capture example)
  - forms.py (fillable forms system)
  - wx.py (NWS API weather - in development)
  - wxnws-ftp.py (NWS FTP retrieval - experimental)
  - sysinfo.sh (node system information)
- Subdirectory documentation sections in `apps/README.md`

### Changed
- Optimized Copilot instructions for token efficiency (limited AI budget)
- Fixed step numbering sequence in main README.md (corrected 5→7 jump, added missing steps 4 and 6)
- Consolidated all images from `apps/images/` and root screenshot into `docs/images/`
- Updated all image references in README files to point to new `docs/images/` location
- Reorganized repository structure: moved games to separate `games/` directory
- Moved configuration examples: `etc/` and `linbpq/` now under `docs/examples/`
- Streamlined main README.md to focus on features/capabilities with links to detailed docs
- Extracted installation instructions from README.md to `docs/INSTALLATION.md`
- Updated all path references throughout documentation
- Added repository structure documentation to copilot-instructions.md
- Moved utilities from `apps/utilities/` to root `/utilities/` directory

### Removed
- `apps/images/` directory (consolidated into `docs/images/`)
- Root-level screenshot file (moved to `docs/images/`)
- battleship.py from `apps/` directory (moved to `games/`)
- Installation instructions from main README.md (extracted to `docs/INSTALLATION.md`)
- Root-level `etc/` directory (moved to `docs/examples/etc/`)
- Root-level `linbpq/` directory (moved to `docs/examples/linbpq/`)

### Deprecated

### Removed

### Fixed

### Security

---

## Historical Changes

Changes prior to 2026-01-11 are not documented in this changelog format.
