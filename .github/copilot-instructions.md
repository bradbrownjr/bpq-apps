# GitHub Copilot Instructions for BPQ Packet Radio Apps

## Context
Packet radio apps for AX.25 networks via linbpq BBS. Target: RPi 3B, Raspbian 9, Python 3.5.3, 1200 baud serial.

## Constraints
- Python 3.5.3 only (no f-strings, async/await, limited type hints)
- ASCII text only (no ANSI, Unicode, control codes)
- Minimal output (1200 baud - every byte counts)
- Stdlib preferred (limited packages available)
- Line-based input, synchronous I/O
- Max 80 char width, no TUI libraries

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
- Include help args (-h, --help, /?) in utilities and CLI tools
- Update both docstring `Version:` and `__version__` variable when bumping versions
- Commit and push changes to GitHub after completing work

## Patterns
- Menu-driven (numeric choices)
- Q&A format for interactive tools
- Column-aligned tables, terse messages
- No colors, progress bars, Unicode, chatty prompts

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
- Direct port connections (C PORT CALL) only valid for first hop from localhost
- Subsequent hops MUST use NetRom routing (C ALIAS) - never "C PORT CALL" after first hop
- Port-specific SSIDs (KC1JMH-7) are for MHEARD tracking, not connection routing

**SSID Selection Standard** (CRITICAL - do not deviate):
1. **CLI-forced SSIDs** (`--force-ssid BASE FULL`) - highest priority, user override
2. **Alias consensus** - aggregate SSIDs from all nodes' own_aliases + seen_aliases (most authoritative)
   - own_aliases: node's self-reported aliases from NODES output
   - seen_aliases: what other nodes report about their neighbors
   - Both contain full SSIDs (KC1JMH-15), unlike routes which use base callsigns
3. **Base callsign only** - if no consensus, strip SSID and let NetRom discovery find it during crawl
4. **MHEARD data (netrom_ssids)** - lowest priority, only to fill gaps, includes transient/port-specific SSIDs
- NEVER use routes table SSIDs - they're base callsigns in JSON, service SSIDs when queried live
- NEVER filter by hardcoded service SSID numbers (-2, -4, -5, -10, etc.) - varies by sysop
- ONLY filter SSIDs outside valid range (0, >15) using _is_likely_node_ssid()
- Service/node distinction determined by data source priority, NOT SSID number

**Path Building**: Uses successful_path from previous crawls
- SSIDs determined from own_aliases/seen_aliases consensus (from NODES output)
- Never assume SSID conventions (BBS=-2, RMS=-10, etc.) - always use consensus or base callsign
- Use NetRom aliases from NODES output for multi-hop connections
- route_ports only for localhost → first hop direct connections

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
- WSL preferred over PowerShell

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
