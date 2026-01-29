# bpq-apps
Custom applications for a BPQ32 packet radio node, your console, or a terminal. Most applications are written in Python.

## Table of Contents
- [Features](#features)
- [Applications](#applications)
- [Games](#games)
- [Utilities](#utilities)
- [Installation](#installation)
- [Development](#development)

## Features

**🔄 Automatic Updates**: All Python applications include built-in auto-update functionality that checks for new versions on GitHub at startup. Updates are downloaded and installed automatically with a 3-second timeout for reliable operation even when internet connectivity is limited.

**� Emergency Communications Ready**: Designed for ARES (Amateur Radio Emergency Service) and SKYWARN operations where internet access may be unavailable during disasters, severe weather events, or infrastructure failures. All applications prioritize offline resilience with local data caching, ensuring critical information remains accessible when commercial communications are down.

**📡 Offline Capability**: All applications, except where noted, work reliably without internet connectivity. Apps use JSON caching (updated via cron), graceful error handling, and user-friendly messages instead of crashing on network failures.

## Applications

These applications are custom-built for low bandwidth terminal access over packet radio:

* **callout.py** - Test application demonstrating BPQ callsign capture for other apps.
* **dict.py** - Dictionary lookup using dictd server. Simple word definition searches.
* **eventcal.py** - Club calendar displaying upcoming ham radio events from iCalendar feeds. Supports custom feed URLs via eventcal.conf.
* **feed.py** - Classic BBS-style community bulletin board (legacy version - see wall.py for enhanced version).
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
* **wxnws-ftp.py** - NWS weather product downloader via FTP.

For detailed documentation, see [apps/README.md](apps/README.md).

## Games

Interactive games that run as standalone TCP servers:

* **battleship.py** - Classic multiplayer Battleship game with ASCII terminal interface and leaderboard tracking.

See [games/README.md](games/README.md) for game documentation and setup instructions.

## Utilities

Sysop tools for BBS management and network monitoring:

* **nodemap.py** - Advanced network topology crawler with intelligent staleness detection. Discovers packet radio network structure by connecting to nodes via RF, analyzing routing tables and neighbor lists. Features resume capability for large networks, adaptive timeouts, and multi-operator data merging for comprehensive coverage.

See [utilities/README.md](utilities/README.md) for detailed documentation.

## Offline Caching

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

All apps continue running even if:
- GitHub is unreachable (auto-update fails silently)
- External APIs are down (uses cached data or shows offline message)
- Network connectivity is intermittent (retries without crashing)
- Config files are missing (uses sensible defaults)

**Setting Up Offline Caching**: See [docs/INSTALLATION.md](docs/INSTALLATION.md) for cron job configuration to keep cached data fresh (typically every 2-6 hours).

## Quick Installation

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