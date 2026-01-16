# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [nodemap 1.7.22] - 2026-01-16
### Changed
- Improved BFS pathfinding debug output to show SSID resolution
- Always shows neighbor check results (even when empty) in verbose mode

## [nodemap 1.7.21] - 2026-01-16
### Fixed
- BFS pathfinding now resolves base callsigns to full SSIDs when looking up node data
- Fixes "KC1JMH neighbors: []" bug where nodes stored with SSIDs weren't found
- START_NODE pathfinding now works correctly with SSID-keyed node data

## [nodemap 1.7.20] - 2026-01-16
### Fixed
- Fixed variable naming bug in alias mapping (is_service should be is_likely_node)
- Prevents service SSIDs (KC1JMH-10, N1REX-2) from overwriting node aliases
- call_to_alias now correctly prefers node SSIDs over service SSIDs

## [nodemap 1.7.19] - 2026-01-16
### Fixed
- Positional START_NODE argument parsing now works when provided without MAX_HOPS
- ./nodemap.py AB1KI-15 --callsign W1DTX-4 now correctly starts from AB1KI-15
- Previously ignored START_NODE when not preceded by MAX_HOPS digit

## [nodemap 1.7.18] - 2026-01-16
### Fixed
- Apply _is_likely_node_ssid() filter when restoring netrom_ssids from JSON
- Prevents loading port-specific SSIDs (KC1JMH-7) into connection map

## [nodemap 1.7.17] - 2026-01-16
### Fixed
- own_aliases restoration now uses primary node alias (matches node's advertised alias field)
- Falls back to _is_likely_node_ssid() check instead of hardcoded service SSID list
- Fixes direct neighbor connections using port SSIDs (KC1JMH-7) instead of node SSIDs (KC1JMH-15)

## [nodemap 1.7.16] - 2026-01-16
### Changed
- Replaced _is_service_ssid() with _is_likely_node_ssid() - uses data source priority instead of SSID number filtering
- Service/port SSIDs vary by sysop (no standard numbers), so can't filter by specific SSIDs
- Priority: ROUTES (authoritative) > own_aliases (advertised) > MHEARD (transient)
- Only filters SSIDs outside valid range (0, >15) when choosing connection targets
- All SSIDs preserved in maps/data for visualization - filtering only affects routing

## [nodemap 1.7.15] - 2026-01-16
### Fixed
- Filter service SSIDs and suspicious SSIDs (like -8) when loading from MHEARD data
- Prevents connecting to KC1JMH-8 (port identifier) instead of KC1JMH-15 (node)
- _is_service_ssid() now filters: -2 (BBS), -4/-5/-13 (CHAT), -10 (RMS), -8 (port ID), -0, >15
- ROUTES data (most authoritative) always preferred over MHEARD data

## [nodemap 1.7.14] - 2026-01-15
### Fixed
- Prevent routing loops by skipping neighbors already in the path
- Example: At KS1R via KC1JMH, no longer routes back through KC1JMH to reach KC1JMH
- Reduces excessive 1200 baud AX.25 traffic from circular routing

## [nodemap 1.7.13] - 2026-01-15
### Added
- Display logging status at startup when -l or -D flags are used
- Shows which log files will be created (telnet.log, debug.log)
- Confirms logging is enabled before crawl starts

## [nodemap 1.7.12] - 2026-01-15
### Fixed
- Added missing _is_service_ssid() method that was referenced but not included in v1.7.9
- Fixes AttributeError when crawling with service alias filtering enabled

## [nodemap 1.7.11] - 2026-01-15
### Changed
- Map generation prompt moved to after crawl completes and summary is displayed
- Allows user to review node/connection counts before generating maps
- Prevents generating maps with bad data before seeing results

## [nodemap 1.7.10] - 2026-01-15
### Changed
- -D/--debug-log now automatically enables verbose output (-v)
- Debug mode no longer requires separate -v flag
- Standard UX: debug implies verbose console output

## [nodemap 1.7.9] - 2026-01-15
### Fixed
- Connection logic now prefers node aliases (e.g., BURG:KS1R-15) over service aliases (CHABUR:KS1R-13, BBSBUR:KS1R-2)
- Prevents connecting to CHAT, BBS, or RMS services when intending to crawl nodes
- Fixes map corruption when crawling with callsign-SSID as start node (e.g., ./nodemap.py KS1R-15)
### Added
- Helper method _is_service_ssid() to identify service SSIDs: -2 (BBS), -4/-5/-13 (CHAT), -10 (RMS)

## [nodemap 1.7.8] - 2026-01-15
### Added
- Short option -D for --debug-log (lowercase -d already used for --display-nodes)

## [nodemap 1.7.7] - 2026-01-15
### Changed
- --log and --debug-log now accept optional filenames
- Default filenames: telnet.log and debug.log if not specified
- Usage: `./nodemap.py -v --debug-log` creates debug.log automatically

## [nodemap-html 1.4.4] - 2026-01-15
### Changed
- Primary NetRom alias (matching node alias field) now shown first and bolded in HTML popups
- Makes it easier for novice users to identify the correct routing alias
- Example: N1QFY shows **KNNGNR:N1QFY-15}** first, then BBSGNR, CHTGNR, RMSGNR

