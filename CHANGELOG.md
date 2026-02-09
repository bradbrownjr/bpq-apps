# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [Apps.py Log Viewer Fix] - 2026-02-09
### Fixed
- **apps.py v2.1→2.2**: Added pause prompt after viewing system log
  and BPQ log in sysop menu
- Log viewer now waits for Enter key before redisplaying menu
- Prevents jarring immediate menu redisplay after exiting log viewer

## [Wiki Enter Key Pagination] - 2026-02-08
### Changed
- **wiki.py v2.9→2.10**: Enter key now advances to next page in search
  results (same as N)ext command)
- Prompt shows "Enter=next" when more results available
- Standardizes pagination navigation across all apps

## [Band Plans Key Frequencies] - 2026-02-08
### Added
- **antenna.py v1.7→1.8**: Key frequencies and calling frequencies
  for all 13 US bands (FT8, FT4, JS8Call, PSK31, CW QRP, SSB QRP,
  SSTV, Winlink, APRS, IARU beacons, ISS, maritime/emergency, etc.)
- Expanded VHF/UHF sub-band segments: 6m (4 segments), 2m (6
  segments), 70cm (6 segments) with mode/usage labels
- Paginated detail view (20 lines/page) for bands with many
  segments and key frequencies

### Changed
- B)ack renamed to C)ountry in band plan overview (clearer
  navigation when DEFAULT_COUNTRY is set)
- Mode column widened from 5 to 7 characters for longer labels

## [Band Plans UI Fix] - 2026-02-08
### Fixed
- **antenna.py v1.7**: Fixed band plan column alignment - header
  columns now properly align with data rows (# column reduced
  from width 3 to 2)
- **antenna.py v1.7**: Pressing B)ack from default country band
  plan now shows country selector instead of exiting to main menu
  (allows access to other countries when DEFAULT_COUNTRY is set)

## [Band Plans Feature] - 2026-02-08
### Added
- **antenna.py v1.6→1.7**: Comprehensive band plan reference
  replacing simple frequency chart. 6 countries:
  - US (FCC): Detailed sub-band segments with license class
    privileges (Extra, Advanced, General, Tech, Novice)
  - Canada (ISED): Advanced, Basic w/ Honours, Basic
  - UK (Ofcom): Full, Intermediate, Foundation
  - Germany (BNetzA/CEPT): Class A, Class E
  - Australia (ACMA): Advanced, Standard, Foundation
  - Japan (MIC): 1st through 4th Class
- US plan includes per-band detail view with sub-band mode
  restrictions, 60m channelized display, calling frequencies
- ITU Region band width differences reference data
- DEFAULT_COUNTRY config variable allows sysops to set default
  country band plan (skips country selector menu)

## [FEED Configuration Fix] - 2026-02-08
### Fixed
- **apps.json**: FEED now correctly points to rss-news.py (RSS feed reader)
  instead of obsolete feed.py (old wall.py duplicate)
- **wall.py v1.8→1.9**: Changed prompt from "Q" to "Q)uit" for consistency
- Removed obsolete feed.py file (duplicate of old wall.py message board)

## [M)ain → M)enu Rename] - 2026-02-08
### Changed
- Renamed M)ain to M)enu in all app prompts to avoid confusion with
  apps.py main menu. M)enu clearly refers to the current app's menu.
- **wx.py v4.11→4.12**: All pagination and report menu prompts
- **wiki.py v2.8→2.9**: All 8 pagination/search/article prompts
- **gopher.py v1.45→1.46**: Help text and main navigation prompt
- **htmlview.py v1.21→1.22**: All 5 navigation and content prompts
- **www.py v1.8→1.9**: Bookmark menu and comment
- **repeater.py v1.12→1.13**: Detail view prompts
- Updated copilot-instructions.md: M)enu standard, removed deprecated
  M)ain historical context section

## [Post-Exit Prompt Fix] - 2026-02-08
### Changed
- **apps.py v1.9→2.0**: Removed redundant Q)uit from post-exit prompt.
  After child app exits, shows `[Enter=continue]` instead of
  `[Q)uit Enter=continue]`.

## [Prompt Standardization - All Apps] - 2026-02-07
### Changed
- **Holistic prompt ordering standardization across all 18 apps**
  - Standard order: Q)uit → M)ain → B)ack → Page navigation → Enter=more
  - Consistent muscle memory across entire application suite
- **wx.py v4.9→4.10**: Added `continue_prompt()` helper; replaced 31 bare
  "Press enter to continue" with Q)uit escape; fixed reports menu and 3
  pagination prompts
- **gopher.py v1.44→1.45**: Reordered all 12 pagination prompts (Q first);
  replaced M)enu→M)ain; Q)uit escape on W)here prompts; reordered help
  and startup banner; fixed 3 main loop prompts
- **antenna.py v1.5→1.6**: Q first in calculator/database/main menus;
  added M to Py3 branches; `pause()` now has Q)uit escape
- **wiki.py v2.7→2.8**: M)enu→M)ain in all 9 prompts; Q first in
  pagination, search results, and article menus
- **rss-news.py v1.15→1.16**: Q first in all 4 main loop state prompts;
  fixed pagination and article fetch prompts
- **htmlview.py v1.20→1.21**: Q first in nav menu and content links;
  removed parentheses from prompt; Q)uit escape on W)here prompts
- **apps.py v1.8→1.9**: Q first in log paginator, sysop menu, app
  install menu, main menu; replaced 7 "Press Enter" with Q)uit escape
- **eventcal.py v2.8→2.9**: Swapped B)ack/Q)uit order; Q first in
  detail prompt; Q)uit escape on ENTER continue
- **feed.py v1.7→1.8**: Q first in menu prompt and error text
- **wall.py v1.7→1.8**: Q first in menu prompt and error text
- **forms.py v1.13→1.14**: Q first in choice/select prompts; added
  `_continue_prompt()` method; replaced 5 "Press Enter" patterns
- **hamtest.py v1.4→1.5**: Q first in exam begin/continue prompts;
  replaced 4 "Press Enter" patterns with Q)uit escape
- **repeater.py v1.11→1.12**: Q first; M)enu→M)ain; Q)uit escape on
  about page continue prompt
- **space.py v1.4→1.5**: Q first in main menu prompt
- **wx-me.py v1.4→1.5**: Q first in main menu prompt
- **www.py v1.7→1.8**: M)enu→M)ain in bookmark menu; Q)uit escape on
  about page and fetch error prompts
- **qrz3.py v1.3→1.4**: Removed ANSI color code wrapping from prompt
- **dict.py v1.12→1.13**: Q first in pagination prompt

## [AI Pagination and Word Wrapping] - 2026-02-07
### Changed
- **ai.py v1.19→1.20**: Added pagination and proper word wrapping for AI responses
  - Long responses now display with 20 lines per page
  - Proper word wrapping using textwrap at terminal width (no more broken words)
  - Pagination prompt: `[Q)uit Enter=more] :>`
  - User can quit mid-response (Q) or continue reading (Enter)
  - Saves bandwidth on 1200 baud connections — user controls flow

## [AI Display - Strip SSID from Callsign] - 2026-02-07
### Changed
- **ai.py v1.18→1.19**: Strip SSID from callsign display (show "KC1JMH" not "KC1JMH-8")
  - Updated all callsign display prints to use `extract_base_call()`
  - Updated AI system context to use base call for cleaner operator identification
  - Internal callsign variable still includes SSID for proper routing/logging

## [Auto-Restart After Update - All Apps] - 2026-02-07
### Changed
- **All 20 apps now auto-restart after update** via `os.execv()` instead of
  printing "Please re-run" and exiting. User sees "Updated to vX.Y. Restarting..."
  and the app immediately relaunches with the new version.
- Works in both launch modes:
  - **From apps.py menu**: `--callsign` arg in argv survives os.execv; subprocess
    returns normally when updated app finishes
  - **Direct from BPQ node**: stdin (TCP socket fd) preserved across os.execv;
    callsign still in buffer for new process to read
- Saves users from navigating back through menus on 1200 baud connections
- dict.py: Removed dead `return True` / caller check pattern (os.execv never returns)

