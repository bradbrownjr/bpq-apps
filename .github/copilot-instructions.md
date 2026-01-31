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
  - **CRITICAL: Both docstring AND VERSION variable must be updated together**
  - Update docstring `Version: X.Y` field in app modules
  - Update `VERSION = "X.Y"` variable (must match docstring exactly to prevent infinite update loops)
  - Update `__version__` variable when present
  - Bump `version` field in .frm JSON form templates
  - **Apps with self-update:** Version bump triggers auto-download on user systems
  - **VERIFY:** Run `grep -n "Version:" appname.py` and `grep -n "^VERSION = " appname.py` to confirm both match before committing
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
- `wall.py`: Caches wall_board.json with timestamps (shows cached messages if fetch fails)
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
                                      |  | +---- Return to node after exit
                                      |  +------ Don't send callsign via stdin
                                      +--------- Host port position
```

**Flag Behavior:**
- `S` flag: Returns user to node prompt after app exits (REQUIRED for interactive apps with pagination/prompts)
- `K` flag: Keeps session alive
- `NOCALL` flag: Prevents BPQ from sending callsign via stdin
- Without `NOCALL`: BPQ sends callsign as first line to stdin
- **Critical:** BPQ32 passes callsign WITH SSID (e.g., `KC1JMH-8`)

**Callsign Handling in Apps:**
- Apps that need callsign: Omit `NOCALL` flag, read callsign from first line of stdin
- Apps must strip SSID if cleaner display needed:
  ```python
  def extract_base_call(callsign):
      """Remove SSID from callsign"""
      return callsign.split('-')[0] if callsign else ""
  ```
- Apps using callsign: wall.py (bulletin board authors), forms.py (form submitter), wx.py (location lookup)
- Apps with `NOCALL`: All others that don't need user identification

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
- Terminal width handling:
  - Separator lines: Fixed 40-character width using dash character: `print("-" * 40)`
  - Longform text (descriptions, content): Adjust dynamically to terminal width with word wrapping
  - Paginate long output (20 lines per page) with prompt
  - Fallback: 80-character width for piped/non-TTY input: `os.get_terminal_size(fallback=(80, 24)).columns`
- **Output buffering**: Flush stdout after status messages that precede blocking operations
  - Pattern: `print("Loading..."); sys.stdout.flush()` then network call
  - Ensures user sees "Loading..." immediately, not after fetch completes
  - Critical on slow packet radio - shows app didn't freeze
  - Example: Before `browser.browse()`, before `urlopen()`, before database queries
- ASCII-only decorative elements - NO Unicode, ANSI codes, or control characters
- No welcome messages - straight to functionality
- Terse but clear prompts and navigation

**ASCII Art Logos**: All main user-facing apps include professional lowercase ASCII art logos
- Generated from asciiart.eu text-to-ascii-art tool
- Lowercase letter designs (modern, polished appearance)
- Implemented using raw strings to handle backslash escaping: `r"ASCII art with \ backslashes"`
- Standard 5-7 line height for consistency
- Examples: wall.py, forms.py, gopher.py, hamtest.py, predict.py, qrz3.py, rss-news.py, space.py, wx-me.py, wx.py

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

**Standard Prompt Ordering** (REQUIRED - consistent design across all apps):
Order commands from furthest to closest scope relative to current page:
1. **Exit scope**: Q)uit (exit app entirely)
2. **Main menu scope**: M)ain (return to main menu)
3. **Parent scope**: B)ack (return to previous page/menu)
4. **Page navigation**: P)age, L)inks, #=follow (navigate within document)
5. **Current content**: Enter=more (advance on current page)

Example pagination prompt:
```
(1/5) [Q)uit M)ain B)ack P)age L)inks #=follow Enter=more] :>
```

Benefits:
- Users scanning left-to-right encounter exit/nav commands first (critical over 1200 baud)
- Prevents accidental re-streaming of large content over slow links
- Consistent everywhere - users learn once, apply everywhere
- Saves bandwidth: Q)uit exits immediately vs navigating back

Implementation notes:
- Apply to ALL interactive prompts in pagination, menus, and dialogs
- Disable unavailable options (e.g., omit Enter=more if at end)
- Maintain ordering even when some options absent (don't rearrange)
- Page menu example: `Select [1-50] Q)uit M)ain B)ack Enter=more :>`
- Content links example: `(#=select Q)uit M)ain B)ack Enter=more) :>`

Historical context:
- **M)enu command** (deprecated - use M)ain instead): When displaying paginated results/menus, include M)enu to redisplay current page
  - Example: `[1-10] M)enu Q)uit :>` allows user to see menu again without navigating
  - Reduces frustration from scrollback limitations on packet radio terminals
  - See wiki.py and gopher.py for reference implementation (legacy pattern - update to M)ain for consistency)

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

