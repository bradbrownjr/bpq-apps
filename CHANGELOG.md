# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]
### Changed
- **Rebranded Feed to Wall**: `feed.py` renamed to `wall.py` for better description of community message wall functionality
  - Updated all configuration examples (bpq32.cfg, /etc/services)
  - Renamed data file from `feed_board.json` to `wall_board.json`
  - Updated documentation and examples throughout repository
  - Application name in BPQ changed from FEED to WALL

## [install-dxspider.sh 1.0] - 2026-01-24
### Added
- **DX Spider Cluster Installer**: Automated installation script for LinBPQ nodes
  - Validates root/sudo early and exits with clear error if not elevated
  - Installs Perl dependencies via apt (no CPAN, compatible with Raspbian 9)
  - Creates isolated `sysop` user and `spider` group for process separation
  - Clones DX Spider from official git repository
  - Configures DXVars.pm, Listeners.pm, and upstream connection scripts
  - Sets up dual upstream clusters (dxc.nc7j.com, w3lpl.net) for spot sharing
  - Creates systemd service with auto-restart on failure
  - Appends to /etc/services and /etc/inetd.conf automatically
  - Reloads inetd after configuration
  - Outputs BPQ32 configuration snippet for manual merge
  - Configurable via variables at top of script (callsign, location, upstreams)

## [dict.py 1.6] - 2026-01-24
### Fixed
- **Python 3.5.3 Compatibility**: `os.get_terminal_size()` doesn't accept `fallback` parameter
  - Wrapped in try/except to catch OSError when no TTY (inetd/telnet)
  - Falls back to 80-char width for non-TTY connections
  - App was crashing immediately on startup via BPQ

## [dict.py 1.5] - 2026-01-24
### Fixed
- **Terminal Width Detection**: Removed exception handler that forced 40-char width
  - Now properly uses 80-char fallback when running via inetd/telnet
  - Exception handler was catching failures and overriding fallback parameter
  - Dictionary definitions now display at full width instead of squished 40 chars

## [dict.py 1.4] - 2026-01-24
### Changed
- **Dynamic Terminal Width**: Output now wraps at detected terminal width instead of fixed 40 chars
  - Word wrapping respects terminal boundaries (80+ columns on desktop, 40 on mobile)
  - Fallback to 80 chars for piped/non-TTY input
- **Pagination Added**: Long definitions now paginate every 20 lines
  - Prompt: "(press Enter, Q to quit)" between pages
  - Prevents flooding terminal with long dictionary entries
  - User can quit mid-definition to return to word prompt

## [dict.py 1.3] - 2026-01-24
### Fixed
- **Display Issues via Telnet/BPQ**: Fixed `()` appearing instead of blank lines
  - Replaced `print()` with `print("")` to avoid repr display
  - Changed from `raw_input()` to explicit `sys.stdout.write()` + `sys.stdin.readline()`
  - Ensures prompt displays immediately before reading input
  - All output now properly formatted for telnet/BPQ connections

## [dict.py 1.2] - 2026-01-24
### Fixed
- **Output Buffering**: Added `sys.stdout.flush()` after all print statements
  - Python buffers stdout when running via inetd TCP sockets
  - App would connect but display nothing until user disconnected
  - Now flushes output immediately for real-time display

