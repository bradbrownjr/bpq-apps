# bpq-apps
Custom applications for a BPQ32 packet radio node, your console, or a terminal. Most applications are written in Python.

## Table of Contents
- [Features](#features)
- [Applications](#applications)
- [Games](#games)
- [Utilities](#utilities)
- [Web Theme for LinBPQ Management Interface](#web-theme-for-linbpq-management-interface)
- [Development](#development)
- [Directory Structure](#directory-structure)
- [Target Environment](#target-environment)

## Features

**🔄 Automatic Updates**: All Python applications include built-in auto-update functionality that checks for new versions on GitHub at startup. Updates are downloaded and installed automatically with a 3-second timeout for reliable operation even when internet connectivity is limited.

**� Emergency Communications Ready**: Designed for ARES (Amateur Radio Emergency Service) and SKYWARN operations where internet access may be unavailable during disasters, severe weather events, or infrastructure failures. All applications prioritize offline resilience with local data caching, ensuring critical information remains accessible when commercial communications are down.

**📡 Offline Capability**: All applications, except where noted, work reliably without internet connectivity. Apps use JSON caching (updated via cron), graceful error handling, and user-friendly messages instead of crashing on network failures.

## Applications

These applications are custom-built for low bandwidth terminal access over packet radio:

* **callout.py** - Test application demonstrating BPQ callsign capture for other apps.
* **dict.py** - Dictionary lookup using dictd server. Simple word definition searches.
* **eventcal.py** - Club calendar displaying upcoming ham radio events from iCalendar feeds. Supports custom feed URLs via eventcal.conf.
* **forms.py** - Fillable forms system for creating formatted messages (ICS-213, radiograms, weather reports, etc.)
* **gopher.py** - Gopher protocol client for accessing gopherspace with text-based navigation. Configurable bookmarks via gopher.conf.
* **hamqsl.py** - HF propagation reports from www.hamqsl.com.  
* **hamtest.py** - Ham radio license test practice with automatic question pool updates.  
* **predict.py** - HF propagation estimator using simplified ionospheric model. Predicts best bands and times for contacts between two locations. Resilient design works online, cached, or fully offline. Supports gridsquare, GPS, DMS, state, country, and callsign input with HamDB lookup integration.
* **qrz3.py** - Look up name, city, state, country of an amateur radio operator with QRZ.com.  
* **rss-news.py** - News feed reader with categorized feeds: News, Science, Technology, Weather, and of course, ham radio topics.  
* **wall.py** - Community bulletin board for one-liner messages. Users can post, view, and delete their own messages.
* **wiki.py** - Wikipedia browser supporting search, article summaries, numbered link navigation, and multiple Wikimedia projects (Wikipedia, Wiktionary, Wikiquote, Wikinews, Wikivoyage). Includes offline caching.
* **space.py** - NOAA Space Weather reports and solar activity data.  
* **sysinfo.sh** - Node system information and BBS service status checker.  
* **wx.py** - Weather reports using National Weather Service API.
* **wx-me.py** - Local weather reports for Southern Maine and New Hampshire.

For detailed documentation, see [apps/README.md](apps/README.md).

### Offline Caching

**Cached Data Applications** (with `--update-cache` cron support):
- **wx.py**: Local weather observations, alerts, and SKYWARN activation status (2-hour cache)
- **rss-news.py**: Emergency bulletins, weather warnings, ham radio news (2-hour cache)
- **hamqsl.py**: HF propagation data for band planning (4-hour cache)
- **space.py**: NOAA space weather reports for HF comms (4-hour cache)
- **eventcal.py**: Club calendar and net schedules (6-hour cache)
- **predict.py**: Callsign lookups with 30-day local cache

**Always-Offline Applications** (no internet required):
- **hamtest.py**: License exam practice with local question pools
- **wall.py**: Community bulletin board (local JSON storage)
- **forms.py**: ICS-213, radiograms, weather reports (local templates)
- **callout.py**: Station information lookup (local data)

**Graceful Degradation** (offline-aware):
- **gopher.py**, **qrz3.py**, **wxnws-ftp.py**: Show "Internet unavailable" messages, continue operating

All apps continue running even if GitHub is unreachable (auto-update fails silently), external APIs are down (uses cached data), or network connectivity is intermittent. See [docs/INSTALLATION.md](docs/INSTALLATION.md) for cron job configuration to keep cached data fresh.

## Games

Interactive games that run as standalone TCP servers:

* **battleship.py** - Classic multiplayer Battleship game with ASCII terminal interface and leaderboard tracking.

See [games/README.md](games/README.md) for game documentation and setup instructions.

## Utilities

Sysop tools for network mapping, mail routing, and service installation:

* **nodemap.py** - Network topology crawler. Discovers packet radio network structure by connecting to nodes via RF and analyzing routing tables. Supports multi-firmware environments (LinBPQ, KPC-3+, FBB, JNOS), resume/merge mode for large networks, adaptive timeouts, and SSID conflict resolution.
* **nodemap-html.py** - Interactive map generator. Reads `nodemap.json` and produces an interactive Leaflet HTML map plus a fully offline SVG vector map with state/county boundaries. Copy `nodemap.html` to your BPQ `HTML/` directory to serve it through the node web interface.
* **mailroute.py** - BBS mail forwarding route analyzer. Reads `nodemap.json` and generates BPQ forwarding configuration recommendations for every reachable BBS — connect scripts, HRoutes/HRoutesP entries, bulletin distribution tree, NTS traffic routing, and FWDAliases.
* **install-dxspider.sh** - Automated DX Spider cluster installer. Sets up a DX Spider spot cluster as a systemd service with a dedicated `sysop` user, Perl dependencies installed via apt, and upstream cluster connectivity configured. Outputs the `bpq32.cfg` snippet needed to register the cluster as a BPQ application.
* **download_boundaries.py** / **map_boundaries.py** - Support files for `nodemap-html.py`'s offline SVG rendering. `download_boundaries.py` fetches Natural Earth 1:10m boundary data and regenerates `map_boundaries.py` if you need updated geographic data.

See [utilities/README.md](utilities/README.md) for detailed documentation and usage examples.

## Web Theme for LinBPQ Management Interface

LinBPQ's management pages (Routes, Nodes, Terminal, Mail, etc.) are generated by the `linbpq` binary — there are no HTML template files to edit. The `html-theme/` directory contains a modern web theme deployed via an **nginx reverse proxy** that injects CSS and JavaScript into every LinBPQ response without touching LinBPQ's configuration or source code. Binary updates cannot overwrite the theme.

### What it does

- **ARES navy/red colour scheme** with automatic light/dark mode and a manual toggle persisted in `localStorage`
- **Grouped navigation** — LinBPQ's flat row of buttons reorganised into three labelled sections: **Node** (Routes, Nodes, Ports, Links, Stats…), **BBS** (WebMail, Terminal, Files), and **Sysop** (Mail/Chat management, config editor, logs)
- **BBS Files browser** at `/files/` — sortable columns, live search filter, subdirectory navigation, backed by nginx's JSON autoindex over your BBS Files directory; no LinBPQ auth required
- **Terminal enhancements** — up/down arrow command history (50 entries), auto-scroll on new output
- **Logo slot** — drop `html-theme/logo.png` in the repo to display your club or ARES section logo in the header
- **HTTPS** via certbot/Let's Encrypt (instructions printed by the deploy script)

### How to deploy

```bash
# From the bpq-apps/ root — uses ws1ec.mainepacketradio.org defaults
./deploy-theme.sh

# Override host / user / SSH port / BBS files path
./deploy-theme.sh -h mynode.example.com -u pi -p 22 -f /home/pi/linbpq/Files

# Push updated CSS/JS only (skip nginx reconfiguration)
./deploy-theme.sh --assets-only
```

The script installs nginx if missing, substitutes host/port placeholders in `bpq-proxy.conf`, SCPs all assets, sets file permissions, and prints the certbot command for HTTPS. Port 80 and 443 must be forwarded to the LinBPQ host; LinBPQ itself stays on its original port (default 9123) with no `bpq32.cfg` changes required.

See [html-theme/README.md](html-theme/README.md) for the full setup guide, colour customisation reference, and terminal selector debugging steps.

## Development

This repository includes [GitHub Copilot instructions](.github/copilot-instructions.md) for AI-assisted development, including the auto-update protocol and coding standards for packet radio applications.

## Directory Structure

```
bpq-apps/
├── apps/              # User-facing BPQ applications
├── games/             # Interactive game servers
├── utilities/         # Sysop tools for BBS management
├── html-theme/        # Modern web theme for the LinBPQ management interface
│   ├── bpq-proxy.conf     nginx reverse proxy config template
│   ├── bpq-modern.css     Stylesheet (CSS custom properties for easy retheming)
│   ├── bpq-terminal.js    Nav grouping, terminal history, theme toggle
│   ├── files-browser.html BBS Files single-page browser
│   └── README.md          Setup and customisation guide
├── docs/              # Documentation and setup guides
│   ├── examples/      # Configuration file examples (inetd, bpq32.cfg)
│   └── images/        # Screenshots and example outputs
├── deploy-theme.sh    # Deploy the web theme to the LinBPQ host
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