**Connection Methods** (priority order):
1. First hop from localhost: `C PORT CALL-SSID` (using local ROUTES) or `C ALIAS` (NetRom)
2. Subsequent hops: Direct port, NetRom alias, or FALLBACK to ROUTES query at current node
3. **Key insight**: Each node's ROUTES table has `PORT CALL-SSID QUALITY` - port numbers work beyond first hop (contrary to BPQ docs)

**SSID Selection** (CRITICAL - do not deviate):
1. CLI-forced SSIDs (`--force-ssid`) - highest priority
2. **ROUTES consensus** - aggregate netrom_ssids from all crawled nodes (these are ACTUAL node SSIDs like KS1R-15, not service SSIDs like KS1R-2 BBS)
3. ROUTES fallback at connection time

**Prohibited SSID sources:**
- ❌ `alias` field (comes from BPQ prompt - may be BBS/RMS/CHAT, not node)
- ❌ `seen_aliases` (equal counts across services)
- ❌ SSID number heuristics (NO standard: node could be -4, -10, -15, anything)
- ✅ Only filter SSIDs outside valid range (0, >15) using `_is_likely_node_ssid()`

**Reachability:**
- Reachable: In ANY node's ROUTES table
- Unreachable: ONLY in MHEARD (never ROUTES) - likely user station or offline

**Path Building**: Uses `successful_path` from previous crawls; determines SSIDs from ROUTES consensus; NetRom aliases preferred when available (faster)

## Repository Structure
```
bpq-apps/
├── apps/              # User-facing BPQ applications (Python/bash)
│   ├── forms/         # .frm JSON form templates (bulletin, ICS-213, radiogram, etc.)
│   ├── predict/       # Ionosphere prediction modules (geo.py, solar.py, regions.json)
│   └── question_pools/  # Ham license test questions (technician, general, extra)
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

## Architecture Overview

**Application Types:**

*1. BPQ Applications (apps/)*:
- Invoked via BPQ32 APPLICATION commands
- inetd pipes stdin/stdout to TCP socket
- Single-instance per user (new process per connection)
- Must handle BPQ callsign via stdin (when S flag set)
- Examples: forms.py, hamtest.py, wx.py, wall.py

*2. TCP Game Servers (games/)*:
- Standalone servers (always-on daemons)
- Multi-user with threading (shared game state)
- Configured in /etc/services + inetd.conf
- No BPQ integration - pure TCP sockets
- Examples: battleship.py (port 23000)

*3. Sysop Utilities (utilities/)*:
- CLI tools (not BPQ applications)
- Run via cron or manual execution
- Export data files (JSON, HTML, SVG)
- Examples: nodemap.py, nodemap-html.py

**Data Flow (BPQ Applications):**
```
User @ RF → BPQ32 Node → Telnet Port 9 → inetd → TCP Socket → Python App
                          (bpq32.cfg)     (services)  (inetd.conf)  (stdin/stdout)
```

**Key Integration Points:**
- `/etc/services`: Maps service names to TCP ports (wx → 63010)
- `/etc/inetd.conf`: Maps ports to executables + user accounts
- `bpq32.cfg`: Maps BPQ commands to services via CMDPORT position numbers
- BPQ S flag: Sends user callsign (WITH SSID) as first line to stdin

## Forms System (.frm Templates)

**Template Structure** (apps/forms/*.frm):
```json
{
  "id": "BULLETIN",
  "title": "Bulletin Message",
  "version": "1.0",
  "description": "Brief description shown in menu",
  "fields": [
    {
      "name": "field_name",
      "label": "Prompt shown to user",
      "type": "text|textarea|yesno|choice|strip",
      "required": true|false,
      "max_length": 100,
      "choices": ["Option 1", "Option 2"],
      "description": "Help text shown during input"
    }
  ]
}
```

**Field Types:**
- `text`: Single-line input (press Enter to finish)
- `textarea`: Multi-line input (type `/EX` on new line to finish)
- `yesno`: Yes/No/NA response (validates Y/N/NA)
- `choice`: Numbered list (validates numeric selection)
- `strip`: Slash-separated format for MARS/SHARES reports

**Form Lifecycle:**
1. forms.py auto-discovers .frm files from GitHub or local cache
2. User selects form from menu
3. App prompts for each field sequentially
4. Validates input (required fields, max length, format)
5. Exports to BPQ message format (`../linbpq/infile`)
6. BPQ auto-imports message to BBS

**Version Bumping**: Increment `version` field in .frm when updating templates (triggers re-download)

## Games Architecture

**Standalone TCP Servers** (different pattern than apps):
- Run as daemon with threading (`python3 battleship.py &`)
- Maintain global game state (clients dict with locks)
- Accept connections: `socket.accept()` in main loop
- Each client gets dedicated thread: `threading.Thread(target=handle_client)`
- Broadcast messages to all connected clients
- Persist leaderboard data to JSON file

**Example Pattern** (battleship.py):
```python
clients = {}  # Global state: {conn: {"name": "KC1JMH", "board": []}}
clients_lock = threading.Lock()