## [dict.py 1.1] - 2026-01-24
### Fixed
- **Python 3.5.3 Compatibility**: Replaced `subprocess.check_output(timeout=X)` with `Popen().communicate()`
  - `check_output` timeout parameter not available in Python 3.5.3
  - Removed `subprocess.TimeoutExpired` exception (doesn't exist in 3.5.3)
  - Now uses Popen with communicate() for proper compatibility
- **BPQ Configuration**: Removed `S` flag from APPLICATION line (conflicts with NOCALL)
  - Correct: `APPLICATION X,DICT,C 9 HOST 15 NOCALL K`
  - App was blocking on stdin waiting for callsign that never arrived
- **Service Name Conflict**: Must use unique service name in /etc/services
  - Standard dictd uses `dict` on port 2628
  - BPQ app should use `bpqdict` on port 63160 to avoid collision

## [dict.py 1.0] - 2026-01-24
### Added
- **New Application**: Dictionary lookup using Linux 'dict' command
  - Simple word definition searches via dictd server
  - ASCII art logo optimized for packet radio
  - NOCALL flag (no callsign authentication required)
  - Graceful handling if dict command not installed
  - Auto-update functionality with 3-second GitHub timeout
  - 40-character terminal width support
  - BPQ32 configuration: `APPLICATION X,DICT,C 9 HOST 16 NOCALL K S`
  - Requires: `sudo apt-get install dictd dict`

## [eventcal.py 2.3] - 2026-01-23
### Fixed
- **Auto-Update Path Bug**: Update wrote to current directory instead of script location
  - Used relative `script_name` instead of `os.path.abspath(__file__)`
  - Update would silently fail when running from different directory
  - Now correctly updates the actual script file and exits for restart

## [eventcal.py 2.2] - 2026-01-23
### Fixed
- **Double-Entry Bug**: Every input required entering twice before being acted upon
  - Root cause: `main()` called `display_events()` then immediately called `main_menu()`
    which called `display_events()` again, discarding the first user input
  - User would type "1", menu would reprint, user had to type "1" again
  - On 1200 baud, this wasted 2-3 seconds of bandwidth per interaction

## [eventcal.py 2.1] - 2026-01-23
### Fixed
- **Location Display Corruption**: Fixed "04\r062" showing as split lines
  - Root cause: iCal CRLF line endings left `\r` in parsed data
  - Solution: Strip all `\r` before processing line continuations
- **Description Display Corruption**: Fixed "visi t", "o perator", "gaps\ ," artifacts
  - Root cause: Same CRLF issue affecting multi-line description fields
  - Now properly joins line continuations without embedded carriage returns
- **iCal Escaped Newlines**: Converted `\n` literals to actual newlines in descriptions

## [eventcal.py 2.0.1] - 2026-01-23
### Fixed
- **DTSTART Parsing Bug**: Fixed date parsing for DTSTART without TZID parameter
  - Resolves missing Winter Field Day 2026-01-24 event
  - Now correctly handles `DTSTART:20260124T150000Z` format (Z suffix without TZID)
  - Parse now handles all three formats: Z suffix, DATE-only, and TZID
- **Deleted Conflicting calendar.py**: Old file caused import conflict with Python stdlib
- **Event Count**: Increased from 141 to 224 with proper parsing of all events

## [eventcal.py 2.0] - 2026-01-23
### Added
- **Recurring Event Support**: Parses RRULE and expands monthly recurring events
  - Supports `FREQ=MONTHLY;BYDAY=nTH` format (nth weekday of month)
  - Expands events 2 years back and 1 year forward
  - Shows all three monthly meetings: Business (2nd Thu), On-Air (3rd Thu), ECT (4th Thu)
- **Next Event Marker**: Shows `<` indicator on the next upcoming event in All Events view

### Fixed
- **iCal Line Continuations**: Properly handles multi-line iCal fields (v1.9)
- **Page Navigation**: All Events starts at today's page, allows P)rev to browse history

## [eventcal.py 1.8] - 2025-01-28
### Fixed
- **Main Menu Detail Selection**: Pressing event number now correctly shows event details
- **All Events View**: Now shows ALL events (historical and future) instead of filtering from today
- **Description Display**: Multi-paragraph descriptions now display fully with proper line breaks
- **Location Alignment**: Fixed indentation consistency with date lines
- **HTML Entity Decoding**: Added common HTML entity conversion (&amp;, &lt;, &gt;, &nbsp;)
- **Escaped Newlines**: Properly converts `\n` sequences in iCal description fields

### Roadmap
- **Weather Alert Beacons**: Currently blocked by BPQ API limitations
  - LinBPQ HOST interface does not support UI frame transmission
  - BPQ REST API does not have beacon endpoints
  - Only option is modifying bpq32.cfg BTEXT (requires config rewrites)
  - Waiting for BPQ API enhancement or LinBPQ HOST protocol documentation
  - See: https://wiki.oarc.uk/packet:bpq-api

## [wx.py 4.2] - 2026-01-22
### Added
- **Beacon Text Generation**: New `--beacon` option for BPQ beacon integration
  - Outputs compact weather alert status: "WS1EC-15: X WEATHER ALERT(S)!"
  - Uppercase for severe/extreme alerts, lowercase for moderate/minor
  - **SKYWARN Spotter Activation Detection**: Checks HWO for spotter requests
    - Searches for "Weather spotters are encouraged to report" phrase
    - Displays "SKYWARN SPOTTERS ACTIVATED" in beacon when active
    - Based on code from skywarn-activation-alerts repository
  - Directs users to connect to WX app for full details
  - Run via wx-alert-update.sh cron job (updates every 15 minutes)
  - Writes to ~/linbpq/beacontext.txt for BPQ beacon inclusion

### Changed
- **CTEXT Simplification**: Removed @ file directive (displayed literal path)
  - CTEXT returns to simple logo + location + menu format
  - Weather alerts now distributed via beacon instead of connection banner

## [wx.py 4.1] - 2026-01-22
### Added
- **CTEXT Local Weather Alert Display**: Shows current alert status on node connection banner
  - New `--alert-summary` CLI option outputs one-line alert summary for CTEXT integration
  - Displays alert count and severity breakdown (Extreme, Severe, Moderate, Minor)
  - Example: "Local Weather: 2 alerts (1S 1M)"
  - Run via cron with utilities/wx-alert-update.sh (every 15-30 minutes)
  - BPQ32 CTEXT includes alert file via `@/home/ect/linbpq/wx-alert.txt`
- **Alert Reference Markers**: Reports menu now shows asterisks (*) next to reports containing alert details
  - Options 4, 5, 9, 10, 11, 12 marked with * (Active Alerts, HWO, Winter Weather, Heat/Cold, Fire Weather, River/Flood)
  - Legend added to menu: "* Alert details may be found here"
  - Helps users quickly find detailed information about active alerts

### Fixed
- **BPQ32 Configuration**: Removed NOCALL flag from WX and FORMS applications
  - Both apps read callsigns via stdin (WX uses select(), FORMS reads directly)
  - Without NOCALL, apps properly receive user callsigns for personalization
  - TEST/hamtest.py correctly retains NOCALL (no callsign handling)

## [wx.py 4.0] - 2026-01-22
### Fixed
- **Winter Weather Report**: Replaced 30-line truncation with 20-line pagination
  - Displays full winter weather product without cutting off content
  - Pagination prompt: "Press enter for more, Q to quit"
  - User can quit early with Q or page through entire report
- **FEED Application Authentication**: Removed NOCALL flag from FEED app configuration
  - App now properly receives callsigns for bulletin board author tracking
  - BPQ32 APPLICATION line changed from "NOCALL K S" to "K S" only

## [wx.py 3.8] - 2026-01-22
### Fixed
- **Pagination UX**: When quitting from paginated reports (HWO, RWS) with Q, no longer prompts "Press enter to continue..."
  - User already indicated they're done by pressing Q - extra prompt was redundant
  - Applies to Hazardous Weather Outlook and Regional Weather Summary
  - Returns directly to menu after Q without additional interaction

## [wx.py 3.7] - 2026-01-22
### Added
- **Regional Weather Summary (Option 7)**: Replaced Area Forecast Discussion with narrative weather overview
  - Pulls from NWS `/products/types/RWS` endpoint
  - Provides practical weather advice (preparation, safety, frostbite warnings, driving conditions)
  - More user-friendly than technical AFD forecaster discussion
  - 20-line pagination with Q to quit
  - Preserves blank lines for readability
  - Based on wx-me.py implementation feedback
### Changed
- Menu option 7: "Area Forecast Discussion" → "Regional Weather Summary"

## [calendar.py 1.0] - 2026-01-22
### Added
- New application: Club calendar event viewer
- Fetches and displays events from iCalendar (.ics) URLs
- First-run configuration prompt for iCal URL
- View upcoming events (next 90 days) or all events
- Displays event date/time, location, and full description
- Handles multi-day events, all-day events, and timed events
- Text wrapping adjusts to terminal width (40-char fallback)
- Refresh calendar functionality
- Internet availability detection with graceful offline handling
- Automatic update functionality
- ASCII-only output optimized for packet radio
- BPQ32 APPLICATION line compatible
- Configuration stored in calendar.conf (JSON format)

## [wx.py 3.6] - 2026-01-22
### Fixed
- **Hazardous Weather Outlook (Option 5)**: Complete rewrite of display formatting
  - Removed 1000 character limit - now displays full HWO product
  - Preserves original blank lines between sections for readability
  - Added pagination: displays 20 lines at a time with "Press ENTER to continue or Q to quit" prompt
  - Matches formatting of raw NWS text products (FTP format)
- **Loading messages**: Fixed buffered output causing delayed display
  - Added `sys.stdout.flush()` to force immediate display before API calls
  - Changed to carriage return (`\r`) so loading message is overwritten by report
  - Critical for packet radio where users need immediate feedback

## [wx.py 3.5] - 2026-01-22
### Changed
- **API timeouts**: Increased all NWS API call timeouts from 3-5 seconds to 10 seconds
  - Improves reliability on slow or congested network connections
  - Reduces timeout errors on slower packet radio links
  - Auto-update check remains at 3 seconds (fast GitHub CDN)
- **User feedback**: Added "Loading..." messages to all report functions
  - Shows "Loading forecast...", "Loading observations...", etc. before API calls
  - Critical for 1200 baud packet radio where delays can seem like freezes
  - Prevents users from thinking the system is unresponsive

## [wx.py 3.4] - 2026-01-22
### Fixed
- **Menu choice 13 (Coastal Flood Info)**: Now works for all locations (not just coastal)
  - Non-coastal locations show "No coastal forecast available" message
  - Prevents "Invalid choice" error for inland users
- **Hazardous Weather Outlook**: Fixed timeout issue preventing HWO display
  - Increased product fetch timeout from 3 to 10 seconds
  - NWS products API can be slow to respond for individual product fetches
  - HWO now reliably displays when available

## [wx.py 3.3] - 2026-01-22
### Fixed
- **Hourly forecast (Option 2)**: Added error handling and "Press enter" prompt when no data available
- **Area Forecast Discussion (Option 7)**: Now uses NWS products API (/products/types/AFD) instead of headlines
  - Headlines endpoint no longer returns AFD reliably
  - Products API provides consistent access to latest AFD product
- **Hazardous Weather Outlook (Option 5)**: Expanded content display from 400 to 1000 characters
  - Shows full HWO text instead of truncated summary
  - Better header parsing (skips first 2 lines instead of 3)
- **Winter Weather (Option 9)**: Improved formatting with intelligent section parsing
  - Skips header codes (000, WWUS41, etc.)
  - Adds spacing before section markers (lines starting with "...")
  - Displays up to 30 lines instead of 25
- **Menu numbering**: Fixed missing Option 13 (Coastal Flood Info)
  - Now always displays in menu with "(N/A)" indicator for non-coastal locations
  - Prevents confusing gap in numbering (12→14)
- **User experience**: Added "Press enter to continue..." prompt to all empty reports
  - Affected: Active Alerts, Heat/Cold Advisories, River/Flood, Fire Weather, Dust, UV, AFD, PoP, Climate, Zone, HWO, Hourly
  - Prevents rapid menu return that could confuse users into thinking report failed

## [wx.py 3.2] - 2026-01-22
### Added
Major expansion using NWS API capabilities discovered via official documentation:
- **Hourly Forecast (12hr)**: Option 2 - Hour-by-hour forecast with temp, conditions, wind for next 12 hours
- **Zone Forecast Product (ZFP)**: Option 6 - Detailed narrative forecast from NWS forecasters
- **Winter Weather Warnings**: Option 9 - Winter storm warnings, watches, and advisories (WSW product)
- **Daily Climate Report (CLI)**: Option 16 - Temperature records, normals, departures, precipitation data
- Proper User-Agent headers for all NWS API requests (required per API guidelines)
### Changed
- Menu expanded from 11 to 16 reports with reorganized layout
- Reorganized menu by priority: immediate conditions (1-3), safety/alerts (4-5), detailed forecasts (6-8), seasonal/situational (9-14), reference (15-16)
- Updated docstring with comprehensive NWS API endpoint documentation
- HWO now uses correct NWS products API endpoint (products/types/HWO)
### Fixed
- Hazardous Weather Outlook now properly fetches from NWS products API with ICAO WFO code conversion

## [wx.py 3.1] - 2026-01-22
### Added
Major expansion using NWS API capabilities discovered via official documentation:
- **Hourly Forecast (12hr)**: Option 2 - Hour-by-hour forecast with temp, conditions, wind for next 12 hours
- **Zone Forecast Product (ZFP)**: Option 5 - Detailed narrative forecast from NWS forecasters
- **Winter Weather Warnings**: Option 7 - Winter storm warnings, watches, and advisories (WSW product)
- **Daily Climate Report (CLI)**: Option 13 - Temperature records, normals, departures, precipitation data
- Proper User-Agent headers for all NWS API requests (required per API guidelines)
### Changed
- Menu expanded from 11 to 16 reports with reorganized layout
- Reorganized menu for logical grouping: forecasts (1-5), hazards (6-9), specialized (10-16)
- Updated docstring with comprehensive NWS API endpoint documentation
- HWO now uses correct NWS products API endpoint (products/types/HWO)
### Fixed
- Hazardous Weather Outlook now properly fetches from NWS products API with ICAO WFO code conversion

## [wx.py 3.1] - 2026-01-22
### Added
- **Precipitation, snowfall, ceiling height**: Added three weather measurements to current observations (display only when non-zero)
  - Quantitative Precipitation: millimeters converted to inches
  - Snowfall Amount: centimeters converted to inches
  - Ceiling Height: meters converted to feet (useful for VHF propagation planning)
- **Hazardous Weather Outlook (HWO)**: New report (Option 4) pulling from NWS office headlines
  - Provides early warnings for potential weather hazards
  - Available when activated by forecast office
  - Appears between Fire Weather Outlook and Heat/Cold Advisories
### Changed
- Menu expanded from 11 to 12 reports
- Report numbering: Fire Weather (3), Hazardous Outlook (4), Heat/Cold (5), River/Flood (6), Coastal (7), AFD (8), PoP (9), UV (10), Dust (11), Alerts (12)
- Conversion functions added: mm_to_inches(), cm_to_inches(), meters_to_feet()

## [wx.py 3.0] - 2026-01-22
### Added
- **Wind gust speed**: Added peak wind speed to current observations (useful for radio antenna/tower safety planning)
- **Wind chill**: Added computed wind chill temperature to current observations (important for winter field operations and emergency planning)
- **Relative humidity**: Added humidity percentage to current observations (better indicator of comfort/conditions than dew point)
### Changed
- Current observations now extract wind gust and humidity from NWS station data
- Wind chill extracted from NWS gridpoint data (more reliable than station-reported values)
- Wind display format updated: "Wind: 12 mph gust 26 mph from W" (includes gust when available)

## [wx.py 2.9] - 2026-01-22
### Removed
- **Removed pollen forecast (Option 10)**: pollen.com API blocks requests with HTTP 405. Investigated alternatives:
  - NWS weather.gov API does not provide pollen data
  - Free pollen APIs either blocked or require API keys
  - Decision: Remove broken feature rather than depend on external APIs
- Pollen forecast function now returns None (gracefully disabled)
- Menu reduced from 12 to 11 reports (pollen removed, other options unchanged)
### Note
- Packet radio users prioritize immediate weather conditions (7-day, observations, alerts) over pollen
- Pollen data remains available through pollen.com website if needed

## [wx.py 2.8] - 2026-01-22
### Fixed
- **Fixed 7-day forecast temperature display**: NWS forecast endpoint returns temperature already in Fahrenheit, not Celsius. Version 2.7 was incorrectly converting F→C→F, resulting in wrong temps (20F displayed as 68F). Now displays temperatures as-is from NWS.
- Wind data in 7-day forecast also already formatted (e.g., "5 mph", "S") - no conversion needed

## [wx.py 2.7] - 2026-01-22
### Changed
- **Converted weather display to imperial units**: All measurements now use US customary units for better readability
  - Temperature: Celsius → Fahrenheit
  - Wind speed: m/s → mph (miles per hour)
  - Visibility: meters → miles
  - Pressure: Pascals → inHg (inches of mercury, standard for weather)
- **Wind direction now shows cardinal compass directions**: Instead of raw degree bearings (0-360), wind direction displays 16-point compass directions (N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW, WSW, W, WNW, NW, NNW)
- **Improved display format**: "Wind: 17 mph from S" is clearer than "Wind: 7.416 190"
- Current observations and 7-day forecast both use new format

## [wx-me.py 1.3] - 2026-01-22
### Changed
- **Updated logo to GYX**: Changed ASCII art logo from generic "wx" to GYX regional branding
- Version bump to trigger auto-update on deployed nodes

## [wx.py 2.6] - 2026-01-22
### Fixed
- **Fixed gridsquare validation regex**: Was rejecting valid 6-character gridsquares (e.g., FN43po) due to incorrect case handling in pattern [a-xa-x]. Changed to [A-X] for uppercase matching. This fixed HamDB lookups failing with "Callsign not in database" message.
- **Fixed NWS forecast endpoint**: `get_forecast_7day()` and `get_pop()` were using wrong endpoint URL (forecastGridData has no periods). Now correctly:
  1. Query `/points/{lat},{lon}` to get forecast URL
  2. Fetch `/gridpoints/{grid}/forecast` for actual periods with temperature/wind/conditions
  3. This fixes "No forecast available" errors across all forecast reports (7-day, PoP)
### Changed
- Refactored forecast data retrieval to use correct NWS endpoint structure
- Updated function signatures: `get_forecast_7day()` and `get_pop()` now take `latlon` instead of `gridpoint` URL
- Both functions now correctly retrieve forecast periods

## [wx.py 2.5] - 2026-01-22
### Added
- **Manual gridsquare entry for callsigns not in database**: If HamDB lookup fails, user can now enter gridsquare manually for that callsign
- Graceful fallback for users not found in database

## [wx.py 2.4] - 2026-01-22
### Changed
- **Clearer callsign prompt**: Replaced "(stdin)" jargon with plain language "(press Enter)"
- Better UX for callsign selection in Option 3

## [wx.py 2.3] - 2026-01-22
### Added
- **Readability pause after each report**: "Press enter to continue..." prompt appears after displaying each weather report
- Gives users time to read on low-baud packet radio connections

## [wx.py 2.2] - 2026-01-22
### Fixed
- **get_bpq_locator() now uses script directory instead of cwd**: Uses `os.path.abspath(__file__)` to find script location, then looks for `../linbpq/bpq32.cfg` relative to script directory (not current working directory)
- **Option 1 now correctly loads node's local gridsquare**: Previously fell back to user's callsign grid when path lookup failed
### Changed
- Paths to try now use parent directory of script location as base, ensuring reliable relative path resolution

## [wx.py 2.1] - 2026-01-22
### Added
- **Zipcode lookup**: Convert US zipcodes (5 digits) to lat/lon via USGS Geocoding API
- **Case-insensitive gridsquare input**: Accept 'fn43sr', 'FN43SR', 'Fn43Sr', etc.
- **Improved bpq32.cfg path resolution**: Priority order is ../linbpq/bpq32.cfg (relative path for apps adjacent to linbpq), then /home/pi/linbpq (RPi default user)
### Fixed
- Gridsquare validation now accepts lowercase input (e.g., 'fn43sr' no longer rejected)
- Config file discovery now checks relative path first, then RPi default locations

## [wx.py 2.0] - 2026-01-22
### Added
- **Two-menu interface**: Location selection (main menu) → 12-report submenu (reports menu)
- **12 comprehensive weather reports** per selected location:
  1. 7-Day Forecast (temp, wind, conditions)
  2. Current Observations (temp, wind direction/speed, visibility, pressure, conditions)
  3. Fire Weather Outlook (from headlines)
  4. Heat/Cold Advisories (auto-extracted from active alerts)
  5. River/Flood Stage (auto-extracted from active alerts)
  6. Coastal Flood Info (conditional for coastal areas)
  7. Area Forecast Discussion (AFD from headlines)
  8. Probability of Precipitation (PoP 5-day outlook)
  9. UV Index (current level)
  10. Pollen Forecast (daily triggers from EPA)
  11. Dust/Haboob/Fire Alerts (auto-extracted from active alerts)
  12. Active Alerts (full SKYWARN status + alert details)
- **Refined UX**: User selects location once, then browses all 14 reports without re-entering
- **Prompt format**: "1-12) B)ack Q)uit :>" with space separation
- **Location header**: "REPORTS FOR: [location]" shows current context throughout submenu
### Changed
- **Main loop restructured**: Location selection loop → reports submenu loop
- **Menu functions**: Separate print_main_menu() and print_reports_menu()
- **Display functions**: Dedicated show_*_report() for each report type
- **Data fetching**: Fetch all data once per location, pass to submenu
- **Back button**: B)ack returns to location selection (can choose different area)
- **Coastal conditional**: Report 6 only shows for coastal areas (auto-detected)
### Technical
- Fetch operations use 3-second timeout, offline resilience maintained
- Bandwidth optimized: Report text truncated for 1200 baud compatibility
- Python 3.5.3 compatible throughout
- All functions handle missing/incomplete data gracefully