## [nodemap-html 1.4.3] - 2026-01-15
### Fixed
- NetRom Access now shows only this node's own aliases (from own_aliases)
- Incomplete crawls (like KY2D) no longer show other nodes' aliases in NetRom Access
- Applications list filters out NetRom aliases and call-SSID patterns
- KY2D now correctly shows only "KY2D2M:KY2D-15}" instead of other nodes' aliases

## [nodemap 1.7.6] - 2026-01-15
### Fixed
- Deduplicate nodes during merge when base callsign and SSID variant both exist
- N1QFY and N1QFY-15 now correctly consolidated (prefers SSID version)
- Prevents duplicate node circles and connections on map
- Map no longer shows darker overlapping nodes from duplicate entries

## [nodemap 1.7.5] - 2026-01-15
### Added
- Separate --debug-log FILE option for verbose debug output only
- --log remains for telnet traffic only (raw send/recv)
- --debug-log captures what you see with -v flag

### Changed
- Clarified --log logs telnet traffic, not verbose output
- _vprint() helper now writes to debug_log instead of log_file

## [nodemap 1.7.4] - 2026-01-15
### Added
- Verbose output (-v) now captured to log file when both -v and -l used
- Helper method _vprint() for verbose messages (logs to file + console)

### Changed
- --log help text clarifies it includes verbose output when both flags present

## [nodemap 1.7.3] - 2026-01-15
### Fixed
- Direct port connections (C PORT CALL) now only used for first hop from localhost
- Subsequent hops correctly use NetRom routing (C ALIAS) via AX.25 connections
- Prevents attempting localhost telnet auth for multi-hop NetRom paths
- Auth only needed once for localhost telnet, then inherited by all AX.25 connections