### Version Bumps
- ai.py 1.17→1.18, antenna.py 1.4→1.5, callout.py 1.1→1.2,
  dict.py 1.11→1.12, eventcal.py 2.7→2.8, feed.py 1.6→1.7,
  forms.py 1.12→1.13, gopher.py 1.43→1.44, hamqsl.py 1.2→1.3,
  hamtest.py 1.3→1.4, predict.py 1.17→1.18, qrz3.py 1.2→1.3,
  repeater.py 1.10→1.11, rss-news.py 1.14→1.15, space.py 1.3→1.4,
  wall.py 1.6→1.7, wiki.py 2.6→2.7, www.py 1.6→1.7,
  wx.py 4.8→4.9, wx-me.py 1.3→1.4

## [Fix - Update Check Before Menu Display] - 2026-02-07
### Fixed
- **Double menu load on 1200 baud**: apps.py displayed the full menu, then discovered
  an update, restarted, and displayed the full menu again — wasting bandwidth on slow
  packet radio connections
- **Fix**: Reordered startup: read callsign from stdin → inject --callsign into
  sys.argv → check for updates (may os.execv restart) → display menu
  - Callsign preserved across os.execv restarts via CLI arg (NOT env var)
  - On restart, callsign recovered from --callsign arg (stdin already consumed)
  - Uses CLI args because env vars don't reliably propagate in inetd/BPQ environment
  - Menu only displayed once, after all updates complete
- apps.py v1.7 → v1.8

## [Fix - Callsign Arg Breaking Non-Callsign Apps] - 2026-02-07
### Fixed
- **--callsign arg sent to ALL apps broke QRZ and others**: v1.5 removed the
  `needs_callsign` gate so all apps received `--callsign CALL` as argv. Apps like
  qrz3.py interpreted this as a callsign to look up, showing "No data found on --callsign"
- **Root cause recap**: The gate was removed because apps.json doesn't auto-update,
  so new `needs_callsign: true` flags never reached production
- **Real fix**: Two-part solution:
  1. Restored `needs_callsign` gate in `launch_app()` — only apps flagged in apps.json get the arg
  2. Added **apps.json auto-update** — apps.py now downloads latest apps.json from GitHub
     on every startup (compares content, only writes if different)
- This ensures new `needs_callsign` flags reach production without manual deployment
- apps.py v1.6 → v1.7

## [Critical Fix - Module Reload Not Assigning] - 2026-02-07
### Fixed
- **Module reload broken**: v1.16 added importlib.reload() calls but didn't assign
  the return value back to variables, causing NameError "name 'geo' is not defined"
- **Fix**: Changed `importlib.reload(geo)` to `geo = importlib.reload(geo)` etc.
  - reload() returns the reloaded module, must be assigned to be used
- predict.py v1.16 → v1.17

## [Critical Fix - Module Files Not Actually Reloading] - 2026-02-07
### Fixed
- **Module files downloaded but not reloaded**: predict.py v1.15 added version-checking
  for module files and downloaded them, but Python had already imported the old versions
  into memory during startup. Modules were updated on disk but never reloaded.
- **Solution**: After check_for_app_update() call, added `importlib.reload()` for
  geo, solar, and ionosphere modules. Ensures fresh versions are used immediately.
  - Modules now: import → update check → reload → execute
- predict.py v1.15 → v1.16

## [Fix - Module Files Not Auto-Updating] - 2026-02-07
### Fixed
- **Module files (geo.py, solar.py, ionosphere.py) not updating**: predict.py only checked
  for MISSING module files, not updated ones. When ionosphere.py was updated with UTC time
  feature, existing installations never re-downloaded the new version.
- **Solution**: Added version-checking for Python module files. predict.py now:
  1. Extracts "Version: X.Y" from remote module file docstring
  2. Compares with local version
  3. Re-downloads if remote version is newer
  - Non-Python files (regions.json) still check for existence only
- predict.py v1.14 → v1.15

## [Fix - UTC Time Label Format in PREDICT] - 2026-02-07
### Fixed
- **UTC time label format**: Changed from "UTC: HH:MM" to "Current time: HH:MM UTC"
  - More natural phrasing, consistent with apps.py welcome message
  - predict.py v1.13 → v1.14, ionosphere.py v1.3 → v1.4

## [Feature - Welcome Header with UTC Time in APPS Menu] - 2026-02-07
### Changed
- **Apps menu header**: Updated from "User: KC1JMH" to "Welcome KC1JMH, the current time is HH:MM UTC"
  - Shows current UTC time at login, helping users coordinate digital modes and band changes
  - Time format: HH:MM UTC (24-hour, matching international standard)
  - apps.py v1.5 → v1.6

## [Feature - Current UTC Time in PREDICT Recommendations] - 2026-02-07
### Added
- **UTC time display**: PREDICT band recommendations now include current UTC time
  - Shows time in HHMM UTC format under the recommended band
  - Example: "Recommended: 20m (Excellent, 0200-2200 UTC)\n  UTC: 1245 UTC"
  - helps users know exactly when this recommendation was generated
  - predict.py v1.12 → v1.13, ionosphere.py v1.2 → v1.3

## [Fix - Callsign Not Reaching PREDICT and Other Apps] - 2026-02-07
### Fixed
- **Root cause found**: apps.json has no auto-update mechanism, so `needs_callsign: true`
  added for PREDICT/REPEATER/FEED/AI in commit 357eeed never reached the production server
  - Only WALL, FORMS, WX had `needs_callsign: true` in the deployed apps.json (from Phase 2)
  - apps.py gated callsign passing on `needs_callsign` flag → PREDICT never received it
- **Fix**: Removed `needs_callsign` gate from `launch_app()` — apps.py now ALWAYS passes
  `--callsign` and `BPQ_CALLSIGN` env var when it has a callsign, regardless of apps.json flag
  - Child apps that don't need callsign simply ignore the extra CLI arg
  - Eliminates dependency on apps.json being up-to-date on production servers
  - apps.py v1.4 → v1.5

## [Multi-App Fix - Callsign Passing via CLI Argument] - 2026-02-06
### Fixed
- **Callsign not reaching child apps via apps.py**: The BPQ_CALLSIGN environment variable
  mechanism was not reliably propagating callsigns from apps.py to child applications
  in production (inetd + BPQ + Python 3.5.3 environment)
  - Symptom: apps.py showed "User: KC1JMH" but child apps (e.g. PREDICT) did not detect callsign
  - Direct BPQ launch (bypassing apps.py) worked correctly via stdin
  - Root cause: env var inheritance through subprocess.call() unreliable in inetd context
  - Fix: apps.py now passes `--callsign CALL` as CLI argument (most reliable IPC mechanism)
  - All 7 callsign apps now check: CLI arg first, then env var, then stdin (triple fallback)
  - Updated: apps.py (1.4), predict.py (1.12), wall.py (1.6), forms.py (1.12),
    wx.py (4.8), repeater.py (1.10), feed.py (1.6), ai.py (1.17)

## [CRITICAL FIX - Infinite Update Loop in PREDICT] - 2026-02-06
### Fixed
- **Infinite update loop in predict.py**: Duplicate VERSION assignment caused mismatch
  - predict.py had two VERSION variable assignments: `VERSION = "1.11"` (line 33) then `VERSION = "1.10"` (line 39)
  - Second assignment overwrote the first, creating mismatch between docstring (1.11) and actual VERSION (1.10)
  - Auto-update always detected 1.11 as "newer" than 1.10, causing infinite loop
  - Users would download update, run app, see update available again, repeat forever
  - Fixed by removing duplicate `VERSION = "1.10"` assignment
  - Per copilot-instructions.md: VERSION variable must EXACTLY match docstring or infinite loops result

## [Multi-App Fix - Callsign Detection Feedback Version Bump] - 2026-02-06
### Fixed
- **Version bumps missing from callsign feedback commit**: 6 apps with callsign detection improvements didn't have version bumps
  - Code changes require BOTH docstring Version AND VERSION variable to match (copilot-instructions.md protocol)
  - Without version bumps, auto-update won't trigger on user systems
  - Bumped all 6 apps: predict.py (1.10→1.11), wall.py (1.4→1.5), feed.py (1.4→1.5), wx.py (4.6→4.7), repeater.py (1.8→1.9), ai.py (1.15→1.16)