## [wx.py 1.5] - 2026-01-22
### Added
- **Coastal flood detection**: Automatically detects if location is in coastal area via NWS API
- **Marine forecast info**: Fetch and display coastal/marine zone forecasts with water level and wave info
- **Conditional menu option**: "Coastal flood info" appears in menu only for coastal locations
- Dynamic menu numbering: Alert option shifts to 5 when coastal option is available
### Changed
- **is_coastal() function**: Check for marine forecast zones to identify coastal areas
- **get_coastal_flood_info() function**: Pull first marine zone forecast with bandwidth optimization (300-char limit)
- **show_coastal_flood_info() function**: Display marine forecast with zone name and truncated content
- **Menu integration**: Menu parameter now includes is_coastal_area flag

## [wx.py 1.4] - 2026-01-21
### Added
- **Weather alerts**: Fetch active NWS alerts for local location and display alert summary in header
- **SKYWARN activation detection**: Check Hazardous Weather Outlook (HWO) for "spotters encouraged" status
- **Alert menu option**: New menu choice (4) to view full alert details when alerts are active
- Alert categories: Tornado, Severe Thunderstorm, Winter Storm, Wildfire, etc.
- Bandwidth-efficient alert display: severity markers (*) for Extreme/Severe alerts
### Changed
- **main() function**: Fetch alerts and SKYWARN status on startup alongside local weather
- **Menu system**: Conditional "4) View alerts" option appears only when alerts are active
- Header format: Display "!!! WEATHER ALERT !!!" with count and severity indicators
- Local weather now includes alert awareness (check displayed before menu loop)

