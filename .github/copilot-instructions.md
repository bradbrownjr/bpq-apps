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

## Patterns
- Menu-driven (numeric choices)
- Q&A format for interactive tools
- Column-aligned tables, terse messages
- No colors, progress bars, Unicode, chatty prompts

## Amateur Radio Formats
**Callsigns**: 1-2 prefix letters, digit, 1-3 suffix letters, optional -SSID (0-15)
- Regex: `^[A-Z]{1,2}\d[A-Z]{1,3}(?:-\d{1,2})?$`
- Examples: `KC1JMH`, `W1ABC-5`, `N2XY`, `G8BPQ-10`

**Gridsquares**: 2 letters (field), 2 digits (square), 2 letters (subsquare)
- Regex: `^[A-R]{2}[0-9]{2}[a-x]{2}$`
- Examples: `FN43hp`, `DM79`, `IO91wm`
- Precision: 6-char (~5x2.5 mi), 4-char (~70x50 mi)

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