## [Multi-App Fix - Callsign Detection Feedback] - 2026-02-06
### Fixed
- **Silent callsign detection left users unsure**: All callsign-using apps silently detected callsigns
  but never confirmed it to the user, causing confusion like "I don't think PREDICT detected my callsign"
  - Users had no feedback that their callsign was recognized or what happened with location lookup
  - All 7 callsign-using apps now display detected callsign immediately:
    - predict.py: Shows "Callsign detected: {call}" and "(Location auto-detected: {grid})" or "(Location lookup failed)" at startup
    - wall.py, feed.py: Show "Callsign: {call}" when detected and confirmed
    - forms.py: Already had "Callsign from BPQ: {call}" feedback
    - wx.py: Shows "Callsign: {call}" and "Location: {grid}" after header
    - repeater.py: Shows "Callsign: {call}" before displaying main menu
    - ai.py: Shows "Callsign: {call}" before provider selection
  - Provides transparency: users know what was detected and can verify

## [Multi-App Fix - Auto-Update Notification Standardization] - 2026-02-06
### Fixed
- **Silent auto-updates broke user expectations**: antenna.py, ai.py, eventcal.py silently downloaded and exited
  - Users had no idea an update happened or why the app quit
  - Fix: Standardized transparent notification pattern across all 21 apps with auto-update
  - All apps now display: "Update available → Downloading → Success → Please re-run"
  - Includes `sys.stdout.flush()` for immediate feedback on slow connections
  - Meets copilot-instructions.md protocol: apps never modify themselves silently
  - Affected: antenna.py (1.4), ai.py (1.15), eventcal.py (2.7)

## [Multi-App Fix - Version Consistency for Auto-Update Detection] - 2026-02-06
### Fixed
- **Version mismatches prevent auto-update**: wall.py, forms.py, wx.py had docstring Version ≠ VERSION variable
  - Version mismatches cause infinite update loops (protocol validates BOTH are identical)
  - Bumped all 13 modified apps to ensure docstring Version matches VERSION variable
  - Affected apps: wall.py (1.3→1.4), forms.py (1.10→1.11), wx.py (4.5→4.6)
  - Validated with: `grep "Version:" appname.py` matches `grep "^VERSION = " appname.py`

## [Multi-App Fix - BPQ_CALLSIGN Support for All Apps] - 2026-02-06
### Fixed
- **Missing BPQ_CALLSIGN support**: predict.py, repeater.py, feed.py, ai.py also use callsign
  for location lookup / user identification but were not updated in previous fix
  - All four now check `BPQ_CALLSIGN` env var first, then stdin pipe, then prompt
  - Updated apps.json: `needs_callsign: true` for predict, repeater, feed, ai
- **copilot-instructions.md**: Documented full callsign handling pattern (env var → stdin → prompt)

## [Multi-App Fix - Callsign Passing via Environment Variable] - 2026-02-06
### Fixed
- **Child apps exit immediately**: apps.py was piping callsign via stdin then closing pipe
  - Over inetd, `/dev/tty` unavailable so child stdin stays closed = EOF on all `input()` calls
  - Fix: Pass callsign via `BPQ_CALLSIGN` environment variable instead
  - Child process inherits real stdin (user's socket), stays interactive
  - Updated: apps.py (launcher), wall.py, forms.py, wx.py (callsign readers)
  - Apps still fall back to stdin pipe for direct BPQ launch (without apps.py)

## [Multi-App Fix - Terminal Width & Screen Clear] - 2026-02-06
### Fixed
- **TERM variable error**: Removed all `os.system('clear')` calls from apps.py
  - `clear` command fails with "TERM environment variable not set" over inetd/BPQ
  - Replaced with print separators (ASCII-only, no ANSI escape codes)
  - Affected: display_menu, show_about, sysop_menu, sysop_manage_apps, log viewer
- **Terminal width detection**: Replaced `os.get_terminal_size()` with `shutil.get_terminal_size(fallback=(80, 24))` across all apps
  - `os.get_terminal_size()` does NOT accept `fallback=` parameter (only `shutil` does)
  - `os.get_terminal_size(fallback=(80, 24))` was silently passing tuple as fd argument
  - Fixed in: apps.py, antenna.py, eventcal.py, www.py, ai.py, dict.py, wiki.py
  - `shutil.get_terminal_size()` gracefully handles missing TERM, no-TTY, and inetd sessions

### Changed
- **copilot-instructions.md**: Added terminal width standard pattern, screen clearing prohibition, and `shutil` vs `os` API clarification

## [apps.py v1.2 - Reverse Chronological Log Viewing] - 2026-02-05
### Changed
- **Log Viewing**: Logs now display in reverse chronological order (newest first)
  - Most recent log entries appear first on screen - critical for 1200 baud efficiency
  - Users can immediately see latest activity without loading old data
  - Changed navigation: O)lder goes back in time, N)ewer goes forward in time
  - Header shows "(Newest First)" to clarify display order
  - Status line updated: "Showing lines X-Y of Z (newest first)"

### Technical Details
- Displays lines in reverse order within each page
- Starts at end of file (most recent entries)
- Single iteration through file, minimal memory overhead
- Works efficiently even with large log files (syslog can be hundreds of MB)

## [apps.py v1.1 - About Screen and Sysop Menu] - 2026-02-05
### Added
- **About Screen**: Explains the bpq-apps project, highlighting key features:
  - Self-updating functionality with 3-second timeout
  - Offline-first design with local caching
  - Bandwidth optimization for 1200 baud packet radio
  - Emergency communications ready (ICS forms, MARS/SHARES, etc.)
  - Provides GitHub repository URL for documentation
- **Sysop Menu**: Only visible to sysops defined in bpq32.cfg with SYSOP privilege
  - **System Status**: Real-time display of CPU load, memory, disk, and uptime
  - **Process Monitoring**: Shows LinBPQ and Direwolf running status
  - **App Management**: Browse and install apps from GitHub repository
  - **Log Viewing**: Paginated system log and BPQ debug log (20 lines per page)
  - **Service Control**: Restart LinBPQ service (requires sudo access)
- Helper functions for parsing bpq32.cfg to extract sysop callsigns
- System statistics gathering from /proc filesystem
- GitHub API integration for listing available apps

### Changed
- Main menu now includes "A)bout" option for all users
- Main menu includes "S)ysop" option for authorized sysops only
- Version bumped from 1.0 to 1.1 (docstring and VERSION variable match)

## [apps.py v1.0 - Application Menu Launcher] - 2026-02-02
### Added
- **apps.py v1.0**: Unified application launcher with categorized menu
  - Displays installed apps organized by category (Internet, Tools, Games)
  - Only shows apps whose executables exist on the system
  - Launches apps via subprocess, returns to menu after exit
  - Passes user callsign via stdin to apps that need it
  - Configuration via apps.json for easy customization
  - Sysops can add third-party apps without modifying code
  - Reduces need for individual inetd service entries per app
  - Auto-update functionality included
  - ASCII art logo and 40-char terminal width support

### Added
- **apps.json**: Configuration file for apps.py menu system
  - Categories: Internet, Tools, Games
  - All current BPQ apps pre-configured
  - Sysops can edit to add/remove apps
  - Each entry includes name, description, executable path, callsign requirement

## [antenna.py v1.3 - Enhanced Dipole Calculator] - 2026-01-31
### Added
- **antenna.py v1.3**: Show formulas and height recommendations in dipole calculator
  - Display calculation formula: "468 / freq(MHz)"
  - Show recommended antenna heights: minimum (0.25λ), good (0.5λ), optimal (1.0λ)
  - Height recommendations include both feet and meters
  - Formula display section added before final separator

## [antenna.py v1.2 - Fix inetd Blocking] - 2026-01-31
### Fixed
- **antenna.py v1.2**: Remove stdin read that blocked inetd connections
  - get_callsign() no longer attempts to read from stdin
  - App uses NOCALL flag so no callsign expected from BPQ
  - Database submissions work anonymously
  - Fixes immediate connection closure via inetd/telnet

## [antenna.py v1.1 - Prompt Ordering Fix] - 2026-01-31
### Fixed
- **antenna.py v1.1**: Comply with standard prompt ordering
  - Main menu: Q)uit before A)bout
  - Calculator submenu: Q)uit M)ain instead of Q) Back
  - Database submenu: Q)uit M)ain instead of Q) Back
  - Pagination: Q)uit first in navigation
  - Both Q)uit (exit app) and M)ain (return to menu) now available in submenus
  - Follows standard: Q (exit scope), M (main), B (back), P (page nav), Enter (content)