## [Interface Standardization] - 2026-01-20
### Changed
- **MAJOR**: Standardized interface across all BPQ apps
- Reduced line width from 60-80 to 40 characters for mobile/older terminals
- Standardized headers: "APP NAME vX.Y - Brief Description" with single line separator
- Removed welcome messages to save bandwidth - utilities are tools, not chatbots
- Compressed prompts: "Menu: P)ost D)el N)ext Q :>" vs verbose alternatives
- Consistent exit message: "Exiting..." for apps (reserve "73!" for node sign-off)
- Updated copilot-instructions.md with comprehensive interface standards
### Apps Updated
- bulletin.py v1.1→1.2: Compressed prompt, removed welcome, 40-char width
- forms.py v1.5→1.6: Minimal header, removed verbose intro, 40-char width  
- space.py v1.1→1.2: Standardized header and menu format
- predict.py v1.3→1.4: Minimal header, compressed menu, 40-char width

## [bulletin 1.1] - 2026-01-20
### Changed
- Simplified interface to match RSS News app pattern
- Replace numbered menu with prompt-based navigation: `P)ost, D)elete, N)ext, Pr)evious, S)tats, Q)uit`
- Show messages immediately on startup (no separate "view messages" option needed)
- Refresh message display automatically after posting or deleting
- Standardize interface pattern across BPQ apps

