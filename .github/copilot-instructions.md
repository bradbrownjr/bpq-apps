# GitHub Copilot Instructions for BPQ Packet Radio Apps

## Context
Packet radio apps for AX.25 networks via linbpq BBS. Target: RPi 3B, Raspbian 9, Python 3.5.3, 1200 baud serial.

## Constraints
- Python 3.5.3 only (no f-strings, async/await, limited type hints)
- ASCII text only (no ANSI, Unicode, control codes)
- Minimal output (1200 baud - every byte counts)
- Stdlib preferred (limited packages available)
- Line-based input, synchronous I/O
- 40-character width limit for mobile/older terminals
- No TUI libraries

## Communication
- Dry, factual, KISS principle
- No repetition or verbose explanations
- Token efficiency critical (limited AI budget)
- "don't" = add prohibition, "remember" = add requirement

## Code Standards
- Remove deprecated/unused code during changes
- Descriptive names, small functions, docstrings
- Handle poor radio conditions (packet loss, intermittent connectivity)
- Document changes in CHANGELOG.md
- Document new and changed features to the respective README.md files
- Include help args (-h, --help, /?) in utilities and CLI tools
- **Auto-Update Protocol:** All Python apps must include auto-update functionality
  - Add version string to docstring: `Version: X.Y`
  - Include `check_for_app_update()` and `compare_versions()` functions
  - Call `check_for_app_update("X.Y", "script.py")` at startup
  - 3-second timeout for GitHub checks (silent failure if no internet)
  - Atomic updates with executable permission preservation
  - Clean error handling with temporary file cleanup
- **README Documentation:** All README.md files longer than one paragraph must include table of contents
- **Version bumping protocol:**
  - Update docstring `Version:` field in app modules
  - Update `__version__` variable when present
  - Bump `version` field in .frm JSON form templates
  - **Apps with self-update:** Version bump triggers auto-download on user systems
- Commit and push changes to GitHub after completing work

## Resilience & Offline Operation
**Design Philosophy**: Apps are internet-optional with graceful fallbacks. Packet radio nodes often have intermittent or no internet connectivity. Apps must never crash on network failure.

**Auto-Update Behavior** (all apps):
- Call `check_for_app_update(VERSION, "appname.py")` at startup
- 3-second timeout for GitHub version check (fails silently if unreachable)
- If update available, downloads in background (atomic operation)
- If GitHub is down: app continues normally with existing code
- **Never** blocks startup or crashes user session on network failure

**Per-App Network Strategy**:

*Apps with local caching (use cached data as fallback):*
- `hamtest.py`: Caches question_pools/*.json locally (uses cached pools if offline)
- `feed.py`: Caches feed_board.json with timestamps (shows cached articles if fetch fails)
- `predict.py`: Caches solar_cache.json (uses cached data if NOAA unreachable, max 7 days stale)
- `forms.py`: Caches forms/*.frm templates (displays cached forms if network down)

*Apps with network detection (show user-friendly offline message):*
- `rss-news.py`: Tests internet connectivity on feed fetch failure, displays "Internet appears to be unavailable. Try again later."
- `hamqsl.py`: Shows offline message if hamqsl.com unreachable
- `space.py`: Shows offline message if NOAA space weather feed fails
- `wx.py`: Shows offline message if NWS headline fetch fails
- `wx-me.py`: Shows offline message if weather API unreachable

*Apps with graceful defaults (work offline with limited features):*
- `gopher.py`: Caches gopher menu structure from previous session
- `qrz3.py`: Uses cached callsign lookups from previous session
- `callout.py`: Works offline for local station info (no internet required)
- `wxnws-ftp.py`: Skips FTP upload if network down, continues with local file handling

**Network Detection Implementation**:
- Use `socket.create_connection('8.8.8.8', 53)` with 2-second timeout
- Returns boolean: True if DNS port responds, False if unreachable
- Example: `is_internet_available()` function in rss-news.py, hamqsl.py, space.py, wx.py, wx-me.py
- Lightweight: DNS check is faster than HTTP and works on restricted networks

**Error Handling Pattern** (all apps):
```python
try:
    # main app execution
except Exception as e:
    if is_internet_available():
        # Show actual error for debugging
        print("Error: {}".format(str(e)))
    else:
        # Show user-friendly offline message
        print("Internet appears to be unavailable.")
        print("Try again later.")
    # Continue execution, don't crash
```

**Configuration File Handling**:
- All apps check for missing config files gracefully
- Use sensible defaults instead of failing
- Example: rss-news.py falls back to default feeds (ARRL, QRZ, BBC) if config missing
- Log missing files but don't exit

**Testing Offline Behavior**:
- Simulate network down: `sudo iptables -I OUTPUT -d 8.8.8.8 -j DROP` (then restore)
- Verify: Apps show offline message, not crash/error
- Check cached data is used (hamtest, feed, predict, forms)
- Confirm startup completes even if GitHub unreachable

## BPQ32 APPLICATION Command Format
**APPLICATION line syntax:** `APPLICATION #,NAME,command,call,flags`

**Command format for Python apps (C 9 HOST):**
```
APPLICATION 5,APPNAME,C 9 HOST # NOCALL S K,CALLSIGN,FLAGS
                                 ↑    ↑  ↑ ↑ ↑
                       Port 9 ---+    |  | | +-- Keep session alive
                                      |  | +---- Send callsign via stdin
                                      |  +------ Don't require auth
                                      +--------- Host port position
```

**Callsign Handling:**
- `S` flag sends the callsign to app via stdin (first line)
- **Critical:** BPQ32 passes callsign WITH SSID (e.g., `KC1JMH-8`)
- Apps must strip SSID using helper function if cleaner display needed:
  ```python
  def extract_base_call(callsign):
      """Remove SSID from callsign"""
      return callsign.split('-')[0] if callsign else ""
  ```
- Used by: feed.py (bulletin board authors), forms.py (form submitter)

## CLI Design Standards
**All command-line options must have both long and short forms:**
- Long form: `--option` (GNU style, descriptive)
- Short form: `-X` (single character, POSIX style)
- Always support `-h`, `--help`, `/?` for help

**Help output format (Linux man page style):**
```
NAME
       toolname - brief description

SYNOPSIS
       toolname.py [OPTIONS] [ARGUMENTS]

VERSION
       X.Y.Z

DESCRIPTION
       Detailed explanation of what the tool does.

OPTIONS
   Category:
       -x, --long-option [ARG]
              Description of option. Default: value.

EXAMPLES
       toolname.py -x
              Brief explanation.

FILES
       filename    Description of file

SEE ALSO
       related-tool.py - brief description
```

**Shorthand conventions (maintain consistency across utilities):**
- `-h` help, `-v` verbose, `-o` overwrite/output
- `-i` input, `-r` resume, `-m` merge, `-q` query
- `-l` log, `-d` display, `-x` exclude
- Use uppercase for specialized flags: `-H` HF, `-I` IP, `-C` cleanup, `-N` note, `-M` mode, `-D` debug

## BPQ App Interface Standards
**Bandwidth Efficiency**: Every character counts on 1200 baud packet radio
- Dynamic terminal width with 40-character fallback for piped input: `os.get_terminal_size().columns` 
- Fixed 40-character separator lines using dash character: `print("-" * 40)`
- Minimal decorative elements (single line separators only, using `-` character)
- ASCII-only decorative elements - NO Unicode, ANSI codes, or control characters
- No welcome messages - straight to functionality
- Terse but clear prompts and navigation

**ASCII Art Logos**: All main user-facing apps include professional lowercase ASCII art logos
- Generated from asciiart.eu text-to-ascii-art tool
- Lowercase letter designs (modern, polished appearance)
- Implemented using raw strings to handle backslash escaping: `r"ASCII art with \ backslashes"`
- Standard 5-7 line height for consistency
- Examples: feed.py, forms.py, gopher.py, hamtest.py, predict.py, qrz3.py, rss-news.py, space.py, wx-me.py, wx.py

**Standard Interface Pattern**:
```
app name (5-7 line ASCII art logo)

APP NAME v1.X - Brief Description

Main Menu:
1) Primary Function
2) Secondary Function
3) Tertiary Function

A) About  Q) Quit
Menu: [options] :>
```

**Consistent Elements**:
- Header: Lowercase ASCII art logo + app name, version, brief description
- Menu: Numbered options with descriptions, no decorative separators between items
- Separators: Fixed 40-char dash lines (`"-" * 40`) before/after menu sections
- Prompts: Context + compressed commands
- Exit: "Exiting..." for apps, "73!" only for node sign-off
- No social pleasantries - these are utilities, not chatbots

**Prompt Optimization**: Compress commands to save bandwidth
- `P)ost D)el N)ext Pr)ev S)tat Q` instead of `P)ost, D)elete, N)ext, Pr)evious, S)tats, Q)uit`
- Context-aware: `Menu: [commands] :>` or `Articles: [commands] :>`

## Amateur Radio Formats
**Callsigns**: 1-2 prefix letters, digit, 1-3 suffix letters, optional -SSID (0-15)
- Regex: `^[A-Z]{1,2}\d[A-Z]{1,3}(?:-\d{1,2})?$`
- Examples: `KC1JMH`, `W1ABC-5`, `N2XY`, `G8BPQ-10`
- **SSID Usage**: No standard convention for node SSIDs
  - Node SSID can be ANY number (0-15), not always -15
  - BBS often -2, RMS often -10, CHAT often -4, but varies by sysop
  - **Authoritative source**: Other nodes' ROUTES tables (consensus)
  - Never assume SSID based on convention - extract from network data

**Gridsquares**: 2 letters (field), 2 digits (square), 2 letters (subsquare)
- Regex: `^[A-R]{2}[0-9]{2}[a-x]{2}$`
- Examples: `FN43hp`, `DM79`, `IO91wm`
- Precision: 6-char (~5x2.5 mi), 4-char (~70x50 mi)

## Nodemap Crawler Constraints
**Authentication**: Only localhost telnet requires auth (username/password)
- Once connected to local node via telnet, all AX.25 NetRom connections inherit auth

**Connection Methods** (in priority order):

**Hop 1 (first hop from localhost):**
1. Direct port: `C PORT CALL-SSID` (requires route_ports entry from local node's ROUTES)
2. NetRom alias: `C ALIAS` (from `call_to_alias` mapping)

**Hop 2+ (subsequent intermediate hops):**
1. Direct port: `C PORT CALL-SSID` (query intermediate node's ROUTES for port number)
2. NetRom alias: `C ALIAS` (from `call_to_alias` mapping)
3. FALLBACK: Query ROUTES at current node to get port number, then use `C PORT CALL-SSID`

**Key insights:**
- Each node's ROUTES table contains everything needed to reach neighbors: `PORT CALL-SSID QUALITY`
- ROUTES can be queried at ANY intermediate node to discover port numbers
- Port numbers ARE valid beyond first hop (unlike what BPQ docs suggest)
- Example at KX1EMA: ROUTES shows `1 WD1O-15 200` → can issue `C 1 WD1O-15`
- NetRom aliases are nice-to-have but not strictly required if ROUTES port info is available

**SSID Selection Standard** (CRITICAL - do not deviate):
1. **CLI-forced SSIDs** (`--force-ssid BASE FULL`) - highest priority, user override
2. **ROUTES consensus** - aggregate `netrom_ssids` from all crawled nodes
   - Each node's ROUTES table shows the SSIDs it uses to reach its neighbors
   - These are the ACTUAL node SSIDs (e.g., KS1R-15), not service SSIDs (KS1R-2 BBS)
   - Consensus = SSID seen by most nodes for a given base callsign
3. **Discovered at connection time** - ROUTES fallback queries intermediate node's ROUTES
- The `alias` field is NOT reliable - it comes from BPQ prompt which may be BBS/RMS/CHAT
- seen_aliases is NOT reliable - counts are equal across all services
- NEVER use SSID number heuristics - there is NO standard for node vs service SSIDs
- ONLY filter SSIDs outside valid range (0, >15) using _is_likely_node_ssid()

**Node Routing Reachability**:
- **Reachable**: Node appears in ANY node's ROUTES table (proof it exists and is routable)
- **Unreachable**: Node ONLY in MHEARD (never in ROUTES) - likely user station or offline
- **Bridging gap**: Even if node lacks NetRom alias, ROUTES fallback allows connection via port numbers

**Path Building**: Uses successful_path from previous crawls
- SSIDs determined from ROUTES consensus across all crawled nodes
- Use NetRom aliases from NODES output when available (faster than ROUTES fallback)
- Query ROUTES at each intermediate hop for port numbers when alias unavailable
- route_ports from localhost's ROUTES only for first-hop direct connections

## Repository Structure
```
bpq-apps/
├── apps/              # User-facing BPQ applications (Python/bash)
├── games/             # Interactive game servers (standalone TCP)
├── utilities/         # Sysop tools for BBS management (cron jobs, maintenance)
├── docs/
│   ├── INSTALLATION.md       # Complete setup guide
│   ├── examples/
│   │   ├── etc/             # inetd.conf, services samples
│   │   └── linbpq/          # bpq32.cfg samples
│   └── images/              # Screenshots, example outputs
└── .github/           # This file (copilot-instructions.md)
```

## Testing
- SSH: ect@ws1ec.mainepacketradio.org -p 4722
- Verify Py3.5.3 compatibility, ASCII output
- WSL terminals required (SSH keys configured, POSIX compatibility)
- Never use PowerShell for SSH or remote commands

## Notification Webhook
Before requesting user testing or executing commands requiring interaction, send notification:

**PowerShell:**
```powershell
Invoke-WebRequest -Method POST -Uri "https://notify.lynwood.us/copilot" -Body "Brief message about what's ready"
```

**Bash/WSL:**
```bash
curl -d "Brief message about what's ready" https://notify.lynwood.us/copilot
```

**When to notify:**
- After changes ready for testing on live node
- Before requesting terminal input or SSH commands
- When awaiting user decision or feedback