## [antenna.py v1.0 - New App] - 2026-01-31
### Added
- **antenna.py v1.0**: New antenna calculator and configuration database app
  - Calculators: Dipole, EFHW (49:1/64:1/9:1/4:1), OCF, Folded Dipole, Moxon, Vertical/Ground Plane, NVIS, Loop, Random Wire
  - User-contributed database for portable antenna configurations
  - Search/browse by band, brand, or antenna type
  - Band frequency chart with half-wave lengths
  - Antenna formulas reference
  - Popular portable antennas info (Buddipole, Wolf River Coil, Chameleon, etc.)
  - ASCII art logo, standard menu interface
  - Auto-update functionality
  - Python 3.5.3 compatible

## [rss-news.py v1.14 + htmlview.py v1.20 - Clean Articles] - 2026-01-31
### Fixed
- **htmlview.py v1.20**: Filter blog title footer references
  - Added patterns to remove "WS1SM Ham Radio Blog" and similar blog title footers
  - Added pattern to catch any "...ham radio blog" style footer references
  
- **rss-news.py v1.14**: Disable link numbering in articles
  - Articles are read linearly, not navigated via links
  - Passes `number_links=False` to HTMLParser.parse()
  - Result: Clean article text without [1], [2], [3] link numbers
  - www.py still has numbered links for navigation (uses HTMLViewer, not parser directly)

## [htmlview.py v1.19 - Comprehensive WordPress Footer Removal] - 2026-01-31
### Fixed
- **htmlview.py v1.19**: Aggressive WordPress footer/metadata removal
  - HTML-level: Removes all `<footer>` tags, sharedaddy sharing plugin, jetpack UI
  - HTML-level: Removes entry-meta, post-meta, wpcom elements, reblog/subscribe divs
  - Text-level: Filters 20+ WordPress junk patterns (Like Loading, Related, Author, Tags, Post navigation, etc.)
  - Text-level: Filters WordPress.com prompts (Sign up, Log in, Create a blog, Join X subscribers, etc.)
  - Result: Winter Field Day article now ends at actual content without any WordPress chrome

## [htmlview.py v1.18 - Post-Processing Cleanup] - 2026-01-31
### Fixed
- **htmlview.py v1.18**: Enhanced text post-processing to remove junk lines
  - Filters "Menu", "Main Menu", "Navigation", "Nav" header lines after text extraction
  - Removes empty list markers (lines with just `-`, `•`, or bullets)
  - Properly filters social media links ("facebook [1]" style) after HTML parsing
  - Result: Cleaner output without stray dashes and menu headers

## [htmlview.py v1.17 - Enhanced WordPress Filtering] - 2026-01-31
### Fixed
- **htmlview.py v1.17**: More aggressive WordPress junk removal
  - Removes "Menu" section headers and standalone menu navigation blocks
  - Removes empty list items (just dashes/bullets)
  - Removes subscribe/newsletter widgets and email signup forms
  - Removes all form elements (not just comment forms)
  - Removes "Related" post sections more reliably
  - Result: Winter Field Day article now ends cleanly without author/tags/subscribe/related sections

## [rss-news.py v1.13 + htmlview.py v1.16 - Pagination & Junk Filtering] - 2026-01-31
### Changed
- **rss-news.py v1.13**: Display default changed to paginated
  - Previously: Default was "all at once" display
  - Now: Pagination is default (shows [default] in prompt)
  - Reduces overwhelming output on slow connections (1200 baud packet radio)
  - Users can still choose A)ll at once if preferred
  
- **htmlview.py v1.16**: Aggressive WordPress footer/metadata filtering
  - Removes post-navigation, comment sections, author boxes, related posts
  - Removes sharing buttons, tags metadata, tags sections
  - Removes "Like Loading..." and WP UI artifacts  
  - Removes entry-footer, author boxes, comment forms
  - Result: Clean article content without fluff
  - Example: Winter Field Day article now ends at actual content, not WordPress chrome

## [rss-news.py v1.12 - Article View State Fix] - 2026-01-31
### Fixed
- **rss-news.py v1.12**: Article view state now works correctly
  - Previously: Y/N to fetch article was broken - input went to wrong handler
  - Now: Y/N is handled properly within article_view state
  - Default behavior: pressing Enter = fetch article (Y is default)
  - Prompt now shows: "Fetch full article? Y)es [default], N)o, B)ack..."
  - B)ack now correctly returns to article list (not feed menu)
  - Q)uit works from article view to exit app

## [rss-news.py v1.11 + htmlview.py v1.15 - UX Improvements] - 2026-01-31
### Fixed
- **rss-news.py v1.11**: Back button from article view now returns to article list
  - Previously: B)ack from article jumped to feed menu (wrong scope)
  - Now: B)ack goes back to articles list for the current feed (correct scope)
  - Added 'article_view' state to track when viewing a single article
  
- **htmlview.py v1.15**: Proper rendering of HTML lists
  - Unordered lists (`<ul><li>`) now render with " - " prefix instead of blank lines
  - Ordered lists (`<ol><li>`) now render with numbers (1. 2. 3. etc)
  - Lists are processed before other HTML to ensure correct text extraction
  - Improves readability of structured content from WordPress, blogs, etc.

## [rss-news.py v1.10 - Performance Diagnostics] - 2026-01-31
### Added
- **rss-news.py v1.10**: Performance timing information
  - Added fetch time to article fetch results: "Article size: X.X KB (fetched in Y.Ys)"
  - Added format time tracking for large articles: "[Formatted in Y.Ys]"
  - Helps diagnose where slowness occurs: network fetch vs text processing

## [rss-news.py v1.9 - Faster Article Fetching] - 2026-01-31
### Fixed
- **rss-news.py v1.9**: Much faster HTML article extraction
  - Previously: Used full interactive HTMLViewer with stdout redirection (slow)
  - Now: Uses HTMLParser.parse() directly for text extraction only
  - Result: Article fetching now as fast as other HTML pages (gopher, www)
  - Also added stdout flush to show "Fetching..." message immediately

## [htmlview Title Width Fix] - 2026-01-31
### Fixed
- **htmlview.py v1.14**: Title width now respects terminal width
  - Previously: titles hardcoded to 40-char width (BPQ mobile standard)
  - Now: uses terminal width minus 2-char margin (80-char term → 78-char title)
  - Minimum 40 chars for backward compatibility with narrow terminals
  - Separator lines match actual title length (no awkward short lines)
  - Result: titles like "OverbiteWX – Get this Extension for Firefox..." display fully instead of truncated

## [htmlview/gopher Fixes - Emoji Filtering + Duplicate Message] - 2026-01-31
### Fixed
- **htmlview.py v1.13**: Strip emoji and non-ASCII unicode from text
  - Filters out emoji (🦊 etc), accents, and other unicode characters
  - Converts to ASCII-only display: "OverbiteWX – Get this Extension for 🦊..." → "OverbiteWX - Get this Extension for ..."
  - Keeps only ASCII printable characters (32-126) + tab/newline
  - Essential for 40-char terminal width and packet radio compatibility
  
- **gopher.py v1.43**: Remove duplicate "Fetching HTML" message
  - Was printing message twice (once at navigate_to start, once in HTML handler)
  - Now prints once only (from navigate_to)

## [htmlview/gopher Fixes - Link Quality + Display] - 2026-01-31
### Fixed
- **htmlview.py v1.12**: Filter out junk links from content links menu
  - Skip pure numeric links (rating numbers, review counts, page numbers)
  - Skip patterns like "5 stars", "15 reviews", "4 votes"
  - Prevents Mozilla Add-ons pages from showing "1", "2", "3", "4", "5" in links menu
  - Result: CONTENT LINKS menu shows only meaningful navigation (vs garbage numbers)
  
- **gopher.py v1.42**: Cleaner HTML fetch messages
  - When fetching HTML pages, show actual HTTP URL instead of raw Gopher selector
  - Before: "Connecting to gopher://gopher.floodgap.com:70/hURL:https://...
  - After: "Fetching HTML from: https://addons.mozilla.org/..."
  - Matches what htmlview displays for clarity

## [Multi-App htmlview Integration] - 2026-01-31
### Added
- **gopher.py v1.41**: HTML link rendering via htmlview
  - When Gopher links point to HTML pages, renders with htmlview instead of crude HTML stripping
  - Intelligent nav menu separation + content links menu
  - Automatic module download if not available
  - Falls back to basic HTMLStripper if htmlview unavailable
  