## [bulletin 1.0] - 2026-01-20
### Added
- New community bulletin board application (bulletin.py)
- Classic BBS-style one-liner message posting and viewing
- JSON storage with callsign, timestamp, and message text
- Automatic callsign detection from BPQ32 or manual entry
- Message pagination (10 messages per page)
- Delete your own messages functionality
- Community statistics and top contributors
- Menu-driven interface optimized for packet radio
- 80-character message limit for bandwidth efficiency
- Chronological display with newest messages first
- Author indicators (*) for deletable messages

## [predict 1.3] - 2026-01-20
### Changed
- Enable callsign lookup for user's own location (not just other stations)
- Improve help text to show callsign option when applicable

## [predict 1.2] - 2026-01-20
### Fixed
- Replace Unicode warning symbol (⚠) with ASCII-only [!] for AX.25 compatibility
- Comply with copilot-instructions: ASCII text only, no Unicode/ANSI

## [predict 1.1] - 2026-01-20
### Changed
- Display all 8 HF bands (80m, 40m, 30m, 20m, 17m, 15m, 12m, 10m) for comprehensive predictions
- Previously showed only 5 most common bands; now includes all amateur HF allocations

## [predict 1.0] - 2026-01-20
### Added
- New HF propagation estimator app (predict.py)
- Estimates best bands and times for HF contacts between two locations
- Simplified ionospheric model (~70-80% accuracy vs full VOACAP ~90%)
- Resilient solar data strategy: online → cached → user input → defaults
- Location input: gridsquare, GPS, DMS, US state, country, callsign lookup
- Callsign gridsquare lookup via HamDB API
- BPQ LOCATOR config integration for user's location
- Support library in apps/predict/:
  - geo.py: Coordinate conversion, great-circle distance/bearing
  - solar.py: Solar data fetching with caching (hamqsl.com)
  - ionosphere.py: MUF estimation using ITU-R correlations
  - regions.json: US state + 50 country centroids

## [utilities README] - 2026-01-18
### Changed
- Rewrote utilities/README.md for clarity and conciseness
- Removed verbose explanations and redundant sections
- Reorganized content: Quick Start, Usage, Common Tasks, Output Files, How It Works
- Condensed option documentation while preserving technical accuracy
- Simplified examples to focus on common use cases
- Reduced overall length by ~60% while maintaining all essential information

## [nodemap-html 1.4.13] - 2026-01-17
### Fixed
- SVG tooltips now properly display line breaks as `<br>` tags instead of literal `\n` characters
- JavaScript `showTooltip()` now splits escaped newlines and converts to HTML line breaks

## [nodemap 1.7.82] - 2026-01-17
### Fixed
- Authentication now properly waits for password prompt using read_until with timeout
- Detects and reports authentication failures (invalid username, incorrect password)
- Warns if no password prompt received after sending username
- Fixes issue where invalid username caused silent failure and broken pipe error
- Auth exchanges now logged to telnet log for debugging

## [nodemap 1.7.81] - 2026-01-17
### Fixed
- Added alias validation to prevent callsigns being used as NetRom aliases
- New `_is_valid_netrom_alias()` validates that aliases are not callsign patterns
- New `_set_call_to_alias()` helper enforces validation at all assignment points
- Connection logic now detects and warns about invalid aliases (callsign stored as alias)
- Fixes bug where nodes without known aliases would attempt "C W1EMA" instead of ROUTES fallback
- Invalid aliases now trigger proper NetRom discovery or ROUTES-based port lookup

## [nodemap-html 1.4.12] - 2026-01-17
### Changed
- SVG tooltips now use custom HTML overlay instead of native browser tooltips
- Tooltips are semi-transparent (75% opacity) so they don't fully obscure connection lines
- Tooltips appear near cursor on mousemove and follow mouse position
- Better visibility of network topology while hovering for information

## [nodemap 1.7.80] - 2026-01-17
### Fixed
- ROUTES consensus now requires explicit SSID (rejects bare callsigns like "KB1TAE")
- Bare callsigns in netrom_ssids are ambiguous and should not count as valid node SSIDs
- Prevents queueing nodes that only appear in MHEARD without proper ROUTES entries
- Stale JSON data with bare callsigns no longer causes connection attempts to unreachable nodes

## [nodemap 1.7.79] - 2026-01-17
### Fixed
- Resume mode no longer skips nodes that lack a NetRom alias
- Nodes in ROUTES tables can now be crawled using port-based connections
- Connection logic queries ROUTES at each hop to get port numbers (C PORT CALL-SSID)
- Example: At KX1EMA, ROUTES shows "1 WD1O-15" so we can "C 1 WD1O-15"
- This enables automatic crawling of nodes that appear in ROUTES but not NODES tables

## [nodemap 1.7.78] - 2026-01-17
### Added
- Version and metadata headers in log files (telnet.log, debug.log)
- Log headers include: version, timestamp, node hostname, and callsign
- Helps identify which version generated logs for troubleshooting via SCP

## [nodemap 1.7.77] - 2026-01-17
### Added
- `-x`/`--exclude` support in query mode (`-q`) to filter unexplored neighbors
- Example: `nodemap.py -q K1NYY-15 -x` filters bad callsigns from neighbor list

## [nodemap 1.7.76] - 2026-01-18
### Added
- Silent/autonomous mode (`-y`/`--yes`) for cron jobs and scripted operation
  - Requires `-u` USERNAME and `-p` PASSWORD
  - Auto-generates maps (skips "Generate maps?" prompt)
  - Auto-selects best path when route discovery prompts appear
  - Skips interactive gridsquare entry prompts
  - Example: `nodemap.py 10 -y -u KC1JMH -p mypass`

## [nodemap-html 1.4.11] - 2026-01-18
### Added
- HF Access indicator in popups shows HF port descriptions (VARA, ARDOP, PACTOR)
- HF Access shown even when no specific frequency is listed
- Useful for nodes with HF gateway capability (use --note to add dial-in frequencies)