def handle_client(conn, addr):
    with clients_lock:
        clients[conn] = {"name": None, "board": None}
    # Game loop...
    with clients_lock:
        del clients[conn]

# Main loop
while True:
    conn, addr = server_socket.accept()
    threading.Thread(target=handle_client, args=(conn, addr)).start()
```

**inetd.conf entry** (different from apps):
```
battleship  stream  tcp  nowait  ect  /usr/bin/python3  python3 /home/ect/games/battleship.py
```

**Testing**: `telnet localhost 23000` (port from /etc/services)

## Testing
- SSH: `ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org` (lowercase -p for port)
- SCP: `scp -i ~/.ssh/id_rsa -P 4722 file.py ect@ws1ec.mainepacketradio.org:/path/` (uppercase -P for port)
- **Sudo commands over SSH**: Use `-t` flag to force pseudo-terminal allocation for password prompt
  - Example: `ssh -i ~/.ssh/id_rsa -p 4722 -t ect@ws1ec.mainepacketradio.org "sudo command && sudo another_command"`
  - User will be prompted for password interactively
  - Multiple sudo commands can be chained with `&&`
  - Always echo confirmation message at end of command chain
- Verify Py3.5.3 compatibility, ASCII output
- WSL terminals required (SSH keys configured, POSIX compatibility)
- Never use PowerShell for SSH or remote commands

**WS1EC Node Paths:**
- User home: `/home/ect/` (~ expands to this)
- BPQ config: `/home/ect/linbpq/bpq32.cfg`
- Apps directory: `/home/ect/apps/`
- System configs: `/etc/inetd.conf`, `/etc/services`
- Service management: systemd (`sudo systemctl restart linbpq`, `sudo killall -HUP inetd`)

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

## Weather Alert Beacon Integration

**wx.py --beacon**: Generates compact beacon text with weather alerts and SKYWARN status
- Outputs: "WS1EC-15: X WEATHER ALERT(S)! SKYWARN SPOTTERS ACTIVATED. Connect to WX app."
- Uppercase for severe/extreme alerts, lowercase for moderate/minor
- SKYWARN detection: Fetches HWO from NWS FTP, searches for "Weather spotters are encouraged to report"
- Based on code from [skywarn-activation-alerts](https://github.com/bradbrownjr/skywarn-activation-alerts)
- Run via cron: `*/15 * * * * /home/ect/utilities/wx-alert-update.sh >/dev/null 2>&1`
- Writes to `~/linbpq/beacontext.txt` for BPQ beacon inclusion
- Already installed and running on WS1EC node

**Beacon Configuration:**
- Configure via BPQ32 Window menu → Beacon Config, or Web interface → Port Config
- Can also use BPQ REST API: https://wiki.oarc.uk/packet:bpq-api
- Beacon text can include dynamic content from files
- Update beacons programmatically via BPQ32 DLL Interface

**BPQ32 Documentation References:**
- Main documentation index: www.cantab.net/users/john.wiseman/Documents/index.html
- Configuration file format: https://www.cantab.net/users/john.wiseman/Documents/BPQCFGFile.html
- BPQ UI Utilities (built into BPQ32): http://www.cantab.net/users/john.wiseman/Documents/BPQUIUtil.htm
- BPQ32 DLL Interface (beacon control): https://www.cantab.net/users/john.wiseman/Documents/BPQ32DLLInterface.htm
- BPQ REST API documentation: https://wiki.oarc.uk/packet:bpq-api
- Sample configs: https://github.com/pe1rrr/linbpq_rtg/blob/main/bpq32.cfg

## Common Pitfalls & Solutions

**Python 3.5.3 Compatibility:**
- ❌ `f"Hello {name}"` → ✅ `"Hello {}".format(name)`
- ❌ `async def` / `await` → ✅ Synchronous I/O only
- ❌ `typing.List[str]` → ✅ `# type: List[str]` (comment-style type hints)
- ❌ `subprocess.run()` → ✅ `subprocess.Popen()` or `subprocess.check_output()`

