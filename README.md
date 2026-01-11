# bpq-apps
Custom applications for a BPQ32 packet radio node

Here are some custom applications I am working on for my
local packet radio node, which runs on a Raspberry Pi B+
running John Wiseman's linbpq32 downloadable from:
https://www.cantab.net/users/john.wiseman/Documents/Downloads.html

## Applications

These applications are custom-built for low bandwidth terminal access over packet radio:

* **gopher.py** - Gopher protocol client for accessing gopherspace with text-based navigation. It's like the Internet, but for terminals!  
* **hamqsl.py** - HF propagation reports from www.hamqsl.com.  
* **hamtest.py** - Ham radio license test practice with automatic question pool updates.  
* **qrz3.py** - Look up name, city, state, country of an amateur radio operator with QRZ.com.  
* **rss-news.py** - News feed reader with categorized feeds: News, Science, Technology, Weather, and of course, ham radio topics.  
* **space.py** - NOAA Space Weather reports and solar activity data.  
* **sysinfo.sh** - Node system information and BBS service status checker.  
* **wx-me.py** - Local weather reports for Southern Maine and New Hampshire.  
* **forms.py** - Fillable forms system for creating formatted messages (ICS-213, radiograms, weather reports, etc.)

For detailed documentation, see [apps/README.md](apps/README.md).

## Games

Interactive games that run as standalone TCP servers:

* **battleship.py** - Classic multiplayer Battleship game with ASCII terminal interface and leaderboard tracking.

See [games/README.md](games/README.md) for game documentation and setup instructions.

## Getting Started

1. **Installation**: See [docs/INSTALLATION.md](docs/INSTALLATION.md) for complete setup instructions
2. **Configuration Examples**: Check [docs/examples/](docs/examples/) for inetd and bpq32.cfg configuration samples
3. **Application Details**: Browse [apps/README.md](apps/README.md) for individual app documentation

## Directory Structure

```
bpq-apps/
├── apps/              # User-facing BPQ applications
├── games/             # Interactive game servers
├── utilities/         # Sysop tools for BBS management
├── docs/              # Documentation and setup guides
│   ├── examples/      # Configuration file examples (inetd, bpq32.cfg)
│   └── images/        # Screenshots and example outputs
└── .github/           # GitHub Copilot instructions for AI development
```

## Target Environment

- **Hardware**: Raspberry Pi 3B or similar
- **OS**: Raspbian GNU/Linux 9 (stretch) or later
- **Python**: 3.5+ (designed for 3.5.3 compatibility)
- **Network**: AX.25 packet radio @ 1200 baud, ASCII-only interface
- **BPQ**: linbpq32 BBS software

## Contributing

This repository is optimized for AI-assisted development using GitHub Copilot. See [.github/copilot-instructions.md](.github/copilot-instructions.md) for development guidelines and constraints.

## License

See [LICENSE](LICENSE) file for details.