- **rss-news.py v1.8**: Full article rendering via htmlview
  - When fetching full articles from web, uses htmlview for clean rendering
  - Removes navigation menus and sidebars, surfaces actual article content
  - Priority: htmlview (best) → w3m (if available) → HTML stripping (fallback)
  - Automatic module download if not available
  
- **wiki.py v2.5**: htmlview auto-update at startup
  - Ensures htmlview module available before running (silent 3-second check)
  - Prepared for future external link rendering via htmlview

### Technical Details
- All three apps now call `ensure_htmlview_module()` at startup
- Automatic download of htmlview.py from GitHub if missing
- Silent auto-update check (3-second timeout, no blocking)
- Graceful fallback if htmlview unavailable (apps continue with basic rendering)
- No performance impact if htmlview module present (just one import)

## [htmlview.py v1.11 - Fix Link Following on Wrong Page] - 2026-01-31
### Fixed
- **htmlview.py v1.11**: Link numbers now only followable if visible on current page
  - Previously: pressing any link number worked globally across ALL content links
  - Now: only link numbers actually displayed on current page can be followed
  - If link is on different page: shows "Link [X] not on this page. Use L)inks to navigate."
  - Prevents confusion when trying to follow link [4] on page 1 when it's actually on page 3
  - Directs users to L)inks menu for cross-page navigation

## [htmlview.py v1.10 - Prompt Ordering and Unicode Fix] - 2026-01-30
### Fixed
- **htmlview.py v1.10**: Proper prompt ordering per standards + unicode-to-ASCII conversion
  - Moved W)here to correct position (after B)ack with page navigation, not at leftmost exit position)
  - Per copilot-instructions: scope ordering = Q)uit, M)ain, B)ack, W)here, S)ite, L)inks, Enter=more
  - Improved unicode entity handling: smart quotes (' "), en-dashes (-), em-dashes (--), ellipsis (...)
  - Converts numeric entities (&#8217; etc) and hex entities (&#x2019; etc) to ASCII
  - Fixes textfiles.com smart quotes displaying as ? characters
  - All three prompts now follow consistent standard ordering

## [htmlview.py v1.9 - Add Where Command] - 2026-01-30
### Added
- **htmlview.py v1.9**: W)here command to show current URL
  - Added W)here option to all three prompts (content page, site menu, content links)
  - Displays current URL for debugging when pages render poorly
  - Consistent with gopher.py pattern for user familiarity
  - Shows URL, waits for Enter, redisplays current page (non-destructive)
  - Helps diagnose encoding issues and verify page source

## [www.py v1.5 - Fix Error Navigation] - 2026-01-30
### Fixed
- **www.py v1.5**: Return to previous page on fetch error instead of main menu
  - When link fetch fails (404, timeout, etc.), prompt user and return to previous page
  - Prevents losing context when encountering broken links
  - User can try other links without re-navigating from main menu

## [htmlview.py v1.8 - WordPress Cleanup] - 2026-01-30
### Fixed
- **htmlview.py v1.8**: Aggressive WordPress junk filtering
  - Fixed content_links tuple inconsistency (pagination links removed - not useful)
  - Strip WordPress sidebars (<aside>, .sidebar, .widget divs)
  - Remove "Skip to content", "open primary menu", social media icons
  - Filter facebook/twitter/etc text lines from output
  - Result: Clean content starts immediately on mainepacketradio.org
  - First page now shows actual content, not 3 pages of sidebar

## [htmlview.py v1.7, www.py v1.4 - Version Bump, Key Fix, WordPress Nav] - 2026-01-30
### Fixed
- **htmlview.py v1.7**: Version bump + key handler fix + improved WordPress nav detection
  - S)ite menu key handler now works (was still using 'p' instead of 's')
  - WordPress/CMS nav detection: Use ONLY explicit `<nav>` tags when present
  - Filters article/main sections before detection to avoid blog post titles
  - Result: mainepacketradio.org shows 11 clean menu items (was 70 with blog titles)
- **www.py v1.4**: Version bump for consistency

## [htmlview.py v1.6.1 - Fix Site Menu Q)uit Signal] - 2026-01-30
### Fixed
- **htmlview.py v1.6.1**: Q)uit from site menu now exits app
  - Q)uit returns __EXIT__ signal instead of None (now properly exits app)
  - M)ain returns __MAIN__ signal to go to main menu
  - B)ack returns None (stays on page)

## [htmlview.py v1.6 - Rename P)age to S)ite, Filter Social Icons] - 2026-01-30
### Changed
- **htmlview.py v1.6**: Rename P)age to S)ite menu for clarity
  - Rename PAGE MENU to SITE MENU (more descriptive of site navigation structure)
  - Update all prompts: P)age -> S)ite for consistency
  - Filter out social media icons (facebook, twitter, instagram, etc.)
  - Social media icons don't render well in terminal, low value in text mode
  - Result: Cleaner site menu focused on actual navigation

## [htmlview.py v1.5 - Pagination/Deduplication Filter] - 2026-01-30
### Fixed
- **htmlview.py v1.5**: Deduplicate nav links and move pagination to content links
  - Move pagination links to L)inks menu instead of filtering them (they're legitimate content nav)
  - Deduplicate navigation links by href URL (fixes WordPress/responsive menu duplicates)
  - Cap nav links to max 75 items to prevent massive menus
  - Result: P)age menu clean (71 items), L)inks menu has pagination (2, Next, Previous)

## [htmlview.py v1.0 - Reusable HTML Viewer Module] - 2026-01-30
### Added
- **htmlview.py v1.0**: Reusable HTML viewer module for packet radio apps
  - Intelligent nav/content link separation using multiple heuristics
  - Detects `<nav>`, `<header>`, nav/menu class divs, link density patterns
  - P)age menu displays navigation links (site menus, sidebars)
  - L)inks shows content-only links (in-page links)
  - Direct link following (#number) during pagination
  - Can be imported by other apps: gopher.py, wiki.py, rss-news.py
  - Auto-download/update via ensure_htmlview_module() function

## [www.py v1.2 - htmlview Integration] - 2026-01-30
### Changed
- **www.py v1.2**: Refactored to use htmlview module
  - Intelligent nav/content link separation
  - P)age menu for site navigation links
  - L)inks for in-content links only
  - Auto-downloads htmlview.py module from GitHub
  - Better user experience on menu-heavy sites

## [www.py v1.0 - New Web Browser App] - 2026-01-30
### Added
- **www.py v1.0**: Terminal web browser for packet radio
  - Text-mode HTML rendering with numbered link navigation
  - Search via FrogFind.com (text-only search engine)
  - Pagination at 24 lines per page
  - Bookmarks: WS1SM, Maine Packet Radio, ARRL, QRZ, eHam, text-only news sites
  - Offline page caching (10 pages, 24-hour expiry)
  - Smart word wrapping for terminal width
  - Menu-based interface similar to GOPHER and WIKI apps
  - Configuration via www.conf (bookmarks, home page, search URL)
  - ASCII art logo
  - Auto-update functionality

## [repeater.py v1.7 - Reduce Pagination Size] - 2026-01-30
### Changed
- **repeater.py v1.7**: Pagination optimized for screen size
  - Reduced from 5 to 4 repeaters per page
  - Better fits on typical packet radio terminal screens
  - Prevents scrolling off-screen during pagination

## [repeater.py v1.6 - Redisplay Menu After Search] - 2026-01-30
### Changed
- **repeater.py v1.6**: Improved navigation UX
  - Menu redisplays after returning from search results
  - Users can see options without scrolling back
  - Better experience on packet radio terminals with limited scrollback

## [repeater.py v1.5 - Display Input Frequency] - 2026-01-30
### Changed
- **repeater.py v1.5**: Display input frequency for convenience
  - Format: "145.110 - (144.510)" shows both output and input frequencies
  - Users no longer need to calculate offset manually
  - Helpful for programming radios

## [repeater.py v1.4 - Fix API Field Names] - 2026-01-30
### Fixed
- **repeater.py v1.4**: Use correct RepeaterBook API field names
  - Changed from "Trustee" to "Callsign" field (correct API field name)
  - Calculate offset direction from "Input Freq" and "Frequency" fields
  - Display format: "Trustee: CALLSIGN" for clarity
  - Offset symbols now display correctly (+/- based on frequency difference)

## [repeater.py v1.3 - Display Formatting Fix] - 2026-01-30
### Fixed
- **repeater.py v1.3**: Repeater display formatting
  - Fixed callsign (trustee) display - now shows on separate line
  - Fixed offset direction symbols (+/-) - now displays correctly
  - Improved output structure with distinct lines for each field
  - Better handling of numeric offset values
  - Index number now prepends frequency line instead of separate line