**Bandwidth Traps:**
- ❌ Word wrapping at 80 chars → ✅ 40 chars for mobile/old terminals
- ❌ Unicode box drawing → ✅ ASCII dashes/pipes only
- ❌ ANSI color codes → ✅ Plain text (no escape sequences)
- ❌ Verbose menus → ✅ Compressed: `P)ost D)el Q)uit` not `Post, Delete, Quit`

**BPQ Integration Gotchas:**
- SSID handling: BPQ passes `KC1JMH-8` (always strip with `split('-')[0]`)
- CMDPORT positions: 0-indexed (first port is `HOST 0`, second is `HOST 1`)
- inetd user: Must match BPQ user (usually `ect` or `pi`) for file access
- Service restarts: `sudo killall -HUP inetd` after /etc/inetd.conf changes
- Path resolution: Use absolute paths in inetd.conf (`/home/ect/apps/wx.py`)
- **Service naming collision:** Don't name app "dict" (conflicts with standard port 2628). Use "dictionary" or other name in `/etc/services` and inetd.conf. BPQ APPLICATION name can still be DICT, but system service name must differ to avoid port resolution conflicts.

**HOST Port and APPLICATION Number Management** (CRITICAL - prevents conflicts):

When adding a new BPQ application, you MUST:

1. **Check existing HOST assignments:**
   ```bash
   ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org "grep 'HOST [0-9]' ~/linbpq/bpq32.cfg | grep -oP 'HOST \K[0-9]+' | sort -n | uniq"
   ```
   - Find the lowest unused HOST number
   - Common issue: Reusing a HOST number causes wrong app to launch

2. **Verify CMDPORT includes the HOST port:**
   ```bash
   ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org "grep 'CMDPORT' ~/linbpq/bpq32.cfg"
   ```
   - CMDPORT format: `CMDPORT 63000 63010 63020 63030 ...` (increments of 10)
   - HOST 0 = port 63000, HOST 1 = port 63010, HOST 21 = port 63210
   - If HOST number not in CMDPORT: Add port to end of CMDPORT line
   - Missing CMDPORT entry causes "Invalid HOST Port" error

3. **Determine APPLICATION number (must be alphabetical):**
   ```bash
   ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org "grep '^APPLICATION' ~/linbpq/bpq32.cfg | sort -t',' -k2"
   ```
   - List shows existing apps in alphabetical order
   - Find where new app fits alphabetically
   - Use Python script to insert and renumber (see example below)

4. **Insert APPLICATION with Python script:**
   ```python
   # Example: Insert ANTENNA (alphabetically after AI, before BANDS)
   import re
   with open('/home/ect/linbpq/bpq32.cfg', 'r') as f:
       lines = f.readlines()
   
   new_lines = []
   for line in lines:
       # Insert after specific app
       if line.startswith('APPLICATION 3,AI'):
           new_lines.append(line)
           new_lines.append('APPLICATION 4,ANTENNA,C 9 HOST 21 NOCALL K S        ; antenna.py\n')
           continue
       
       # Renumber all apps >= 4 to make room
       match = re.match(r'^APPLICATION (\d+),', line)
       if match:
           num = int(match.group(1))
           if num >= 4:
               line = re.sub(r'^APPLICATION \d+,', 'APPLICATION {},'.format(num+1), line)
       
       new_lines.append(line)
   
   with open('/home/ect/linbpq/bpq32.cfg', 'w') as f:
       f.writelines(new_lines)
   ```

5. **Restart linbpq to apply changes:**
   ```bash
   ssh -i ~/.ssh/id_rsa -p 4722 -t ect@ws1ec.mainepacketradio.org "sudo systemctl restart linbpq"
   ```

**Common Errors:**
- ❌ "Error - Invalid HOST Port" → CMDPORT missing the HOST number
- ❌ Wrong app launches → HOST number conflict with existing app
- ❌ App not in INFO menu → APPLICATION number not sequential or alphabetical