## [nodemap 1.7.75] - 2026-01-18
### Added
- Shorthand options for all CLI flags (POSIX style single-character)
  - `-g` for `--set-grid`, `-N` for `--note`, `-C` for `--cleanup`
  - `-H` for `--hf`, `-I` for `--ip`, `-M` for `--mode`
  - `-c` for `--callsign`, `-u` for `--user`, `-p` for `--pass`
- Man page style help output with NAME, SYNOPSIS, VERSION, DESCRIPTION,
  OPTIONS, EXAMPLES, FILES, ENVIRONMENT, and SEE ALSO sections

## [nodemap-html 1.4.10] - 2026-01-18
### Added
- Shorthand options for all CLI flags
  - `-a` for `--all`, `-t` for `--html`, `-s` for `--svg`
  - `-i` for `--input`, `-o` for `--output-dir`
- Man page style help output

## [nodemap 1.7.74] - 2026-01-18
### Added
- `--note CALL [TEXT]` flag to add/remove notes for nodes
- Notes stored in `note` field of nodemap.json
- Notes displayed in HTML popups (yellow highlight) and SVG tooltips
- Useful for maintenance schedules, HF frequencies, offline status, etc.
- Auto-regenerates maps after adding/removing notes

## [nodemap-html 1.4.9] - 2026-01-18
### Added
- Note display in HTML popups with yellow background styling
- Note display in SVG tooltips ("Note: ..." line)

## [nodemap 1.7.70] - 2026-01-17
### Fixed
- HF detection: Added standalone "HF" keyword (e.g., port description "HF" or "3 HF")
- Removed redundant legacy is_rf fallback in MHEARD loop

## [nodemap-html 1.4.7] - 2026-01-17
### Added
- Link type visualization: IP links shown as dotted cyan, HF links as dashed yellow
- Support for `port_type` field from nodemap.json (rf, hf, ip)
- Tooltip now shows link type (RF/HF/IP) alongside frequency

### Changed  
- Connection color logic: IP=cyan, HF=yellow, RF=band-based colors
- SVG output uses same dash patterns as HTML for IP/HF links

## [nodemap 1.7.69] - 2026-01-17
### Added
- `--hf` flag to include HF ports (VARA, ARDOP, PACTOR) in crawling
- `--ip` flag to include IP ports (AXIP, TCP, Telnet) in crawling
- Port type classification: 'rf' (VHF/UHF), 'hf' (slow digital), 'ip' (Internet)
- HF detection: VARA/ARDOP/PACTOR keywords, frequency <30 MHz, speed ≤300 baud

### Changed
- Default behavior: Skip HF ports (too slow at 300 baud for crawling)
- Default behavior: Skip IP ports (not RF, may be temporary links)
- MHEARD loop now filters by port_type instead of just is_rf flag

## [nodemap 1.7.68] - 2026-01-17
### Fixed
- ROUTES port fallback: When no NetRom alias exists at intermediate hop, query ROUTES for port
- Use `C PORT CALLSIGN-SSID` format (e.g., `C 1 WD1O-15`) to connect via ROUTES table
- Previous callsign-only fallback (`C WD1O-15`) violated BPQ requirement for port number
- Now correctly replicates manual connection method through intermediate nodes

## [nodemap 1.7.67] - 2026-01-17
### Fixed
- Target-only mode: `--callsign` now ONLY crawls the target node, not all neighbors
- When both START_NODE and --callsign provided, path is START_NODE → target (not START_NODE crawl)
- Example: `./nodemap.py K1NYY-15 --callsign WD1O-15` now crawls WD1O-15 only via K1NYY-15
- Callsign fallback: When no NetRom alias exists, try `C CALLSIGN-SSID` directly
- Allows connecting to nodes in ROUTES/MHEARD that lack NODES table entry

### Added
- `target_only_mode` flag to restrict crawling to specific target
- Display "Mode: Target-only" when --callsign is used
- Improved verbose output for target-only path building

## [nodemap 1.7.66] - 2026-01-16
### Fixed
- CLI-forced SSIDs (--callsign) now exempt nodes from NetRom alias/consensus checks
- Nodes with forced SSID no longer skipped due to tied votes or missing alias
- Example: `./nodemap.py K1NYY-15 --callsign WD1O-15` now crawls WD1O-15 even if no alias found
- Allows correcting bad SSID data and crawling neighbors without NetRom discovery

## [nodemap 1.7.65] - 2026-01-16
### Fixed
- START_NODE + --callsign now uses default max_hops=4 instead of 0
- Correction mode (max_hops=0) only applies when --callsign used alone
- Example: `./nodemap.py K1NYY-15 --callsign WD1O-15` now crawls 4 hops from K1NYY-15
- Example: `./nodemap.py --callsign WD1O-15` still uses correction mode (0 hops)

## [nodemap 1.7.64] - 2026-01-16
### Fixed
- Verify START_NODE has NetRom alias or is direct neighbor before attempting crawl
- Prevents timeout errors when user specifies unroutable node as start point
- Use JSON own_aliases as fallback for routing when no ROUTES consensus
- Eliminates redundant NetRom discovery for previously crawled nodes
- Prioritizes historical JSON data over live discovery for known nodes

## [nodemap 1.7.63] - 2026-01-16
### Changed
- Added _normalize_callsign() helper for case-insensitive comparisons
- Normalize all callsigns to uppercase when storing/comparing
- Applies to: callsign init, exclude set, alias maps, SSID maps, ROUTES/NODES parsing, MHEARD
- Ensures packet radio case assumptions hold (uppercase standard) even with mixed-case stale data

## [nodemap 1.7.62] - 2026-01-16
### Fixed
- Display-nodes exclusion filtering now case-insensitive (fixes KX1nMA vs KX1NMA)
- Unexplored column comparison also case-insensitive

## [nodemap 1.7.61] - 2026-01-16
### Fixed
- Display-nodes (-d) now respects exclusions file when used with -x flag
- Parses exclusions.txt before displaying unexplored neighbors
- Filters both summary unexplored list and per-node unexplored columns
- Supports comma-separated values in exclusions.txt

## [nodemap 1.7.60] - 2026-01-16
### Fixed
- Display-nodes (-d) now correctly strips SSIDs when comparing explored vs unexplored
- Prevents showing already-crawled nodes (KC1JMH-15, KS1R-15, etc) as "Unexplored"
- Both node keys and neighbor lists now normalized to base callsigns for comparison

## [nodemap 1.7.59] - 2026-01-16
### Fixed
- Skip nodes without NetRom alias during planning phase
- Catches nodes in ROUTES but not in any NODES table (unreachable)
- Prevents 15+ failed connection attempts to unroutable nodes
- Nodes like VE1YAR, KC1JMF, N1LJK, W1LH, etc now skipped upfront

## [nodemap 1.7.58] - 2026-01-16
### Fixed
- Expanded NetRom discovery only runs from localhost (i==0)
- Prevents breaking connection path when on intermediate nodes
- Aborts if alias not found in current node's NODES (can't discover further)
- Stops connecting to BBS/RMS/CHAT nodes that break the path