## [repeater.py v1.2 - API Authentication Fix] - 2026-01-30
### Fixed
- **repeater.py v1.2**: RepeaterBook API authentication
  - Added proper User-Agent header per RepeaterBook requirements
  - Format: "BPQ-Repeater-Directory/1.2 (URL, email)"
  - Resolves 401 Unauthorized errors
  - No API key required for non-commercial use

### Changed
- **repeater.py v1.2**: Simplified about text
  - Removed authentication limitation note
  - API now works reliably for all search types

## [bpq32.cfg - APPLICATION Renumbering] - 2026-01-30
### Fixed
- **WS1EC bpq32.cfg**: Fixed APPLICATION number conflicts
  - DX: Changed from #8 to #9 (was conflicting with WALL)
  - REPEATER: Changed from #17 to #16 (alphabetical order)
  - QRZ: Changed from #16 to #17
  - WALL: Changed from #9 to #22 (alphabetical order)
  - WIKI: Changed from #22 to #23
  - WX: Changed from #23 to #24
  - All APPLICATION numbers now unique and alphabetical

## [repeater.py v1.1 - Enhanced Search Features] - 2026-01-30
### Added
- **repeater.py v1.1**: Enhanced search capabilities
  - Search by callsign (auto-lookup gridsquare via HamDB API)
  - Search by frequency (find repeaters near specific frequency with tolerance)
  - "My Location" quick search (remembers last search location)
  - Auto-detect user callsign from BPQ stdin
  - Save last search location to repeater.conf
  - Display user callsign in menu when connected via BPQ

### Changed
- **repeater.py v1.1**: Improved user experience
  - Callsign search suggests user's callsign as default
  - My Location menu option shows saved gridsquare
  - All search methods save location for quick re-search
  - Updated menu structure (6 options + About/Quit)

## [repeater.py v1.0 - Repeater Directory] - 2026-01-30
### Added
- **repeater.py v1.0**: Amateur radio repeater directory search
  - Search by gridsquare or state with proximity radius
  - RepeaterBook.com API integration (free public API)
  - Filter by band (6M, 2M, 1.25M, 70cm, 33cm, 23cm)
  - Display frequency, offset, tone (PL), location, callsign
  - Sort results by distance from search center
  - 30-day local caching for offline operation
  - Paginated display (5 repeaters per page, 40-char width)
  - Graceful offline fallback with cached searches
  - Lowercase ASCII art logo

## [eventcal.py v2.6 - Remove Word Wrapping] - 2026-01-30
### Changed
- **eventcal.py v2.6**: Removed automatic word wrapping
  - Display text as-is from calendar source (preserves original formatting)
  - No more line breaking on locations or descriptions
  - Calendar content controls its own formatting

## [eventcal.py v2.5 - Wordwrap Fix] - 2026-01-30
### Fixed
- **eventcal.py v2.5**: Fixed wordwrap in event detail view
  - Enforced 40-character max width for packet radio (previously used 80-char default)
  - Applied word wrapping to location field in detail view
  - Description text now properly wraps to terminal width

### Fixed
- **BUG FIX: CALENDAR application** - Fixed /etc/inetd.conf pointing to non-existent calendar.py instead of eventcal.py. Application now loads correctly.
- **BUG FIX: DX application conflict** - Fixed APPLICATION 22 DX app conflicting with AI (both on HOST 17). Changed DX to connect directly to DX Spider daemon on port 7300.
- **BUG FIX: NEWS 403 errors** - Replaced failed rsshub.app feeds (AP/Reuters) with working alternatives:
  - Associated Press: https://feedx.net/rss/ap.xml
  - Added CNN Top Stories: http://rss.cnn.com/rss/cnn_topstories.rss
  - Added NPR News: https://feeds.npr.org/1001/rss.xml

## [ai.py v1.2 - Politics/Religion Prohibition] - 2026-01-29
### Changed
- **ai.py v1.2**: Added politics and religion prohibition to Ham Radio commandments
  - Added commandment #11: "Never discuss politics or religion on the air"
  - Reinforces amateur radio etiquette in AI system prompt
  - Updated User-Agent to BPQ-AI/1.2

## [ai.py v1.1 - Rename and Unicode Fix] - 2026-01-29
### Changed
- **ai.py v1.1**: Renamed from gemini.py (reserves "gemini" for Gemini web protocol)
  - Renamed gemini.py → ai.py, gemini.conf → ai.conf
  - Enhanced system prompt with explicit Unicode/emoji prohibition
  - Added CRITICAL directive: ASCII only (characters 32-126), no Unicode, no emoji
  - Updated all references and documentation
  - BPQ APPLICATION command now uses "AI" instead of "GEMINI"

## [ai.py v1.0 - AI Chat Assistant] - 2026-01-29
### Added
- **ai.py v1.0**: AI chat assistant for amateur radio operators
  - Interactive chat powered by Google Gemini API (free tier)
  - Personalized greetings using HamDB/QRZ operator name lookup
  - Ham Radio Ten Commandments system prompt for appropriate tone/context
  - Brief responses optimized for 1200 baud packet radio
  - Conversational memory within session (last 10 exchanges)
  - Internet connectivity check with graceful offline message
  - ASCII-only output, 40-char width text wrapping
  - Config file for API key storage (ai.conf)
  - Interactive API key setup with instructions and Google link
  - Auto-update functionality with 3-second GitHub timeout
  - Ham radio sign-offs (73, Good DX, See you down the log)
  - Transactional prompts - user can quit at any time

## [rss-news.py v1.7 - Auto-Download Config] - 2026-01-29
### Changed
- **rss-news.py v1.7**: Auto-download rss-news.conf if missing during update check
  - Checks for missing rss-news.conf on startup (same time as app update check)
  - Downloads default config from GitHub if file doesn't exist
  - Never overwrites existing rss-news.conf (preserves user customizations)
  - Falls back silently to defaults if download fails (no internet)
  - Simplified installation - just download rss-news.py

## [predict.py v1.9 - Auto-Download Modules] - 2026-01-29
### Changed
- **predict.py v1.9**: Auto-download missing library files during startup
  - Checks for missing predict module files (geo.py, solar.py, ionosphere.py, regions.json, __init__.py)
  - Downloads missing files from GitHub if not present (3-second timeout)
  - Creates predict/ subdirectory automatically
  - Fails silently if download fails - user can manually download if needed
  - Simplifies installation - now just download predict.py and run it

## [gopher.py v1.40 - Auto-Download Config] - 2026-01-29
### Changed
- **gopher.py v1.40**: Auto-download gopher.conf if missing during update check
  - Checks for missing gopher.conf on startup (same time as app update check)
  - Downloads default config from GitHub if file doesn't exist
  - Never overwrites existing gopher.conf (preserves user customizations)
  - Falls back silently to defaults if download fails (no internet)

## [gopher.py v1.39 - External Config] - 2026-01-29
### Added
- **gopher.conf**: New JSON configuration file for bookmarks and settings
  - Easier to update bookmarks without editing Python code
  - Configuration: home page, bookmarks list, page size, timeouts
  - Falls back to sensible defaults if file missing or invalid

### Changed
- **gopher.py v1.39**: Load configuration from gopher.conf JSON file
  - Bookmarks now defined in external JSON file (easier for sysops to customize)
  - Graceful fallback to defaults if config file doesn't exist
  - Removed Gopherpedia bookmark (site currently down)
  - Default bookmarks: Floodgap, SDF Gopher

## [nodemap-html - Bidirectional Route Quality Check] - 2026-01-29
### Fixed
- **nodemap-html.py**: Map connections now require quality > 0 routes from BOTH nodes
  - Fixes issue where connection shown as viable when one sysop blocks route with quality 0
  - Example: K1NYY with 0 quality to W1EMA, but W1EMA non-zero to K1NYY
  - Connection line NOT drawn if either node has quality 0 route to other
  - Applies to both HTML (Leaflet) and SVG maps
  - Prevents users from attempting blocked routes shown as working

## [YAPP Dead End - Cleanup] - 2026-01-28
### Removed
- **yapp-demo-server.py**: Deleted proof-of-concept socket server
  - Proved protocol works via direct sockets
  - But packet radio users have no way to access socket servers
  - Cannot bypass BPQ32 stdio filtering (no outbound TELNET command)
  - Socket approach only works for internet users, not RF users