### Reverted
- v1.7.2 incorrect SSID stripping logic (auth doesn't work that way)

## [nodemap 1.7.1] - 2026-01-15
### Added
- Query mode (-q/--query) now shows known SSIDs for a node from multiple sources:
  - Current crawled SSID
  - Own MHEARD data (netrom_ssids)
  - Other nodes' MHEARD references
  - Other nodes' ROUTES tables (most authoritative)
- Helps determine which SSID to use for forced recrawls (--callsign)
- Summary shows SSID usage across network for better recrawl decisions

## [nodemap-html 1.4.2] - 2026-01-15
### Added
- Incomplete crawl detection for nodes with empty routes tables
- Inbound neighbor tracking from network perspective (who has routes TO this node)
- Shows neighbor counts "(from network)" label for incomplete crawls instead of misleading "0"

### Fixed
- KY2D and similar incomplete crawls now show inbound neighbors (RF=1 from K1NYY) instead of 0
- Both HTML popups and SVG tooltips updated with incomplete crawl detection

## [nodemap-html 1.4.1] - 2026-01-15
### Fixed
- Node popups (HTML) and tooltips (SVG) now calculate and display correct RF/IP neighbor counts per node
- Removed misleading neighbors count (was showing raw MHEARD data with 11 neighbors for NG1P)
- Each node now shows: RF Neighbors (heard on RF port + in routes) and IP Neighbors (in routes but not heard on RF)

## [nodemap-html 1.4.0] - 2026-01-15
### Fixed
- **Neighbor statistics** now correctly count from ROUTES table only (not MHEARD)
- RF Neighbors: Routes where neighbor is heard on RF port
- IP Neighbors: Routes where neighbor is NOT heard on RF port (AXIP/telnet only)
- Deduplicated by base callsign
- **Node popups and tooltips** now show correct RF/IP neighbor counts instead of raw MHEARD count
- Removed misleading `neighbors` field (MHEARD data) from popups/tooltips

## [nodemap-html 1.3.0] - 2026-01-15
### Fixed
- **CRITICAL BUG**: Connection logic - now builds from routes tables (quality > 0)
- Node keys can be base callsign (KC1JMH) OR with SSID (N1QFY-15) - now checks both
- Removed incorrect netrom_ssids resolution
- Version now displays on --all runs, not just --help

### Added
- Neighbor statistics in map info box

## [nodemap 1.7.0] - 2026-01-15
### Changed
- Unified cleanup into single --cleanup command with targets: nodes, connections, or all
- Replaces separate --cleanup and --repair options
- Usage: `--cleanup nodes` (duplicates/incomplete), `--cleanup connections` (invalid), `--cleanup all` (both, default)
- More intuitive and discoverable interface

## [nodemap 1.6.15] - 2026-01-15
### Changed
- Unified cleanup into single --cleanup command with targets: nodes, connections, or all
- Replaces separate --cleanup and --repair options
- Usage: `--cleanup nodes` (duplicates/incomplete), `--cleanup connections` (invalid),
  `--cleanup all` (both, default)
- More intuitive and discoverable interface

## [nodemap 1.6.15] - 2026-01-15
### Added
- --repair option to remove invalid connections without re-crawling
- Validates connections against ROUTES tables (quality > 0)
- Shows preview of connections to be removed before confirmation
- Lightweight alternative to full network re-crawl for fixing stale links

## [nodemap 1.6.14] - 2026-01-15
### Added
- --repair option to remove invalid connections without re-crawling
- Validates connections against ROUTES tables (quality > 0)
- Shows preview of connections to be removed before confirmation
- Lightweight alternative to full network re-crawl for fixing stale links

## [nodemap 1.6.14] - 2026-01-15
### Fixed
- Remove old connections involving re-crawled nodes during merge
- Prevents stale connections from appearing on maps after single-node updates
- Fixes issue where old KC1JMH→NG1P connection persisted after NG1P re-crawl

## [nodemap 1.6.13] - 2026-01-15
### Fixed
- Remove old connections involving re-crawled nodes during merge
- Prevents stale connections from appearing on maps after single-node updates
- Fixes issue where old KC1JMH→NG1P connection persisted after NG1P re-crawl

## [nodemap 1.6.13] - 2026-01-15
### Fixed
- Prioritize node's own SSID from topology keys over netrom_ssids mappings
- Prevents using MHEARD SSIDs (e.g., KC1JMH-7) when authoritative node SSID exists (KC1JMH-15)
- Fixes forced_target path connections to use correct node SSIDs

## [nodemap 1.6.12] - 2026-01-15
### Fixed
- Prioritize node's own SSID from topology keys over netrom_ssids mappings
- Prevents using MHEARD SSIDs (e.g., KC1JMH-7) when authoritative node SSID exists (KC1JMH-15)
- Fixes forced_target path connections to use correct node SSIDs

## [nodemap 1.6.12] - 2026-01-15
### Fixed
- Only create connections for neighbors in ROUTES table with non-zero quality
- Prevents map from showing RF links to non-routing stations (heard but not routable)
- Fixes issue where direct RF links were shown instead of actual routing paths

## [nodemap 1.6.11] - 2026-01-15
### Fixed
- Only create connections for neighbors in ROUTES table with non-zero quality
- Prevents map from showing RF links to non-routing stations (heard but not routable)
- Fixes issue where direct RF links were shown instead of actual routing paths

## [nodemap 1.6.11] - 2026-01-15
### Added
- Prompt to regenerate maps after using --set-grid option

## [nodemap 1.6.10] - 2026-01-15
### Added
- Prompt to regenerate maps after using --set-grid option

## [nodemap 1.6.10] - 2026-01-15
### Added
- Interactive prompt after crawl to set gridsquares for nodes without location data
- Shows city/state context when available to help identify nodes
- Validates gridsquare format with option to override
- Skip nodes by leaving input blank
- Automatically re-exports data after updates

## [nodemap 1.6.9] - 2026-01-15
### Added
- Interactive prompt after crawl to set gridsquares for nodes without location data
- Shows city/state context when available to help identify nodes
- Validates gridsquare format with option to override
- Skip nodes by leaving input blank
- Automatically re-exports data after updates

## [nodemap 1.6.9] - 2026-01-15
### Added
- --set-grid option to manually set gridsquare for nodes
- Validates gridsquare format (warns if non-standard)
- Handles multiple SSID variants (offers to update all)
- Example: `./nodemap.py --set-grid NG1P FN43vp`

## [nodemap 1.6.8] - 2026-01-15
### Fixed
- Populate route_ports from topology data alongside netrom_ssid_map
- Enables connection to first hop when using --callsign forced target
- Extracts port numbers from heard_on_ports arrays
- Fixes "No known route to [neighbor]" errors despite topology data available

## [nodemap 1.6.7] - 2026-01-15
### Fixed
- Populate netrom_ssid_map from topology before BFS runs for forced_target
- Now properly resolves N1QFY to N1QFY-15 when finding paths

## [nodemap 1.6.6] - 2026-01-15
### Fixed
- Populate netrom_ssid_map from topology before BFS runs for forced_target
- Now properly resolves N1QFY to N1QFY-15 when finding paths

## [nodemap 1.6.6] - 2026-01-15
### Fixed
- BFS path-finding now resolves base callsigns to SSIDs when looking up node data
- Fixes issue where neighbor "N1QFY" couldn't find node data stored as "N1QFY-15"

## [nodemap 1.6.5] - 2026-01-15
### Added
- Debug output for BFS path-finding to diagnose topology search issues

## [nodemap 1.6.4] - 2026-01-15
### Fixed
- Fixed UnboundLocalError when using --callsign (existing variable scope issue)

## [nodemap 1.6.3] - 2026-01-15
### Fixed
- `--callsign` now properly crawls TO target node instead of starting FROM it
- Added forced_target parameter to distinguish between start node and target node  
- BFS path-finding now runs for forced targets, queues with correct path

## [nodemap 1.6.2] - 2026-01-15
### Fixed
- `--callsign` now properly crawls TO target node instead of starting FROM it
- Added forced_target parameter to distinguish between start node and target node
- BFS path-finding now runs for forced targets, queues with correct path

## [nodemap 1.6.2] - 2026-01-15
### Fixed
- Reverted 1.6.1 change that broke --callsign by setting start_node in arg parsing
- Original logic at line 3581 correctly sets start_node from forced SSID base call
- BFS path-finding should now trigger properly for remote targets

## [nodemap 1.6.1] - 2026-01-15
### Fixed
- `--callsign` now triggers path-finding logic when target is not local node
- Previously, `--callsign NG1P-4` would attempt direct connection and fail
- Now properly finds path through intermediate nodes using BFS and prompts user

## [nodemap 1.6.0] - 2026-01-15
### Added
- `--cleanup` option to automatically clean nodemap.json
- Removes duplicate base callsign entries (keeps most complete one)
- Removes incomplete nodes (no neighbors, no location, no apps)
- Creates backup file before cleaning
- Scores duplicates by: neighbor count + location (100 pts) + apps (50 pts)

## [nodemap 1.5.11] - 2026-01-15
### Added
- Manual callsign input as final fallback when all automatic path finding fails
- Validates manual input exists in topology and finds path to it

### Fixed
- No longer shows empty prompt "(1-0)" when no nodes found
- Gracefully handles case where topology data is incomplete

## [nodemap 1.5.10] - 2026-01-15
### Fixed
- MHEARD parsing now prefers SSID entries over non-SSID entries (e.g., KB1TAE-4 over KB1TAE)
- Non-SSID entries no longer block SSID entries for same base callsign
- Upgrades existing non-SSID entry when SSID entry found later in MHEARD list

## [nodemap 1.5.9] - 2026-01-15
### Changed
- Increased operation timeout: 6min base + 4min/hop (was 4min + 3min/hop)
- Prevents premature timeouts on slow RF networks at 1200 baud
- 1 hop now gets 10min (was 7min), 2 hops get 14min (was 10min)

## [nodemap 1.5.8] - 2026-01-15
### Fixed
- Path building now uses CLI-forced SSID (--callsign) instead of discovered SSID from JSON
- Prevents connecting to wrong SSID (e.g., NG1P-1 BBS instead of NG1P-4 node)

## [nodemap 1.5.7] - 2026-01-15
### Added
- Metadata section in JSON with nodemap_version, generated timestamp, and generator name
- Helps identify which script version generated the data

## [nodemap 1.5.6] - 2026-01-15
### Fixed
- Now always prompts for manual node selection when automatic path finding fails
- Shows all known nodes sorted by connectivity when target not found in any neighbor list

## [nodemap 1.5.5] - 2026-01-15
### Added
- Debug output in verbose mode showing each node's neighbor list during BFS path search

## [nodemap 1.5.4] - 2026-01-15
### Fixed
- Removed NetRom alias fallback when no path found - now always prompts for neighbor selection
- When no direct neighbors have heard target, searches all nodes and prompts user to choose path
- Prevents wasteful connection attempts when NRR reports no route

### Changed
- Interactive path selection now shows all nodes (not just direct) when direct neighbors don't have target

## [nodemap 1.5.3] - 2026-01-15
### Changed
- Interactive path selection now only shows direct neighbors (1 hop) instead of all nodes
- Direct neighbors sorted by route quality (best first) instead of hop distance
- Simplified path building since all options are direct neighbors

## [nodemap 1.5.2] - 2026-01-15
### Changed
- Interactive path selection now sorts nodes by hop distance (closest first) instead of alphabetically
- Display shows hop count for each intermediate node option (e.g., "1 hop", "2 hops")

## [nodemap 1.5.1] - 2026-01-15
### Added
- Interactive path selection when target node not directly reachable with `--callsign`
  - Script now searches for nodes that have heard the target on RF
  - Prompts user to choose intermediate node to connect through
  - Automatically builds path: local → intermediate → target
  - Validates intermediate node is reachable before proceeding
  - Example: `./nodemap.py --callsign NG1P-4` shows nodes that heard NG1P, lets you pick one

### Fixed
- `--callsign` with max_hops=0 no longer tries impossible direct connections
- Better error messages when target node is not in network topology

## [nodemap 1.5.0] - 2026-01-15
### Changed
- **Default max_hops reduced from 10 to 4** (realistic for 1200 baud RF with acceptable latency)
- **`--callsign` now defaults to max_hops=0** (correction mode: fix one node without crawling neighbors)
  - Example: `./nodemap.py --callsign NG1P-4` automatically sets max_hops=0 and start_node=NG1P
  - To crawl neighbors too: `./nodemap.py 5 --callsign NG1P-4` (explicit max_hops overrides)
- `--callsign` behavior: correction tool for fixing bad SSID data, not a full network crawl

### Fixed
- nodemap-html: Deduplicate unmapped nodes by base callsign (prevents showing NG1P and NG1P-4 separately)

## [nodemap 1.4.5] - 2026-01-14
### Fixed
- Improved timeout handling for long MHEARD/INFO responses over multi-hop RF
  - Increased per-read timeout from 3s to max 8s (scales with command timeout)
  - Require 3 consecutive stable readings instead of 2 before terminating (prevents premature cutoff)
  - More retry attempts (8 minimum vs 5) for reliability on slow RF links
  - Fixes incomplete MHEARD lists and missing INFO data on 3+ hop connections

## [nodemap 1.4.4] - 2026-01-14
### Fixed
- CLI-forced SSIDs now used when resolving start node callsign to SSID
  - Previously: `./nodemap.py 5 NG1P --callsign NG1P-4` would resolve to NG1P-1 from stale data
  - Now: checks `cli_forced_ssids` before `netrom_ssid_map` during start node resolution
  - Verbose mode shows "Resolved NG1P to node SSID: NG1P-4 (CLI-forced)"

## [nodemap 1.4.3] - 2026-01-14
### Changed
- CLI-forced SSIDs (`--callsign`) now update the node's `netrom_ssids` in saved JSON
  - Allows correcting bad SSID data in existing nodemap.json files
  - Forced SSID persists for future crawls even without the CLI flag
  - Verbose mode shows "Updated netrom_ssids: CALL = CALL-SSID (CLI-forced)"

## [nodemap 1.4.2] - 2026-01-14
### Fixed
- CLI-forced SSIDs (`--callsign`) now respected during reconnection attempts after timeouts/disconnects
  - Previously: node disconnects mid-crawl, script reconnects using stale SSID from `netrom_ssid_map`
  - Now: checks `cli_forced_ssids` first before falling back to discovered SSIDs on all connection attempts

## [nodemap 1.4.1] - 2026-01-14
### Fixed
- `--callsign` forced SSIDs now survive resume mode (were being overwritten by JSON data)
- CLI-forced SSIDs now correctly override any discovered SSIDs from previous crawls

## [nodemap 1.4.0] - 2026-01-14
### Added
- `--callsign CALL-SSID` CLI option to force specific node SSID (e.g., `--callsign NG1P-4`)
- `--query CALL` or `-q CALL` to display node info: neighbors, apps, routes, best path
- SSID source tracking: now tracks whether SSID came from ROUTES, MHEARD, or CLI

### Changed
- MHEARD SSIDs can now update older MHEARD entries (>1hr old) but never overwrite ROUTES
- ROUTES SSIDs always take priority as most authoritative source
- Fixes issue where stale SSID discovery prevented correct node connections

### Fixed
- Nodes with multiple SSIDs (e.g., NG1P-1 BBS vs NG1P-4 node) now correctly connect to node SSID
- SSID map now updates during crawl instead of only at startup

## [nodemap-html 1.0.1] - 2026-01-14
### Added
- HTML map now displays unmapped nodes (nodes without gridsquare data) in info box with orange header.
- Unmapped nodes listed separately to explain why some crawled nodes don't appear on map.

## [nodemap 1.3.106] - 2026-01-14
### Changed
- Improved application detection: Now correctly identifies custom apps (GOPHER, EANHUB, TEST, FORMS, etc.) vs standard BPQ commands. Uses set for faster lookups.
- Fixed nodemap-html.py to display all applications properly (was incorrectly filtering NetRom aliases that didn't match node callsign).

### Added
- Partial crawl data now saved on timeout. If node times out mid-crawl, partial PORTS, ROUTES, and neighbor data is preserved for future analysis.
- Track partial crawls with 'partial': True flag in node data.

## [nodemap 1.3.105] - 2026-01-14
### Changed
- Queue entries now include route quality from BPQ ROUTES command. Queue sorted by quality (desc), hop count (asc), then MHEARD recency.
- Allow multiple paths to same node (queue all valid paths, not just shortest). Enables fallback to alternate paths when primary route fails.
- Skip quality 0 routes (sysop-blocked) during neighbor discovery.
- Track queued paths to prevent duplicate queue entries for same path.

## [nodemap 1.3.104] - 2026-01-14
### Fixed
- Fixed timeout issue with large NODES responses over multi-hop paths. Reduced per-read timeout from full cmd_timeout to 3s max and increased retry attempts proportional to overall timeout. Prevents premature timeout when NODES list hasn't finished transmitting before ROUTES command sent.

## [nodemap 1.3.103] - 2026-01-14
### Changed
- SSID restoration now uses consensus from all nodes' ROUTES tables (authoritative)
- No longer assumes -15 for node SSIDs (can be any 0-15)
- Picks most common SSID when multiple nodes route to same callsign
- Fallback to netrom_ssids (MHEARD) only if not in any routes

## [nodemap 1.3.102] - 2026-01-14
### Fixed
- SSID restoration from own_aliases now searches for -15 suffix (node SSID)
- Fixes KC1JMH-4 (CHAT) being used instead of KC1JMH-15 (node)
- Primary alias field may point to application SSID, not node SSID

## [nodemap 1.3.101] - 2026-01-14
### Fixed
- Skip routes without SSID suffix when restoring netrom_ssid_map
- Prevents old JSON routes ("KC1JMH": 168) from overwriting netrom_ssids ("KC1JMH": "KC1JMH-15")
- Now correctly uses netrom_ssids from node's MHEARD data for connections

## [nodemap 1.3.100] - 2026-01-14
### Fixed
- SSID restoration now prioritizes own_aliases (node's own SSID) over routes
- Fixes KC1JMH resolving to KC1JMH-15 instead of KC1JMH-7 from old netrom_ssids
- Extracts node SSID from primary alias in own_aliases (e.g., CMBWBK:KC1JMH-15)

## [nodemap 1.3.99] - 2026-01-14
### Fixed
- Resume mode now checks if **parent node** has valid route (quality > 0) to neighbor
- Prevents queuing N1REX via KC1JMH when KC1JMH has quality 0 route
- Will correctly queue N1REX via N1QFY (which has quality 200 route) instead

## [nodemap 1.3.98] - 2026-01-14
### Fixed
- Resume mode now prioritizes neighbor's own successful_path over parent reconstruction
- SSID restoration now prioritizes ROUTES data (node SSIDs) over netrom_ssids (may contain user SSIDs)
- Fixes KC1JMH-7 issue - now correctly uses KC1JMH-15 (node SSID) from ROUTES
- Prevents attempting blocked routes when better proven paths exist

## [nodemap 1.3.97] - 2026-01-14
### Added
- Track successful connection path for each node in `successful_path` field
- Resume mode now uses proven working paths from previous crawls
- Reduces failed connection attempts by reusing known-good routes (e.g., KC1JMH > K1NYY > AB1KI)

## [nodemap 1.3.96] - 2026-01-14
### Fixed
- Resume mode now respects quality 0 (blocked) routes
- Prevents queuing nodes with sysop-blocked routes (e.g., N1REX from KC1JMH)
- Aligns resume behavior with normal crawl mode route filtering

## [nodemap 1.3.95] - 2026-01-14
### Fixed
- Improved command response handling for large outputs (NODES, ROUTES)
- Increased wait time between read attempts from 0.5s to 1.0s for slow RF links
- Requires 2 consecutive stable readings (2s total) before considering response complete
- Prevents premature command interruption on multi-hop simplex RF connections

## [nodemap 1.3.94] - 2026-01-14
### Fixed
- Frequency parsing now handles formats without "MHz" suffix (e.g., "144.990" from KY2D-15)
- Added frequency validation (30-3000 MHz range) to avoid false positives

## [nodemap 1.3.93] - 2026-01-14
### Changed
- Added future-proofing for telnetlib removal in Python 3.13+
- Automatically falls back to telnetlib3 if stdlib telnetlib unavailable
- Added informative error message with installation instructions
- Works seamlessly on Python 3.5.3 through 3.13+

## [nodemap 1.3.92] - 2026-01-14
### Fixed
- Connection timeout now properly enforced using read_very_eager() instead of read_some()
- Prevents indefinite hangs when connecting to offline/unreachable nodes (e.g., N1REX)
- Added exception handling for socket errors during connection attempts

## [nodemap 1.3.91] - 2026-01-14
### Fixed
- Resume mode now uses node SSID from ROUTES table when queuing unexplored neighbors
- Prevents attempting to connect to wrong SSIDs (e.g., KC1JMH-7 instead of KC1JMH-15)
- Ensures authoritative SSID from routing tables is used for connections

## [nodemap 1.3.90] - 2026-01-13
### Changed
- Increased connection timeout per hop from 30s to 45s (max 240s)
- Increased operation timeout from 3min+2min/hop to 4min+3min/hop
- Increased inter-command delay from 0.5s+0.5s/hop to 1s+0.5s/hop
- Allows more time for slow RF links to complete multi-hop operations

## [nodemap-html 1.1.6] - 2026-01-13
### Fixed
- HTML map output now reports deduplicated connection count (matching SVG count)
- Eliminates confusion from bidirectional connections being counted twice

## [nodemap 1.3.89] - 2026-01-13
### Fixed
- Notification errors now display in red color for better visibility
### Fixed
- Notification errors now display in red color for better visibility

## [map_boundaries.py & download_boundaries.py] - 2026-01-13
### Changed
- Replaced heavily simplified boundary coordinates with accurate Natural Earth 1:10m data
- Updated to Natural Earth Data (Public Domain) from naturalearthdata.com
- Improved boundary accuracy for SVG offline maps
- Added download_boundaries.py utility to regenerate boundaries from source
- Implemented Douglas-Peucker simplification algorithm for manageable file sizes
- Filtered to 14 northeastern US states (ME, NH, VT, MA, CT, RI, NY, PA, NJ, MD, DE, VA, WV, DC)
- Note: County boundaries still require separate processing from Census TIGER/Line files

## [nodemap 1.3.88] - 2026-01-13
### Changed
- Simplified verbose skip message to remove redundant explanation

## [nodemap 1.3.87] - 2026-01-13
### Fixed
- Resume mode now checks ROUTES data instead of netrom_ssids to identify nodes
- Prevents connection attempts to BBS/application SSIDs (e.g., KB1TAE with only KB1TAE-2/KB1TAE-4)
- Only queues neighbors that have routing entries (actual nodes, not just services)
- Fixes issue where script connected to KB1TAE PBBS instead of recognizing it's not a node

## [nodemap-html 1.1.5] - 2026-01-13
### Fixed
- HTML map now deduplicates bidirectional connections (was showing 14, now shows 7)
- SVG connection colors now match per-connection frequencies (not just first port)
- SVG tooltips cleaned up to match HTML format (Type, Frequencies, Neighbors)
- SVG connection tooltips now show frequency like HTML version
- Both HTML and SVG now display identical connection counts and colors

## [nodemap 1.3.86] - 2026-01-13
### Fixed
- Resume mode now filters out user station SSIDs (e.g., KC1JMH-7) from unexplored neighbors
- Only queues neighbors that have known node SSIDs from netrom_ssids data
- Prevents attempts to connect to application/user SSIDs as nodes
- Adds verbose logging when skipping non-node SSIDs

## [nodemap 1.3.85] - 2026-01-13
### Changed
- Added ANSI color codes to all error (red), warning (yellow), and success (green) messages
- Improved visibility of critical messages in terminal output

## [nodemap-html 1.1.4] - 2026-01-13
### Changed
- Added ANSI color codes to all error (red) and warning (yellow) messages
- Improved visibility of critical messages in terminal output

## [nodemap 1.3.84] - 2026-01-13
### Added
- Prompt at script start to generate HTML/SVG maps after crawl completes
- Auto-detects nodemap-html.py in same directory
- Runs map generation automatically if user opts in (default: yes)
- Allows unattended operation from prompt to completion

## [nodemap-html 1.1.3] - 2026-01-13
### Changed
- NetRom access entries now displayed in separate "NetRom Access:" section
- Applications list no longer includes NetRom aliases for cleaner display
- NetRom entries identified by format "ALIAS:CALLSIGN-SSID" matching node callsign

## [nodemap-html 1.1.2] - 2026-01-13
### Added
- Auto-detects ../linbpq/HTML directory and prompts to save files there
- `--output-dir DIR` option to specify custom output directory
- Skips deployment reminder if files already saved to linbpq directory

### Changed
- Default behavior now offers to save directly to BPQ web server location

## [nodemap-html 1.1.1] - 2026-01-13
### Fixed
- SSIDs field now shows only node's own service SSIDs (from own_aliases)
- Previously displayed neighbors' SSIDs from netrom_ssids
- Frequency displays now color-coded by band (blue=2m, orange=70cm, purple=1.25m)
- Colors match connection line colors in legend

## [nodemap 1.3.83] - 2026-01-13
### Added
- `--exclude` or `-x` flag to skip specific nodes during crawl
- Accepts comma-separated list of callsigns: `--exclude AB1KI,N1REX,K1NYY`
- Useful for excluding offline or problematic nodes
- Displays excluded nodes at start of crawl

## [nodemap 1.3.82] - 2026-01-13
### Fixed
- Connection timeout enforcement now properly exits wait loops
- Added elapsed time check at start of each I/O loop iteration
- Prevents 5+ minute hangs when connections fail to respond
- Timeouts now respect configured values (60-120s) instead of hanging indefinitely
- Affects both direct port connections and NetRom fallback attempts

## [nodemap 1.3.81] - 2026-01-13
### Added
- Multiple path attempts for unreachable nodes
- Queues all paths to each unexplored neighbor (not just first path found)
- Automatically retries via alternate parent nodes if connection fails
- Paths prioritized by hop count (fewer hops tried first)

### Changed
- Node only marked as "visited" after successful crawl completion
- Failed connection no longer prevents retry via different path
- Better utilization of redundant network topology

### Fixed
- Nodes reachable from multiple parents now get multiple connection attempts
- Example: AB1KI unreachable via N1QFY will retry via KS1R or K1NYY

## [nodemap 1.3.80] - 2026-01-13
### Fixed
- Unexplored neighbors now use correct multi-hop paths to parent nodes
- Added BFS path-finding to reconstruct routes through network topology
- Previously assumed direct connection to parent node, causing connection failures
- Matches behavior of "start from callsign" path resolution

## [nodemap 1.3.79] - 2026-01-13
### Changed
- Cleaned up verbose output during data restoration
- Removed per-item SSID/port restoration messages (too noisy)
- Added summary counts for restored SSIDs and route ports
- Improved unexplored neighbors display (shows which node has which unexplored neighbors)
- Limited unexplored neighbor lists to first 5 items with '...' if more

## [nodemap 1.3.78] - 2026-01-13
### Added
- Unknown argument detection with helpful error message
- Now exits with error and suggests `--help` for invalid arguments
- Prevents silent failures from typos like `--mode: new-only`

## [nodemap 1.3.77] - 2026-01-13
### Fixed
- `new-only` mode now correctly skips nodes already in self.nodes (from nodemap.json)
- Previously only checked self.visited (current session), causing re-crawl of known nodes

## [nodemap 1.3.76] - 2026-01-13
### Added
- Crawl mode selection: `--mode update|reaudit|new-only`
- `update` mode (default): Skip already-visited nodes in current session
- `reaudit` mode: Re-crawl all nodes to verify and update network data
- `new-only` mode: Auto-load nodemap.json and queue unexplored neighbors only
- Reduces RF bandwidth usage when only discovering new network nodes
- Useful for limited bandwidth (1200 baud simplex) operations
### Changed
- `new-only` mode now behaves like `--resume` but skips known nodes
- Automatically queues unexplored neighbors from existing nodemap.json

## [nodemap 1.3.75] - 2026-01-13
### Added
- Send `?` command first to discover available commands on node
- Some nodes don't support standard BPQ sysop commands
- Helps identify non-BPQ or differently configured nodes

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