## [nodemap 1.7.57] - 2026-01-16
### Fixed
- Fixed syntax error from orphaned else clause (line 633)
- Moved alias fallback logic into except block where it belongs

## [nodemap 1.7.56] - 2026-01-16
### Changed
- Clarified: BPQ waits for input after connection (no auto-banner)
- CR requests prompt directly, avoiding INFO display entirely

## [nodemap 1.7.55] - 2026-01-16
### Changed
- Send CR after connection to skip INFO banner before waiting for prompt
- Reduces unnecessary INFO traffic when connecting through intermediate nodes
- Node responds with prompt immediately if CR interrupts INFO display

## [nodemap 1.7.54] - 2026-01-16
### Fixed
- NetRom discovery now runs from intermediate nodes, not just first hop
- Allows finding aliases for next hop from current node's NODES table
- Reduces failed connections when alias not in previously crawled data

## [nodemap 1.7.53] - 2026-01-16
### Fixed
- Connection now aborts if no NetRom alias found (base callsign does NOT work)
- Removed base callsign fallback - NetRom requires alias or port, no exceptions
- Updated copilot-instructions.md: skip nodes without alias during planning

## [nodemap 1.7.52] - 2026-01-16
### Fixed
- Connection fallback now checks call_to_alias mappings before using base callsign
- No longer attempts "C CALLSIGN-SSID" without port (always fails beyond first hop)
- Fallback priority: NetRom alias from mappings → base callsign (let NetRom route)

## [nodemap 1.7.51] - 2026-01-16
### Fixed
- Added missing check for tied SSID votes during unexplored neighbor processing
- KB1TAE and similar nodes with tied votes now properly skipped during planning
- Was checking "not in ROUTES" but not "has tied votes"

## [nodemap 1.7.50] - 2026-01-16
### Fixed
- Removed redundant SSID filtering check during crawl phase
- All node filtering now happens during planning phase only (no duplicate checks)
- Eliminates duplicate "Skipping KB1TAE" messages

## [nodemap 1.7.49] - 2026-01-16
### Changed
- Skip nodes not in any ROUTES table (unreachable via NetRom)
- Track skipped nodes in `skipped_no_route` set
- Report unreachable nodes at end of crawl
- Updated copilot-instructions: cannot use "C CALL-SSID" beyond first hop (needs port)
- Port numbers vary between nodes - only localhost route_ports usable

### Fixed
- Stop attempting connections to nodes only in MHEARD (likely user stations or offline)
- KX1KMA and similar nodes now properly skipped instead of timing out

## [nodemap 1.7.48] - 2026-01-16
### Fixed
- Exclusion matching now checks both full callsign and base callsign
- `--exclude KC1JMF` now skips KC1JMF, KC1JMF-15, KC1JMF-1, etc. (all SSIDs)
- Fixes issue where KC1JMF-15 was not being excluded despite KC1JMF in exclusions list
- Applied to both crawl_node and unexplored_neighbors processing

## [nodemap 1.7.47] - 2026-01-16
### Changed
- Skip nodes with tied SSID votes instead of using base callsign (base callsign = user, not node)
- Track skipped nodes in `skipped_no_ssid` dict with their vote counts
- Report skipped nodes at end of crawl with suggestion to use --force-ssid
- Notification now includes skipped count

### Fixed
- Don't try to connect to base callsign (e.g., KB1TAE) - that's a user station, not a node

## [nodemap 1.7.46] - 2026-01-16
### Fixed
- ROUTES consensus: Only use SSID when there's a CLEAR winner (more votes than others)
- When votes are tied (e.g., KB1TAE-2:1, KB1TAE-15:1), use base callsign only
- Per SSID Selection Standard: "if no ROUTES data, strip SSID and let NetRom figure it out"
- Tied consensus is effectively "no clear data" - don't guess arbitrarily

## [nodemap 1.7.45] - 2026-01-16
### Changed
- SSID Selection Standard: Use ROUTES consensus (aggregate netrom_ssids from all nodes)
- ROUTES tables are AUTHORITATIVE - they show actual node SSIDs used for routing
- Build consensus by counting which SSID each node reports for a given base callsign
- Removed reliance on `alias` field (was unreliable - could be BBS/RMS/CHAT prompt)
- Updated copilot-instructions.md with correct ROUTES-based standard

### Fixed
- KS1R now correctly uses KS1R-15 (3 nodes agree) instead of KS1R-2 (BBS)
- KC1JMH correctly uses KC1JMH-15 (4 nodes agree)
- All SSID selection now based on network-wide ROUTES consensus

## [nodemap 1.7.44] - 2026-01-16
### Changed
- SSID Selection Standard: Use node's PRIMARY ALIAS from `alias` field (from BPQ prompt)
- Removed consensus counting from seen_aliases (was unreliable - equal counts for all services)
- Primary alias is authoritative: when we connect, BPQ reports "BURG:KS1R-15}" in prompt
- The `alias` field maps to own_aliases to find the actual node SSID
- Updated copilot-instructions.md with correct SSID Selection Standard

### Fixed
- KS1R now correctly uses BURG (KS1R-15) instead of BBSBUR (KS1R-2)
- All SSID selection now based on actual node identity, not service alias counting

## [nodemap 1.7.43] - 2026-01-16
### Fixed
- STRICTLY enforce alias consensus: call_to_alias ONLY populated when alias matches consensus SSID
- Removed ALL heuristics based on SSID numbers (no assumptions about higher/lower)
- Fixed 3 separate code locations adding aliases without consensus check
- If no consensus exists, alias is NOT added - let NetRom routing use base callsign
- Follows SSID Selection Standard: consensus or nothing, never guess

## [nodemap 1.7.42] - 2026-01-16
### Fixed
- Live NODES discovery now prefers aliases matching consensus SSID
- For uncrawled nodes, prefers higher SSIDs (like -15) over lower SSIDs (like -2)
- Node SSIDs tend to be higher numbers, service SSIDs (BBS, RMS) tend to be lower
- Fixes connecting to BBSBUR (KS1R-2) instead of BURG (KS1R-15)

## [nodemap 1.7.41] - 2026-01-16
### Fixed
- Resume/new-only mode now correctly processes unexplored_neighbors from JSON
- Previous code was looking for non-existent 'neighbors' and 'routes' fields
- unexplored_neighbors with SSIDs are stripped to base callsign unless alias consensus exists
- Fixes v1.7.39 not working - the whole unexplored neighbor loop was broken

## [nodemap 1.7.40] - 2026-01-16
### Fixed
- Local BPQ node connection failures (Broken pipe, connection refused) now exit immediately
- Prevents crawler from continuing when localhost telnet connection is lost
- Distinguishes fatal local errors from expected remote node connection failures

## [nodemap 1.7.39] - 2026-01-16
### Fixed
- Unexplored neighbors now use base callsign only (no SSID) unless alias consensus exists
- Prevents using service SSIDs (BBS -2, RMS -10) from routes tables for new nodes
- NetRom discovery during crawl will find correct node SSID from NODES output
- Follows SSID Selection Standard: only use own_aliases/seen_aliases consensus, never routes SSIDs