### Changed
- **yapp.py**: Updated header to "DEAD END - NOT VIABLE"
  - Clarified that packet radio users CANNOT bypass control byte filtering
  - Only access path is via APPLICATION (stdio) which strips < 0x20
  - Code retained as reference for unlikely case G8BPQ adds binary mode
- **YAPP-PROTOCOL.md**: Added prominent warning at top
  - Documents architectural impossibility for packet radio
  - Recommends text-based file serving instead (forms.py, gopher.py)
  - Research preserved for historical reference

## [YAPP Demo Server Created] - 2026-01-28
### Added
- **yapp-demo-server.py v1.0**: Proof-of-concept YAPP socket server
  - Demonstrates direct socket I/O bypasses control byte filtering
  - Simple echo server that responds to YAPP ENQ frames
  - Shows control characters (< 0x20) ARE received via direct sockets
  - Confirms problem is stdio/inetd pipeline, not protocol itself
  - Ready for testing on live node
  - Usage: `./yapp-demo-server.py --port 63020`

## [YAPP Binary Mode Research] - 2026-01-28
### Documentation
- **YAPP-PROTOCOL.md**: Conclusive research on telnet binary mode
  - Reviewed BPQ32/LinBPQ source code (150+ excerpts)
  - ProcessTelnetCommand() only supports echo and suppressgoahead
  - Binary mode (option 0) explicitly rejected with WONT
  - No ConnectionInfo field for binary mode flag
  - Control character filtering hardcoded in multiple code paths
  - **Verdict**: Telnet binary mode NOT VIABLE without C code changes
  - Updated Alternative 4 with test case that would fail
  - Confirms dedicated socket server is only practical solution

## [Gopher YAPP Disabled] - 2026-01-28
### Changed
- **gopher.py v1.16**: Disabled YAPP download functionality
  - YAPP control bytes (0x01-0x06) are stripped by BPQ32/inetd pipeline
  - Text files: V)iew only (removed D)ownload option)
  - Binary files: Display info only with explanation
  - Removed yapp.py dependency auto-update logic
  - Simplified startup banner (no YAPP status line)
  - See docs/YAPP-PROTOCOL.md for protocol details and future solutions

## [YAPP Status: Experimental] - 2026-01-28
### Changed
- **yapp.py v1.4**: Added STATUS: EXPERIMENTAL header
  - Documents control byte stripping issue by BPQ32/inetd/stdio pipeline
  - Lists potential solutions for future implementation
  - Protocol implementation complete but not functional over stdio
  - Retained as reference for future socket-based approach

## [Gopher Pagination Adjustment] - 2026-01-28
### Changed
- **gopher.py v1.15**: Increased page size from 20 to 24 lines
  - Matches standard terminal height (80x24)
  - Better screen utilization on typical terminals
  - Reduces number of page prompts for longer articles

## [YAPP Unbuffered Output] - 2026-01-28
### Fixed
- **yapp.py v1.3**: Force unbuffered binary mode for stdout
  - Uses `io.open(sys.stdout.fileno(), 'wb', buffering=0)`
  - sys.stdout.buffer can have line buffering that corrupts YAPP frames
  - Unbuffered mode ensures control bytes are sent immediately
  - Prevents frame header being split or buffered separately from payload
  - Should finally resolve "HD: File Header Error" in EasyTerm

## [Gopher Update Messages] - 2026-01-28
### Changed
- **gopher.py v1.14**: Improved update messages with more detail
  - `update_dependency()` now detects and reports yapp.py version changes
  - Shows "Installing dependency: yapp.py vX.Y" on first install
  - Shows "Updating dependency: yapp.py vX.Y -> vZ.W" on updates
  - Main app update includes script name: "gopher.py update available: vX.Y -> vZ.W"
  - Helps users understand what's being updated and why

## [Gopher YAPP Version Display] - 2026-01-28
### Changed
- **gopher.py v1.13**: Startup banner now shows YAPP module version
  - Imports `__version__` from yapp.py module
  - Displays "YAPP file download support: Enabled (yapp.py vX.Y)"
  - Helps verify correct yapp.py version is loaded
- **yapp.py v1.2**: Added `__version__ = "1.2"` constant for version detection

## [YAPP Binary Mode Fix] - 2026-01-28
### Fixed
- **yapp.py v1.2**: Force binary mode for stdin/stdout in create_stdio_yapp()
  - Control bytes (0x01-0x06, etc.) were being lost in text mode
  - Now properly accesses sys.stdin.buffer and sys.stdout.buffer
  - Falls back to io.open() for binary stream if buffer not available
  - Fixes "HD: File Header Error" in EasyTerm caused by missing SOH/length bytes
  - Ensures complete YAPP frames are transmitted correctly

## [YAPP Header Validation] - 2026-01-28
### Fixed
- **yapp.py v1.1**: Added header length validation
  - Headers limited to 256 bytes per YAPP protocol
  - Returns clear error if filename + filesize exceeds limit
  - Prevents silent truncation of headers > 256 bytes
  - Improves compatibility with EasyTerm and other YAPP clients

## [Gopher Update Exit Fix] - 2026-01-28
### Fixed
- **gopher.py v1.12**: App now exits properly after installing update
  - Changed `return` to `sys.exit(0)` after successful update install
  - Forces clean exit so user reconnects with new version
  - Prevents running stale code from memory after update
  - Updated message: "Please reconnect to use the updated version."

## [Gopher PNG Support] - 2026-01-28
### Added
- **gopher.py v1.11**: Added PNG image download support
  - Type 'p' (PNG) now recognized in ITEM_TYPES
  - Added to binary download handler alongside GIF, IMG types
  - PNG images can be downloaded via YAPP protocol

## [Gopher YAPP Import Fix] - 2026-01-28
### Fixed
- **gopher.py v1.10**: YAPP availability now detected correctly after dependency update
  - Added `reimport_yapp()` function to re-import yapp.py after download
  - Called after `check_for_app_update()` runs
  - Enables YAPP downloads immediately on first run (no restart needed)
  - Fixes "yapp.py not found" message when module was just downloaded

## [Gopher Dependency Auto-Update] - 2026-01-28
### Changed
- **gopher.py v1.9**: Auto-update now includes yapp.py dependency
  - `update_dependency()` function silently downloads/updates yapp.py from GitHub
  - Called during app startup update check (3-second timeout)
  - Ensures YAPP protocol module is always present and current
  - Graceful fallback if GitHub unreachable

## [Gopher YAPP Integration] - 2026-01-28
### Changed
- **gopher.py v1.8**: Added YAPP file download support
  - Text files (type 0): V)iew or D)ownload options
  - Binary files (types 4, 5, 6, 9, g, I, s): D)ownload option
  - Filenames extracted from selector path (last component after '/')
  - Graceful fallback if yapp.py unavailable
  - All file types now displayed in menus (not filtered)
  - Item selection filter only excludes 'i' (info lines)
  - YAPP status indicator on startup banner
  - Updated help text to mention download capability

## [YAPP Protocol Documentation] - 2026-01-28
### Added
- **YAPP Protocol Documentation** (`docs/YAPP-PROTOCOL.md`): Comprehensive technical documentation
  - Complete protocol specification with frame formats
  - Control characters (SOH, STX, ETX, EOT, ENQ, ACK, NAK, CAN)
  - Handshaking sequences for normal and error scenarios
  - State machine diagrams for sender and receiver
  - YAPPC extension for resume capability
  - Comparison with XMODEM, B2, FBB protocols
  - BPQ32 implementation analysis from linbpq source code
- **YAPP Python Implementation** (`apps/yapp.py`): Python 3.5.3 compatible module
  - `YAPPProtocol` class for sending and receiving files
  - Support for YAPPC resume capability
  - Timeout handling and error recovery
  - Debug mode for protocol tracing
  - Command-line interface for testing
  - stdio helper for BPQ application integration
- **Application Ideas**: Documented potential uses for YAPP in bpq-apps
  - Custom FILES repository (hierarchical, with metadata)
  - Gopher file downloads (binary type 9 items)
  - FTP browser (bridge internet FTP to packet users)

### Notes
- BPQ32 node rejects YAPP at command level ("Node doesn't support YAPP Transfers")
- All YAPP transfers must occur within BPQ APPLICATION contexts
- YAPP is streaming protocol (no per-block ACK) - efficient for packet radio
- Protocol relies on AX.25 layer for error correction