**Checklist for new app:**
- [ ] Find unused HOST number (check existing assignments)
- [ ] Verify CMDPORT includes that HOST port (add if missing)
- [ ] Determine correct APPLICATION number (alphabetical order)
- [ ] Use Python script to insert and renumber APPLICATIONs
- [ ] Restart linbpq
- [ ] Test via BPQ INFO menu and app command

**Auto-Update Implementation:**
- **VERSION variable must match docstring version exactly** - mismatch causes infinite update loop (CRITICAL)
- Must use atomic writes (write to temp, then rename)
- Must preserve executable permissions: `os.chmod(script_path, current_mode)`
- Must cleanup temp files on failure: `try/finally` with `os.remove(temp_path)`
- Version comparison: Parse as tuples `(1, 2, 3)` for proper numeric comparison
- Timeout: Hardcode to 3 seconds (never configurable - user frustration)
- **Before committing version bumps, verify:** `grep "Version:" appname.py` matches `grep "^VERSION = " appname.py`

**Network Resilience:**
- Always wrap external API calls in `try/except` with timeout
- Use `socket.create_connection('8.8.8.8', 53)` for internet check (not HTTP)
- Cache data locally with timestamps (JSON files in app directory)
- Show "Internet unavailable" not technical errors when offline
- Never block startup on network checks (fail silently)

## Development Workflows

**Creating New App:**
1. Copy template from existing app (e.g., space.py for simple, forms.py for complex)
2. Update docstring: `Version: 1.0`, author, date, description
3. Add `check_for_app_update()` and `compare_versions()` functions
4. Design ASCII logo (lowercase, 5-7 lines, asciiart.eu)
5. Implement menu structure with compressed prompts
6. Add to `/etc/services` with new TCP port (63000+ range)
7. Add to `/etc/inetd.conf` with executable path
8. **CRITICAL:** Follow "HOST Port and APPLICATION Number Management" section:
   - Check existing HOST assignments, find unused number
   - Verify CMDPORT includes that HOST port (add if missing)
   - Use Python script to insert APPLICATION alphabetically and renumber
9. Test: `telnet localhost PORT` then live on RF
10. Document in apps/README.md and CHANGELOG.md

**Testing Checklist:**
- [ ] Python 3.5.3 compatible (no f-strings, async/await)
- [ ] ASCII-only output (no Unicode, ANSI codes)
- [ ] 40-char terminal width handling
- [ ] Offline operation (internet check + graceful fallback)
- [ ] Auto-update functionality (3-second timeout)
- [ ] BPQ callsign handling (strip SSID if needed)
- [ ] Help text: `-h`, `--help`, `/?`
- [ ] Version bumping in docstring
- [ ] CHANGELOG.md entry
- [ ] README.md documentation

**Deploying to WS1EC:**
```bash
# SCP file to node (uppercase -P for port)
scp -i ~/.ssh/id_rsa -P 4722 appname.py ect@ws1ec.mainepacketradio.org:/home/ect/apps/

# Make executable
ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org "chmod +x /home/ect/apps/appname.py"

# Add service and inetd entry with sudo (use -t flag for interactive password prompt)
ssh -i ~/.ssh/id_rsa -p 4722 -t ect@ws1ec.mainepacketradio.org "sudo sed -i '\$ a appname        PORT/tcp       # Description' /etc/services && sudo bash -c \"echo 'appname  stream  tcp  nowait  ect  /home/ect/apps/appname.py  appname.py' >> /etc/inetd.conf\" && sudo killall -HUP inetd && echo 'Services configured'"

# Add APPLICATION to bpq32.cfg
ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org "sed -i '/^APPLICATION [0-9]*,/a APPLICATION X,APPNAME,C 9 HOST X S K,WS1EC-6,CCEDX,255' ~/linbpq/bpq32.cfg"

# Or manual deployment via interactive SSH:
ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org
cd ~/apps
wget -O appname.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/appname.py
chmod +x appname.py

# Restart services (requires sudo password)
sudo killall -HUP inetd

# Restart BPQ if bpq32.cfg changed (requires sudo password)
sudo systemctl restart linbpq
```

**Git Workflow:**
```bash
# Make changes
git add .
git commit -m "feat(app): brief description"
git push origin main

# Version bump triggers auto-download on user systems within 24-48 hours
```