## [nodemap 1.7.38] - 2026-01-16
### Fixed
- new-only mode now populates self.nodes from existing JSON data
- Fixes new-only mode re-crawling known nodes (self.nodes was always empty)
- Skip check at crawl_node() requires self.nodes to be populated, not just self.visited

## [nodemap 1.7.37] - 2026-01-16
### Fixed
- route_ports now restored ONLY from local node's heard_on_ports, not all nodes
- Fixes using wrong port number (KS1R's port 2 instead of WS1EC's port 1 for KC1JMH)
- heard_on_ports is node-specific - tells which port on THAT node heard a neighbor

## [nodemap 1.7.36] - 2026-01-16
### Changed
- unexplored_neighbors now stores full SSIDs (KC1JMH-15) instead of base callsigns (KC1JMH)
- Allows distinguishing node SSIDs from future user station SSIDs

### Added
- `--cleanup unexplored` option to upgrade existing base callsigns to full SSIDs
- Uses consensus from own_aliases, seen_aliases, and netrom_ssids to determine best SSID

## [nodemap 1.7.35] - 2026-01-16
### Fixed
- new-only mode now correctly skips known nodes when callsign lacks SSID
- Compares base callsign (KC1JMH) against nodes stored with SSID (KC1JMH-15)
- Prevents re-crawling already-visited nodes in new-only mode

## [nodemap 1.7.34] - 2026-01-16
### Fixed
- Renamed _log() to _debug_log() to avoid conflict with telnet traffic _log() method
- Fixes TypeError when crawling due to method signature mismatch

## [nodemap 1.7.33] - 2026-01-16
### Fixed
- Resume mode now restores call_to_alias mappings from JSON (was only in start-node mode)
- Fixes using service SSID alias (RMSWDB/K1NYY-10) instead of node alias (LLNWDB/K1NYY-15)
- call_to_alias restoration uses consensus SSID to find matching alias

### Changed
- Debug log (-D) now captures key progress messages (Crawling, Connected, etc.) even if not verbose
- Added _log() method for always-on debug logging separate from verbose _vprint()

## [nodemap 1.7.32] - 2026-01-16
### Fixed
- SSID consensus now aggregates from own_aliases + seen_aliases instead of routes keys
- Routes in JSON use base callsigns (KC1JMH) without SSIDs, so ROUTES consensus was empty
- own_aliases/seen_aliases contain full SSIDs from NODES output (KC1JMH-15) - authoritative
- Fixes incorrect SSID selection (KC1JMH-8 from MHEARD instead of KC1JMH-15 from aliases)

## [nodemap 1.7.31] - 2026-01-16
### Added
- Exclusion file support: -x/--exclude now accepts filename or defaults to exclusions.txt
- File format: newline or comma-delimited callsigns, # comments supported
- Use -x alone to load exclusions.txt, or -x filename.txt for custom file
- Helps filter corrupted callsigns from AX.25 routing table pollution

## [nodemap-html 1.4.6] - 2026-01-16
### Fixed
- SVG node labels now positioned below icons instead of beside them
- Prevents overlapping labels from blocking node hover/tooltip access
- Labels centered under nodes with text-anchor="middle"

## [nodemap-html 1.4.5] - 2026-01-16
### Added
- Draw separate colored lines for each band nodes connect on
- Uses heard_on_ports to determine actual frequencies for each connection
- Supports 2m (blue), 70cm (orange), 1.25m/220 MHz (purple), 6m (green)
- Falls back to first RF port only when no MHEARD port data available

## [nodemap 1.7.30] - 2026-01-16
### Fixed
- Rewrote JSON restoration to use two-pass ROUTES consensus approach
- PASS 1: Aggregate SSIDs from ALL nodes' ROUTES tables first (authoritative)
- PASS 2: Fill gaps from own_aliases, build call_to_alias using consensus SSID
- Removes reliance on unreliable `alias` field (could be BBS, RMS, CHAT alias)
- KS1R now correctly maps to BURG (KS1R-15) not BBSBUR (KS1R-2)

## [nodemap 1.7.29] - 2026-01-16
### Fixed
- call_to_alias restoration now uses ROUTES consensus SSID to find matching alias
- Follows SSID Selection Standard: ROUTES consensus > own_aliases match > fallback
- Fixes using BBSBUR (KS1R-2 BBS) instead of BURG (KS1R-15 node) for NetRom routing
- Never assumes SSID by number - uses data source priority per copilot-instructions.md

## [nodemap 1.7.28] - 2026-01-16
### Fixed
- call_to_alias now uses node's primary alias field (authoritative) instead of first seen_alias
- Fixes routing using BBS alias (BBSWHT/N1REX-2) instead of node alias (LNCWHT/N1REX-15)
- Node's own primary alias from JSON takes precedence over seen_aliases
- Data-driven: uses alias field from v1.7.25 prompt parsing, no SSID assumptions

## [nodemap 1.7.27] - 2026-01-16
### Fixed
- netrom_ssid_map now stores base callsign as key (KC1JMH), not full SSID (KC1JMH-15)
- Fixes BFS neighbor lookup when neighbors list uses base callsigns
- Ensures netrom_ssid_map.get("KC1JMH") returns "KC1JMH-15" for SSID resolution

## [nodemap 1.7.26] - 2026-01-16
### Fixed
- BFS pathfinding now tries base callsign lookup when SSID lookup fails
- Handles nodes stored without SSID (WS1EC) when self.callsign has SSID (WS1EC-15)
- Fixes "neighbors: (none)" bug when node exists in JSON but under different key format

## [nodemap 1.7.25] - 2026-01-16
### Added
- Added _find_node_alias() method to parse NODEALIAS from bpq32.cfg
- Localhost now uses NODEALIAS from bpq32.cfg as authoritative primary alias source

### Fixed
- Primary alias extraction now parses prompt format (ALIAS:CALL-SSID}) from commands list
- Fixes alias field containing wrong service alias (CCERMS instead of CCEMA for WS1EC)
- Localhost uses bpq32.cfg NODEALIAS (authoritative), remote nodes use prompt parsing
- Fallback to first own_aliases entry only when prompt parsing and config unavailable

## [nodemap 1.7.24] - 2026-01-16
### Fixed
- Removed hardcoded -15 SSID assumption from v1.7.23
- own_aliases fallback now uses FIRST entry (primary alias, data-driven)
- Relies on own_aliases dict order from JSON (primary alias listed first)

## [nodemap 1.7.23] - 2026-01-16
### Fixed (REVERTED - made bad SSID assumptions)
- own_aliases fallback now prioritizes -15 SSIDs (typical node SSID) over service SSIDs
- Fixes WS1EC resolving to WS1EC-5 (CHAT) instead of WS1EC-15 (node) when alias field missing
- Two-pass fallback: first looks for -15, then any valid SSID (1-15)

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