## [Offline Caching Update] - 2026-01-28
### Added
- **Offline support via cron-updated caches**: Multiple apps now support offline operation
  - `wx.py` v4.6: Local weather cache (`wx_cache.json`, -c flag, 2hr interval)
  - `rss-news.py` v1.6: RSS feed cache (`rss_cache.json`, -c flag, 2hr interval)
  - `hamqsl.py` v1.2: HF propagation cache (`hamqsl_cache.json`, -c flag, 4hr interval)
  - `space.py` v1.3: Space weather cache (`space_cache.json`, -c flag, 4hr interval)
  - `eventcal.py` v2.4: Calendar cache (`eventcal_cache.json`, -c flag, 6hr interval)
  - `predict.py` v1.8: Callsign lookup cache (`callsign_cache.json`, 30-day TTL)
- **Cache freshness display**: Shows timestamp when using cached data
  - Format: "Cached: 01/15/2026 at 10:00 EST"
  - Warning when data >24 hours old
- **INSTALLATION.md**: Added cron setup section with recommended schedules

### Changed
- `wall.py`: Renamed `wall_board.json` to `wall.json` for consistency

### Fixed
- `space.py`: Added missing `is_internet_available()` function (was referenced but undefined)

### Removed
- `clubcal.py`: Removed (redundant with eventcal.py)

## [wiki.py 2.4] - 2026-01-28
### Changed
- **Wiktionary UX**: Skip blank summary screen, go straight to full article for Wiktionary/Wikiquote/etc
  - Non-Wikipedia projects often have no summary (blank extract)
  - Auto-fetch full article for empty summaries, saves user keystroke
  - Still shows summary+menu for Wikipedia projects

## [wiki.py 2.3] - 2026-01-28
### Fixed
- **Wiktionary and non-ASCII content**: Search results and articles now sanitized for ASCII terminals
  - Removes Tamil script, IPA phonetic symbols, and Unicode characters
  - Keeps readable ASCII text: "From Tamil (kaumaram)" instead of "From Tamil கட்டுமரம् (kaṭṭumaram)"
  - Works for Wiktionary, Wikiquote, and other multilingual projects
- **Wiktionary article fetch**: Uses MediaWiki API fallback for projects where REST API unavailable
  - Wiktionary "catamaran" now fetches correctly with definition

## [wiki.py 2.2] - 2026-01-28
### Fixed
- **Q)uit during pagination**: Pressing Q during full article pagination now properly exits the app and returns to node
  - Previously only returned to article menu
  - Now sets quit flag that propagates through all nested calls
  - Works during pagination, full article view, and article menu

## [wiki.py 2.1] - 2026-01-28
### Added
- **B)ack navigation**: Return to previous article after following tangent links
  - Shows B)ack option only when history available
  - Navigates back without re-adding to history
  - Prompts: `[F]ull [L]inks [1-N] B)ack M)enu Q)uit`
  - Lets you explore references then return to continue reading

## [wiki.py 2.0] - 2026-01-28
### Changed
- **M) Menu prompt**: All prompts now include M to return to main menu
  - Article view: `[F]ull [L]inks [1-N] M) Q)uit :>`
  - Search results: `[1-N] or N)ext M) Q)uit :>`
  - Article pagination: `[Enter]=Next [1-N] M) Q)uit :>`
  - Both M and Q return to node (menu exit)

## [wiki.py 1.9] - 2026-01-28
### Changed
- **Inline link markers**: Links now shown as `[#]` markers within the text itself
  - "The Patriots compete in the National Football League[1] (NFL[2])..."
  - Type a number to follow that link directly
  - L) shows the full link list with titles
  - No more automatic link preview after summary

## [wiki.py 1.8] - 2026-01-28
### Changed
- **Contextual links**: Links now filtered to only those appearing in displayed text
  - Summary shows links found in summary (e.g., "NFL", "Gillette Stadium")
  - Full article shows links found in full text
  - Links sorted by order of appearance, not alphabetically
  - No more irrelevant "1960 Boston Patriots season" links in summary view

## [wiki.py 1.7] - 2026-01-28
### Added
- **Link preview**: Shows first 5 related links after article summary
  - Displays total link count: "Related Links (47 total)"
  - Users can immediately enter a number to navigate
  - Prompt now shows valid range: `[1-47]` instead of `[#]=Link`

## [wiki.py 1.6] - 2026-01-28
### Changed
- **Dynamic terminal width**: Text now wraps to actual terminal width instead of fixed value
- **Paragraph spacing**: Full articles display with blank lines between paragraphs for easier reading
- Width is queried dynamically at each display, adapting to terminal resizes

## [wiki.py 1.5] - 2026-01-28
### Changed
- **Paginated search results**: Display 5 results at a time instead of 10
  - Shows "Search Results (1-5 of 20)" header with current range
  - N) Next to see more results
  - Enter number anytime to select article (1-20)
  - Q) Quit to cancel search
  - Fetches up to 20 results for better browsing

## [wiki.py 1.4] - 2026-01-28
### Fixed
- **403 Forbidden error**: Wikipedia API now requires proper User-Agent header
  - Added User-Agent header to all HTTP requests via requests.Session
  - Format: `WikiPacketRadio/1.4 (https://github.com/bradbrownjr/bpq-apps; packet radio terminal)`
  - Searches and article fetches now work correctly

## [dict.py 1.9] - 2026-01-28
### Fixed
- **Silent auto-update**: Added update messages and proper exit after update
  - Now prints "Update available" and "Update installed successfully" messages
  - Returns from main() after successful update (prompts user to re-run)
  - Matches auto-update behavior of other apps (wiki, gopher, etc.)

## [dict.py 1.8] - 2026-01-28
### Fixed
- **Connection drop on quit**: Removed all return values from main()
  - Changed `return 0` and `return 1` to just `return`
  - BPQ interprets non-zero exit codes as errors, causing disconnection
  - App now exits cleanly without disconnecting stream

## [gopher.py 1.5] - 2026-01-28
### Fixed
- **Connection drop on auto-update**: Replaced `sys.exit(0)` with `return` in auto-update success path
  - Prevents BPQ from disconnecting stream when update is installed
  - Matches clean exit pattern used in other apps

## [dict.py 1.7] - 2026-01-28
### Fixed
- **Connection drop on quit**: Removed `sys.exit()` wrapper that caused BPQ to disconnect stream
  - Now calls `main()` directly without sys.exit()
  - Proper return to node prompt after quitting DICT
  - Matches pattern used in other BPQ apps

## [wiki.py 1.3] - 2026-01-28
### Changed
- **Removed callsign handling**: WIKI is an article reader and doesn't need user identification
  - Removed stdin callsign reading code entirely
  - Simplified startup - no more stdin handling
  - BPQ32 APPLICATION line should use `NOCALL K` (no S flag)
  - Faster startup without stdin checks

## [wiki.py 1.2] - 2026-01-28
### Fixed
- **Startup hang**: Fixed blocking stdin read that caused delay at startup
  - Now uses select() with 0.1s timeout to check if callsign data available
  - Only reads stdin if data is present (BPQ with S flag)
  - Removed redundant internet connectivity warning at startup
  - App now starts instantly when no callsign present

## [wiki.py 1.1] - 2026-01-28
### Fixed
- **Menu duplication**: Fixed double menu display caused by BPQ callsign input
  - App now consumes callsign line from stdin before showing menu
  - Same fix pattern used in other BPQ apps (wall.py, forms.py, etc.)

## [wiki.py 1.0] - 2026-01-28
### Added
- **wiki.py 1.0**: Wikipedia and sister wiki browser for packet radio
  - Search Wikipedia, Simple Wikipedia, Wiktionary, Wikiquote, Wikinews, Wikivoyage
  - Article summaries with optional full text viewing
  - Numbered link navigation for recursive browsing (similar to Gopher)
  - Smart word wrapping for any terminal width
  - Pagination for long articles (20 lines per page)
  - Random article feature
  - Offline caching (last 10 summaries, 24-hour expiry in wiki_cache.json)
  - Internet detection with graceful offline fallback
  - Uses MediaWiki REST API (direct API calls, not Wikipedia-API library due to Python 3.5.3 constraint)
  - Port 63170 (HOST 17 in BPQ32)
  - Python 3.5+ compatible with requests library

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
