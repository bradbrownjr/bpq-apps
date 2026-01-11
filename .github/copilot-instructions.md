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

## Patterns
- Menu-driven (numeric choices)
- Q&A format for interactive tools
- Column-aligned tables, terse messages
- No colors, progress bars, Unicode, chatty prompts

## Repository Structure
```
bpq-apps/
├── apps/              # User-facing BPQ applications (Python/bash)
├── games/             # Interactive game servers (standalone TCP)
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
