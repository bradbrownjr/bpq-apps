# bpq-apps
Custom applications for a BPQ32 packet radio node

## Table of Contents
- [Features](#features)
- [Applications](#applications)
- [Games](#games)
- [Utilities](#utilities)
- [Installation](#installation)
- [Development](#development)

## Features

**🔄 Automatic Updates**: All Python applications include built-in auto-update functionality that checks for new versions on GitHub at startup. Updates are downloaded and installed automatically with a 3-second timeout for reliable operation even when internet connectivity is limited.

Here are some custom applications I am working on for my
local packet radio node, which runs on a Raspberry Pi B+
running John Wiseman's linbpq32 downloadable from:
https://www.cantab.net/users/john.wiseman/Documents/Downloads.html

## Applications

These applications are custom-built for low bandwidth terminal access over packet radio:

* **callout.py** - Test application demonstrating BPQ callsign capture for other apps.
* **forms.py** - Fillable forms system for creating formatted messages (ICS-213, radiograms, weather reports, etc.)
* **gopher.py** - Gopher protocol client for accessing gopherspace with text-based navigation. It's like the Internet, but for terminals!  
* **hamqsl.py** - HF propagation reports from www.hamqsl.com.  
* **hamtest.py** - Ham radio license test practice with automatic question pool updates.  
* **qrz3.py** - Look up name, city, state, country of an amateur radio operator with QRZ.com.  
* **rss-news.py** - News feed reader with categorized feeds: News, Science, Technology, Weather, and of course, ham radio topics.  
* **space.py** - NOAA Space Weather reports and solar activity data.  
* **sysinfo.sh** - Node system information and BBS service status checker.  
* **wx.py** - Weather reports using National Weather Service API.
* **wx-me.py** - Local weather reports for Southern Maine and New Hampshire.
* **wxnws-ftp.py** - NWS weather product downloader via FTP.

For detailed documentation, see [apps/README.md](apps/README.md).

## Games

Interactive games that run as standalone TCP servers:

* **battleship.py** - Classic multiplayer Battleship game with ASCII terminal interface and leaderboard tracking.

See [games/README.md](games/README.md) for game documentation and setup instructions.

## Utilities

Sysop tools for BBS management and network monitoring:

* **nodemap.py** - Advanced network topology crawler with intelligent staleness detection. Discovers packet radio network structure by connecting to nodes via RF, analyzing routing tables and neighbor lists. Features resume capability for large networks, adaptive timeouts, and multi-operator data merging for comprehensive coverage.

**Recommended Commands:**
```bash
# Initial crawl
./nodemap.py 10 -v -l traffic.log -n https://notify.lynwood.us/packet

# Resume interrupted crawl (recommended for large networks)
./nodemap.py --resume -v -l traffic.log -n https://notify.lynwood.us/packet

# Merge multiple operator perspectives
./nodemap.py -m remote_*.json
```

See [utilities/README.md](utilities/README.md) for detailed documentation.

## Installation

All applications feature automatic updates and can be installed with simple wget commands:

```bash
# Download any application
wget https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/[script-name].py
chmod +x [script-name].py

# Example: Install forms application
wget -O forms.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/forms.py
chmod +x forms.py
```

**Complete Setup**: See [docs/INSTALLATION.md](docs/INSTALLATION.md) for detailed installation and BPQ configuration instructions.

## Development

This repository includes [GitHub Copilot instructions](.github/copilot-instructions.md) for AI-assisted development, including the auto-update protocol and coding standards for packet radio applications.

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