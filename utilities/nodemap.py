#!/usr/bin/env python3
"""
Node Map Crawler for BPQ Packet Radio Networks
-----------------------------------------------
Automatically crawls through packet radio nodes to discover network topology.
Connects to nodes, retrieves MHEARD lists and INFO, and builds a map of
node connectivity for visualization.

Features:
- Discovers nodes via MHEARD lists on RF ports
- Extracts location data from INFO command
- Traverses network breadth-first to avoid loops
- Uses ROUTES command to find optimal paths
- Handles BPQ, FBB, and JNOS nodes
- Exports to JSON and CSV formats
- Reads BPQ telnet port from bpq32.cfg automatically
- Skips IP-based ports (focuses on RF connectivity)
- Detects and quarantines corrupt callsigns from un-FEC'd MHEARD packets
- Tracks first/last seen per node and link, and marks nodes offline or stale
- Remembers sysop-entered gridsquares in nodemap-overrides.json
- Fills missing locations from INFO text, geocoding, Callook/HamDB/QRZ
- Routes by NET/ROM link quality rather than raw hop count

Sidecar files (all safe to edit or delete):
  nodemap-overrides.json  sysop-entered grids, ignore list, whitelist
  nodemap-geocache.json   cached location lookups, so repeat crawls are free

Network Resources:
- Maine Packet Network: https://www.mainepacketradio.org/
- Network Map: https://n1xp.com/HAM/content/pkt/MEPktNtMap.pdf
- Station Map: https://n1xp.com/HAM/content/pkt/MEPktStMap.pdf
- BPQ Commands: https://cheatography.com/gcremerius/cheat-sheets/bpq-user-and-sysop-commands/
- BPQ Node Commands: https://www.cantab.net/users/john.wiseman/Documents/NodeCommands.html

Author: Brad Brown, KC1JMH
Date: January 2026
Version: 1.8.4
"""

__version__ = '1.8.4'

import sys
import socket
import time
import json
import csv
import glob
import re
import os
from collections import deque

# Telnet library import with future-proofing for Python 3.13+
# Note: telnetlib was deprecated in Python 3.11 and removed in 3.13
# For Python 3.13+, install telnetlib3: pip install telnetlib3
# Then use: from telnetlib3.telnetlib import Telnet (drop-in replacement)
telnetlib = None
_TELNET_IMPORT_ERROR = (
    "telnetlib is not available. Python 3.13 removed it from the standard\n"
    "library; install the drop-in replacement with: pip install telnetlib3")
try:
    import telnetlib
except ImportError:
    # Python 3.13+ - telnetlib removed from stdlib
    try:
        from telnetlib3 import telnetlib
    except ImportError:
        # Deliberately not fatal at import time. Plenty of what this script
        # does never opens a socket - reading the map, setting a gridsquare,
        # managing the ignore list - and refusing to start at all would make
        # those unusable on a current Python for no reason.
        telnetlib = None


def _require_telnet():
    """Fail loudly, but only once something actually needs to connect."""
    if telnetlib is None:
        colored_print("Error: " + _TELNET_IMPORT_ERROR, Colors.RED)
        sys.exit(1)


class Colors:
    """ANSI color codes for console output."""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def colored_print(message, color=None):
    """Print message with color if stdout is a terminal."""
    if color and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        print("{}{}{}".format(color, message, Colors.RESET))
    else:
        print(message)


# Check Python version
if sys.version_info < (3, 5):
    colored_print("Error: This script requires Python 3.5 or later.", Colors.RED)
    colored_print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ), Colors.YELLOW)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Callsign quality control
# ---------------------------------------------------------------------------
#
# MHEARD output is the only discovery source that arrives as bare AX.25 UI
# frames: no FEC, no ARQ, nothing that would catch a flipped bit before the
# TNC prints the address. ROUTES and the NODES table, by contrast, arrive
# inside an L2-acked NET/ROM session, so a callsign that shows up there has
# already survived a CRC. That asymmetry is the whole basis of the scoring
# below - MHEARD is a lead, structured output is evidence.
#
# Note that a node's `netrom_ssids` field is NOT structured evidence despite
# the name: crawl_node() populates it from the MHEARD SSIDs, not from ROUTES,
# so every ghost callsign carries one. Only `routes` and `own_aliases` count.


class CallsignValidator:
    """Structural validation and bit-error detection for observed callsigns."""

    # 1-2 character prefix (letter-letter, letter-digit, or digit-letter),
    # one digit, 1-4 letter suffix, optional AX.25 SSID.
    PATTERN = re.compile(r'^([A-Z0-9]{1,2}\d[A-Z]{1,4})(?:-(\d{1,2}))?$')

    # ITU prefix blocks allocated to the amateur service, keyed by first
    # character. Q is deliberately absent - it is reserved for Q signals and is
    # never issued to a station, which makes it a free catch for corruption
    # (a flipped bit in "N1QFY" lands on "Q1QFY" surprisingly often).
    ALLOCATED_PREFIXES = {
        'A': 'ABCDEFGHIJKLMNOPRSTUVWXYZ23456789',
        'B': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'C': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789',
        'D': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ2345679',
        'E': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567',
        'F': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'G': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'H': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ2345678',
        'I': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'J': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ2345678',
        'K': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'L': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789',
        'M': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'N': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'O': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'P': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567',
        'R': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'S': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789',
        'T': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ2345678',
        'U': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'V': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234568',
        'W': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        'X': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'Y': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'Z': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ2345678',
        '2': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '3': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '4': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '5': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '6': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '7': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '8': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '9': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    }

    # AX.25 destination fields that name a protocol or a broadcast, not a
    # station. BPQ will happily list these in MHEARD.
    RESERVED_WORDS = frozenset([
        'MAIL', 'NODES', 'NODE', 'ID', 'BEACON', 'QST', 'CQ', 'APRS', 'RELAY',
        'WIDE', 'TRACE', 'TCPIP', 'NETROM', 'BBS', 'CHAT', 'RMS', 'SYNC',
        'TEST', 'ALL', 'TIME', 'OPENBCM', 'FBB',
    ])

    @staticmethod
    def is_structurally_valid(callsign):
        """True if the string could be a real callsign at all."""
        if not callsign:
            return False
        up = callsign.upper()
        if up.split('-')[0] in CallsignValidator.RESERVED_WORDS:
            return False
        m = CallsignValidator.PATTERN.match(up)
        if not m:
            return False
        # AX.25 carries the SSID in 4 bits, so 0-15 and nothing else.
        if m.group(2) is not None and int(m.group(2)) > 15:
            return False
        prefix = m.group(1)
        allowed = CallsignValidator.ALLOCATED_PREFIXES.get(prefix[0])
        if allowed is None:
            return False
        if len(prefix) > 1 and prefix[1] not in allowed:
            return False
        return True

    @staticmethod
    def _substitution_distance(a, b):
        """Count differing positions, or None when the lengths differ.

        Deliberately not a full edit distance. A corrupted AX.25 address keeps
        its length - the field is a fixed 7 bytes - so real corruption shows up
        as substitution, never as an insertion or deletion. Using Levenshtein
        here would pull in genuine callsigns that merely happen to be short
        (W1ZE is edit-distance 2 from W1EMA, and both are real stations).
        """
        if len(a) != len(b):
            return None
        return sum(1 for x, y in zip(a, b) if x != y)

    @staticmethod
    def classify(raw_callsign, confirmed, structured=None, heard_by=1):
        """Judge one observed callsign.

        Args:
            raw_callsign: the callsign as it came off the wire, case preserved
            confirmed: set of base callsigns we connected to or read from
                       an own_aliases map - these are known-good anchors
            structured: set of base callsigns seen in some node's ROUTES table
            heard_by: how many distinct nodes reported hearing it

        Returns:
            (verdict, reason) where verdict is 'confirmed', 'unverified'
            or 'suspect'. Callers quarantine 'suspect' and keep the rest.
        """
        structured = structured or set()
        base = raw_callsign.split('-')[0]
        up = base.upper()

        # Structured NET/ROM corroboration outranks every heuristic below it.
        # This is the escape hatch that keeps a genuinely new station from
        # being quarantined just for resembling an established one.
        trusted = up in confirmed or up in structured

        if up in CallsignValidator.RESERVED_WORDS:
            return 'suspect', 'reserved_word'

        # AX.25 shifts uppercase ASCII into the address field; there is no way
        # to transmit a lowercase callsign. Lowercase means a flipped bit.
        if base != base.upper() and not trusted:
            return 'suspect', 'case_anomaly'

        if not CallsignValidator.is_structurally_valid(base):
            m = CallsignValidator.PATTERN.match(up)
            if m and m.group(2) is not None and int(m.group(2)) > 15:
                return 'suspect', 'bad_ssid'
            if m:
                return 'suspect', 'unallocated_prefix'
            return 'suspect', 'malformed'

        if trusted:
            return 'confirmed', 'structured'

        # Bit-error signature: same length as a known-good call, differing in
        # only a position or two. The threshold tightens for short callsigns -
        # at four characters, two substitutions is half the string, and real
        # pairs collide there (N1EP vs NG1P differ in 2 of 4 positions).
        limit = 1 if len(up) <= 4 else 2
        # Report the closest anchor, not merely the first one that matched:
        # this string is what a sysop reads when deciding whether the
        # quarantine was right, so it needs to name the likeliest original.
        best_match, best_distance = None, None
        for good in confirmed:
            d = CallsignValidator._substitution_distance(up, good)
            if d is not None and 0 < d <= limit:
                if best_distance is None or d < best_distance or (
                        d == best_distance and good < best_match):
                    best_match, best_distance = good, d
        if best_match:
            return 'suspect', 'bit_error:{}'.format(best_match)

        # Truncation signature: the frame was cut short mid-address, leaving a
        # strict prefix of a real call.
        candidates = sorted(good for good in confirmed
                            if 3 <= len(up) < len(good) and good.startswith(up))
        if candidates:
            return 'suspect', 'truncated:{}'.format(candidates[0])

        # Heard independently by two different nodes: two receivers are
        # unlikely to invent the same corruption, so treat that as real.
        if heard_by >= 2:
            return 'confirmed', 'multi_source_mheard'
        return 'unverified', 'single_source_mheard'

def _now():
    """Timestamp in the fixed-width format the rest of the export already uses."""
    return time.strftime('%Y-%m-%d %H:%M:%S')


def _base_call(callsign):
    """Strip an AX.25 SSID, returning the bare callsign in uppercase."""
    if not callsign:
        return callsign
    return callsign.split('-')[0].upper()


class OverrideStore:
    """Sysop-entered facts that a crawl must never overwrite.

    nodemap.json is regenerated from what the network says on each run, so
    anything a human typed in has to live somewhere the crawl only reads.
    Before this existed, a hand-entered gridsquare survived exactly until the
    next crawl of that node: export_json() replaced the whole node dict, and a
    node whose INFO text has no grid in it re-exported as gridsquare=None.

    Holds four maps:
      grids      callsign -> gridsquare, authoritative over anything parsed
      locations  callsign -> city/state, same precedence
      ignore     callsign -> never crawl, never map (quarantined ghosts and
                 anything the sysop rejected by hand)
      confirm    callsign -> force 'confirmed', overriding the bit-error
                 heuristics for a real station that resembles another one
    """

    FILENAME = 'nodemap-overrides.json'
    VERSION = 1

    def __init__(self, filename=None, verbose=False):
        self.filename = filename or self.FILENAME
        self.verbose = verbose
        self.grids = {}
        self.locations = {}
        self.ignore = {}
        self.confirm = {}
        self.load()

    def load(self):
        if not os.path.exists(self.filename):
            return
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
        except (ValueError, IOError) as e:
            # A damaged overrides file must not take the crawl down with it.
            colored_print("Warning: could not read {}: {}".format(
                self.filename, e), Colors.YELLOW)
            return
        self.grids = data.get('grids', {}) or {}
        self.locations = data.get('locations', {}) or {}
        self.ignore = data.get('ignore', {}) or {}
        self.confirm = data.get('confirm', {}) or {}
        if self.verbose:
            print("Loaded overrides: {} grids, {} ignored, {} confirmed".format(
                len(self.grids), len(self.ignore), len(self.confirm)))

    def save(self):
        data = {
            'version': self.VERSION,
            'updated': _now(),
            'comment': 'Sysop-entered data. nodemap.py reads this and never '
                       'overwrites it from a crawl. Safe to edit by hand.',
            'grids': self.grids,
            'locations': self.locations,
            'ignore': self.ignore,
            'confirm': self.confirm,
        }
        tmp = self.filename + '.tmp'
        try:
            with open(tmp, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write('\n')
            os.rename(tmp, self.filename)      # atomic, survives a crash mid-write
        except IOError as e:
            colored_print("Warning: could not save {}: {}".format(
                self.filename, e), Colors.YELLOW)

    # -- lookups ----------------------------------------------------------
    # Every lookup tries the exact key first, then the bare callsign, so an
    # override entered against "NG1P" still applies once the crawl learns the
    # node is really "NG1P-4".

    def _lookup(self, table, callsign):
        if not callsign:
            return None
        if callsign in table:
            return table[callsign]
        base = _base_call(callsign)
        if base in table:
            return table[base]
        for key, value in table.items():
            if _base_call(key) == base:
                return value
        return None

    def grid_for(self, callsign):
        entry = self._lookup(self.grids, callsign)
        return entry.get('grid') if entry else None

    def location_for(self, callsign):
        entry = self._lookup(self.locations, callsign)
        return dict(entry) if entry else None

    def is_ignored(self, callsign):
        return self._lookup(self.ignore, callsign) is not None

    def is_confirmed(self, callsign):
        return self._lookup(self.confirm, callsign) is not None

    # -- mutations --------------------------------------------------------

    def set_grid(self, callsign, grid, source='manual'):
        self.grids[callsign] = {
            'grid': grid, 'source': source, 'updated': _now()}

    def set_location(self, callsign, city=None, state=None, source='manual'):
        entry = {'source': source, 'updated': _now()}
        if city:
            entry['city'] = city
        if state:
            entry['state'] = state
        self.locations[callsign] = entry

    def add_ignore(self, callsign, reason, source='quarantine'):
        """Record a callsign the crawler should stop spending air time on.

        Re-quarantining an already-ignored call bumps its hit count rather
        than resetting it, so a persistently-reappearing ghost is visible as
        such in the file.
        """
        key = _base_call(callsign)
        existing = self.ignore.get(key)
        if existing:
            existing['hits'] = existing.get('hits', 1) + 1
            existing['last_seen'] = _now()
            existing['reason'] = reason
            return False
        self.ignore[key] = {
            'reason': reason,
            'source': source,
            'added': _now(),
            'last_seen': _now(),
            'hits': 1,
        }
        return True

    def remove_ignore(self, callsign):
        key = _base_call(callsign)
        for candidate in [key] + [k for k in self.ignore if _base_call(k) == key]:
            if candidate in self.ignore:
                del self.ignore[candidate]
                return True
        return False

    def add_confirm(self, callsign, reason='sysop confirmed'):
        """Whitelist a real station that the corruption heuristics flag.

        Also lifts any existing ignore entry - keeping both would leave the
        call whitelisted and still un-crawlable.
        """
        key = _base_call(callsign)
        self.confirm[key] = {'reason': reason, 'added': _now()}
        self.remove_ignore(key)

# ---------------------------------------------------------------------------
# Location resolution
# ---------------------------------------------------------------------------
#
# A node's own INFO text is the only location source a crawl gets for free,
# and it is freeform sysop prose - some nodes state a gridsquare, most name a
# mountain or a town, and a few say nothing at all. Everything below is a
# ladder of decreasing confidence, tried in order and stopped at the first
# hit, with every network answer cached to disk so a repeat crawl costs
# nothing and an offline node degrades to "whatever we already knew".

US_STATES = frozenset([
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
    'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
    'WI', 'WY', 'DC', 'PR', 'VI', 'GU', 'AS', 'MP',
    # Canadian provinces and territories - the Maritimes are RF neighbours.
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT',
])

# Words that the old City/State regex happily accepted as a city name. The
# pattern "([A-Z][a-z]+),?\s+([A-Z]{2})" matches "Packet BBS" and "Node EM"
# just as readily as "Portland ME", which is how nodes ended up on the map at
# a city of literally "Node".
PLACE_NOISE_WORDS = frozenset([
    'node', 'packet', 'bbs', 'net', 'winlink', 'rms', 'chat', 'mail', 'gateway',
    'digipeater', 'digi', 'repeater', 'system', 'server', 'station', 'sysop',
    'welcome', 'info', 'baud', 'port', 'ports', 'mhz', 'khz', 'user', 'users',
    'connect', 'telnet', 'radio', 'amateur', 'club', 'group', 'county',
    'emergency', 'ares', 'races', 'skywarn', 'the', 'and', 'this', 'is',
])

# Landmarks worth geocoding on their own. Packet nodes live on hilltops and
# the sysop almost always says so ("on Streaked Mtn", "Mt Washington site").
LANDMARK_RE = re.compile(
    r'\b((?:Mt\.?|Mount|Mtn\.?)\s+[A-Z][A-Za-z]+'
    r'|[A-Z][A-Za-z]+\s+(?:Mountain|Mtn\.?|Hill|Ridge|Peak|Summit|Island|Butte|Knob))\b')

# "QTH is Foo", "located in Foo", "Foo, ME" - the keyword forms are much more
# reliable than a bare capitalised word and are tried first.
QTH_RE = re.compile(
    r'(?:QTH|Location|Located|Site|Based)\s*(?:is|in|at|near|:)?\s*'
    r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})', re.IGNORECASE)
CITY_STATE_RE = re.compile(
    r'\b((?:St\.?|Mt\.?|Ft\.?|Pt\.?)\s+)?'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}),?\s+([A-Z]{2})\b')
CITY_STATE_CAPS_RE = re.compile(
    r'\b([A-Z][A-Z.\']{1,}(?:\s+[A-Z][A-Z.\']{1,}){0,2}),\s*([A-Z]{2})\b')
# Words that lead into a place name without being part of it.
PLACE_LEAD_WORDS = frozenset(['at', 'in', 'on', 'near', 'from', 'the', 'is', 'of'])

# Degrees-and-minutes as well as decimal: "43 39.5 N 070 15.2 W" and "43.66N".
LATLON_RE = re.compile(
    r'(\d{1,3})(?:\s*[.:]\s*|\s+)?(\d{0,2}(?:\.\d+)?)\s*([NS])'
    r'[\s,/]+(\d{1,3})(?:\s*[.:]\s*|\s+)?(\d{0,2}(?:\.\d+)?)\s*([EW])',
    re.IGNORECASE)


def latlon_to_grid(lat, lon, precision=6):
    """Convert decimal degrees to a Maidenhead locator.

    Returns None rather than raising on out-of-range input - callers feed this
    straight from scraped INFO text, where a "latitude" of 4366 is normal.
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        return None

    lat += 90.0
    lon += 180.0
    grid = chr(int(lon / 20) + ord('A')) + chr(int(lat / 10) + ord('A'))
    grid += str(int((lon % 20) / 2)) + str(int(lat % 10))
    if precision >= 6:
        grid += chr(int((lon % 2) * 12) + ord('a'))
        grid += chr(int((lat % 1) * 24) + ord('a'))
    return grid


def _dm_to_decimal(degrees, minutes, hemisphere):
    """Combine a degrees/minutes/hemisphere triple into decimal degrees."""
    try:
        value = float(degrees) + (float(minutes) / 60.0 if minutes else 0.0)
    except ValueError:
        return None
    if hemisphere.upper() in ('S', 'W'):
        value = -value
    return value


class LocationResolver:
    """Resolves a node's position, cheapest and most trustworthy source first.

    Order of preference:
      1. sysop override           (OverrideStore - always wins)
      2. gridsquare in INFO text  (the sysop stated it outright)
      3. lat/lon in INFO text     (converted to a grid)
      4. place name in INFO text  (landmark or town, geocoded)
      5. callsign lookup          (Callook, then HamDB, then QRZ)

    Every network result is cached in nodemap-geocache.json keyed by query, so
    the second crawl of a network costs no HTTP at all, and a node with no
    internet simply falls through to whatever the cache already holds. No
    lookup is ever allowed to raise: an emergency-time crawl on a dead uplink
    has to keep going.
    """

    CACHE_FILE = 'nodemap-geocache.json'
    USER_AGENT = 'bpq-apps-nodemap/{} (+https://github.com/bradbrownjr/bpq-apps)'
    TIMEOUT = 8

    def __init__(self, enabled=True, verbose=False, cache_file=None,
                 qrz_user=None, qrz_pass=None):
        self.enabled = enabled          # False disables all network lookups
        self.verbose = verbose
        self.cache_file = cache_file or self.CACHE_FILE
        self.cache = {}
        self.dirty = False
        self.qrz_user = qrz_user
        self.qrz_pass = qrz_pass
        self.qrz_session = None
        self.qrz_failed = False         # stop retrying a bad login every node
        self.offline = False            # set after the first connection failure
        self._last_nominatim = 0.0      # Nominatim asks for <=1 request/second
        self.stats = {'cache_hit': 0, 'lookup': 0, 'fail': 0}
        self._load_cache()

    # -- cache ------------------------------------------------------------

    def _load_cache(self):
        if not os.path.exists(self.cache_file):
            return
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        except (ValueError, IOError):
            self.cache = {}

    def save_cache(self):
        if not self.dirty:
            return
        try:
            tmp = self.cache_file + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(self.cache, f, indent=2, sort_keys=True)
                f.write('\n')
            os.rename(tmp, self.cache_file)
        except IOError:
            pass

    def _cached(self, key):
        entry = self.cache.get(key)
        if entry is not None:
            self.stats['cache_hit'] += 1
        return entry

    def _store(self, key, value):
        self.cache[key] = value
        self.dirty = True
        return value

    # -- HTTP -------------------------------------------------------------

    def _fetch(self, url):
        """GET a URL, returning the body as text or None. Never raises."""
        if not self.enabled or self.offline:
            return None
        try:
            import urllib.request
            request = urllib.request.Request(url, headers={
                'User-Agent': self.USER_AGENT.format(__version__)})
            response = urllib.request.urlopen(request, timeout=self.TIMEOUT)
            try:
                return response.read().decode('utf-8', 'replace')
            finally:
                response.close()
        except Exception as e:
            # Anything at all - DNS failure, TLS error, timeout, 404, a proxy
            # returning HTML. The crawl is the point; location is a bonus.
            if self.verbose:
                print("    lookup failed ({}): {}".format(url.split('?')[0], e))
            self.stats['fail'] += 1
            # One connection-level failure means the uplink is down; stop
            # burning eight seconds per node discovering that repeatedly.
            if isinstance(e, (IOError, OSError)) and not hasattr(e, 'code'):
                self.offline = True
                if self.verbose:
                    print("    no internet - disabling further lookups")
            return None

    # -- INFO text --------------------------------------------------------

    @staticmethod
    def parse_info_text(text):
        """Pull whatever location signal exists out of freeform INFO output.

        Returns a dict that may contain grid, lat, lon, city, state, place.
        Nothing here contacts the network.
        """
        location = {}
        if not text:
            return location

        # A stated gridsquare is the strongest thing INFO can give us. Accept
        # 4-character grids too - plenty of sysops only publish FN43.
        grid_match = re.search(r'\b([A-R]{2}\d{2}(?:[a-x]{2})?)\b', text, re.IGNORECASE)
        if grid_match:
            grid = grid_match.group(1)
            location['grid'] = grid[:4].upper() + grid[4:].lower()

        latlon = LATLON_RE.search(text)
        if latlon:
            lat = _dm_to_decimal(latlon.group(1), latlon.group(2), latlon.group(3))
            lon = _dm_to_decimal(latlon.group(4), latlon.group(5), latlon.group(6))
            if lat is not None and lon is not None and abs(lat) <= 90 and abs(lon) <= 180:
                location['lat'] = lat
                location['lon'] = lon

        landmark = LANDMARK_RE.search(text)
        if landmark:
            location['place'] = landmark.group(1).strip()

        # Only accept City, ST when ST is a real state or province and the
        # city word is not obvious node boilerplate.
        for match in CITY_STATE_RE.finditer(text):
            prefix = (match.group(1) or '').strip()
            city = ('{} {}'.format(prefix, match.group(2)) if prefix
                    else match.group(2)).strip()
            state = match.group(3).upper()
            if state not in US_STATES:
                continue
            words = [w.lower() for w in city.split()]
            if any(w in PLACE_NOISE_WORDS for w in words):
                continue
            location['city'] = city
            location['state'] = state
            break

        if 'city' not in location:
            for match in CITY_STATE_CAPS_RE.finditer(text):
                state = match.group(2).upper()
                if state not in US_STATES:
                    continue
                words = match.group(1).split()
                # Drop a leading preposition the greedy match swept up, e.g.
                # "AT WINDHAM" -> "WINDHAM".
                while words and words[0].lower() in PLACE_LEAD_WORDS:
                    words.pop(0)
                if not words:
                    continue
                if any(w.lower() in PLACE_NOISE_WORDS for w in words):
                    continue
                location['city'] = ' '.join(w.title() for w in words)
                location['state'] = state
                break

        if 'city' not in location:
            qth = QTH_RE.search(text)
            if qth:
                candidate = qth.group(1).strip()
                words = [w.lower() for w in candidate.split()]
                if not any(w in PLACE_NOISE_WORDS for w in words):
                    location.setdefault('place', candidate)

        return location

    # -- network sources --------------------------------------------------

    def geocode_place(self, place, state=None):
        """Geocode a free-text place name via OpenStreetMap Nominatim."""
        query = place if not state else '{}, {}'.format(place, state)
        key = 'geocode:' + query.lower()
        cached = self._cached(key)
        if cached is not None:
            return cached or None

        import urllib.parse
        # Nominatim's usage policy caps this at one request per second.
        elapsed = time.time() - self._last_nominatim
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        self._last_nominatim = time.time()

        url = ('https://nominatim.openstreetmap.org/search?q={}&format=json'
               '&limit=1&countrycodes=us,ca'.format(urllib.parse.quote(query)))
        self.stats['lookup'] += 1
        body = self._fetch(url)
        if not body:
            return None
        try:
            results = json.loads(body)
        except ValueError:
            return None
        if not results:
            self._store(key, {})       # cache the miss, do not re-ask
            return None
        top = results[0]
        grid = latlon_to_grid(top.get('lat'), top.get('lon'))
        if not grid:
            self._store(key, {})
            return None
        return self._store(key, {
            'grid': grid,
            'lat': float(top['lat']),
            'lon': float(top['lon']),
            'source': 'nominatim:' + query,
        })

    def lookup_callsign(self, callsign):
        """Look up a callsign's location, trying the free services first."""
        base = _base_call(callsign)
        key = 'call:' + base
        cached = self._cached(key)
        if cached is not None:
            return cached or None

        for method in (self._callook, self._hamdb, self._qrz):
            result = method(base)
            if result:
                return self._store(key, result)
        # Cache the miss too - re-asking three services per crawl for a
        # Canadian or club call that none of them carry is pure air time.
        self._store(key, {})
        return None

    def _callook(self, callsign):
        """callook.info - free, no key, FCC data, US callsigns only."""
        self.stats['lookup'] += 1
        body = self._fetch('https://callook.info/{}/json'.format(callsign))
        if not body:
            return None
        try:
            data = json.loads(body)
        except ValueError:
            return None
        if data.get('status') != 'VALID':
            return None
        loc = data.get('location', {}) or {}
        addr = data.get('address', {}) or {}
        grid = (loc.get('gridsquare') or '').strip()
        if not grid and loc.get('latitude') and loc.get('longitude'):
            grid = latlon_to_grid(loc['latitude'], loc['longitude'])
        if not grid:
            return None
        result = {'grid': grid, 'source': 'callook'}
        # "PORTLAND, ME" in a single line field.
        line2 = (addr.get('line2') or '').strip()
        if ',' in line2:
            city, _, tail = line2.rpartition(',')
            # tail looks like "ME 04640"; keep the state, drop the ZIP.
            state = tail.strip().split()[0].upper() if tail.strip() else ''
            if state in US_STATES:
                result['city'] = city.strip().title()
                result['state'] = state
        return result

    def _hamdb(self, callsign):
        """hamdb.org - free, no key, wider coverage than callook."""
        self.stats['lookup'] += 1
        body = self._fetch(
            'https://api.hamdb.org/v1/{}/json/bpq-nodemap'.format(callsign))
        if not body:
            return None
        try:
            data = json.loads(body).get('hamdb', {}).get('callsign', {})
        except (ValueError, AttributeError):
            return None
        grid = (data.get('grid') or '').strip()
        if grid.upper() in ('', 'NOT_FOUND'):
            return None
        result = {'grid': grid, 'source': 'hamdb'}
        state = (data.get('state') or '').strip().upper()
        if data.get('addr2') and state in US_STATES:
            result['city'] = data['addr2'].title()
            result['state'] = state
        return result

    def _qrz(self, callsign):
        """QRZ XML API - needs the credentials from the qrz3.py config."""
        if not self.qrz_user or not self.qrz_pass or self.qrz_failed:
            return None
        if not self.qrz_session and not self._qrz_login():
            return None

        import xml.etree.ElementTree as ET
        self.stats['lookup'] += 1
        body = self._fetch('https://xmldata.qrz.com/xml/current/?s={};callsign={}'
                           .format(self.qrz_session, callsign))
        if not body:
            return None
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return None
        ns = {'q': 'http://xmldata.qrz.com'}

        def field(name):
            node = root.find('.//q:{}'.format(name), ns)
            return node.text.strip() if node is not None and node.text else None

        # A session can expire between crawls; drop it and let the next node
        # re-login rather than failing every remaining lookup.
        if field('Error') and 'session' in field('Error').lower():
            self.qrz_session = None
            return None

        grid = field('grid')
        if not grid:
            lat, lon = field('lat'), field('lon')
            grid = latlon_to_grid(lat, lon) if lat and lon else None
        if not grid:
            return None
        result = {'grid': grid, 'source': 'qrz'}
        if field('addr2'):
            result['city'] = field('addr2')
        state = (field('state') or '').strip().upper()
        if state in US_STATES:
            result['state'] = state
        return result

    def _qrz_login(self):
        import urllib.parse
        import xml.etree.ElementTree as ET
        body = self._fetch(
            'https://xmldata.qrz.com/xml/current/?username={};password={};agent=bpq-nodemap'
            .format(urllib.parse.quote_plus(self.qrz_user),
                    urllib.parse.quote_plus(self.qrz_pass)))
        if not body:
            return False
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            self.qrz_failed = True
            return False
        ns = {'q': 'http://xmldata.qrz.com'}
        key = root.find('.//q:Key', ns)
        if key is not None and key.text:
            self.qrz_session = key.text.strip()
            return True
        error = root.find('.//q:Error', ns)
        if error is not None and error.text:
            colored_print("QRZ login failed: {}".format(error.text.strip()),
                          Colors.YELLOW)
        # Bad credentials will not fix themselves mid-crawl.
        self.qrz_failed = True
        return False

    # -- the ladder -------------------------------------------------------

    def resolve(self, callsign, info_text=None, existing=None):
        """Best-effort location for one node.

        Returns a dict with at least 'grid' and 'location_source', or None.
        'location_source' records which rung of the ladder answered, so the
        map and the mepn import can weight a scraped guess differently from a
        gridsquare the sysop published.
        """
        parsed = self.parse_info_text(info_text) if info_text else {}

        if parsed.get('grid'):
            return {'grid': parsed['grid'], 'location_source': 'info_grid',
                    'city': parsed.get('city'), 'state': parsed.get('state')}

        if parsed.get('lat') is not None and parsed.get('lon') is not None:
            grid = latlon_to_grid(parsed['lat'], parsed['lon'])
            if grid:
                return {'grid': grid, 'lat': parsed['lat'], 'lon': parsed['lon'],
                        'location_source': 'info_latlon',
                        'city': parsed.get('city'), 'state': parsed.get('state')}

        # An existing grid from a previous crawl beats a fresh network guess.
        if existing and existing.get('grid'):
            return None

        if parsed.get('place'):
            hit = self.geocode_place(parsed['place'], parsed.get('state'))
            if hit:
                return {'grid': hit['grid'], 'lat': hit.get('lat'),
                        'lon': hit.get('lon'), 'location_source': 'info_place',
                        'place': parsed['place'],
                        'city': parsed.get('city'), 'state': parsed.get('state')}

        if parsed.get('city') and parsed.get('state'):
            hit = self.geocode_place(parsed['city'], parsed['state'])
            if hit:
                return {'grid': hit['grid'], 'lat': hit.get('lat'),
                        'lon': hit.get('lon'), 'location_source': 'info_city',
                        'city': parsed['city'], 'state': parsed['state']}

        hit = self.lookup_callsign(callsign)
        if hit:
            return {'grid': hit['grid'],
                    'location_source': 'lookup_' + hit.get('source', 'unknown'),
                    'city': hit.get('city') or parsed.get('city'),
                    'state': hit.get('state') or parsed.get('state')}
        return None


def load_qrz_credentials(verbose=False):
    """Read qrz_user/qrz_pass out of the qrz3.py config, if it is installed.

    Parsed with a regex rather than imported: config.py sits in the apps
    directory next to modules that do real work at import time, and a network
    crawler has no business executing them.
    """
    candidates = [
        os.path.expanduser('~/apps/config.py'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'apps', 'config.py'),
        os.path.expanduser('~/bpq-apps/apps/config.py'),
        'config.py',
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r') as f:
                text = f.read()
        except IOError:
            continue
        user = re.search(r'^\s*qrz_user\s*=\s*[\'"]([^\'"]*)[\'"]', text, re.M)
        password = re.search(r'^\s*qrz_pass\s*=\s*[\'"]([^\'"]*)[\'"]', text, re.M)
        if user and password and user.group(1) and password.group(1):
            if verbose:
                print("Using QRZ credentials from {}".format(path))
            return user.group(1), password.group(1)
    return None, None


class NodeCrawler:
    """Crawls BPQ packet radio network to discover topology."""
    
    # Valid amateur radio callsign pattern: 1-2 prefix chars, digit, 1-3 suffix chars, optional -SSID
    # Retained for compatibility; CallsignValidator is now authoritative.
    CALLSIGN_PATTERN = CallsignValidator.PATTERN
    
    def __init__(self, host='localhost', port=None, callsign=None, max_hops=10, username=None, password=None, verbose=False, notify_url=None, log_file=None, debug_log=None, resume=False, crawl_mode='update', exclude=None, hf_mode='off', ip_mode='off', op_timeout=None,
                 resolve_locations=True, auto_ignore=True):
        """
        Initialize crawler.
        
        Args:
            host: BPQ node hostname (default: localhost)
            port: BPQ telnet port (auto-detected if None)
            callsign: Your callsign for login (auto-detected if None)
            max_hops: Maximum hops to traverse (default: 10)
            username: Telnet login username (default: None, prompts when needed)
            password: Telnet login password (default: None, prompts when needed)
            verbose: Enable verbose output (default: False)
            notify_url: URL to POST notifications to (default: None)
            log_file: File to log telnet traffic (default: None)
            debug_log: File to log verbose debug output (default: None)
            resume: Resume from unexplored nodes in existing nodemap.json (default: False)
            crawl_mode: How to handle existing nodes: 'update' (skip known), 'reaudit' (re-crawl all), 'new-only' (only new nodes)
            exclude: Set of callsigns to exclude from crawling (default: None)
            hf_mode: 'off' (default), 'audit' (list what's heard, never connect),
                     or 'crawl' (connect and fully crawl - slow at 300 baud)
            ip_mode: 'off' (default), 'audit', or 'crawl' - same tri-state as hf_mode,
                     for AXIP/Telnet ports
            op_timeout: Override per-node operation timeout in seconds (default: None = 360 + hop_count*240)
            resolve_locations: Allow network lookups (geocoding, QRZ) to fill missing grids (default: True)
            auto_ignore: Add quarantined ghost callsigns to the persistent ignore list (default: True)
        """
        self.host = host
        self.port = port if port else self._find_bpq_port()
        self.callsign = self._normalize_callsign(callsign if callsign else self._find_callsign())
        self.max_hops = max_hops
        self.username = username  # None means prompt when needed
        self.password = password  # None means prompt when needed
        self.verbose = verbose
        self.notify_url = notify_url
        self.log_file = log_file
        self.log_handle = None
        self.debug_log = debug_log
        self.debug_handle = None
        self.resume = resume
        self.resume_file = None  # Set externally if specific file needed
        self.crawl_mode = crawl_mode  # 'update', 'reaudit', or 'new-only'
        self.exclude = {self._normalize_callsign(c) for c in exclude} if exclude else set()  # Nodes to skip
        self.hf_mode = hf_mode  # 'off', 'audit', or 'crawl' - HF ports (VARA/ARDOP/PACTOR)
        self.ip_mode = ip_mode  # 'off', 'audit', or 'crawl' - IP ports (AXIP/Telnet)
        self.op_timeout = op_timeout  # Per-node operation timeout override (seconds); None = auto
        self.visited = set()  # Nodes we've already crawled
        # Subset of self.visited actually (re)crawled *this run* - distinct from
        # self.visited itself, which _load_unexplored_nodes() pre-seeds with
        # every node already in nodemap.json before a single connection is made
        # this run (so an 'update'-mode run that never re-visits a known node,
        # e.g. the local/start node, still shows it as visited). export_json()'s
        # merge step needs the narrower set: it decides which *old* connections
        # to keep by checking whether either endpoint was re-crawled, and using
        # self.nodes.keys() (which also includes every preloaded node) there
        # silently drops a still-true connection for any node this run didn't
        # actually touch, with nothing appended to replace it.
        self.freshly_crawled = set()
        self.failed = set()  # Nodes that failed connection
        self.skipped_no_ssid = {}  # Nodes skipped due to tied SSID votes: {callsign: {votes}}
        self.skipped_no_route = set()  # Nodes skipped: not in any ROUTES table (unreachable)
        self.nodes = {}  # Node data: {callsign: {info, neighbors, location, type}}
        self.connections = []  # List of [node1, node2, port] connections
        self.routes = {}  # Best routes to nodes: {callsign: [path]}
        self.route_ports = {}  # Port numbers for direct neighbors of LOCAL node: {callsign: port_number}
        self.node_route_ports = {}  # Per-node port maps: {node_base: {neighbor_base: port}}
        self.shortest_paths = {}  # Shortest discovered path to each node: {callsign: [path]}
        self.netrom_ssid_map = {}  # Global NetRom SSID mapping: {base_callsign: 'CALLSIGN-SSID'}
        self.ssid_source = {}  # Track SSID source: {base_callsign: ('routes'|'mheard', timestamp)}
        self.alias_to_call = {}  # Global alias->callsign-SSID mapping: {'CHABUR': 'KS1R-13'}
        self.call_to_alias = {}  # Reverse lookup: {'KS1R': 'CHABUR'}
        self.last_heard = {}  # MHEARD timestamps: {callsign: seconds_ago}
        self.intermittent_links = {}  # Failed connections: {(from, to): [attempts]}
        self.queue = deque()  # BFS queue for crawling: entries are (callsign, path, quality)
        self.queued_paths = set()  # Track queued paths to avoid duplicates: {(callsign, tuple(path))}
        self.timeout = 10  # Telnet timeout in seconds
        self.cli_forced_ssids = {}  # SSIDs forced via --callsign CLI option: {base_call: full_ssid}
        self.target_only_mode = False  # When True, only crawl target node (no neighbor discovery)
        self.target_callsign = None  # The specific target callsign when using --callsign
        self.silent_mode = False  # When True, skip all interactive prompts (for cron/scripts)
        self.failed_relays = set()  # Intermediates that failed as relays this session: {base_callsign}
        self.last_failed_relay = None  # The specific hop that failed in last _connect_to_node call
        self.loaded_nodes = {}  # Node data loaded from nodemap.json: {callsign: {neighbors, ...}}

        # -- Callsign quality control ------------------------------------
        # Anchors for the bit-error heuristics. confirmed_calls holds base
        # callsigns we actually connected to or read out of an own_aliases
        # map; structured_calls holds anything seen in a ROUTES table. Both
        # are rebuilt from nodemap.json at load time so a first-hop crawl
        # still has anchors to compare against.
        self.confirmed_calls = set()
        self.structured_calls = set()
        self.mheard_counts = {}      # base call -> how many nodes heard it
        self.suspect_calls = {}      # base call -> {reason, verdict, heard_by}
        self.auto_ignore = auto_ignore

        # -- Temporal tracking -------------------------------------------
        # Carried across crawls so a node that stops answering can be aged
        # out instead of sitting in the map forever looking healthy.
        self.crawl_started = _now()
        self.previous_crawl_time = None  # timestamp of the export we loaded
        self.node_history = {}       # callsign -> preserved temporal fields
        self.connection_history = {} # "FROM>TO" -> {first_seen, last_seen, count}
        self.crawl_failures = {}     # base call -> reason this run
        self.location_fixes = {}     # callsign -> corrected city/state
                                     # (export_json re-reads the file, so a
                                     #  scrub has to be replayed there)

        # -- Sysop overrides and location lookup -------------------------
        self.overrides = OverrideStore(verbose=verbose)
        qrz_user, qrz_pass = (None, None)
        if resolve_locations:
            qrz_user, qrz_pass = load_qrz_credentials(verbose=verbose)
        self.resolver = LocationResolver(
            enabled=resolve_locations, verbose=verbose,
            qrz_user=qrz_user, qrz_pass=qrz_pass)

        # -- Path quality -------------------------------------------------
        # Remembering which paths worked (and which did not) lets the next
        # crawl try the good one first instead of rediscovering it over RF.
        self.loaded_connection_history = {}  # from a previous export's connections
        self.path_history = {}       # target base -> [{path, ok, at}]
        self.link_quality = {}       # "FROM>TO" -> best observed NET/ROM quality
    
    def _write_log_header(self, log_file):
        """Write header with version and metadata to log file on first use."""
        if not log_file or not os.path.exists(log_file):
            return
        
        # Check if file just created (size 0) or empty
        try:
            file_size = os.path.getsize(log_file)
            if file_size == 0:
                with open(log_file, 'w') as f:
                    f.write("=" * 60 + "\n")
                    f.write("BPQ Node Map Crawler v{}\n".format(__version__))
                    f.write("=" * 60 + "\n")
                    f.write("Started: {}\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
                    f.write("Node: {} (callsign: {})\n".format(self.host, self.callsign))
                    f.write("=" * 60 + "\n\n")
        except Exception:
            pass  # Silently ignore header write failures
    
    def _debug_log(self, message):
        """Log message to debug log (if --debug-log set). Always logs, regardless of verbose."""
        if self.debug_log:
            # Open debug log on first use
            if self.debug_handle is None:
                try:
                    self.debug_handle = open(self.debug_log, 'a')
                    # Write header to new debug log
                    self._write_log_header(self.debug_log)
                except Exception as e:
                    colored_print("Warning: Could not open debug log {}: {}".format(self.debug_log, e), Colors.YELLOW)
                    self.debug_log = None
                    return
            
            try:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                self.debug_handle.write("[{}] {}\n".format(timestamp, message))
                self.debug_handle.flush()
            except Exception:
                pass  # Silent fail for log writes
    
    def _vprint(self, message):
        """Print verbose message to console and debug log (if --debug-log set)."""
        if self.verbose:
            print(message)
        self._debug_log(message)
        
    def _find_bpq_port(self):
        """Find BPQ telnet port from bpq32.cfg (Telnet Server port only)."""
        config_paths = [
            '../linbpq/bpq32.cfg',          # Script in utilities/ or apps/, cfg in linbpq/
            '/home/pi/linbpq/bpq32.cfg',    # Standard RPi location
            '/home/ect/linbpq/bpq32.cfg',   # Alternative user
            'bpq32.cfg',                    # Same directory as script
            'linbpq/bpq32.cfg'              # Script in parent, cfg in linbpq/
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        in_telnet_port = False
                        for line in f:
                            line_upper = line.upper()
                            # Start of Telnet port section
                            if 'DRIVER=TELNET' in line_upper or 'ID=TELNET SERVER' in line_upper:
                                in_telnet_port = True
                            # End of port section
                            elif 'ENDPORT' in line_upper:
                                in_telnet_port = False
                            # Look for TCPPORT only in Telnet port section
                            elif in_telnet_port:
                                match = re.search(r'TCPPORT\s*=\s*(\d+)', line, re.IGNORECASE)
                                if match:
                                    port = int(match.group(1))
                                    print("Found BPQ telnet port: {}".format(port))
                                    return port
                except Exception as e:
                    print("Error reading {}: {}".format(path, e))
        
        # Default to 8010 if not found
        print("BPQ port not found in config, using default: 8010")
        return 8010
    
    @staticmethod
    def _is_valid_callsign(callsign):
        """Validate callsign structure: real prefix, valid AX.25 SSID, not a
        reserved protocol word. Delegates to CallsignValidator so the crawler
        and the quarantine logic can never disagree about what is a callsign."""
        if not callsign:
            return False
        return CallsignValidator.is_structurally_valid(callsign)
    
    @staticmethod
    def _normalize_callsign(callsign):
        """Normalize callsign to uppercase for case-insensitive comparisons.
        Packet radio uses uppercase, but handle mixed-case from stale data."""
        if not callsign:
            return callsign
        return callsign.upper()
    
    def _find_callsign(self):
        """Extract callsign from bpq32.cfg."""
        config_paths = [
            '../linbpq/bpq32.cfg',          # Script in utilities/ or apps/, cfg in linbpq/
            '/home/pi/linbpq/bpq32.cfg',    # Standard RPi location
            '/home/ect/linbpq/bpq32.cfg',   # Alternative user
            'bpq32.cfg',                    # Same directory as script
            'linbpq/bpq32.cfg'              # Script in parent, cfg in linbpq/
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        for line in f:
                            # Look for NODECALL=WS1EC or similar
                            match = re.search(r'NODECALL\s*=\s*(\w+)', line, re.IGNORECASE)
                            if match:
                                call = match.group(1)
                                print("Found node callsign: {}".format(call))
                                return call
                except Exception as e:
                    print("Error reading {}: {}".format(path, e))
        
        return None
    
    def _find_node_alias(self):
        """Extract node alias from bpq32.cfg.
        
        Returns:
            str: Node alias (e.g., 'CCEMA'), or None if not found
        """
        config_paths = [
            '../linbpq/bpq32.cfg',
            '/home/pi/linbpq/bpq32.cfg',
            '/home/ect/linbpq/bpq32.cfg',
            'bpq32.cfg',
            'linbpq/bpq32.cfg'
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        for line in f:
                            # Look for NODEALIAS=CCEMA or similar
                            match = re.search(r'NODEALIAS\s*=\s*(\w+)', line, re.IGNORECASE)
                            if match:
                                alias = match.group(1)
                                print("Found node alias: {}".format(alias))
                                return alias
                except Exception as e:
                    print("Error reading {}: {}".format(path, e))
        
        return None
    
    def _log(self, direction, data):
        """Log telnet traffic to file if logging enabled.
        
        Args:
            direction: 'SEND' or 'RECV'
            data: Bytes or string to log
        """
        if not self.log_file:
            return
        
        # Open log file on first use
        if self.log_handle is None:
            try:
                self.log_handle = open(self.log_file, 'a')
                # Write header to new log file
                self._write_log_header(self.log_file)
            except Exception as e:
                colored_print("Warning: Could not open log file {}: {}".format(self.log_file, e), Colors.YELLOW)
                self.log_file = None
                return
        
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(data, bytes):
                data_str = data.decode('ascii', errors='replace')
            else:
                data_str = data
            self.log_handle.write("[{}] {}: {}\n".format(timestamp, direction, repr(data_str)))
            self.log_handle.flush()
        except Exception as e:
            if self.verbose:
                print("    Log write failed: {}".format(e))
    
    def _send_notification(self, message):
        """Send notification to webhook URL if configured."""
        if not self.notify_url:
            return
        
        try:
            # Python 3.x
            if sys.version_info[0] >= 3:
                import urllib.request
                data = message.encode('utf-8')
                req = urllib.request.Request(self.notify_url, data=data, method='POST')
                urllib.request.urlopen(req, timeout=5)
            else:
                # Python 2.x fallback
                import urllib2
                urllib2.urlopen(self.notify_url, data=message, timeout=5)
        except Exception as e:
            if self.verbose:
                colored_print("Notification failed: {}".format(e), Colors.RED)
    
    def _calculate_connection_timeout(self, hop_count):
        """
        Calculate connection timeout based on number of hops.
        At 1200 baud simplex RF: ~45s per hop for connection establishment.
        Simplex means each packet must be ACKed before next can be sent.
        
        Args:
            hop_count: Number of hops in the path
            
        Returns:
            Timeout in seconds (base 45s + 45s per hop, max 240s)
        """
        return min(45 + (hop_count * 45), 240)
    
    def _find_alternate_path(self, target_base):
        """
        BFS through known node data to find a path to target_base that avoids
        nodes in self.failed_relays. Used to re-route after an intermediate times out.

        Args:
            target_base: Base callsign of target node (no SSID)

        Returns:
            List of intermediate base callsigns (path to pass to crawl_node), or None if not found.
            Empty list means target is a direct neighbor of local node.
        """
        local_base = self.callsign.split('-')[0] if '-' in self.callsign else self.callsign

        # BFS: (current_base, path_to_current)
        queue = deque()
        queue.append((local_base, []))
        visited = {local_base}

        while queue:
            current, path = queue.popleft()

            # Resolve to full SSID for node lookup
            current_full = self.netrom_ssid_map.get(current, current)
            # Check both current-session nodes and pre-loaded JSON nodes
            current_info = (self.nodes.get(current_full)
                            or self.nodes.get(current)
                            or self.loaded_nodes.get(current_full)
                            or self.loaded_nodes.get(current)
                            or {})
            neighbors = current_info.get('neighbors', [])

            for neighbor in neighbors:
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                if neighbor_base in visited:
                    continue
                # Skip failed relays (but allow them as the FINAL target)
                if neighbor_base in self.failed_relays and neighbor_base != target_base:
                    if self.verbose:
                        print("    Alt-path BFS: skipping failed relay {}".format(neighbor_base))
                    continue
                visited.add(neighbor_base)

                new_path = path + [neighbor_base]

                if neighbor_base == target_base:
                    # Found it - new_path includes target; return only the intermediates
                    return path  # path = intermediates before target

                # Continue BFS deeper
                queue.append((neighbor_base, new_path))

        return None  # No alternate path found

    def _verify_netrom_route(self, tn, target):
        """
        Verify NetRom route to target using NRR command.
        
        Args:
            tn: Active telnet connection
            target: Target callsign or alias
            
        Returns:
            Tuple of (route_exists, hop_count, route_path)
            route_path is list of callsigns in route, or None if not found
        """
        try:
            # Try NRR command (NetRom Route Request)
            # Response format: "NRR Response: CALL1 CALL2* CALL3" where * marks destination
            cmd = "NRR {}".format(target)
            response = self._send_command(tn, cmd, timeout=10, expect_content='Response')
            
            # Check for "Not found" or "Ok" response
            if 'not found' in response.lower():
                return (False, 0, None)
            
            # Parse route response: "NRR Response: CALL1 CALL2* CALL3"
            # The * marks the destination node
            match = re.search(r'NRR Response:\s*(.+)', response, re.IGNORECASE)
            if match:
                route_str = match.group(1).strip()
                # Split by whitespace and remove the * marker
                route_calls = [c.replace('*', '') for c in route_str.split()]
                # Hop count is number of intermediate nodes (exclude source and destination)
                hop_count = max(0, len(route_calls) - 2)
                return (True, hop_count, route_calls)
            
            return (False, 0, None)
            
        except Exception as e:
            if self.verbose:
                print("    NRR command failed: {}".format(e))
            return (False, 0, None)
    
    def _connect_to_node(self, path=[]):
        """
        Connect to a node via telnet.
        
        Args:
            path: List of callsigns to connect through (empty for local node)
            
        Returns:
            telnetlib.Telnet object or None
        """
        _require_telnet()
        try:
            # Show progress for local connections
            if not path:
                print("  Connecting to localhost:{}...".format(self.port))
            
            tn = telnetlib.Telnet(self.host, self.port, self.timeout)
            
            # Set socket-level timeout for ALL subsequent read operations
            # Without this, read_some() blocks indefinitely
            # Use 5s socket timeout - the outer loop handles per-hop timing
            tn.sock.settimeout(5)
            
            time.sleep(1)
            
            # Always handle authentication when connecting to localhost
            # Read initial response (may be login prompt or direct prompt)
            initial = tn.read_very_eager().decode('ascii', errors='ignore')
            
            # Check if login is required
            if 'user:' in initial.lower() or 'callsign:' in initial.lower():
                print("  Authentication required...")
                
                # Prompt for username if not provided
                if not self.username:
                    self.username = raw_input("    Username: ") if sys.version_info[0] < 3 else input("    Username: ")
                
                # Send username
                tn.write("{}\r".format(self.username).encode('ascii'))
                self._log('SEND', "{}\r".format(self.username).encode('ascii'))
                
                # Wait for password prompt (with timeout) - don't use read_very_eager
                # Server may take time to respond, especially if validating username
                try:
                    response = tn.read_until(b':', timeout=10).decode('ascii', errors='ignore')
                    self._log('RECV', response.encode('ascii'))
                except socket.timeout:
                    response = tn.read_very_eager().decode('ascii', errors='ignore')
                    self._log('RECV', response.encode('ascii'))
                
                # Check for authentication errors
                response_lower = response.lower()
                if 'invalid' in response_lower or 'unknown' in response_lower or 'bad' in response_lower:
                    print("  Authentication failed: invalid username")
                    tn.close()
                    return None
                
                if 'password:' in response_lower or 'password' in response_lower:
                    # Prompt for password if not provided
                    if self.password is None:
                        import getpass
                        self.password = getpass.getpass("    Password: ")
                    
                    # Send password
                    tn.write("{}\r".format(self.password).encode('ascii'))
                    self._log('SEND', "(password)\r".encode('ascii'))
                    time.sleep(0.5)
                    
                    # Check for auth success/failure
                    try:
                        auth_response = tn.read_until(b'>', timeout=5).decode('ascii', errors='ignore')
                        self._log('RECV', auth_response.encode('ascii'))
                        auth_lower = auth_response.lower()
                        if 'invalid' in auth_lower or 'incorrect' in auth_lower or 'failed' in auth_lower:
                            print("  Authentication failed: incorrect password")
                            tn.close()
                            return None
                    except socket.timeout:
                        pass  # May not get response before prompt, that's OK
                else:
                    # No password prompt - server may have rejected username silently
                    # or doesn't require password. Check for prompt.
                    if '>' not in response and '}' not in response:
                        print("  Warning: No password prompt received after username")
                        print("  Server response: {}".format(response[:100] if response else '(empty)'))
            
            # Wait for command prompt
            print("  Waiting for node prompt...")
            tn.read_until(b'>', timeout=5)
            print("  Connected to local node")
            
            # If no path, just return (connecting to local node)
            if not path:
                return tn
            
            # Verify NetRom route to first hop before attempting connection
            # Only check NRR if we don't have direct port info
            # NRR only works for nodes in NetRom routing table, not direct neighbors
            if len(path) > 0 and self.verbose:
                first_hop = path[0]
                lookup_call = first_hop.split('-')[0] if '-' in first_hop else first_hop
                
                # Skip NRR check if we have port info (direct neighbor)
                port_num = self.route_ports.get(lookup_call)
                if not port_num and lookup_call in self.call_to_alias:
                    # Only verify NetRom routes when we need NetRom routing
                    target_for_nrr = self.call_to_alias.get(lookup_call)
                    
                    print("  Verifying NetRom route to {} (using NRR {})...".format(first_hop, target_for_nrr))
                    route_exists, verified_hops, route_path = self._verify_netrom_route(tn, target_for_nrr)
                    
                    if route_exists and route_path:
                        print("  Route found: {} ({} hop{})".format(' -> '.join(route_path), verified_hops, 's' if verified_hops != 1 else ''))
                        if verified_hops > len(path):
                            print("  Note: Actual route has {} hops (expected {})".format(verified_hops, len(path)))
                    elif not route_exists:
                        print("  Warning: NRR reports no route to {}".format(target_for_nrr))
                elif port_num:
                    print("  Using direct port connection to {} on port {}".format(first_hop, port_num))
            
            # Connect through nodes in path (for multi-hop or direct connections from local node)
            for i, callsign in enumerate(path):
                # Track which hop we are attempting - if this iteration returns None,
                # last_failed_relay will correctly point to the actual failing hop
                # (not path[-1] which may be a different node entirely)
                self.last_failed_relay = callsign.split('-')[0] if '-' in callsign else callsign
                # Strategy: Prefer direct connection (C PORT CALL-SSID) when we have port info
                # This bypasses NetRom routing and is faster for direct neighbors
                # Fallback to NetRom alias (C ALIAS) if no port info available
                
                # Extract base callsign for lookups (route_ports and netrom_ssid_map are keyed by base call)
                lookup_call = callsign.split('-')[0] if '-' in callsign else callsign
                
                # Determine port from current node's perspective.
                # At hop i we're physically connected to path[i-1] (or local node if i==0).
                # C PORT uses the CURRENT node's port numbering, not localhost's.
                current_node = path[i-1] if i > 0 else self.callsign
                current_node_base = current_node.split('-')[0] if '-' in current_node else current_node
                port_num = self.node_route_ports.get(current_node_base, {}).get(lookup_call)
                if not port_num:
                    port_num = self.route_ports.get(lookup_call)  # Fallback to local node's map
                # CLI-forced SSIDs always take precedence over discovered SSIDs
                full_callsign = self.cli_forced_ssids.get(lookup_call) or self.netrom_ssid_map.get(lookup_call, callsign)
                
                # Prefer direct port connection (C PORT CALL-SSID) at every hop when port and SSID
                # are known. This works at any connected BPQ node, not just from localhost.
                # Faster than NetRom alias routing and avoids alias table lookup delays.
                # Fall back to NetRom alias if port or SSID are unknown.
                
                # Check for valid alias (not a callsign - that would be a bug)
                alias = self.call_to_alias.get(lookup_call)
                if alias and (alias == lookup_call or self._is_valid_callsign(alias)):
                    # Bug: callsign was stored as its own alias
                    if self.verbose:
                        print("    WARNING: Invalid alias '{}' for {} (callsign stored as alias - bug!)".format(alias, lookup_call))
                    alias = None  # Invalidate and fall through to discovery
                
                if port_num and full_callsign:
                    # Direct port connection: C PORT CALLSIGN-SSID
                    # Works at any hop - bypasses NetRom routing entirely
                    cmd = "C {} {}\r".format(port_num, full_callsign).encode('ascii')
                    connect_target = "{} {} (port {}, direct)".format(port_num, full_callsign, port_num)
                    if self.verbose:
                        print("    Issuing command: C {} {} (direct port connection, hop {}/{})".format(port_num, full_callsign, i+1, len(path)))
                elif alias:
                    # NetRom alias available: C ALIAS
                    # Uses NetRom routing - slower but works for non-direct neighbors
                    cmd = "C {}\r".format(alias).encode('ascii')
                    connect_target = alias
                    if self.verbose:
                        full_call = self.alias_to_call.get(alias, 'unknown')
                        print("    Issuing command: C {} (NetRom alias for {}, hop {}/{})".format(alias, full_call, i+1, len(path)))
                else:
                    # No known alias - try NetRom discovery from current hop
                    if self.verbose:
                        print("    No known route to {} - attempting NetRom discovery from current node...".format(callsign))
                    
                    # Get NODES command to discover aliases
                    try:
                        nodes_output = self._send_command(tn, 'NODES', timeout=10, expect_content=':')
                        all_aliases, discovered_ssids, _ = self._parse_nodes_aliases(nodes_output)
                        
                        # Update global mappings - ONLY use aliases that match consensus SSID
                        # If no consensus exists, DO NOT add to call_to_alias
                        # Let NetRom routing figure it out with base callsign
                        for alias, full_call in all_aliases.items():
                            base_call = full_call.split('-')[0]
                            
                            # Check if this alias matches the consensus SSID for this callsign
                            consensus_ssid = self.netrom_ssid_map.get(base_call)
                            
                            if consensus_ssid and full_call == consensus_ssid:
                                # This alias matches consensus - safe to use
                                self._set_call_to_alias(base_call, alias, 'NODES_discovery')
                                self.alias_to_call[alias] = full_call
                            
                            # Always add to alias_to_call for reverse lookups
                            if alias not in self.alias_to_call:
                                self.alias_to_call[alias] = full_call
                        
                        # Update SSID mappings
                        for base_call, full_call in discovered_ssids.items():
                            if base_call not in self.netrom_ssid_map:
                                self.netrom_ssid_map[base_call] = full_call
                        
                        # Try again with discovered aliases
                        if lookup_call in self.call_to_alias:
                            alias = self.call_to_alias[lookup_call]
                            cmd = "C {}\r".format(alias).encode('ascii')
                            connect_target = alias
                            if self.verbose:
                                print("    Found NetRom alias: {} -> {}".format(lookup_call, alias))
                                print("    Issuing command: C {} (discovered NetRom alias, hop {}/{})".format(alias, i+1, len(path)))
                        elif i == 0:
                            # Still no alias found - try connecting to known nodes to discover more
                            # ONLY do this from localhost (i==0) - don't disconnect from intermediate nodes
                            if self.verbose:
                                print("    {} not in local NetRom table - trying known nodes...".format(lookup_call))
                            
                            # Try connecting to known nodes to expand NetRom discovery
                            found_via_neighbor = False
                            for alias, full_call in all_aliases.items():
                                neighbor_base = full_call.split('-')[0]
                                if neighbor_base != self.callsign:  # Skip self
                                    try:
                                        if self.verbose:
                                            print("    Trying {} ({}) for expanded NetRom discovery...".format(alias, full_call))
                                        
                                        # Connect to neighbor
                                        neighbor_cmd = "C {}\r".format(alias).encode('ascii')
                                        tn.write(neighbor_cmd)
                                        self._log('SEND', neighbor_cmd)
                                        time.sleep(1)

                                        # Look for CONNECTED response
                                        response = ""
                                        start_time = time.time()
                                        while time.time() - start_time < 10:  # Short timeout
                                            try:
                                                chunk = tn.read_some()
                                                self._log('RECV', chunk)
                                                response += chunk.decode('ascii', errors='ignore')
                                                if 'CONNECTED' in response.upper():
                                                    if self.verbose:
                                                        print("    Connected to {} - getting NODES...".format(alias))
                                                    
                                                    # Wait for prompt and get NODES
                                                    tn.read_until(b'} ', timeout=5)
                                                    neighbor_nodes = self._send_command(tn, 'NODES', timeout=10, expect_content=':')
                                                    neighbor_aliases, neighbor_ssids, _ = self._parse_nodes_aliases(neighbor_nodes)
                                                    
                                                    # Check if our target is in this node's table
                                                    for n_alias, n_full_call in neighbor_aliases.items():
                                                        n_base = n_full_call.split('-')[0]
                                                        if n_base == lookup_call:
                                                            if self.verbose:
                                                                print("    Found {} via {}: {} -> {}".format(lookup_call, alias, n_alias, n_full_call))
                                                            # Disconnect from neighbor and use its alias
                                                            tn.write(b'BYE\r')
                                                            time.sleep(0.5)
                                                            tn.read_very_eager()  # Clear response
                                                            
                                                            # Now connect using the discovered alias
                                                            cmd = "C {}\r".format(n_alias).encode('ascii')
                                                            connect_target = "{} (via {})".format(n_alias, alias)
                                                            found_via_neighbor = True
                                                            if self.verbose:
                                                                print("    Issuing command: C {} (found via {}, hop {}/{})".format(n_alias, alias, i+1, len(path)))
                                                            break
                                                    
                                                    if found_via_neighbor:
                                                        break
                                                    else:
                                                        # Target not found, disconnect
                                                        tn.write(b'BYE\r')
                                                        time.sleep(0.5)
                                                        tn.read_very_eager()
                                                        break
                                                
                                            except socket.timeout:
                                                pass
                                            except EOFError:
                                                break
                                        
                                        if found_via_neighbor:
                                            break
                                            
                                    except Exception as e:
                                        if self.verbose:
                                            print("    Failed to query {}: {}".format(alias, e))
                                        continue
                            
                            if not found_via_neighbor:
                                # Still no route after expanded search from localhost
                                if self.verbose:
                                    print("    No route found after expanded search from localhost")
                                # Abort - cannot proceed without alias
                                if self.verbose:
                                    print("    Connection impossible without NetRom alias - aborting")
                                tn.close()
                                return None
                        else:
                            # Intermediate hop (i > 0) and no alias found in current node's NODES
                            # Cannot do expanded discovery without breaking our connection path
                            # 
                            # FALLBACK: Query ROUTES to get port number, then use C PORT CALLSIGN-SSID
                            # This works when target is in ROUTES but not in NODES table
                            if self.verbose:
                                print("    {} not in current node's NODES table".format(lookup_call))
                                print("    Querying ROUTES for port information...")
                            
                            try:
                                routes_output = self._send_command(tn, 'ROUTES', timeout=15, expect_content='!')
                                routes, route_ports, route_ssids, _ = self._parse_routes(routes_output)
                                
                                # Check if target is in ROUTES
                                if lookup_call in route_ports or lookup_call in routes:
                                    port_num = route_ports.get(lookup_call)
                                    target_ssid = route_ssids.get(lookup_call) or full_callsign
                                    
                                    if port_num:
                                        # Found port - use C PORT CALLSIGN-SSID
                                        cmd = "C {} {}\r".format(port_num, target_ssid).encode('ascii')
                                        connect_target = "{} {} (via ROUTES port)".format(port_num, target_ssid)
                                        if self.verbose:
                                            print("    Found in ROUTES: port {}, SSID {}".format(port_num, target_ssid))
                                            print("    Issuing command: C {} {} (ROUTES fallback, hop {}/{})".format(port_num, target_ssid, i+1, len(path)))
                                    else:
                                        # In routes but no port (shouldn't happen, but handle gracefully)
                                        if self.verbose:
                                            print("    {} in ROUTES but no port number - cannot connect".format(lookup_call))
                                            print("    Connection impossible without port - aborting")
                                        tn.close()
                                        return None
                                else:
                                    # Not in ROUTES either
                                    if self.verbose:
                                        print("    {} not in ROUTES table either".format(lookup_call))
                                        print("    Connection impossible - target not routable from this node")
                                    tn.close()
                                    return None
                                    
                            except Exception as e:
                                if self.verbose:
                                    print("    ROUTES query failed: {}".format(e))
                                    print("    Connection impossible without routing data - aborting")
                                tn.close()
                                return None
                    
                    except Exception as e:
                        if self.verbose:
                            print("    NetRom discovery failed: {}".format(e))
                        
                        # Final check: must have NetRom alias to proceed
                        # Base callsign fallback does NOT work - NetRom requires alias or port
                        if lookup_call not in self.call_to_alias:
                            if self.verbose:
                                print("    No NetRom alias found for {} - UNROUTABLE".format(callsign))
                                print("    Connection impossible without alias or port - aborting")
                            tn.close()
                            return None
                        
                        # Use NetRom alias from mappings as fallback
                        alias = self.call_to_alias[lookup_call]
                        cmd = "C {}\r".format(alias).encode('ascii')
                        connect_target = "{} (from mappings after discovery failure)".format(alias)
                        if self.verbose:
                            print("    Issuing command: C {} (NetRom alias from mappings, hop {}/{})".format(alias, i+1, len(path)))
                
                # Set socket timeout before write to prevent blocking on dead connections
                # TCP write() can block if remote end's receive buffer is full
                tn.sock.settimeout(10.0)
                
                try:
                    tn.write(cmd)
                    # Connect attempts previously went out unlogged, so a
                    # failed or timed-out connect (e.g. the N1QFY and K1NYY
                    # timeouts on the 2026-08-21 crawl) left no trace at all
                    # in telnet.log - only the next login attempt would show
                    # up, minutes later, with nothing to explain the gap.
                    self._log('SEND', cmd)
                except socket.timeout:
                    print("  Connection to {} timed out (write blocked)".format(callsign))
                    tn.close()
                    return None
                
                # Wait for connection response (scale timeout with hop count)
                # At 1200 baud RF: ~20s per hop for connection establishment
                # Calculate timeout based on total path length (this hop + remaining hops)
                remaining_hops = len(path) - i
                conn_timeout = self._calculate_connection_timeout(remaining_hops)
                connection_start_time = time.time()
                connected = False
                response = ""
                
                if self.verbose:
                    print("    Waiting for connection (timeout: {}s for {} hop{})...".format(
                        conn_timeout, remaining_hops, 's' if remaining_hops != 1 else ''))
                
                # Set socket timeout to prevent read_some() from blocking forever
                # Use short timeout so we can check elapsed time in the loop
                try:
                    if tn.sock:
                        tn.sock.settimeout(2.0)
                except:
                    pass
                
                while time.time() - connection_start_time < conn_timeout:
                    # Check timeout FIRST before any I/O operations
                    elapsed = time.time() - connection_start_time
                    if elapsed >= conn_timeout:
                        break
                    
                    try:
                        # Use read_very_eager() instead of read_some() - it's non-blocking
                        chunk = tn.read_very_eager()
                        if chunk:
                            self._log('RECV', chunk)
                            response += chunk.decode('ascii', errors='ignore')

                        # Check for connection success
                        if 'CONNECTED' in response.upper():
                            connected = True
                            print("  Connected to {}".format(callsign))
                            self._debug_log("Connected to {}".format(callsign))
                            break
                        
                        # Check for failure patterns.
                        # BPQ32's actual wording is "Failure with <call>", not
                        # "Failed" - that word never appeared here before, so
                        # every real failure was missed and this loop burned
                        # its full conn_timeout waiting for a CONNECTED that
                        # was never coming (confirmed 2026-08-21: 14 straight
                        # "Failure with X" responses, all silently ignored).
                        if any(x in response.upper() for x in ['BUSY', 'FAILED', 'FAILURE', 'NO ROUTE',
                                                                 'TIMEOUT', 'DISCONNECTED',
                                                                 'NOT HEARD', 'NO ANSWER',
                                                                 'NOT IN TABLES', 'NO ROUTE TO']):
                            # Extract last meaningful line for error message
                            error_line = response.strip().split('\n')[-1] if response.strip() else 'Unknown error'
                            fail_msg = "Connection to {} (via {}) failed: {}".format(
                                callsign, 
                                connect_target,
                                error_line
                            )
                            colored_print("  " + fail_msg, Colors.RED)
                            self._debug_log(fail_msg)
                            tn.close()
                            return None
                        
                        # Sleep between checks to avoid busy-waiting
                        # Sleep between checks to avoid busy-waiting
                        time.sleep(0.5)
                        
                    except EOFError:
                        print("  Connection lost to {}".format(callsign))
                        tn.close()
                        return None
                    except Exception as e:
                        # Any other exception during read
                        if self.verbose:
                            print("  Read error: {}".format(e))
                        # Check if we've exceeded timeout
                        if time.time() - connection_start_time >= conn_timeout:
                            break
                        time.sleep(0.5)
                
                if not connected:
                    elapsed = time.time() - connection_start_time
                    if self.verbose:
                        print("  Connection to {} (via {}) timed out after {:.1f}s (expected timeout: {}s)".format(
                            callsign, connect_target, elapsed, conn_timeout))
                    else:
                        print("  Connection to {} (via {}) timed out (no CONNECTED response)".format(callsign, connect_target))
                    
                    # If direct port connection failed, try NetRom alias as fallback
                    # But ONLY if alias is valid (not a callsign - that would be a bug)
                    fallback_alias = self.call_to_alias.get(lookup_call)
                    if fallback_alias and (fallback_alias == lookup_call or self._is_valid_callsign(fallback_alias)):
                        fallback_alias = None  # Invalid alias, don't use
                    
                    if port_num and fallback_alias:
                        if self.verbose:
                            print("    Direct port connection failed - trying NetRom alias: {}".format(fallback_alias))
                        
                        # Clear any buffered data
                        try:
                            tn.read_very_eager()
                        except:
                            pass
                        
                        # Try NetRom connection
                        cmd = "C {}\r".format(fallback_alias).encode('ascii')
                        try:
                            tn.write(cmd)
                            self._log('SEND', cmd)
                        except:
                            tn.close()
                            return None
                        
                        # Calculate remaining timeout from original start time
                        elapsed = time.time() - connection_start_time
                        remaining_timeout = max(5, conn_timeout - elapsed)  # At least 5s for fallback
                        connected = False
                        response = ""
                        
                        if self.verbose:
                            print("    Waiting for NetRom connection (timeout: {}s remaining)...".format(int(remaining_timeout)))
                        
                        while time.time() - connection_start_time < conn_timeout:
                            # Check timeout FIRST before any I/O operations
                            elapsed = time.time() - connection_start_time
                            if elapsed >= conn_timeout:
                                break
                            
                            try:
                                chunk = tn.read_some()
                                self._log('RECV', chunk)
                                response += chunk.decode('ascii', errors='ignore')

                                if 'CONNECTED' in response.upper():
                                    connected = True
                                    print("  Connected to {} via NetRom alias {}".format(callsign, alias))
                                    break
                                
                                if any(x in response.upper() for x in ['BUSY', 'FAILED', 'FAILURE', 'NO ROUTE',
                                                                         'TIMEOUT', 'DISCONNECTED',
                                                                         'NOT HEARD', 'NO ANSWER']):
                                    break
                                
                                time.sleep(0.5)
                            except socket.timeout:
                                # Check if total timeout exceeded
                                if time.time() - connection_start_time >= conn_timeout:
                                    break
                                pass
                            except EOFError:
                                break
                    
                    if not connected:
                        tn.close()
                        return None
                
                # Wait for remote node prompt after connection
                # BPQ remote nodes use "ALIAS:CALLSIGN-SSID} " prompt format
                # After connection, BPQ waits for input - no auto-banner
                # Send CR to request prompt without triggering INFO display
                try:
                    # Send CR to get prompt without INFO banner
                    # BPQ will respond with prompt immediately instead of showing full INFO
                    tn.write(b'\r')
                    time.sleep(0.5)  # Brief delay for node to respond
                    
                    # Look for BPQ remote prompt: "} " at end of response
                    # Allow 30s for response at 1200 baud over RF hops
                    if self.verbose:
                        print("    Waiting for remote node prompt (30s timeout)...")
                    prompt_data = tn.read_until(b'} ', timeout=30)
                    self._log('RECV', prompt_data)
                    prompt_text = prompt_data.decode('ascii', errors='replace')
                    
                    # Extract actual node SSID from prompt: "ALIAS:CALL-SSID} "
                    # Example: "WINFLD:N1QFY-4} " means node is N1QFY-4
                    prompt_match = re.search(r'(\w+):(\w+(?:-\d+)?)\}\s*$', prompt_text)
                    if prompt_match:
                        prompt_alias = self._normalize_callsign(prompt_match.group(1))
                        prompt_callsign = self._normalize_callsign(prompt_match.group(2))
                        base_call = prompt_callsign.split('-')[0]
                        
                        # Store the ACTUAL node SSID we're connected to
                        self.netrom_ssid_map[base_call] = prompt_callsign
                        self.alias_to_call[prompt_alias] = prompt_callsign
                        self._set_call_to_alias(base_call, prompt_alias, 'prompt_extraction')
                        
                        if self.verbose:
                            print("    Connected to node: {} ({}) - stored for routing".format(prompt_callsign, prompt_alias))
                    elif self.verbose:
                        print("    Received remote prompt: {}...".format(prompt_data[-20:].decode('ascii', errors='replace').strip()))
                    
                    # Always consume any remaining buffered data after prompt
                    # This prevents leftover banner/info text from contaminating first command response
                    time.sleep(1.5)  # Give trailing data time to arrive over 1200 baud RF
                    extra_data = tn.read_very_eager()
                    if extra_data:
                        self._log('RECV', extra_data)
                        if self.verbose:
                            print("    Cleared {} bytes of buffered data".format(len(extra_data)))
                except socket.timeout:
                    if self.verbose:
                        print("    Timeout waiting for prompt - node may be slow or connection unstable")
                    # Consume whatever is buffered
                    buffered = tn.read_very_eager()
                    self._log('RECV', buffered)
                    if self.verbose:
                        print("    Consumed {} bytes of buffered data".format(len(buffered)))
                except Exception as e:
                    # If no prompt received, just consume whatever is buffered
                    if self.verbose:
                        print("    Error reading prompt: {}".format(e))
                    buffered = tn.read_very_eager()
                    self._log('RECV', buffered)
                    if self.verbose:
                        print("    Consumed {} bytes".format(len(buffered)))
            
            return tn
            
        except (socket.error, OSError) as e:
            # Network/socket errors - check if this is local or remote connection failure
            if not path:
                # Failed to connect to LOCAL BPQ node - this is fatal
                colored_print("FATAL: Cannot connect to local BPQ node at {}:{} - {}".format(
                    self.host, self.port, e), Colors.RED)
                colored_print("Local BPQ node must be running and accessible. Exiting.", Colors.RED)
                sys.exit(1)
            else:
                # Failed to connect to REMOTE node - this is expected for unreachable nodes
                colored_print("Error connecting: {}".format(e), Colors.RED)
                return None
        except Exception as e:
            # Other exceptions
            if not path:
                # Any error connecting to LOCAL node is fatal
                colored_print("FATAL: Error connecting to local BPQ node - {}".format(e), Colors.RED)
                sys.exit(1)
            colored_print("Error connecting: {}".format(e), Colors.RED)
            return None
    
    def _send_command(self, tn, command, wait_for=b'>', timeout=5, expect_content=None):
        """Send command and read response with timeout protection.
        
        Args:
            tn: Telnet connection
            command: Command to send
            wait_for: Prompt to wait for (default: >)
            timeout: Read timeout in seconds
            expect_content: Optional string that should appear in response for validation
        
        Returns:
            Decoded response string
        """
        try:
            if self.verbose:
                print("    Sending command: {}".format(command))
            cmd_bytes = "{}\r".format(command).encode('ascii')
            tn.write(cmd_bytes)
            self._log('SEND', cmd_bytes)
            
            # Wait for command echo before reading response
            # This helps synchronize on slow multi-hop RF links
            time.sleep(0.3)

            # Poll non-blockingly (read_very_eager) instead of parking in
            # read_until() for a fixed per-read timeout every iteration - that
            # blocked the FULL timeout even when the response had already
            # finished arriving, costing ~35-45s of pure dead air after every
            # command on a multi-hop node (measured against a real crawl's
            # telnet.log) and consuming most of the per-node operation budget
            # on silence rather than actual RF latency. Same read_very_eager
            # + wall-clock-deadline pattern already used in _connect_to_node.
            #
            # quiet_window scales with the caller's timeout (itself scaled by
            # hop count via cmd_timeout in crawl_node), so a distant,
            # genuinely slow multi-hop response still gets patience - it just
            # stops paying for silence the moment the response goes quiet.
            #
            # The floor here is deliberately generous: a real 2-hop MHEARD
            # response (telnet.log, 2026-08-21 15:24:28) went 16s between two
            # data-bearing chunks while still mid-response. A short
            # quiet_window would read that as "done" and truncate the
            # NODES/ROUTES/MHEARD table it was in the middle of - silent data
            # loss, which is worse than the wasted time this loop exists to
            # cut. 25s gives that observed worst case comfortable margin.
            quiet_window = min(4.0 + (timeout * 0.35), 25.0)
            poll_interval = 0.4

            response = b''
            start_time = time.time()
            last_growth = start_time

            while True:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    break

                chunk = tn.read_very_eager()
                if chunk:
                    self._log('RECV', chunk)
                    response += chunk
                    last_growth = time.time()
                    continue

                quiet_for = time.time() - last_growth
                if response and quiet_for >= quiet_window:
                    break

                # Exit early once expected content has shown up and things
                # have gone quiet for a short tail-wait, rather than always
                # burning the full quiet_window.
                if expect_content and response:
                    decoded_check = response.decode('ascii', errors='ignore')
                    if (expect_content.lower() in decoded_check.lower()
                            and quiet_for >= max(1.0, quiet_window / 2)):
                        break

                time.sleep(poll_interval)

            decoded = response.decode('ascii', errors='ignore')
            
            # Validate response content if expected
            if expect_content and expect_content.lower() not in decoded.lower():
                if self.verbose:
                    print("    Warning: Expected '{}' not found in response".format(expect_content))
            
            if self.verbose:
                print("    Response ({} bytes):".format(len(decoded)))
                # Show more of response for debugging
                display = decoded[:300] if len(decoded) > 300 else decoded
                print("    {}".format(display.replace('\r\n', '\n    ')))
            return decoded
        except EOFError:
            print("    Connection lost during {} command".format(command))
            return ""
        except:
            # Timeout or other error - try to get whatever is buffered
            try:
                buffered = tn.read_very_eager().decode('ascii', errors='ignore')
                if not buffered:
                    print("    Timeout on {} command ({}s)".format(command, timeout))
                return buffered
            except:
                return ""
    
    def _parse_mheard(self, output, port_num=None):
        """
        Parse MHEARD output to extract callsigns, timestamps, and port numbers.
        
        Supports two MHEARD formats:
        
        BPQ32 format:
            Heard List for Port N
            CALLSIGN-SSID  DD:HH:MM:SS (days:hours:mins:secs since last heard)
        
        Kantronics X1J4 format (columnar with signal data):
            Callsign    Pkts   Port  Time      Dev.   dBm   Type
            AB1KI-15    4553   0     0:5:3     2.9    -40   Node
            VE9SIX      27     0     3:40:45   2.9    -40   Node
        
        Args:
            output: MHEARD command output
            port_num: Port number if known (from command context)
        
        Returns:
            If port_num provided: List of base callsigns (without SSID)
            If port_num None: List of (callsign, port) tuples
            Also updates self.last_heard dict with timestamps
        """
        heard = []
        lines = output.split('\n')
        
        # Detect Kantronics X1J4 columnar format
        # Header line: "Callsign    Pkts   Port  Time      Dev.   dBm   Type"
        is_kantronics = any('Pkts' in line and 'dBm' in line for line in lines)
        
        if is_kantronics:
            return self._parse_mheard_kantronics(lines, port_num)
        
        # Try to extract port from header if not provided
        detected_port = port_num
        if detected_port is None:
            for line in lines:
                if 'Heard List for Port' in line:
                    match = re.search(r'Port\s+(\d+)', line)
                    if match:
                        detected_port = int(match.group(1))
                        break
        
        for line in lines:
            # Skip header lines
            if 'Heard List' in line or not line.strip():
                continue
            
            # Look for callsign and timestamp: "KC1JMH-15  00:00:00:03"
            # Match callsign with optional SSID, followed by timestamp
            match = re.match(r'^(\w+(?:-\d+)?)\s+(\d+):(\d+):(\d+):(\d+)', line)
            if match:
                full_callsign = self._normalize_callsign(match.group(1))
                callsign = full_callsign.split('-')[0]  # Strip SSID for base call
                
                # Validate callsign format
                if not self._is_valid_callsign(callsign):
                    continue
                
                # Parse timestamp (DD:HH:MM:SS) to total seconds
                days = int(match.group(2))
                hours = int(match.group(3))
                minutes = int(match.group(4))
                seconds = int(match.group(5))
                total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
                
                # Update last_heard with most recent time for this callsign
                if callsign not in self.last_heard or total_seconds < self.last_heard[callsign]:
                    self.last_heard[callsign] = total_seconds
                
                # If we have port info, return (callsign, port) tuple
                if detected_port is not None:
                    if callsign not in [h[0] if isinstance(h, tuple) else h for h in heard]:
                        if port_num is not None:
                            # Called with explicit port, return just callsigns
                            heard.append(callsign)
                        else:
                            # Called without explicit port, return tuples
                            heard.append((callsign, detected_port))
                else:
                    # No port info, just return callsigns
                    if callsign not in heard:
                        heard.append(callsign)
        
        return heard
    
    def _parse_mheard_kantronics(self, lines, port_num=None):
        """
        Parse Kantronics X1J4 MHEARD columnar output.
        
        Format:
            Callsign    Pkts   Port  Time      Dev.   dBm   Type
            AB1KI-15    4553   0     0:5:3     2.9    -40   Node
            VE9SIX      27     0     3:40:45   2.9    -40   Node
        
        Key differences from BPQ32:
        - Column header line present
        - Packet count column between callsign and port
        - Port is per-row (not in header), always 0 on single-port Kantronics
        - Time format H:M:S (3 fields, not 4 like BPQ's DD:HH:MM:SS)
        - Signal quality: deviation (kHz) and dBm columns
        - Type column: 'Node' tag for known NET/ROM nodes
        
        Args:
            lines: Pre-split output lines
            port_num: Port number override (from command context)
        
        Returns:
            List of (callsign, port) tuples or list of callsigns
        """
        heard = []
        
        for line in lines:
            # Skip header, empty lines, and prompt lines
            if not line.strip() or 'Callsign' in line or 'Pkts' in line:
                continue
            if '}' in line and ':' in line.split('}')[0]:
                continue  # Prompt line like "CAL:W1LH-6}"
            
            # Kantronics MHEARD format:
            # CALLSIGN    PKTS   PORT  H:M:S     DEV    DBM   [TYPE]
            # Match: callsign, then digits (pkts), then digit (port), then H:M:S timestamp
            match = re.match(
                r'^(\w+(?:-\d+)?)\s+(\d+)\s+(\d+)\s+(\d+):(\d+):(\d+)',
                line
            )
            if not match:
                continue
            
            full_callsign = self._normalize_callsign(match.group(1))
            callsign = full_callsign.split('-')[0]  # Strip SSID for base call
            
            # Validate callsign format
            if not self._is_valid_callsign(callsign):
                continue
            
            # Extract fields
            # pkts = int(match.group(2))  # Packet count (not used for routing)
            kantronics_port = int(match.group(3))  # Port from column
            hours = int(match.group(4))
            minutes = int(match.group(5))
            seconds = int(match.group(6))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Use port_num override if provided, otherwise use per-row port
            detected_port = port_num if port_num is not None else kantronics_port
            
            # Update last_heard with most recent time for this callsign
            if callsign not in self.last_heard or total_seconds < self.last_heard[callsign]:
                self.last_heard[callsign] = total_seconds
            
            # Add to heard list (avoid duplicates)
            if detected_port is not None:
                if callsign not in [h[0] if isinstance(h, tuple) else h for h in heard]:
                    if port_num is not None:
                        heard.append(callsign)
                    else:
                        heard.append((callsign, detected_port))
            else:
                if callsign not in heard:
                    heard.append(callsign)
        
        return heard
    
    def _filter_rf_ports(self, heard_list, ports_output):
        """
        Filter heard list to only include RF ports (not Telnet/IP).
        
        Args:
            heard_list: List of (callsign, port) tuples
            ports_output: Output from PORTS command
            
        Returns:
            Filtered list of (callsign, port) tuples
        """
        # Parse PORTS to identify non-RF ports
        ip_ports = set()
        lines = ports_output.split('\n')
        
        for line in lines:
            # Look for Telnet, TCPIP, etc.
            if re.search(r'Port\s+(\d+).*(?:Telnet|TCPIP|IP)', line, re.IGNORECASE):
                match = re.search(r'Port\s+(\d+)', line)
                if match:
                    ip_ports.add(int(match.group(1)))
        
        # Filter out IP-based ports
        return [(call, port) for call, port in heard_list if port not in ip_ports]
    
    def _parse_info(self, output):
        """
        Extract location from INFO output.
        
        Note: INFO is freeform text entered by sysop. Parsing is unreliable
        and should be given less weight than structured command output.
        
        Returns:
            Dictionary with location data (lat, lon, grid, city, state)
        """
        # Delegates to LocationResolver.parse_info_text, which validates the
        # state against a real list and rejects node boilerplate. The old
        # inline regex accepted "Node EM" and "Packet BBS" as a City/State
        # pair, which is how stations ended up mapped to a city of "Node".
        return LocationResolver.parse_info_text(output)
    
    def _detect_node_type(self, info_output, prompt_chars, commands=None):
        """
        Detect node software type (BPQ, Kantronics, FBB, JNOS).
        
        Note: Detection from INFO text is unreliable (sysop-entered freeform).
        Prompt character detection (> or :) is more reliable fallback.
        Command list from ? output provides additional hints.
        
        Args:
            info_output: Output from INFO command
            prompt_chars: Last characters received (prompt indicators)
            commands: List of available commands from ? output (optional)
            
        Returns:
            String: 'BPQ', 'Kantronics', 'FBB', 'JNOS', or 'Unknown'
        """
        info_upper = info_output.upper()
        
        # Kantronics KPC-3 Plus / X1J4 firmware detection
        # X1J4 firmware identifier, or Kantronics/KPC in INFO text
        if 'X1J4' in info_upper or 'KANTRONICS' in info_upper or 'KPC' in info_upper:
            return 'Kantronics'
        
        # Check command list for Kantronics-specific commands
        # 'Adc' command is unique to Kantronics hardware (ADC voltage readout)
        if commands:
            cmd_set = {c.upper() for c in commands if isinstance(c, str)}
            if 'ADC' in cmd_set:
                return 'Kantronics'
        
        if 'BPQ' in info_upper or 'G8BPQ' in info_upper:
            return 'BPQ'
        elif 'FBB' in info_upper or 'F6FBB' in info_upper:
            return 'FBB'
        elif 'JNOS' in info_upper or 'NOS' in info_upper:
            return 'JNOS'
        elif '>' in prompt_chars:
            return 'BPQ'  # BPQ uses > prompt
        elif ':' in prompt_chars:
            return 'FBB'  # FBB uses : prompt
        
        return 'Unknown'
    
    def _load_existing_data(self, filename):
        """Load existing nodemap data if available."""
        if not os.path.exists(filename):
            return None
        
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            colored_print("Warning: Could not load {}: {}".format(filename, e), Colors.YELLOW)
            return None
    
    def _build_link_graph(self, nodes_data):
        """Build a weighted adjacency map of the network, keyed by base call.

        Edges come from each node's own ROUTES output where available, since
        that carries a real NET/ROM quality figure, and fall back to bare
        MHEARD adjacency where it does not. Everything is normalised to base
        callsigns: the node records are keyed by SSID ("KX1EMA-15") while the
        neighbour lists hold bare calls ("KX1EMA"), and mixing the two is what
        made the old path search unable to see past the first hop.
        """
        graph = {}
        for callsign, node in nodes_data.items():
            source = _base_call(callsign)
            edges = graph.setdefault(source, {})

            # ROUTES: an explicit, node-reported quality per neighbour.
            for neighbor, detail in (node.get('direct_routes') or {}).items():
                quality = detail.get('quality') if isinstance(detail, dict) else detail
                try:
                    quality = int(quality)
                except (TypeError, ValueError):
                    continue
                # BPQ uses quality 0 to mean "do not route through this";
                # treat the link as absent rather than as merely poor.
                if quality <= 0:
                    continue
                target = _base_call(neighbor)
                if target and target != source:
                    edges[target] = max(edges.get(target, 0), quality)

            # MHEARD: heard on RF but with no quality figure. Score it below
            # any real ROUTES entry so a measured path always wins.
            for neighbor in (node.get('neighbors') or []):
                target = _base_call(neighbor)
                if not target or target == source:
                    continue
                if target in self.suspect_calls or self.overrides.is_ignored(target):
                    continue
                edges.setdefault(target, 60)
        return graph

    def _find_path_to_node(self, target_callsign, nodes_data):
        """Find the best path from the local node to a target.

        Dijkstra over NET/ROM link quality rather than a plain hop count: a
        two-hop path over two solid links routes far better than a single
        marginal one, and BPQ already tells us which is which. A fixed cost
        is added per hop so that, all else equal, shorter still wins.

        Returns a list of intermediate base callsigns (excluding both the
        local node and the target), or None when no path is known.
        """
        if not self.callsign:
            return None
        source = _base_call(self.callsign)
        target = _base_call(target_callsign)
        if target == source:
            return []

        graph = self._build_link_graph(nodes_data)
        if source not in graph:
            return None

        # A path that has actually worked before beats anything computed.
        for attempt in reversed(self.path_history.get(target, [])):
            if attempt.get('ok') and attempt.get('path') is not None:
                path = [_base_call(p) for p in attempt['path']]
                if all(hop in graph for hop in path):
                    if self.verbose:
                        print("  Reusing known-good path to {}: {}".format(
                            target, ' > '.join(path) or 'direct'))
                    return path

        import heapq
        HOP_COST = 40          # discourage long paths without forbidding them
        best = {source: 0}
        previous = {}
        heap = [(0, source)]
        seen = set()

        while heap:
            cost, current = heapq.heappop(heap)
            if current in seen:
                continue
            seen.add(current)
            if current == target:
                break
            for neighbor, quality in graph.get(current, {}).items():
                if neighbor in seen:
                    continue
                if neighbor in self.suspect_calls or self.overrides.is_ignored(neighbor):
                    continue
                # Higher NET/ROM quality means a cheaper edge.
                edge_cost = max(1, 256 - int(quality)) + HOP_COST
                # An intermediate that already failed as a relay this session
                # is not forbidden, just made expensive.
                if neighbor in self.failed_relays:
                    edge_cost += 500
                candidate = cost + edge_cost
                if candidate < best.get(neighbor, float('inf')):
                    best[neighbor] = candidate
                    previous[neighbor] = current
                    heapq.heappush(heap, (candidate, neighbor))

        if target not in best:
            return None

        path = []
        node = target
        while node != source:
            path.append(node)
            node = previous.get(node)
            if node is None:
                return None          # disconnected; should not happen
        path.reverse()
        return path[:-1]             # drop the target itself

    def _record_path_result(self, target_callsign, path, ok):
        """Remember whether a path worked, for this crawl and the next one."""
        target = _base_call(target_callsign)
        attempts = self.path_history.setdefault(target, [])
        normalised = [_base_call(p) for p in (path or [])]
        for attempt in attempts:
            if attempt.get('path') == normalised:
                attempt['ok'] = ok
                attempt['at'] = _now()
                attempt['tries'] = attempt.get('tries', 1) + 1
                break
        else:
            attempts.append({'path': normalised, 'ok': ok,
                             'at': _now(), 'tries': 1})
        # Keep the record bounded; only the recent past is informative.
        if len(attempts) > 8:
            del attempts[:-8]

    def _prime_from_existing(self, existing):
        """Seed anchors, history and the ignore list from a previous export.

        Has to run on every crawl mode, not just resume. The default update
        mode never called _load_unexplored_nodes at all, which left the
        corruption heuristics with no known-good callsigns to compare against
        and skipped the cleanup of ghosts already recorded in the map.
        """
        if not existing or 'nodes' not in existing:
            return
        nodes_data = existing['nodes']
        self._rebuild_anchors(nodes_data)
        self._count_mheard(nodes_data)
        for key, record in (existing.get('connection_history') or {}).items():
            self.loaded_connection_history[key] = record
        self._load_history(nodes_data)
        # Bootstrap value for nodes that predate temporal tracking: the run
        # that produced this file is the last time we can honestly claim to
        # have seen them, which is not the same as "now".
        self.previous_crawl_time = (
            (existing.get('crawl_info') or {}).get('timestamp')
            or (existing.get('metadata') or {}).get('generated'))
        self._scrub_loaded_data(nodes_data)
        self._scrub_locations(nodes_data)
        # Carry forward per-target path outcomes so _connect_to_node can try
        # the path that worked last time before rediscovering it over RF.
        for target, attempts in (existing.get('path_history') or {}).items():
            self.path_history[target] = attempts
        if self.verbose:
            print("Anchors: {} confirmed, {} corroborated by ROUTES".format(
                len(self.confirmed_calls), len(self.structured_calls)))

    def _load_unexplored_nodes(self, filename='nodemap.json'):
        """Load unexplored nodes from existing nodemap data.
        
        Returns:
            List of (callsign, path) tuples for unexplored neighbors
        """
        # Try multiple possible filenames if default doesn't exist
        possible_files = [filename]
        if filename == 'nodemap.json':
            # Also try partial files from interrupted crawls
            import glob
            partial_files = glob.glob('nodemap_partial*.json')
            if partial_files:
                # Use most recent partial file
                partial_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
                possible_files.extend(partial_files)
        
        existing = None
        used_file = None
        for try_file in possible_files:
            existing = self._load_existing_data(try_file)
            if existing and 'nodes' in existing:
                used_file = try_file
                break
        
        if not existing or 'nodes' not in existing:
            print("No existing nodemap data found. Starting fresh crawl.")
            print("Tried files: {}".format(', '.join(possible_files)))
            return []
        
        if used_file != filename:
            print("Using existing data from: {}".format(used_file))
        
        unexplored = []
        nodes_data = existing['nodes']
        
        # Populate self.nodes from existing data (needed for new-only mode skip check)
        self.nodes = nodes_data.copy()
        
        # Mark all previously visited nodes
        for callsign in nodes_data.keys():
            self.visited.add(callsign)
        
        print("Loaded {} previously visited nodes".format(len(self.visited)))

        # Seed the callsign quality-control anchors and the temporal record
        # from what we already know. This has to happen before any crawling:
        # the bit-error heuristics compare observed calls against known-good
        # ones, and on an update-mode run most known-good calls come from the
        # previous export rather than from this run's connections.
        self._prime_from_existing(existing)
        
        # Restore SSID mappings from previous crawl data
        # SSID Selection Standard:
        # 1. CLI-forced SSIDs (already in cli_forced_ssids) - highest priority
        # 2. ROUTES consensus (aggregate netrom_ssids from all nodes) - AUTHORITATIVE
        # 3. Base callsign only (let NetRom figure it out)
        #
        # The 'alias' field is NOT reliable - it comes from the BPQ prompt which may be
        # from a BBS, RMS, or CHAT service rather than the node itself.
        # ROUTES data (stored in netrom_ssids) IS reliable - it shows actual node SSIDs.
        
        # Build ROUTES consensus by aggregating netrom_ssids from ALL crawled nodes
        # Each node's ROUTES table shows what SSIDs it knows for its neighbors
        from collections import defaultdict
        ssid_votes = defaultdict(lambda: defaultdict(int))
        
        for node_data in nodes_data.values():
            netrom = node_data.get('netrom_ssids', {})
            for base_call, full_ssid in netrom.items():
                # Only count valid callsigns WITH explicit SSID (skip bare callsigns and corrupted data)
                # Bare callsigns in ROUTES are ambiguous - could be any service
                # Node SSIDs should have explicit -N suffix
                if self._is_valid_callsign(base_call) and '-' in full_ssid and self._is_likely_node_ssid(full_ssid):
                    ssid_votes[base_call][full_ssid] += 1
        
        # Use ROUTES consensus to build SSID map
        # Only use consensus if there's a CLEAR winner (more votes than any other)
        # If tied, skip this node - insufficient routing data
        for base_call, votes in ssid_votes.items():
            sorted_votes = sorted(votes.items(), key=lambda x: (-x[1], x[0]))
            best_ssid, best_count = sorted_votes[0]
            
            # Check if there's a clear winner (no tie for first place)
            if len(sorted_votes) == 1 or best_count > sorted_votes[1][1]:
                # Clear consensus - use this SSID
                self.netrom_ssid_map[base_call] = best_ssid
                self.ssid_source[base_call] = ('routes_consensus', time.time())
            else:
                # Tied votes - skip this node, insufficient routing data
                self.skipped_no_ssid[base_call] = dict(votes)
                if self.verbose:
                    print("  No consensus for {} (tied: {}), skipping".format(
                        base_call, dict(votes)))
        
        if self.verbose and ssid_votes:
            print("Built ROUTES consensus from {} callsigns".format(len(ssid_votes)))
        
        # Build alias mappings from own_aliases (for NetRom routing)
        # We populate alias_to_call for reverse lookups, but do NOT use alias field for SSIDs
        for callsign, node_data in nodes_data.items():
            node_base = callsign.split('-')[0] if '-' in callsign else callsign
            own_aliases = node_data.get('own_aliases', {})
            
            # For each alias this node has, map it to the full callsign
            for alias, full_call in own_aliases.items():
                if alias not in self.alias_to_call:
                    self.alias_to_call[alias] = full_call
                    
            # If we have ROUTES consensus for this base call, find matching alias for routing
            if node_base in self.netrom_ssid_map:
                consensus_ssid = self.netrom_ssid_map[node_base]
                # Find alias that maps to this SSID
                for alias, full_call in own_aliases.items():
                    if full_call == consensus_ssid:
                        self._set_call_to_alias(node_base, alias, 'JSON_own_aliases')
                        break
        
        # Also populate alias_to_call from seen_aliases (other nodes' aliases)
        for callsign, node_data in nodes_data.items():
            for alias, full_call in node_data.get('seen_aliases', {}).items():
                if alias not in self.alias_to_call:
                    self.alias_to_call[alias] = full_call
        
        # Note: netrom_ssids already processed via ROUTES consensus above
        
        # Restore route_ports from LOCAL node's heard_on_ports (for first-hop fallback)
        # Also build node_route_ports for ALL nodes (needed for direct port connections
        # at intermediate hops: C PORT uses the CURRENT node's port numbering, not localhost)
        local_base = self.callsign.split('-')[0] if '-' in self.callsign else self.callsign
        local_node_data = None
        
        # Find local node's data (may be stored with or without SSID)
        for node_key, node_data in nodes_data.items():
            node_base = node_key.split('-')[0] if '-' in node_key else node_key
            if node_base == local_base:
                local_node_data = node_data
                break
        
        if local_node_data:
            # Restore route_ports from LOCAL node's heard_on_ports only
            heard_on_ports = local_node_data.get('heard_on_ports', [])
            for call, port in heard_on_ports:
                if port is not None:
                    self.route_ports[call] = port
            
            # Also use LOCAL node's routes for fallback port assignment
            routes = local_node_data.get('routes', {})
            for neighbor, quality in routes.items():
                if neighbor not in self.route_ports and quality > 0:
                    # Use port 1 as fallback if no MHEARD data available
                    self.route_ports[neighbor] = 1
        
        # Build per-node port map from ALL nodes (for multi-hop direct port connections)
        for node_key, node_data in nodes_data.items():
            node_b = node_key.split('-')[0] if '-' in node_key else node_key
            hp = node_data.get('heard_on_ports', [])
            if hp:
                ports = {}
                for call, port in hp:
                    if port is not None:
                        cb = call.split('-')[0] if '-' in call else call
                        ports[cb] = port
                if ports:
                    self.node_route_ports[node_b] = ports
        
        # Restore CLI-forced SSIDs (these override anything from JSON)
        for base_call, forced_ssid in self.cli_forced_ssids.items():
            self.netrom_ssid_map[base_call] = forced_ssid
            self.ssid_source[base_call] = ('cli', time.time())
            # Also pull alias from own_aliases if we have it - enables NetRom fallback routing
            node_data = nodes_data.get(base_call) or nodes_data.get(forced_ssid, {})
            own_aliases = node_data.get('own_aliases', {})
            for alias, full_call in own_aliases.items():
                if full_call == forced_ssid:
                    self._set_call_to_alias(base_call, alias, 'cli_forced')
                    if alias not in self.alias_to_call:
                        self.alias_to_call[alias] = forced_ssid
                    break
            if self.verbose:
                print("Restored CLI-forced SSID: {} = {}".format(base_call, forced_ssid))
        
        if self.netrom_ssid_map:
            print("Restored {} SSID mappings from previous crawl".format(len(self.netrom_ssid_map)))
        if self.call_to_alias:
            print("Restored {} NetRom aliases from previous crawl".format(len(self.call_to_alias)))
        if self.route_ports:
            print("Restored {} route ports from previous crawl".format(len(self.route_ports)))
        
        # Find unexplored neighbors from each visited node
        for callsign, node_data in nodes_data.items():
            unexplored_neighbors = node_data.get('unexplored_neighbors', [])
            if unexplored_neighbors:
                print("  {} has {} unexplored: {}".format(callsign, len(unexplored_neighbors), ', '.join(sorted(unexplored_neighbors)[:5]) + ('...' if len(unexplored_neighbors) > 5 else '')))
            
            # Process each unexplored neighbor
            for neighbor in unexplored_neighbors:
                # Skip if already visited or excluded (check both full callsign and base)
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                if neighbor in self.visited or neighbor_base in self.visited or neighbor in self.exclude or neighbor_base in self.exclude:
                    continue
                
                # Skip if not in any ROUTES table (unreachable via NetRom)
                # Nodes only in MHEARD but not ROUTES are likely user stations or offline nodes
                if neighbor_base not in ssid_votes:
                    self.skipped_no_route.add(neighbor_base)
                    if self.verbose:
                        print("  Skipping {} (not in any ROUTES table)".format(neighbor))
                    continue
                
                # Skip if SSID has tied votes (already marked as skipped during consensus)
                # UNLESS user has CLI-forced the SSID (override consensus)
                if neighbor_base in self.skipped_no_ssid and neighbor_base not in self.cli_forced_ssids:
                    if self.verbose:
                        print("  Skipping {} (tied SSID votes)".format(neighbor))
                    continue
                
                # NOTE: We do NOT skip nodes that lack a NetRom alias!
                # If the node is in ROUTES (ssid_votes check above passed), we can reach it.
                # The connection logic queries ROUTES at each hop to get port numbers.
                # Example: At KX1EMA, ROUTES shows "1 WD1O-15 200" - we can "C 1 WD1O-15"
                # This allows crawling nodes that appear in ROUTES but not in NODES tables.
                
                # Determine SSID to use for this unexplored neighbor
                # SSID Selection Standard: CLI > ROUTES consensus > base callsign only
                # unexplored_neighbors may contain SSIDs from routes/MHEARD - only trust netrom_ssid_map
                neighbor_to_queue = neighbor
                
                # Check if we have SSID from primary alias for this neighbor
                if neighbor_base in self.netrom_ssid_map:
                    # We have SSID from primary alias or CLI - use it
                    neighbor_to_queue = self.netrom_ssid_map[neighbor_base]
                elif '-' in neighbor:
                    # No primary alias known, neighbor has SSID - strip to base callsign
                    # Let NetRom discovery find the correct node SSID during crawl
                    neighbor_to_queue = neighbor_base
                
                # Calculate path to this neighbor
                # Priority:
                # 1. If neighbor was previously visited successfully, use its own successful_path
                # 2. Otherwise, use parent's successful_path + parent callsign
                # 3. Fallback to BFS reconstruction
                neighbor_node_data = nodes_data.get(neighbor_to_queue)
                if neighbor_node_data and 'successful_path' in neighbor_node_data:
                    # Use the neighbor's own proven successful path (highest priority)
                    path = neighbor_node_data['successful_path']
                    if self.verbose:
                        print("    Using proven path for {}: {}".format(neighbor_to_queue, ' > '.join(path) if path else '(direct)'))
                else:
                    # Reconstruct path via parent node
                    parent_successful_path = node_data.get('successful_path')
                    if parent_successful_path is not None:
                        # Use the proven successful path from previous crawl
                        if callsign == self.callsign:
                            # Parent is local node
                            path = []
                        else:
                            # Path to neighbor = proven path to parent + parent itself
                            path = parent_successful_path + [callsign]
                    else:
                        # Fallback to BFS reconstruction
                        hop_distance = node_data.get('hop_distance', 0)
                        if hop_distance == 0:
                            # Parent is local node, direct connection to neighbor
                            path = []
                        else:
                            # Use BFS to find path from local node to parent node
                            # Then neighbor is reached via parent
                            parent_path = self._find_path_to_node(callsign, nodes_data)
                            if parent_path is not None:
                                # Path to neighbor = path to parent + parent itself
                                path = parent_path + [callsign]
                            else:
                                # Fallback: assume direct connection to parent
                                path = [callsign]

                # A node that shows up as "unexplored" in several different
                # parents' neighbor lists (common - e.g. KC1JMH-15 was listed
                # by WS1EC, NG1P-4, WD1O-15 AND KX1EMA-15 on 2026-08-21)
                # always resolves to the SAME successful_path here, since that
                # path comes from the neighbor's own record, not the parent's.
                # Without this check the same (target, path) pair went into
                # the queue once per parent that mentioned it - on that run
                # KC1JMH-15 was queued 4 times and, combined with each failed
                # attempt burning a full conn_timeout, consumed the entire
                # session without ever reaching any of the other 7 targets.
                path_key = (neighbor_to_queue, tuple(path))
                if path_key in self.queued_paths:
                    continue
                self.queued_paths.add(path_key)
                unexplored.append((neighbor_to_queue, path))
        
        # Sort by multiple criteria to try best paths first:
        # 1. Hop count (fewer hops = more reliable)
        # 2. Node callsign (for deterministic ordering)
        # This allows multiple attempts to same node via different paths
        unexplored.sort(key=lambda x: (len(x[1]), x[0]))
        
        print("Found {} path(s) to {} unique neighbor(s)".format(len(unexplored), len(set(call for call, _ in unexplored))))
        return unexplored
    
    def _is_likely_node_ssid(self, full_callsign):
        """
        Check if a callsign-SSID looks like a node SSID (used for routing).
        
        Node SSIDs are typically -15, but vary by sysop. We can't rely on specific numbers.
        Instead, we use heuristics: SSIDs in valid range (1-15) are potentially nodes.
        
        This is ONLY used to decide connection preference when multiple SSIDs exist.
        All SSIDs are preserved in maps for visualization.
        
        Args:
            full_callsign: Full callsign with SSID (e.g., 'KS1R-13')
            
        Returns:
            True if valid SSID range (1-15), False if suspicious (0, >15, or invalid)
        """
        if '-' not in full_callsign:
            return True  # Base callsign without SSID is valid
        
        try:
            ssid = int(full_callsign.rsplit('-', 1)[1])
            # Valid SSID range is 0-15, but 0 and >15 are suspicious
            return 1 <= ssid <= 15
        except (ValueError, IndexError):
            return False
    
    def _is_valid_netrom_alias(self, alias, base_call=None):
        """
        Check if an alias is a valid NetRom alias (not a callsign stored by mistake).
        
        Valid NetRom aliases are 6-character names like "CHABUR", "KNXSTG", etc.
        Invalid: callsigns stored as aliases (bug) like "KS1R" for "KS1R"
        
        Args:
            alias: The alias string to validate
            base_call: Optional base callsign - if alias == base_call, it's invalid
            
        Returns:
            True if valid alias, False if it looks like a callsign
        """
        if not alias:
            return False
        
        # If alias equals base callsign, it's definitely wrong
        if base_call and alias == base_call:
            return False
        
        # If alias looks like a callsign, it's wrong
        if self._is_valid_callsign(alias):
            return False
        
        return True
    
    def _set_call_to_alias(self, base_call, alias, source='unknown'):
        """
        Safely set a call-to-alias mapping, validating that alias is not a callsign.
        
        Args:
            base_call: Base callsign (e.g., 'KS1R')
            alias: NetRom alias (e.g., 'CHABUR')
            source: Debug string for logging where this was called from
            
        Returns:
            True if set successfully, False if alias was invalid
        """
        if not self._is_valid_netrom_alias(alias, base_call):
            if self.verbose:
                print("    WARNING: Rejecting invalid alias '{}' for {} (from {})".format(
                    alias, base_call, source))
            return False
        
        self.call_to_alias[base_call] = alias
        return True
    
    def _parse_ports(self, output):
        """
        Parse PORTS output to extract port details.
        
        Expected format:
            Ports
              1 433.300 MHz 1200 BAUD
              2 145.050 MHz @ 1200 b/s
              8 AX/IP/UDP
              9 Telnet Server
              3 VARA HF
        
        Returns:
            List of port dictionaries with number, frequency, speed, type, port_type
            port_type: 'rf' (VHF/UHF), 'hf' (VARA/ARDOP/PACTOR), 'ip' (AXIP/TCP/Telnet)
        """
        ports = []
        lines = output.split('\n')
        
        for line in lines:
            # Skip empty lines and header
            line = line.strip()
            if not line or line.lower() == 'ports':
                continue
            
            # Pattern: port_num followed by description
            # Examples: "1 433.300 MHz 1200 BAUD", "9 Telnet Server", "8 AX/IP/UDP"
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if not match:
                continue
            
            port_num = int(match.group(1))
            rest = match.group(2).strip()
            
            # Try to extract speed (baud rate) from description
            # Look for patterns like "1200 BAUD", "@ 1200 b/s", "1200 Baud"
            speed = None
            speed_match = re.search(r'@?\s*(\d+)\s*(?:b/s|baud|BAUD)', rest, re.IGNORECASE)
            if speed_match:
                speed = int(speed_match.group(1))
            
            # Try to extract frequency from description
            # Look for patterns like "433.300 MHz", "145.050 MHz", "144.930 MHz", "144.990" (MHz implied)
            frequency = None
            freq_match = re.search(r'(\d+\.\d+)\s*(?:MHz)?', rest, re.IGNORECASE)
            if freq_match:
                freq_str = freq_match.group(1)
                # Only parse if it looks like a frequency (30-3000 MHz range for amateur radio)
                freq_val = float(freq_str)
                if 30.0 <= freq_val <= 3000.0:
                    frequency = freq_val
            
            # Full description is everything after port number
            description = rest
            
            # Classify port type: rf (VHF/UHF), hf (VARA/ARDOP/PACTOR), ip (AXIP/TCP/Telnet)
            desc_upper = description.upper()
            
            # Check for IP-based ports first
            if any(x in desc_upper for x in ['TELNET', 'TCP', 'IP', 'UDP', 'AX/IP', 'AXIP', 'AXUDP']):
                port_type = 'ip'
                is_rf = False
            # Check for HF digital modes (slow, typically 300 baud or less)
            # Match standalone "HF" or mode names like VARA, ARDOP, PACTOR
            elif any(x in desc_upper for x in ['VARA', 'ARDOP', 'PACTOR', 'WINMOR', 'PACKET HF', 'HF PACKET', ' HF', 'HF ']):
                port_type = 'hf'
                is_rf = True  # HF is RF, but we may want to skip it
            # Check if description is just "HF" or starts/ends with HF
            elif desc_upper == 'HF' or desc_upper.startswith('HF ') or desc_upper.endswith(' HF'):
                port_type = 'hf'
                is_rf = True
            # Check for HF by frequency (below 30 MHz)
            elif frequency and frequency < 30.0:
                port_type = 'hf'
                is_rf = True
            # Check for HF by slow speed (300 baud or less typically HF)
            elif speed and speed <= 300:
                port_type = 'hf'
                is_rf = True
            else:
                # Default: VHF/UHF RF port
                port_type = 'rf'
                is_rf = True
            
            ports.append({
                'number': port_num,
                'description': description,
                'frequency': frequency,  # MHz as float (433.3, 145.05, etc.)
                'speed': speed,
                'is_rf': is_rf,
                'port_type': port_type  # 'rf', 'hf', or 'ip'
            })
        
        return ports
    
    def _parse_nodes_aliases(self, output):
        """
        Parse NODES output to get alias/SSID mappings and neighbor callsigns.
        
        NODES output contains two types of entries:
        1. Aliased: "CCEBBS:WS1EC-2" (alias:callsign-ssid)
        2. Non-aliased: "N1LJK-15" (just callsign-ssid, no alias)
        
        Both types indicate entries in the routing table (crawlable nodes).
        Non-aliased entries are common for nodes that only advertise their
        node SSID without application aliases.
        
        Returns:
            Tuple of (aliases dict, netrom_ssids dict, neighbors list)
            - aliases: Maps alias to full callsign-SSID
            - netrom_ssids: Maps base callsign to NetRom SSID for connections
            - neighbors: List of base callsigns (without SSID)
        """
        aliases = {}
        netrom_ssids = {}
        neighbors = []
        
        # First pass: Look for aliased entries like "CCEBBS:WS1EC-2"
        matches = re.findall(r'(\w+):(\w+(?:-\d+)?)', output)
        for alias, callsign in matches:
            alias = self._normalize_callsign(alias)
            callsign = self._normalize_callsign(callsign)
            # Validate callsign format
            if self._is_valid_callsign(callsign):
                aliases[alias] = callsign
                # Extract base callsign and SSID
                if '-' in callsign:
                    base_call, ssid = callsign.rsplit('-', 1)
                    netrom_ssids[base_call] = callsign
                else:
                    base_call = callsign
                    netrom_ssids[base_call] = callsign
                
                if base_call not in neighbors:
                    neighbors.append(base_call)
        
        # Second pass: Look for non-aliased entries like "N1LJK-15"
        # These are callsign-SSID patterns NOT preceded by a colon (not part of alias)
        # Pattern: word boundary, callsign-SSID, whitespace or end
        # Exclude entries already found via aliases
        non_aliased = re.findall(r'\b([A-Z]{1,2}\d[A-Z]{1,3}-\d{1,2})\b', output)
        for full_callsign in non_aliased:
            full_callsign = self._normalize_callsign(full_callsign)
            base_call = full_callsign.rsplit('-', 1)[0]
            # Skip if we already have this from aliased entries
            if base_call in netrom_ssids:
                continue
            # Validate callsign format
            if self._is_valid_callsign(full_callsign):
                netrom_ssids[base_call] = full_callsign
                if base_call not in neighbors:
                    neighbors.append(base_call)
        
        return aliases, netrom_ssids, neighbors
    
    def _parse_applications(self, info_output):
        """
        Extract application list from INFO output.
        
        Note: INFO is freeform text entered by sysop. Application list format
        and content varies widely and should be considered unreliable.
        
        Returns:
            List of application dictionaries with name, description, ssid
        """
        apps = []
        lines = info_output.split('\n')
        in_apps_section = False
        
        for line in lines:
            # Look for "Applications" header
            if 'application' in line.lower() and ('---' in lines[lines.index(line) + 1] if lines.index(line) + 1 < len(lines) else False):
                in_apps_section = True
                continue
            
            # Stop at next section header (dashes or all caps words followed by dashes)
            if in_apps_section and ('---' in line or (line.isupper() and line.strip())):
                in_apps_section = False
                continue
            
            # Parse application lines like: "BBS     Inter-node Mail      WS1EC-2"
            if in_apps_section and line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    # Find SSID if present (callsign-number at end)
                    ssid = None
                    if len(parts) > 1 and re.match(r'\w+-\d+', parts[-1]):
                        ssid = parts[-1]
                        description = ' '.join(parts[1:-1])
                    else:
                        description = ' '.join(parts[1:])
                    
                    apps.append({
                        'name': name,
                        'description': description.strip(),
                        'ssid': ssid
                    })
        
        return apps
    
    def _parse_commands(self, output):
        """
        Parse ? command output to get list of available commands/applications.
        
        Returns:
            Tuple of (commands list, applications list)
            - commands: All available commands
            - applications: Subset that are actual applications (BBS, CHAT, RMS, etc.)
        """
        commands = []
        lines = output.split('\n')
        
        for line in lines:
            # Skip header/separator lines
            if not line.strip() or '---' in line or 'Commands' in line:
                continue
            
            # Commands are typically listed in columns or one per line
            # Extract words that look like commands (uppercase, alphanumeric)
            words = line.split()
            for word in words:
                # Filter for likely command names (avoid help text)
                if word.isupper() or (word[0].isupper() and len(word) <= 10):
                    # Clean up any trailing punctuation
                    cmd = word.strip('.,;:')
                    if cmd and cmd not in commands:
                        commands.append(cmd)
        
        # Identify actual applications (interactive services)
        # Exclude standard BPQ/JNOS/FBB commands - only keep user-facing applications
        # Standard commands that are NOT applications:
        standard_commands = {
            # BPQ User Commands
            'BYE', 'CONNECT', 'C', 'DISCONNECT', 'D', 'INFO', 'I', 'NODES', 'N',
            'PORTS', 'ROUTES', 'USERS', 'U', 'MHEARD', 'MH', 'LINKS', 'L',
            'SESSION', 'S', 'YAPP', 'UNPROTO', 'VERSION', 'V', 'HOME', 'CQ',
            # BPQ Sysop Commands (uppercase only - avoids filtering 'Sysop' as text)
            'SYSOP', 'ATTACH', 'DETACH', 'RECONNECT', 'RESPTIME', 'FRACK',
            'FRACKS', 'PACLEN', 'MAXFRAME', 'RETRIES', 'RESET',
            # JNOS Commands
            'ARP', 'DIALER', 'DOMAIN', 'EXIT', 'FINGER', 'FTP', 'HELP',
            'HOPCHECK', 'IFCONFIG', 'IP', 'KICK', 'LOG', 'NETROM', 'PING',
            'PPP', 'RECORD', 'REMOTE', 'ROUTE', 'SMTP', 'START',
            'STOP', 'TCP', 'TRACE', 'UDP', 'UPLOAD',
            # FBB Commands
            'ABORT', 'CHECK', 'DIR', 'EXPERT', 'HELP', 'KILL', 'LIST',
            'READ', 'REPLY', 'SEND', 'STATS', 'TALK', 'VERBOSE', 'WHO',
            # Kantronics X1J4 Commands (KPC-3 Plus TNC firmware)
            'ADC', 'HOST', 'IPROUTE', 'QUIT'
        }
        
        # Built-in BPQ applications that should ALWAYS be counted as apps
        builtin_apps = {'BBS', 'CHAT', 'RMS', 'APRS', 'CHATSVR', 'MAIL'}
        
        # Filter applications: Include if:
        # 1. In builtin_apps (BBS, CHAT, RMS, etc.)
        # 2. Not in standard_commands (custom apps like GOPHER, EANHUB, TEST, FORMS, etc.)
        applications = []
        for cmd in commands:
            cmd_upper = cmd.upper()
            # Always include builtins
            if cmd_upper in builtin_apps:
                applications.append(cmd)
            # Include if not a standard command
            elif cmd_upper not in standard_commands:
                # Exclude node prompts (contain ':' or '}' like "CCEMA:WS1EC-15}")
                if ':' not in cmd and '}' not in cmd:
                    applications.append(cmd)
        
        return commands, applications
    
    def _parse_routes(self, output):
        """
        Parse ROUTES output to find best paths to destinations.
        
        ROUTES is the AUTHORITATIVE source for node SSIDs!
        Direct neighbor entries (lines starting with >) show the actual node SSID,
        not application SSIDs like BBS (-2), RMS (-10), or CHAT (-13).
        
        Example:
            > 1 K1NYY-15  200 13!   <- K1NYY-15 is the NODE (not K1NYY-2 BBS or K1NYY-10 RMS)
            > 1 KS1R-15   200 20!   <- KS1R-15 is the NODE (not KS1R-13 CHAT)
        
        Returns:
            Tuple of (routes dict, ports dict, ssids dict, direct_neighbors set)
            - routes: {callsign: quality} for all routes
            - ports: {callsign: port_number} for direct neighbors only
            - ssids: {base_callsign: full_callsign-ssid} for direct neighbors (AUTHORITATIVE)
            - direct_neighbors: set of base callsigns that are direct RF neighbors (> prefix)
        """
        routes = {}
        ports = {}
        ssids = {}  # Store authoritative node SSIDs from ROUTES
        direct_neighbors = set()  # Only entries with > prefix (actual RF neighbors)
        lines = output.split('\n')
        
        for line in lines:
            # Look for direct neighbor routes (start with >)
            # Format: "> PORT CALLSIGN-SSID QUALITY METRIC"
            # Example: "> 1 WS1EC-15  200 4!"
            # Kantronics X1J4 format: "> PORT ALIAS:CALLSIGN-SSID QUALITY METRIC"
            # Example: "> 0 KNXABN:AB1KI-15 10 4"
            if line.strip().startswith('>'):
                match = re.search(r'>\s+(\d+)\s+(\S+)\s+(\d+)', line)
                if match:
                    port_num = int(match.group(1))
                    call_field = match.group(2)
                    quality = int(match.group(3))
                    # Strip ALIAS: prefix if present (Kantronics X1J4 format)
                    if ':' in call_field:
                        call_field = call_field.split(':')[-1]
                    full_call = self._normalize_callsign(call_field)
                    base_call = full_call.split('-')[0]
                    
                    # Validate callsign format
                    if self._is_valid_callsign(base_call):
                        routes[base_call] = quality
                        ports[base_call] = port_num  # Store port for direct neighbors
                        ssids[base_call] = full_call  # AUTHORITATIVE node SSID
                        direct_neighbors.add(base_call)
                        continue
            
            # Look for other route lines (non-direct neighbors)
            # Format: "  PORT CALLSIGN-SSID QUALITY METRIC"
            # Example: "  1 K1NYY-15  200 0!" (reachable via intermediate hop)
            # Kantronics X1J4: "  PORT ALIAS:CALLSIGN-SSID QUALITY METRIC"
            # The port number indicates which port the node was last heard on
            # Skip routes with quality 0 (blocked/poor paths that sysop disabled)
            match = re.search(r'^\s+(\d+)\s+(\S+)\s+(\d+)', line)
            if match:
                port_num = int(match.group(1))
                call_field = match.group(2)
                quality = int(match.group(3))
                # Strip ALIAS: prefix if present (Kantronics X1J4 format)
                if ':' in call_field:
                    call_field = call_field.split(':')[-1]
                full_call = self._normalize_callsign(call_field)
                base_call = full_call.split('-')[0]
                
                # Validate callsign format and skip quality 0 (blocked routes)
                if self._is_valid_callsign(base_call):
                    if quality > 0:
                        if base_call not in routes:  # Don't overwrite direct neighbor entries
                            routes[base_call] = quality
                            ports[base_call] = port_num  # Store port for connection fallback
                            ssids[base_call] = full_call  # AUTHORITATIVE node SSID from ROUTES
                    elif self.verbose:
                        print("    Ignoring {} (quality 0 - sysop blocked route)".format(full_call))
        
        return routes, ports, ssids, direct_neighbors
    
    # ------------------------------------------------------------------
    # Callsign quality control
    # ------------------------------------------------------------------

    @staticmethod
    def _has_crawl_evidence(node):
        """True if this record came from an actual conversation with a station.

        A node we have connected to and read commands from is real, whatever
        its callsign looks like. WD1F is a genuine Maine BBS whose callsign
        happens to sit one character from WD1O, a genuine node; without this
        check a single early quarantine would delete it from the map on every
        subsequent crawl and block it from ever being retried.
        """
        if not isinstance(node, dict):
            return False
        if node.get('own_aliases') or node.get('ports') or node.get('commands'):
            return True
        info = (node.get('info') or '').strip()
        return len(info) > 20

    def _clear_ignore(self, callsign, why):
        """Un-quarantine a callsign that has proved itself real."""
        base = _base_call(callsign)
        removed = self.suspect_calls.pop(base, None)
        if self.overrides.is_ignored(base):
            self.overrides.remove_ignore(base)
            removed = True
        if removed:
            colored_print("  {} is real ({}) - removed from the ignore list".format(
                base, why), Colors.GREEN)
        return bool(removed)

    def _rebuild_anchors(self, nodes_data):
        """Rebuild the known-good callsign sets from existing nodemap data.

        Called before the first connection so the bit-error heuristics have
        something to compare against even on a resumed or update-mode crawl
        that never re-visits a node.
        """
        for callsign, node in nodes_data.items():
            self.confirmed_calls.add(_base_call(callsign))
            # own_aliases is this node describing its own services - as
            # authoritative as it gets.
            for full in (node.get('own_aliases') or {}).values():
                self.confirmed_calls.add(_base_call(str(full)))
            # ROUTES arrives inside an acked NET/ROM session, so it is
            # corroboration, though not proof of a station we have met.
            for neighbor in (node.get('routes') or {}):
                self.structured_calls.add(_base_call(neighbor))
            for neighbor in (node.get('direct_routes') or {}):
                self.structured_calls.add(_base_call(neighbor))

    def _count_mheard(self, nodes_data):
        """Tally how many distinct nodes reported hearing each callsign."""
        for node in nodes_data.values():
            for neighbor in set(node.get('neighbors') or []):
                key = _base_call(neighbor)
                self.mheard_counts[key] = self.mheard_counts.get(key, 0) + 1

    def _scrub_loaded_data(self, nodes_data):
        """Re-judge callsigns already sitting in nodemap.json.

        Filtering only at crawl time would leave every ghost that earlier
        versions recorded permanently baked into the map, since update-mode
        runs never re-visit most nodes. Running the same heuristics over the
        loaded data lets one crawl clean up the whole history.
        """
        observed = set()
        for node in nodes_data.values():
            for field in ('neighbors', 'unexplored_neighbors',
                          'explored_neighbors', 'intermittent_neighbors'):
                for neighbor in (node.get(field) or []):
                    observed.add(neighbor)

        known = {_base_call(c) for c in nodes_data}
        rejected = []
        judged = set()
        for neighbor in sorted(observed):
            base = _base_call(neighbor)
            # Never quarantine a node we have actually crawled and stored.
            if base in known:
                continue
            # Judge each station once. Without this the SSID variants get
            # judged after the bare call has already been added to the ignore
            # list, and every one of them reports back as 'sysop_ignored'.
            if base in judged:
                if base in self.suspect_calls:
                    self._quarantine(neighbor, self.suspect_calls[base]['reason'])
                continue
            judged.add(base)
            verdict, reason = self._judge_callsign(neighbor)
            if verdict == 'suspect':
                self._quarantine(neighbor, reason)
                rejected.append((neighbor, reason))
        if rejected:
            colored_print("Quarantined {} suspect callsign(s) from existing data".format(
                len(rejected)), Colors.YELLOW)
            for neighbor, reason in sorted(rejected):
                print("    {:<12} {}".format(neighbor, reason))
        return rejected

    def _scrub_locations(self, nodes_data):
        """Re-parse stored location text with the current rules.

        Earlier versions accepted any capitalised word before a two-letter
        token as a City/State pair, so "BPQ32 Node KNXSTG - St. George, ME"
        stored a city of "Node". Those values sit in nodemap.json until the
        node happens to be re-crawled, and they are what the web map and the
        mepn import read. Re-deriving them from each node's own stored INFO
        text fixes the whole history in one pass.

        Only city and state are touched. A gridsquare is never rewritten
        here - it may have come from a sysop override or a lookup, neither of
        which is reconstructible from INFO text.
        """
        cleaned = 0
        for callsign, node in nodes_data.items():
            location = node.get('location')
            if not isinstance(location, dict):
                continue
            city = (location.get('city') or '').strip()
            state = (location.get('state') or '').strip().upper()
            if not city and not state:
                continue

            suspect_city = any(word.lower() in PLACE_NOISE_WORDS
                               for word in city.split())
            suspect_state = bool(state) and state not in US_STATES
            if not (suspect_city or suspect_state):
                continue

            parsed = LocationResolver.parse_info_text(node.get('info') or '')
            if parsed.get('city') and parsed.get('state'):
                location['city'] = parsed['city']
                location['state'] = parsed['state']
                self.location_fixes[callsign] = {
                    'city': parsed['city'], 'state': parsed['state']}
            else:
                # Nothing trustworthy to replace it with; better absent than wrong.
                location.pop('city', None)
                location.pop('state', None)
                self.location_fixes[callsign] = {'city': None, 'state': None}
            cleaned += 1
            if self.verbose:
                print("    Re-parsed location for {}: {!r} -> {!r}".format(
                    callsign, city, location.get('city', '')))
        if cleaned:
            colored_print("Re-parsed {} bad city/state value(s) from stored INFO text".format(
                cleaned), Colors.YELLOW)
        return cleaned

    def _judge_callsign(self, callsign):
        """Classify one observed callsign, honouring sysop overrides.

        Returns (verdict, reason). A sysop decision short-circuits both ways:
        an explicit confirm beats the heuristics, an explicit ignore beats
        everything.
        """
        base = _base_call(callsign)
        if self.overrides.is_confirmed(base):
            return 'confirmed', 'sysop_confirmed'
        if self.overrides.is_ignored(base):
            return 'suspect', 'sysop_ignored'
        return CallsignValidator.classify(
            callsign, self.confirmed_calls, self.structured_calls,
            self.mheard_counts.get(base, 1))

    def _quarantine(self, callsign, reason):
        """Record a ghost callsign and keep it out of the crawl queue."""
        base = _base_call(callsign)
        if base not in self.suspect_calls:
            self.suspect_calls[base] = {
                'reason': reason,
                'observed_as': [callsign],
                'heard_by': self.mheard_counts.get(base, 1),
                'flagged': _now(),
            }
        elif callsign not in self.suspect_calls[base]['observed_as']:
            self.suspect_calls[base]['observed_as'].append(callsign)
        # Feeding the persistent ignore list is what stops the next crawl
        # spending RF time trying to connect to a call that never existed.
        if self.auto_ignore and reason != 'sysop_ignored':
            self.overrides.add_ignore(base, reason, source='quarantine')

    def _filter_callsigns(self, callsigns):
        """Split observed callsigns into (keep, quarantined).

        'unverified' calls are kept - they are single-source MHEARD hits that
        do not resemble anything known, which is exactly what a genuinely new
        station looks like on its first beacon.
        """
        keep, dropped = [], []
        for callsign in callsigns:
            verdict, reason = self._judge_callsign(callsign)
            if verdict == 'suspect':
                self._quarantine(callsign, reason)
                dropped.append((callsign, reason))
            else:
                keep.append(callsign)
        if dropped and self.verbose:
            for callsign, reason in dropped:
                print("    Quarantined {} ({})".format(callsign, reason))
        return keep, dropped

    # ------------------------------------------------------------------
    # Temporal tracking
    # ------------------------------------------------------------------

    # A node is 'online' if we reached it or heard it recently; 'stale' once
    # nothing has confirmed it for a week; 'offline' once we have tried and
    # failed repeatedly. These thresholds are deliberately generous - a
    # packet node can be off the air for days of bad weather and still be a
    # real, wanted part of the map.
    STALE_AFTER_DAYS = 7
    OFFLINE_AFTER_FAILURES = 3
    RECENT_HEARD_SECONDS = 86400

    @staticmethod
    def _parse_stamp(value):
        """Parse an export timestamp, returning epoch seconds or None."""
        if not value:
            return None
        try:
            return time.mktime(time.strptime(value, '%Y-%m-%d %H:%M:%S'))
        except (ValueError, TypeError):
            return None

    def _days_since(self, value):
        stamp = self._parse_stamp(value)
        if stamp is None:
            return None
        return (time.time() - stamp) / 86400.0

    def _load_history(self, nodes_data):
        """Preserve temporal fields from a previous export.

        Everything here has to survive a crawl that does not re-visit the
        node, which is the normal case in update mode.
        """
        for callsign, node in nodes_data.items():
            # Keyed by base callsign: nodemap.json stores remote nodes with
            # their SSID (e.g. 'KS1R-15'), but crawl_node() and every other
            # writer of node_history only ever sees the base call ('KS1R') -
            # loading under the SSID key meant a re-crawled node's history
            # was written to a different dict entry than the one export read
            # back, so status/last_crawled silently reverted to whatever was
            # loaded here on every single run.
            self.node_history[_base_call(callsign)] = {
                'first_seen': node.get('first_seen') or node.get('timestamp'),
                'last_seen': node.get('last_seen'),
                'last_crawled': node.get('last_crawled'),
                'crawl_successes': node.get('crawl_successes', 0),
                'crawl_attempts': node.get('crawl_attempts', 0),
                'consecutive_failures': node.get('consecutive_failures', 0),
            }
        for key, record in (self.loaded_connection_history or {}).items():
            self.connection_history[key] = record

    def _record_crawl_result(self, callsign, success, reason=None):
        """Update attempt/success counters for one node."""
        history = self.node_history.setdefault(callsign, {})
        history['crawl_attempts'] = history.get('crawl_attempts', 0) + 1
        if success:
            history['crawl_successes'] = history.get('crawl_successes', 0) + 1
            history['consecutive_failures'] = 0
            history['last_crawled'] = _now()
            history['last_seen'] = _now()
            history.setdefault('first_seen', _now())
        else:
            history['consecutive_failures'] = history.get('consecutive_failures', 0) + 1
            if reason:
                self.crawl_failures[_base_call(callsign)] = reason

    def _node_status(self, callsign, node):
        """Derive online/stale/offline for one node.

        Two independent signals feed this: whether we could connect, and how
        recently anybody heard the node on RF. A node we cannot route to may
        still be plainly alive and beaconing, and that is worth showing
        differently from one that has genuinely gone quiet.
        """
        base = _base_call(callsign)
        history = self.node_history.get(base, {})
        failures = history.get('consecutive_failures', 0)

        if base in self.freshly_crawled:
            return 'online'

        heard = self.last_heard.get(base)
        if heard is not None and heard <= self.RECENT_HEARD_SECONDS:
            return 'online'

        if failures >= self.OFFLINE_AFTER_FAILURES:
            return 'offline'
        if base in self.crawl_failures:
            return 'unreachable'

        # Nothing below this point is positive evidence of the node being up
        # this run - it is all inference from how long ago we last had any.
        age = self._days_since(history.get('last_seen') or node.get('last_seen'))
        if age is None:
            return 'unreachable' if failures else 'unknown'
        if age > self.STALE_AFTER_DAYS:
            return 'stale'
        return 'recent'

    def _apply_temporal_fields(self, callsign, node):
        """Stamp first/last seen and status onto one exported node record."""
        base = _base_call(callsign)
        history = self.node_history.get(base, {})

        # Fall back to the previous export's timestamp rather than to now:
        # claiming a node was seen this instant because we happened to load a
        # file that mentions it would make every stale node look healthy.
        bootstrap = self.previous_crawl_time or self.crawl_started
        first_seen = history.get('first_seen') or node.get('first_seen') or bootstrap
        last_crawled = history.get('last_crawled') or node.get('last_crawled')

        # last_seen means "most recent evidence this station exists", which
        # includes being heard by somebody else even when we never reached it.
        last_seen = history.get('last_seen') or node.get('last_seen')
        heard = self.last_heard.get(base)
        if base in self.freshly_crawled:
            last_seen = self.crawl_started
        elif heard is not None:
            heard_at = time.time() - heard
            candidate = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(heard_at))
            if not last_seen or candidate > last_seen:
                last_seen = candidate

        node['first_seen'] = first_seen
        node['last_seen'] = last_seen or bootstrap
        if last_crawled:
            node['last_crawled'] = last_crawled
        node['crawl_attempts'] = history.get('crawl_attempts', node.get('crawl_attempts', 0))
        node['crawl_successes'] = history.get('crawl_successes', node.get('crawl_successes', 0))
        node['consecutive_failures'] = history.get(
            'consecutive_failures', node.get('consecutive_failures', 0))
        if heard is not None:
            node['last_heard_seconds'] = heard
        node['status'] = self._node_status(callsign, node)
        age = self._days_since(node['last_seen'])
        if age is not None:
            node['days_since_seen'] = round(age, 2)
        return node

    def _should_crawl(self, callsign):
        """Gate on the ignore list before any RF time is spent.

        Quarantined ghosts and sysop-rejected callsigns are dropped here
        rather than at export, so a corrupt call discovered on one crawl
        costs nothing on every crawl after it - each avoided connection
        attempt is minutes of 1200-baud air time.
        """
        base = _base_call(callsign)
        # Anything we have successfully crawled outranks the ignore list. A
        # stale quarantine must not be able to make a real station
        # permanently unreachable.
        for known, node in self.nodes.items():
            if _base_call(known) == base and self._has_crawl_evidence(node):
                return True
        if base in self.suspect_calls:
            return False
        if self.overrides.is_ignored(base):
            if self.verbose:
                print("  Skipping {} (on ignore list)".format(callsign))
            return False
        return True

    def crawl_node(self, callsign, path=[]):
        """
        Crawl a single node to discover neighbors.
        
        Args:
            callsign: Node callsign to crawl
            path: Connection path to reach this node
        """
        # Check if node is excluded (match both full callsign and base callsign)
        callsign = self._normalize_callsign(callsign)
        base_call = callsign.split('-')[0] if '-' in callsign else callsign
        if not self._should_crawl(callsign):
            return
        if callsign in self.exclude or base_call in self.exclude:
            if self.verbose:
                print("  Skipping {} (excluded via --exclude)".format(callsign))
            return
        
        # Check if already visited based on crawl mode
        if callsign in self.visited:
            if self.crawl_mode == 'reaudit':
                # Re-audit mode: allow re-crawling known nodes
                if self.verbose:
                    print("  Re-auditing {} (reaudit mode)".format(callsign))
                self.visited.remove(callsign)  # Remove so we can re-crawl
            else:
                # Update or new-only mode: skip already visited
                return
        
        # In new-only mode, also skip nodes already in self.nodes (from nodemap.json)
        if self.crawl_mode == 'new-only':
            # Check both exact callsign and base callsign (nodes may be stored with SSID)
            base_call = callsign.split('-')[0] if '-' in callsign else callsign
            already_known = callsign in self.nodes
            # Also check if any node with same base callsign exists
            if not already_known:
                for node_key in self.nodes:
                    node_base = node_key.split('-')[0] if '-' in node_key else node_key
                    if node_base == base_call:
                        already_known = True
                        break
            if already_known:
                if self.verbose:
                    print("  Skipping {} (already in nodemap.json, new-only mode)".format(callsign))
                return
        
        # Build readable path description
        if not path:
            if callsign == self.callsign:
                path_desc = " (local node)"
            else:
                path_desc = " (direct connection)"
        else:
            path_desc = " (via {})".format(' > '.join(path))
        
        colored_print("Crawling {}{}".format(callsign, path_desc), Colors.CYAN)
        self._debug_log("Crawling {}{}".format(callsign, path_desc))
        
        # Don't add to visited yet - only after successful connection
        # This allows retrying via alternate paths if this path fails
        
        # Calculate command timeout based on path length.
        # hop_count = number of RF jumps from start node to THIS node.
        # path holds intermediate hops only, not the target itself, so a
        # node reached via one relay (path=['KC1JMH'], target=KS1R) is 2
        # hops away, not 1 - this used to under-count every multi-hop node
        # by exactly one, handing it a timeout and operation deadline sized
        # for the wrong distance and killing the crawl mid-node.
        hop_count = (len(path) + 1) if path else (0 if callsign == self.callsign else 1)
        # A real 2-hop MHEARD response measured on WS1EC took 43s to finish
        # arriving (telnet.log, 2026-08-21 15:24:28) - the old 5+10/hop
        # formula gave that command only 15s, and _send_command's previous
        # implementation got away with it only because its retry loop wasn't
        # actually bounded by this value. Now that _send_command polls to a
        # hard deadline of `timeout`, the formula has to reflect real 1200
        # baud multi-hop relay latency, with margin for network contention.
        cmd_timeout = min(10 + (hop_count * 25), 120)
        
        # Notify about connection attempt before connecting
        if not path:
            if callsign != self.callsign:
                notify_msg = "Connecting to {}".format(callsign)
            else:
                notify_msg = "Connecting to {}".format(callsign)
        else:
            notify_msg = "{} connecting to {}".format(path[-1], callsign)
        self._send_notification(notify_msg)
        
        # Connect to node
        # path contains intermediate hops only (not target)
        # For local node: path=[] (no intermediate hops)
        # For direct neighbor: callsign=KC1JMH, path=[] -> connect with C KC1JMH-15
        # For multi-hop: callsign=KS1R, path=[KC1JMH] -> C KC1JMH-15, then C KS1R-15
        connect_path = path + [callsign] if path else ([callsign] if callsign != self.callsign else [])
        
        self.last_failed_relay = None  # Reset before connection attempt
        tn = self._connect_to_node(connect_path)

        # Record how this path fared so the next crawl can start with the one
        # that worked instead of rediscovering it hop by hop over RF.
        self._record_path_result(callsign, connect_path, bool(tn))
        self._record_crawl_result(callsign, bool(tn),
                                  reason=None if tn else 'connection failed')

        # Send 'Starting crawl' notification after successful connection to local node
        if tn and not path and callsign == self.callsign:
            self._send_notification("Starting crawl from {}".format(callsign))
        if not tn:
            colored_print("  Skipping {} (connection failed)".format(callsign), Colors.YELLOW)
            
            # Track this as an intermittent/unreliable link
            # Don't add to self.failed - node may be reachable from other paths
            if path:
                # Multi-hop: track connection from last hop
                link_key = (path[-1], callsign)
            else:
                # Direct: track from local node
                link_key = (self.callsign if self.callsign else 'LOCAL', callsign)
            
            if link_key not in self.intermittent_links:
                self.intermittent_links[link_key] = []
            self.intermittent_links[link_key].append(time.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Show who failed to reach whom
            if not path:
                fail_msg = "Failed: {} unreachable".format(callsign)
            else:
                fail_msg = "{} failed to reach {}".format(path[-1], callsign)
            self._send_notification(fail_msg)
            
            # If there were intermediate hops, mark the last one as a failed relay
            # and try to find an alternative path to the target
            if path:
                failed_relay = self.last_failed_relay or (path[-1].split('-')[0] if '-' in path[-1] else path[-1])
                if failed_relay not in self.failed_relays:
                    self.failed_relays.add(failed_relay)
                    colored_print("  Marking {} as failed relay - searching for alternate path to {}".format(failed_relay, callsign), Colors.YELLOW)
                    
                    # BFS through known nodes to find alternate path avoiding failed relays
                    target_base = callsign.split('-')[0] if '-' in callsign else callsign
                    alt_path = self._find_alternate_path(target_base)
                    if alt_path is not None:
                        queue_key = (callsign, tuple(alt_path))
                        if queue_key not in self.queued_paths:
                            self.queue.appendleft((callsign, alt_path, 0))  # High priority
                            self.queued_paths.add(queue_key)
                            alt_desc = ' -> '.join(alt_path) if alt_path else '(direct)'
                            colored_print("  Re-queuing {} via alternate path: {}".format(callsign, alt_desc), Colors.CYAN)
                    else:
                        colored_print("  No alternate path found to {} (all routes blocked)".format(callsign), Colors.YELLOW)
            
            # Note: NOT adding to self.failed - node can still be explored from other neighbors
            # This allows mapping intermittent/poor connections while still discovering the node
            return
        
        # Set overall operation timeout (commands + processing)
        # Allow more generous timeout for nodes with many neighbors
        # 7 minutes base + 5 minutes per hop (was 6min + 4min/hop)
        # RF at 1200 baud is slow; need patience for multi-hop responses,
        # plus margin for other traffic contending on the same channel.
        # A node can issue a dozen commands in one crawl (?, PORTS, NODES,
        # ROUTES, one MHEARD per port, INFO, ?) each now budgeted up to
        # cmd_timeout (see above) - this has to cover all of them.
        # Override with --timeout if the default isn't enough (e.g. nodes with huge ROUTES tables)
        if self.op_timeout:
            operation_deadline = time.time() + self.op_timeout
        else:
            operation_deadline = time.time() + 420 + (hop_count * 300)
        
        # Track partial crawl data in case of timeout
        partial_data = {
            'callsign': callsign,
            'path': path,
            'hop_distance': hop_count,
            'successful_path': path if path else ([] if callsign == self.callsign else [callsign]),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'partial': True  # Mark as incomplete
        }
        
        try:
            # Helper to check if we've exceeded deadline
            def check_deadline():
                if time.time() > operation_deadline:
                    colored_print("  Operation timeout for {} ({} hops)".format(callsign, hop_count), Colors.YELLOW)
                    # Save partial data before timeout
                    if partial_data.get('info') or partial_data.get('ports') or partial_data.get('neighbors'):
                        colored_print("  Saving partial crawl data for {}...".format(callsign), Colors.YELLOW)
                        self.nodes[callsign] = partial_data
                        self.visited.add(callsign)  # Mark as visited to avoid re-crawl loops
                    return True
                return False
            
            # Inter-command delay scales with hop count
            # Over multi-hop RF, need time for responses to fully arrive
            inter_cmd_delay = 1.0 + (hop_count * 0.5)  # 1s base + 0.5s per hop
            
            # First, try ? to discover available commands
            # Some nodes may not support standard BPQ commands
            if check_deadline():
                return
            try:
                help_output = self._send_command(tn, '?', timeout=cmd_timeout, expect_content=None)
                if self.verbose:
                    cmds_summary = ' '.join(help_output.split()[:20])
                    print("  Available commands: {}".format(cmds_summary))
                    self._debug_log("Available commands: {}".format(cmds_summary))
                time.sleep(inter_cmd_delay)
            except Exception as e:
                if self.verbose:
                    print("  Note: ? command not available or failed: {}".format(e))
            
            # Get PORTS to identify RF ports
            if check_deadline():
                return
            ports_output = self._send_command(tn, 'PORTS', timeout=cmd_timeout, expect_content='Port')
            ports_list = self._parse_ports(ports_output)
            partial_data['ports'] = ports_list  # Save partial
            time.sleep(inter_cmd_delay)
            
            # Get NODES for alias mappings only (not for neighbor discovery)
            # NODES shows routing table (all reachable nodes), not RF neighbors
            if check_deadline():
                return
            nodes_output = self._send_command(tn, 'NODES', timeout=cmd_timeout, expect_content=':')
            all_aliases, netrom_ssids_from_nodes, _ = self._parse_nodes_aliases(nodes_output)
            # Discard neighbors_from_nodes - NODES is routing table, not neighbor list
            time.sleep(inter_cmd_delay)
            
            # Base callsign without SSID (for filtering self from neighbors)
            # e.g., when on KC1JMH-15, base_callsign = KC1JMH
            base_callsign = callsign.split('-')[0] if '-' in callsign else callsign
            
            # Separate this node's own aliases from other nodes' aliases
            # Own aliases: entries where the callsign matches current node's base callsign
            # Example: On WS1EC, own aliases are CCEMA:WS1EC-15, CCEBBS:WS1EC-2, etc.
            own_aliases = {}
            other_aliases = {}
            for alias, full_call in all_aliases.items():
                alias_base = full_call.split('-')[0]
                if alias_base == base_callsign:
                    own_aliases[alias] = full_call
                else:
                    other_aliases[alias] = full_call
            
            # Update global alias mappings from NODES (routing table)
            # These are useful for routing to other nodes
            # ONLY add aliases that match consensus SSID
            for alias, full_call in other_aliases.items():
                base_call = full_call.split('-')[0]
                consensus_ssid = self.netrom_ssid_map.get(base_call)
                
                # Only add to call_to_alias if this alias matches consensus
                if consensus_ssid and full_call == consensus_ssid:
                    self._set_call_to_alias(base_call, alias, 'crawl_NODES')
                
                # Always add to alias_to_call for reverse lookups/documentation
                if alias not in self.alias_to_call:
                    self.alias_to_call[alias] = full_call
            
            # NOTE: Do NOT pre-populate netrom_ssid_map from NODES aliases here!
            # NODES aliases include BBS (-2), RMS (-10), CHAT (-13) etc.
            # These are APPLICATION SSIDs, not NODE SSIDs.
            # ROUTES is the authoritative source for node SSIDs (see below).
            
            # Get ROUTES for path optimization (BPQ only)
            # ROUTES is AUTHORITATIVE for node SSIDs - direct neighbor entries show actual node SSID
            if check_deadline():
                return
            routes_output = self._send_command(tn, 'ROUTES', timeout=cmd_timeout)
            routes, route_ports, routes_ssids, direct_neighbors = self._parse_routes(routes_output)
            partial_data['routes'] = routes  # Save partial
            partial_data['direct_routes'] = {
                k: {'quality': v, 'port': route_ports.get(k)}
                for k, v in routes.items()
                if k in direct_neighbors and k != base_callsign
            }  # Save partial (with port info, no self-loops)
            # Update global route_ports with direct neighbor port info from this node
            self.route_ports.update(route_ports)
            
            # ROUTES SSIDs are AUTHORITATIVE for node connections
            # These are the actual node SSIDs (e.g., K1NYY-15), not app SSIDs (K1NYY-2 BBS, K1NYY-10 RMS)
            for call, ssid in routes_ssids.items():
                # Always update from ROUTES - it's authoritative
                self.netrom_ssid_map[call] = ssid
                self.ssid_source[call] = ('routes', time.time())
                if self.verbose:
                    print("    Node SSID from ROUTES: {} = {} (authoritative)".format(call, ssid))
            time.sleep(inter_cmd_delay)
            
            # Get MHEARD from each RF port to find actual RF neighbors
            # MHEARD shows stations recently heard on RF - actual connectivity
            # Also extract port numbers for each neighbor AND their SSIDs (for connections)
            # 
            # SSID Selection Priority:
            # 1. ROUTES (authoritative for direct neighbors - shows actual node SSID)
            # 2. MHEARD (fallback - what was heard on RF, may include apps/operators)
            # 
            # Do NOT use NODES aliases for SSIDs - they include app SSIDs like BBS, RMS, CHAT
            mheard_neighbors = []
            mheard_ports = {}  # {callsign: port_num}
            mheard_ssids = {}  # {base_callsign: 'CALLSIGN-SSID'} - from actual RF
            port_audit = []  # HF/IP ports in 'audit' mode: [{port, port_type, description, heard}]
            
            # Kantronics / X1J4 fallback: single-port devices don't have PORTS command
            # Send plain MHEARD (no port argument) and parse columnar output
            if not ports_list:
                if check_deadline():
                    return
                if self.verbose:
                    print("  No ports detected (possibly Kantronics/X1J4) - sending plain MHEARD")
                mheard_output = self._send_command(tn, 'MHEARD', timeout=cmd_timeout, expect_content='Callsign')
                time.sleep(inter_cmd_delay)
                
                # Detect Kantronics columnar format (has "Pkts" and "dBm" in header)
                is_kantronics_mheard = ('Pkts' in mheard_output and 'dBm' in mheard_output)
                
                mh_lines = mheard_output.split('\n')
                for line in mh_lines:
                    if not line.strip():
                        continue
                    
                    if is_kantronics_mheard:
                        # Kantronics X1J4 columnar format:
                        # Callsign    Pkts   Port  Time      Dev.   dBm   Type
                        # AB1KI-15    4553   0     0:5:3     2.9    -40   Node
                        if 'Callsign' in line or 'Pkts' in line:
                            continue  # Skip header
                        if '}' in line and ':' in line.split('}')[0]:
                            continue  # Skip prompt line
                        match = re.match(
                            r'^(\w+(?:-\d+)?)\s+(\d+)\s+(\d+)\s+(\d+):(\d+):(\d+)',
                            line
                        )
                        if not match:
                            continue
                        full_callsign = match.group(1)
                        # pkts = int(match.group(2))
                        kantronics_port = int(match.group(3))
                        hours = int(match.group(4))
                        minutes = int(match.group(5))
                        seconds = int(match.group(6))
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        
                        # Check for "Node" type tag (Kantronics marks known nodes)
                        is_tagged_node = bool(re.search(r'\bNode\b', line))
                        port_num = kantronics_port
                    else:
                        # Standard BPQ format without port header
                        # CALLSIGN-SSID  DD:HH:MM:SS
                        match = re.match(r'^(\w+(?:-\d+)?)\s+(\d+):(\d+):(\d+):(\d+)', line)
                        if not match:
                            continue
                        full_callsign = match.group(1)
                        days = int(match.group(2))
                        hours = int(match.group(3))
                        minutes = int(match.group(4))
                        seconds = int(match.group(5))
                        total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
                        is_tagged_node = False
                        port_num = 0  # Unknown port
                    
                    base_call = full_callsign.split('-')[0]
                    if not self._is_valid_callsign(base_call):
                        continue
                    
                    has_ssid = '-' in full_callsign
                    
                    # Update last_heard
                    if base_call not in self.last_heard or total_seconds < self.last_heard[base_call]:
                        self.last_heard[base_call] = total_seconds
                    
                    # SSID selection (same logic as per-port loop below)
                    if base_call in routes_ssids:
                        if base_call not in mheard_ssids:
                            mheard_ssids[base_call] = routes_ssids[base_call]
                    elif base_call in routes and routes[base_call] == 0:
                        continue
                    elif base_call not in mheard_ssids:
                        if has_ssid:
                            mheard_ssids[base_call] = full_callsign
                        elif is_tagged_node:
                            # Kantronics "Node" tag - station is a node even without SSID
                            # Store base callsign as placeholder; ROUTES consensus may resolve later
                            mheard_ssids[base_call] = full_callsign
                            if self.verbose:
                                print("    {} tagged as Node by Kantronics (no SSID)".format(full_callsign))
                        else:
                            if self.verbose:
                                print("    MHEARD {} (no SSID - not a node, skipping)".format(full_callsign))
                            continue
                    
                    # Add to neighbors if it has SSID or is tagged as Node
                    if has_ssid or is_tagged_node:
                        mheard_neighbors.append(base_call)
                        if base_call not in mheard_ports:
                            mheard_ports[base_call] = port_num
            for port_info in ports_list:
                port_type = port_info.get('port_type', 'rf')
                # RF (VHF/UHF) is always fully processed. HF and IP each have
                # their own tri-state: 'off' skips the port entirely, 'audit'
                # lists what MHEARD reports without ever connecting to it,
                # 'crawl' behaves like RF - full discovery and a place in the
                # queue. Set via --hf[:audit|:crawl] / --ip[:audit|:crawl].
                if port_type == 'hf':
                    port_mode = self.hf_mode
                elif port_type == 'ip':
                    port_mode = self.ip_mode
                else:
                    port_mode = 'crawl'

                if port_mode == 'off':
                    if self.verbose:
                        print("    Skipping {} port {} ({})".format(
                            port_type.upper(), port_info['number'], port_info['description']))
                    continue

                if check_deadline():
                    return
                port_num = port_info['number']
                mheard_output = self._send_command(tn, 'MHEARD {}'.format(port_num), timeout=cmd_timeout, expect_content='Heard')
                time.sleep(inter_cmd_delay)
                lines = mheard_output.split('\n')

                if port_mode == 'audit':
                    # List what is out there without ever dialing it: nothing
                    # parsed here reaches mheard_neighbors, so nothing on this
                    # port enters the crawl queue. Recorded separately on the
                    # node for awareness/mapping rather than as a first-class
                    # mapped node - we have no INFO or ROUTES for a station we
                    # never connected to, only "heard here, this recently".
                    heard_here = []
                    for line in lines:
                        if 'Heard List' in line or not line.strip():
                            continue
                        match = re.match(r'^(\w+(?:-\d+)?)\s+(\d+):(\d+):(\d+):(\d+)', line)
                        if not match:
                            continue
                        full_callsign = match.group(1)
                        base_call = full_callsign.split('-')[0]
                        if not self._is_valid_callsign(base_call):
                            continue
                        days, hours, minutes, seconds = (int(match.group(i)) for i in (2, 3, 4, 5))
                        heard_here.append({
                            'callsign': full_callsign,
                            'last_heard_seconds': days * 86400 + hours * 3600 + minutes * 60 + seconds,
                        })
                    if heard_here:
                        port_audit.append({
                            'port': port_num,
                            'port_type': port_type,
                            'description': port_info.get('description', ''),
                            'heard': heard_here,
                        })
                        if self.verbose:
                            print("    Audited {} port {}: {} station(s) heard, not crawled".format(
                                port_type.upper(), port_num, len(heard_here)))
                    continue  # never falls through to neighbor/queue logic below

                # port_mode == 'crawl' from here (RF ports, or HF/IP opted all the way in).
                for line in lines:
                    # Skip header lines
                    if 'Heard List' in line or not line.strip():
                        continue
                    
                    # Look for callsign with SSID: "KC1JMH-15  00:00:00:03"
                    match = re.match(r'^(\w+(?:-\d+)?)\s+(\d+):(\d+):(\d+):(\d+)', line)
                    if match:
                        full_callsign = match.group(1)
                        base_call = full_callsign.split('-')[0]
                        
                        # Validate callsign format
                        if not self._is_valid_callsign(base_call):
                            continue
                        
                        # Check if this has a node SSID (contains -number)
                        # Stations without SSID are likely user stations or digipeaters
                        # They can't be crawled as nodes (no BPQ commands)
                        has_ssid = '-' in full_callsign
                        
                        # SSID Selection: Prefer ROUTES over MHEARD
                        # ROUTES shows actual node SSIDs; MHEARD may include apps/operators
                        if base_call in routes_ssids:
                            # Already have authoritative SSID from ROUTES - use it
                            if base_call not in mheard_ssids:
                                mheard_ssids[base_call] = routes_ssids[base_call]
                                if self.verbose:
                                    print("    {} in ROUTES as {} (authoritative)".format(base_call, routes_ssids[base_call]))
                        elif base_call in routes and routes[base_call] == 0:
                            # Station is in ROUTES but with quality 0 (sysop blocked)
                            if self.verbose and has_ssid:
                                print("    Skipping {} (quality 0 in ROUTES - sysop blocked route)".format(full_callsign))
                            # Don't add to mheard_ssids or neighbors - skip this station
                            continue
                        elif base_call not in mheard_ssids:
                            # First MHEARD entry for this callsign, not in ROUTES
                            if has_ssid:
                                mheard_ssids[base_call] = full_callsign
                                if self.verbose:
                                    print("    MHEARD SSID for {}: {} (not in ROUTES table)".format(base_call, full_callsign))
                            else:
                                # No SSID - likely user station, skip it
                                if self.verbose:
                                    print("    MHEARD {} (no SSID - not a node, skipping)".format(full_callsign))
                                continue
                        elif self.verbose and has_ssid:
                            # Already have SSID for this base call
                            existing = mheard_ssids[base_call]
                            existing_has_ssid = '-' in existing
                            # If we already have a no-SSID entry, replace with SSID entry
                            if not existing_has_ssid and has_ssid:
                                mheard_ssids[base_call] = full_callsign
                                print("    Upgraded {} to {} (found SSID)".format(existing, full_callsign))
                            else:
                                print("    Ignoring {} (already have {})".format(full_callsign, existing))
                        
                        # Only add to neighbor list if it has an SSID (is a node)
                        # Stations without SSIDs can't be crawled
                        if has_ssid:
                            mheard_neighbors.append(base_call)
                            
                            # Store port info
                            if base_call not in mheard_ports:
                                mheard_ports[base_call] = port_num
            
            # Update global netrom_ssid_map with MHEARD data
            # Priority: 1) ROUTES (already stored above - authoritative)
            #           2) Newer MHEARD (can overwrite older MHEARD, but not ROUTES)
            for call, ssid in mheard_ssids.items():
                source, timestamp = self.ssid_source.get(call, (None, 0))
                # Update if: no existing SSID, OR existing is from MHEARD and this is newer
                if call not in self.netrom_ssid_map or (source == 'mheard' and time.time() > timestamp + 3600):
                    self.netrom_ssid_map[call] = ssid
                    self.ssid_source[call] = ('mheard', time.time())
                    if self.verbose and call in self.netrom_ssid_map:
                        print("    Updated SSID from newer MHEARD: {} = {}".format(call, ssid))
            
            # Use MHEARD exclusively for neighbors (stations actually heard on RF with SSIDs)
            # Remove duplicates and exclude self (all SSIDs)
            all_neighbors = list(set([n for n in mheard_neighbors if n != base_callsign]))

            # MHEARD is bare AX.25 with no error correction, so a share of
            # these "stations" are corrupted copies of real ones. Quarantine
            # them here, before they reach the neighbour lists, the crawl
            # queue, or the map. This node's own successful connection makes
            # it an anchor for judging everything it heard.
            self.confirmed_calls.add(base_callsign)
            for _alias, _full in (own_aliases or {}).items():
                self.confirmed_calls.add(_base_call(str(_full)))
            for _neighbor in (routes or {}):
                self.structured_calls.add(_base_call(_neighbor))
            for _neighbor in set(all_neighbors):
                _key = _base_call(_neighbor)
                self.mheard_counts[_key] = self.mheard_counts.get(_key, 0) + 1

            all_neighbors, _rejected = self._filter_callsigns(all_neighbors)
            if _rejected:
                colored_print("  Quarantined {} corrupt callsign(s) heard by {}: {}".format(
                    len(_rejected), callsign,
                    ', '.join(c for c, _r in _rejected[:6])), Colors.YELLOW)
            
            # Update global route_ports with MHEARD port info
            # Combine with ROUTES data (ROUTES takes precedence if both exist)
            for call, port in mheard_ports.items():
                if call not in self.route_ports:
                    self.route_ports[call] = port
                    if self.verbose:
                        print("    Port info from MHEARD: {} on port {}".format(call, port))
            
            # Mark which neighbors will be explored vs skipped
            # A neighbor is explored if: visited or failed (actual exploration attempt made)
            # A neighbor is unexplored if: not visited, not failed, but either exceeds hop limit or will be queued
            # Store full SSIDs (not base calls) so we can distinguish nodes from user stations later
            explored_neighbors = []
            unexplored_neighbors = []
            for neighbor in all_neighbors:
                # Get full SSID for this neighbor (prefer netrom_ssid_map which has ROUTES + MHEARD data)
                full_neighbor = self.netrom_ssid_map.get(neighbor, neighbor)
                
                # Check visited/failed using both base and full callsign
                is_visited = neighbor in self.visited or full_neighbor in self.visited
                is_failed = neighbor in self.failed or full_neighbor in self.failed
                
                if is_visited or is_failed:
                    # Actually visited or connection attempt failed
                    explored_neighbors.append(full_neighbor)
                elif hop_count + 1 > self.max_hops:
                    # Beyond hop limit, won't be visited
                    unexplored_neighbors.append(full_neighbor)
                else:
                    # Within hop limit, will be queued for future exploration
                    unexplored_neighbors.append(full_neighbor)
            
            # Get INFO
            if check_deadline():
                return
            info_output = self._send_command(tn, 'INFO', timeout=cmd_timeout)
            location = self._parse_info(info_output)

            # Climb the resolution ladder for anything INFO did not state
            # outright: a named mountain or town gets geocoded, and failing
            # that the callsign gets looked up. All of it is cached and all of
            # it is optional - an offline node just keeps what it parsed.
            resolved = None
            try:
                resolved = self.resolver.resolve(
                    callsign, info_text=info_output, existing=location)
            except Exception as e:
                # Location is a nicety; never let it interrupt a crawl.
                self._debug_log("location resolve failed for {}: {}".format(callsign, e))
            if resolved and resolved.get('grid') and not location.get('grid'):
                location['grid'] = resolved['grid']
                for key in ('city', 'state', 'lat', 'lon', 'place'):
                    if resolved.get(key) and not location.get(key):
                        location[key] = resolved[key]
                location['source'] = resolved.get('location_source')
                if self.verbose:
                    print("    Location: {} via {}".format(
                        resolved['grid'], resolved.get('location_source')))
            time.sleep(inter_cmd_delay)
            
            # Get available commands (? command)
            if check_deadline():
                return
            commands_output = self._send_command(tn, '?', timeout=cmd_timeout)
            commands, applications = self._parse_commands(commands_output)
            
            # Detect node type (pass commands list for Kantronics detection via 'Adc')
            node_type = self._detect_node_type(info_output, '>:', commands)
            
            # Store node data
            # Note: INFO-derived data (location, applications, type from keywords) is marked
            # with 'source' to indicate reliability. Structured command data is preferred.
            
            # Find which neighbors are intermittent (failed connections from this node)
            intermittent_neighbors = []
            for neighbor in all_neighbors:
                link_key = (callsign, neighbor)
                if link_key in self.intermittent_links:
                    intermittent_neighbors.append(neighbor)
            
            # Extract top-level fields for convenience
            # Primary alias determination:
            # 1. For localhost: Parse NODEALIAS from bpq32.cfg (authoritative)
            # 2. For all nodes: Parse prompt from commands list (format: ALIAS:CALL-SSID})
            # 3. Fallback: First entry in own_aliases dict (may be service alias)
            primary_alias = None
            
            # For localhost, check bpq32.cfg first (authoritative source)
            if callsign == self.callsign:
                primary_alias = self._find_node_alias()
                if primary_alias and self.verbose:
                    print("  Using node alias from bpq32.cfg: {}".format(primary_alias))
            
            # Try to extract primary alias from prompt in commands list
            # Prompt format: "ALIAS:CALL-SSID}" (e.g., "CCEMA:WS1EC-15}")
            if not primary_alias and commands:
                first_cmd = commands[0] if commands else ''
                match = re.match(r'^(\w+):\w+(?:-\d+)?\}', first_cmd)
                if match:
                    primary_alias = match.group(1)
                    if self.verbose:
                        print("  Extracted primary alias from prompt: {}".format(primary_alias))
            
            # Fallback: Use first own_aliases entry (unreliable - dict order may be wrong)
            if not primary_alias and own_aliases:
                primary_alias = list(own_aliases.keys())[0]
                if self.verbose:
                    print("  Using first own_alias (may be service alias): {}".format(primary_alias))
            
            gridsquare = location.get('grid', None)
            
            # Get successful connection path from shortest_paths (if available)
            successful_path = self.shortest_paths.get(callsign, path)
            
            self.nodes[callsign] = {
                'info': info_output.strip(),
                'alias': primary_alias,  # Primary NetRom alias (extracted from own_aliases)
                'gridsquare': gridsquare,  # Maidenhead locator (extracted from location)
                'neighbors': all_neighbors,  # Direct RF neighbors from MHEARD (with SSIDs only)
                'explored_neighbors': explored_neighbors,  # Neighbors that were/will be visited
                'unexplored_neighbors': unexplored_neighbors,  # Neighbors skipped (hop limit)
                'intermittent_neighbors': intermittent_neighbors,  # Neighbors with failed connections
                'hop_distance': hop_count,  # RF hops from start node
                'successful_path': successful_path,  # Intermediate nodes used to reach this node
                'location': location,  # From INFO (unreliable, sysop-entered)
                'location_source': location.get('source', 'info'),  # how the grid was determined
                'ports': ports_list,  # From PORTS (reliable)
                'heard_on_ports': [(call, mheard_ports.get(call)) for call in all_neighbors],
                'type': node_type,  # From INFO or prompt (low/medium confidence)
                'type_source': 'info' if 'BPQ' in info_output.upper() or 'FBB' in info_output.upper() else 'prompt',
                'routes': routes,  # From ROUTES (reliable) - ALL routes (direct + indirect)
                'direct_routes': {
                    k: {'quality': v, 'port': route_ports.get(k)}
                    for k, v in routes.items()
                    if k in direct_neighbors and k != base_callsign
                },  # Only > prefix entries, with port number for frequency lookup
                'own_aliases': own_aliases,  # This node's aliases (CCEMA:WS1EC-15, etc.)
                'seen_aliases': other_aliases,  # Other nodes' aliases seen in NODES
                'netrom_ssids': mheard_ssids,  # From MHEARD (actual RF transmissions)
                'applications': applications,  # From ? command (BBS, CHAT, RMS, etc.)
                'commands': commands,  # From ? command (all available commands)
                'port_audit': port_audit  # HF/IP stations heard but not crawled (awareness only)
            }
            
            # Update node_route_ports with freshly crawled port data
            node_b = callsign.split('-')[0] if '-' in callsign else callsign
            fresh_ports = {}
            for call in all_neighbors:
                port = mheard_ports.get(call)
                if port is not None:
                    cb = call.split('-')[0] if '-' in call else call
                    fresh_ports[cb] = port
            if fresh_ports:
                self.node_route_ports[node_b] = fresh_ports
            
            # If this node was crawled with a CLI-forced SSID, update its netrom_ssids entry
            # This ensures the corrected SSID persists in the JSON for future crawls
            base_call = callsign.split('-')[0] if '-' in callsign else callsign
            if base_call in self.cli_forced_ssids:
                forced_ssid = self.cli_forced_ssids[base_call]
                self.nodes[callsign]['netrom_ssids'][base_call] = forced_ssid
                if self.verbose:
                    print("  Updated netrom_ssids: {} = {} (CLI-forced)".format(base_call, forced_ssid))
            
            # Record connections - only for neighbors in ROUTES with non-zero quality
            # MHEARD shows all stations heard on RF, but ROUTES shows actual routing neighbors
            for neighbor in all_neighbors:
                # Check if neighbor is in ROUTES (has a route entry)
                neighbor_base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                if neighbor_base not in routes:
                    continue  # Skip neighbors not in ROUTES (not routing nodes)
                
                quality = routes.get(neighbor_base, 0)
                if quality == 0:
                    continue  # Skip quality 0 routes (sysop blocked)
                
                link_key = (callsign, neighbor)
                is_intermittent = link_key in self.intermittent_links
                
                self.connections.append({
                    'from': callsign,
                    'to': neighbor,
                    'port': None,
                    'quality': quality,
                    'intermittent': is_intermittent  # Mark unreliable/failed connections
                })
                
                # Skip neighbor queuing in target-only mode (--callsign used)
                # In this mode, we only crawl the specific target, not discover network
                if self.target_only_mode:
                    continue
                
                # Add unvisited neighbors to queue - allow multiple paths per node
                # Queue all valid paths, prioritized by route quality from current node
                # Only queue if within hop limit (next hop would be hop_count + 1)
                # Note: We don't check self.failed here - nodes with intermittent connections
                # can still be explored from other neighbors (better paths)
                if neighbor not in self.visited and hop_count + 1 <= self.max_hops:
                    # Determine path to this neighbor (intermediate hops only, not target)
                    # If we're at local node WS1EC (path=[], callsign==self.callsign), queue KC1JMH with path=[]
                    #   (direct connection from local, no intermediate hops)
                    # If we're at KC1JMH (path=[], callsign!=self.callsign), queue KS1R with path=[KC1JMH]
                    #   (go through KC1JMH to reach KS1R)
                    # If we're at KS1R (path=[KC1JMH]), queue N1XP with path=[KC1JMH, KS1R]
                    #   (go through KC1JMH, then KS1R, to reach N1XP)
                    if path:
                        # We're not at local node, path contains route to current node
                        # Current node becomes an intermediate hop to reach neighbor
                        new_path = path + [callsign]
                    elif callsign == self.callsign:
                        # We're at the actual local node, direct connection to neighbor (no intermediate hops)
                        new_path = []
                    else:
                        # We're at a direct neighbor of local node (path=[] but not local node)
                        # Need to route through this node to reach its neighbors
                        new_path = [callsign]
                    
                    # Skip if neighbor is already in the path (prevents routing loops)
                    # Example: At KS1R via KC1JMH, don't route back through KC1JMH to reach KC1JMH
                    if neighbor in new_path or neighbor == self.callsign:
                        if self.verbose:
                            print("    Skipping {} (already in path: {})".format(neighbor, ' > '.join(new_path) if new_path else 'local'))
                        continue
                    
                    # Track shortest path for reference (but queue all paths)
                    if neighbor not in self.shortest_paths or len(new_path) < len(self.shortest_paths[neighbor]):
                        self.shortest_paths[neighbor] = new_path
                    
                    # Get route quality from current node to this neighbor
                    route_quality = routes.get(neighbor, 0)
                    
                    # Skip quality 0 routes (sysop-blocked/poor paths)
                    if route_quality == 0:
                        if self.verbose:
                            print("    Skipping {} via {} (route quality 0)".format(neighbor, callsign))
                        continue
                    
                    # Check if we've already queued this exact path
                    path_key = (neighbor, tuple(new_path))
                    if path_key in self.queued_paths:
                        if self.verbose:
                            print("    Skipping duplicate path to {} via {}".format(neighbor, ' > '.join(new_path) if new_path else 'direct'))
                        continue
                    
                    # Skip nodes that haven't been heard in over 24 hours (likely offline)
                    # 86400 seconds = 24 hours
                    stale_threshold = 86400
                    neighbor_age = self.last_heard.get(neighbor, 0)
                    
                    if neighbor_age > stale_threshold:
                        if self.verbose:
                            days = neighbor_age // 86400
                            hours = (neighbor_age % 86400) // 3600
                            print("    Skipping {} (stale: {}d {}h ago)".format(neighbor, days, hours))
                        continue
                    
                    # Queue this path with quality (for prioritization)
                    if not self._should_crawl(neighbor):
                        continue
                    self.queue.append((neighbor, new_path, route_quality))
                    self.queued_paths.add(path_key)
            
            print("  Found {} neighbors: {}".format(
                len(all_neighbors),
                ', '.join(all_neighbors)
            ))
            print("  Node type: {}".format(node_type))
            print("  RF Ports: {}".format(len([p for p in ports_list if p['is_rf']])))
            print("  Applications: {} ({})".format(len(applications), ', '.join(applications) if applications else 'none'))
            print("  Commands: {}".format(len(commands)))
            if own_aliases:
                print("  Own Aliases: {}".format(len(own_aliases)))
            
            # Notify after successful crawl
            if not path:
                if callsign == self.callsign:
                    notify_msg = "{}: {} neighbors".format(callsign, len(all_neighbors))
                else:
                    notify_msg = "{}: {} neighbors".format(callsign, len(all_neighbors))
            else:
                notify_msg = "{}: {} neighbors".format(callsign, len(all_neighbors))
            self._send_notification(notify_msg)
            
            # Mark as successfully visited after crawl completes
            self.visited.add(callsign)
            # This callsign's own ROUTES table was just read and its connections
            # (if any) already appended above - see self.freshly_crawled's own
            # comment in __init__ for why this has to be tracked separately
            # from self.visited.
            self.freshly_crawled.add(callsign)

        finally:
            # Disconnect
            try:
                tn.write(b'BYE\r')
                time.sleep(0.5)
            except:
                pass
            tn.close()
    
    def crawl_network(self, start_node=None, forced_target=None):
        """
        Crawl entire network starting from specified or local node.
        
        Args:
            start_node: Callsign to start crawl from (default: local node)
        """
        # Every mode benefits from the previous export's context, even the
        # ones that do not resume from it: known-good callsigns to judge
        # corruption against, the temporal record, and the ignore list.
        #
        # 'update' mode additionally pre-seeds self.visited and the crawl
        # queue from what nodemap.json already has. Without this, self.visited
        # only ever tracked nodes touched during the CURRENT run - it started
        # empty on every invocation that did not also pass --resume - so
        # "skip already-visited nodes" had nothing pre-existing to skip, and a
        # plain `update` run re-crawled the entire reachable network exactly
        # like `reaudit`. _load_unexplored_nodes() both primes (it calls
        # _prime_from_existing internally) and returns each known node's
        # previously recorded unexplored neighbours, which is what lets update
        # mode still grow into new territory while skipping nodes it has
        # already fully mapped. Skipped for a single forced target
        # (--callsign): that is a narrow, deliberate one-node operation, not a
        # general sweep, and does not want a flood of unrelated queued nodes.
        preseeded_unexplored = []
        if self.resume or self.crawl_mode == 'new-only':
            pass  # primed and seeded below, in the resume/new-only branch
        elif self.crawl_mode == 'update' and not forced_target:
            preseeded_unexplored = self._load_unexplored_nodes('nodemap.json')
            # The node being crawled FROM must always be crawled fresh, not
            # skipped as "already known". Its live MHEARD/ROUTES output is
            # what update mode uses to discover anything new at hop 1; on
            # every run after the first, it is also the one node guaranteed
            # to already be in nodemap.json, so without this a plain update
            # run would silently stop refreshing local RF data at all and
            # rely entirely on stale stubs recorded on a previous crawl.
            effective_start = (start_node or self.callsign or '').upper()
            if effective_start:
                effective_base = effective_start.split('-')[0]
                for known in list(self.visited):
                    if known.split('-')[0] == effective_base:
                        self.visited.discard(known)
        else:
            self._prime_from_existing(self._load_existing_data('nodemap.json'))

        # Resume mode OR new-only mode: load unexplored nodes from existing data
        if self.resume or self.crawl_mode == 'new-only':
            resume_filename = self.resume_file if self.resume_file else 'nodemap.json'
            mode_name = "Resume" if self.resume else "New-only"
            print("{} mode: Loading unexplored nodes from {}...".format(mode_name, resume_filename))
            unexplored = self._load_unexplored_nodes(resume_filename)
            
            if not unexplored:
                print("No unexplored nodes found.")
                if len(self.visited) > 0:
                    print("All {} previously crawled nodes have been fully explored.".format(len(self.visited)))
                    colored_print("Use normal mode to start a fresh crawl or increase max hops.", Colors.YELLOW)
                else:
                    colored_print("No previous crawl data found. Use normal mode to start a fresh crawl.", Colors.RED)
                return
            
            # Queue all unexplored nodes (with default quality for resume)
            for callsign, path in unexplored:
                self.queue.append((callsign, path, 255))  # Default high quality for resume paths
            
            colored_print("Queued {} unexplored nodes for crawling".format(len(unexplored)), Colors.GREEN)
            mode_name = "Resume" if self.resume else "New-only"
            self._send_notification("{} crawl: {} unexplored nodes".format(mode_name, len(unexplored)))
            
            # In resume/new-only mode, we don't have a single starting callsign
            starting_callsign = None
            
            # Skip the normal start node logic
            print("BPQ node: {}:{}".format(self.host, self.port))
            print("Max hops: {}".format(self.max_hops))
            print("-" * 50)
        else:
            # Normal mode: start from specified or local node
            # Determine starting node
            starting_path = []  # Path to reach the starting node
            
            # Pre-load route information from existing nodemap.json if available
            # Needed for both start_node and forced_target path-finding
            existing = self._load_existing_data('nodemap.json')
            
            if start_node:
                # Validate provided callsign
                if not self._is_valid_callsign(start_node):
                    colored_print("Error: Invalid callsign format: {}".format(start_node), Colors.RED)
                    return
                starting_callsign = start_node.upper()
                print("Starting network crawl from: {}...".format(starting_callsign))
                
                if existing and 'nodes' in existing:
                    nodes_data = existing['nodes']
                    self.loaded_nodes = nodes_data  # Store for use by _find_alternate_path()
                    
                    if self.verbose:
                        print("Loaded existing data with {} nodes: {}".format(
                            len(nodes_data), 
                            ', '.join(sorted(nodes_data.keys()))))
                    
                    # SSID Selection Standard (from copilot-instructions.md):
                    # 1. CLI-forced SSIDs (handled via cli_forced_ssids, highest priority)
                    # 2. ROUTES consensus (aggregate netrom_ssids from all nodes) - AUTHORITATIVE
                    # 3. Base callsign only (let NetRom figure it out)
                    #
                    # The 'alias' field is NOT reliable - it comes from the BPQ prompt which may be
                    # from a BBS, RMS, or CHAT service rather than the node itself.
                    # ROUTES data (stored in netrom_ssids) IS reliable - it shows actual node SSIDs.
                    
                    # Build ROUTES consensus by aggregating netrom_ssids from ALL crawled nodes
                    from collections import defaultdict
                    ssid_votes = defaultdict(lambda: defaultdict(int))
                    
                    for node_info in nodes_data.values():
                        netrom = node_info.get('netrom_ssids', {})
                        for base_call, full_ssid in netrom.items():
                            if self._is_valid_callsign(base_call) and self._is_likely_node_ssid(full_ssid):
                                ssid_votes[base_call][full_ssid] += 1
                    
                    # Use ROUTES consensus to build SSID map
                    # Only use consensus if there's a CLEAR winner (more votes than any other)
                    # If tied, skip this node - insufficient routing data
                    for base_call, votes in ssid_votes.items():
                        sorted_votes = sorted(votes.items(), key=lambda x: (-x[1], x[0]))
                        best_ssid, best_count = sorted_votes[0]
                        
                        # Check if there's a clear winner (no tie for first place)
                        if len(sorted_votes) == 1 or best_count > sorted_votes[1][1]:
                            # Clear consensus - use this SSID
                            self.netrom_ssid_map[base_call] = best_ssid
                            self.ssid_source[base_call] = ('routes_consensus', time.time())
                        else:
                            # Tied votes - skip this node, insufficient routing data
                            self.skipped_no_ssid[base_call] = dict(votes)
                            if self.verbose:
                                print("  No consensus for {} (tied: {}), skipping".format(
                                    base_call, dict(votes)))
                    
                    if self.verbose and ssid_votes:
                        print("Built ROUTES consensus for {} callsigns".format(len(ssid_votes)))
                    
                    # Build alias mappings from own_aliases (for NetRom routing)
                    for node_call, node_info in nodes_data.items():
                        node_base = node_call.split('-')[0] if '-' in node_call else node_call
                        own_aliases = node_info.get('own_aliases', {})
                        
                        # Map all aliases to their full callsigns
                        for alias, full_call in own_aliases.items():
                            if alias not in self.alias_to_call:
                                self.alias_to_call[alias] = full_call
                        
                        # If we have ROUTES consensus for this base call, find matching alias
                        if node_base in self.netrom_ssid_map:
                            consensus_ssid = self.netrom_ssid_map[node_base]
                            for alias, full_call in own_aliases.items():
                                if full_call == consensus_ssid:
                                    self._set_call_to_alias(node_base, alias, 'resume_consensus')
                                    break
                        else:
                            # No ROUTES consensus, but node was previously crawled
                            # Use historical own_aliases as fallback for routing
                            # Pick first alias that matches node SSID pattern (likely the node alias)
                            for alias, full_call in own_aliases.items():
                                call_base = full_call.split('-')[0] if '-' in full_call else full_call
                                if call_base == node_base and self._is_likely_node_ssid(full_call):
                                    self._set_call_to_alias(node_base, alias, 'resume_fallback')
                                    if node_base not in self.netrom_ssid_map:
                                        self.netrom_ssid_map[node_base] = full_call
                                        self.ssid_source[node_base] = ('json_fallback', time.time())
                                    break
                        
                        # Also add seen_aliases
                        for alias, full_call in node_info.get('seen_aliases', {}).items():
                            if alias not in self.alias_to_call:
                                self.alias_to_call[alias] = full_call
                    
                    # Restore route_ports from LOCAL node's heard_on_ports (first-hop fallback)
                    # Also build node_route_ports for ALL nodes (needed for direct port
                    # connections at intermediate hops: C PORT uses the CURRENT node's port
                    # numbering, not localhost's)
                    local_base = self.callsign.split('-')[0] if '-' in self.callsign else self.callsign
                    local_node_data = None
                    
                    for node_key, node_info in nodes_data.items():
                        node_base = node_key.split('-')[0] if '-' in node_key else node_key
                        if node_base == local_base:
                            local_node_data = node_info
                            break
                    
                    if local_node_data:
                        heard_on_ports = local_node_data.get('heard_on_ports', [])
                        for call, port in heard_on_ports:
                            if port is not None:
                                self.route_ports[call] = port
                        
                        # Fallback: use routes for neighbors without port info
                        routes = local_node_data.get('routes', {})
                        for neighbor, quality in routes.items():
                            if neighbor not in self.route_ports and quality > 0:
                                self.route_ports[neighbor] = 1
                    
                    # Build per-node port map from ALL nodes (for multi-hop direct port connections)
                    for node_key, node_info in nodes_data.items():
                        node_b = node_key.split('-')[0] if '-' in node_key else node_key
                        hp = node_info.get('heard_on_ports', [])
                        if hp:
                            ports = {}
                            for call, port in hp:
                                if port is not None:
                                    cb = call.split('-')[0] if '-' in call else call
                                    ports[cb] = port
                            if ports:
                                self.node_route_ports[node_b] = ports
                    
                    if self.route_ports:
                        if self.verbose:
                            print("Loaded {} port mappings from existing nodemap.json".format(len(self.route_ports)))
                    
                    if self.call_to_alias:
                        if self.verbose:
                            print("Loaded {} NetRom aliases from existing nodemap.json".format(len(self.call_to_alias)))
                    
                    # Find path to remote start node through existing network
                    # Use BFS to find shortest path from local node to target
                    if starting_callsign != self.callsign:
                        # Not the local node - need to find how to reach it
                        target_base = starting_callsign.split('-')[0] if '-' in starting_callsign else starting_callsign
                        
                        # If user provided base callsign, look up the node SSID
                        # CLI-forced SSIDs take precedence over discovered SSIDs
                        if '-' not in starting_callsign:
                            resolved_ssid = self.cli_forced_ssids.get(target_base) or self.netrom_ssid_map.get(target_base)
                            if resolved_ssid and '-' in resolved_ssid:
                                starting_callsign = resolved_ssid
                                if self.verbose:
                                    source = "CLI-forced" if target_base in self.cli_forced_ssids else "discovered"
                                    print("Resolved {} to node SSID: {} ({})".format(target_base, resolved_ssid, source))
                        
                        # User can force specific SSID via netrom_ssid_map (pre-populated by --callsign)
                        # This overrides any discovered SSID
                        
                        # Check if target is actually a node (has SSID) vs user station
                        # CLI-forced SSIDs take precedence
                        target_ssid = self.cli_forced_ssids.get(target_base) or self.netrom_ssid_map.get(target_base)
                        if not target_ssid or '-' not in target_ssid:
                            # No SSID means it's a user station, not a node
                            colored_print("Error: {} appears to be a user station, not a node (no SSID in network data)".format(target_base), Colors.RED)
                            colored_print("User stations don't run BPQ node software and can't be crawled.", Colors.YELLOW)
                            
                            # Suggest other unexplored neighbors that ARE nodes
                            other_unexplored = []
                            for node_call, node_info in nodes_data.items():
                                for neighbor in node_info.get('unexplored_neighbors', []):
                                    neighbor_ssid = self.netrom_ssid_map.get(neighbor)
                                    if neighbor != target_base and neighbor_ssid and '-' in neighbor_ssid:
                                        if neighbor not in other_unexplored:
                                            other_unexplored.append(neighbor)
                            
                            if other_unexplored:
                                colored_print("Try one of these unexplored nodes instead: {}".format(', '.join(sorted(other_unexplored)[:10])), Colors.CYAN)
                            return
                        
                        # Verify node is routable (has NetRom alias or is direct neighbor)
                        # Skip this check when SSID was CLI-forced: user asserts the path exists
                        if target_base not in self.call_to_alias and target_base not in self.route_ports \
                                and target_base not in self.cli_forced_ssids:
                            colored_print("Error: {} is not routable (no NetRom alias in network data)".format(target_base), Colors.RED)
                            colored_print("NetRom routing requires an alias from the NODES table.", Colors.YELLOW)
                            colored_print("This node may be offline or unreachable from your location.", Colors.YELLOW)
                            
                            # Check if it was previously crawled
                            if target_base in nodes_data or target_ssid in nodes_data:
                                colored_print("Note: {} exists in nodemap.json but lacks routing information.".format(target_base), Colors.YELLOW)
                                colored_print("Try crawling from a node closer to {} in the network topology.".format(target_base), Colors.CYAN)
                            return
                        
                        if self.verbose:
                            print("Looking for path to {} among known neighbors...".format(target_base))
                        
                        # BFS to find shortest path
                        queue = [(self.callsign, [])]  # (current_node, path_to_current)
                        visited = {self.callsign}
                        found_path = False
                        
                        while queue and not found_path:
                            current, path = queue.pop(0)
                            # Resolve base callsign to full SSID for node lookup
                            current_full = self.netrom_ssid_map.get(current, current)
                            
                            # Try lookup with resolved SSID first, then base callsign
                            current_info = nodes_data.get(current_full, {})
                            if not current_info:
                                # Not found with SSID - try base callsign
                                current_base = current_full.split('-')[0] if '-' in current_full else current_full
                                current_info = nodes_data.get(current_base, {})
                            
                            neighbors = current_info.get('neighbors', [])
                            
                            if self.verbose:
                                print("  Checking {} (resolved to {}) neighbors: {}".format(
                                    current, current_full, neighbors if neighbors else "(none)"))
                            
                            for neighbor in neighbors:
                                if neighbor in visited:
                                    continue
                                visited.add(neighbor)
                                
                                # Build path to this neighbor
                                new_path = path + [neighbor]
                                
                                # Check if this neighbor is the target
                                if neighbor == target_base:
                                    # Found target - use path excluding target itself
                                    starting_path = path if path else []
                                    if self.verbose:
                                        if starting_path:
                                            print("Found {} reachable via: {}".format(target_base, ' -> '.join(starting_path)))
                                        else:
                                            print("Found {} as direct neighbor of local node {}".format(target_base, self.callsign))
                                    found_path = True
                                    break
                                
                                # Check if this neighbor node has the target as ITS neighbor
                                # Resolve neighbor base to full SSID for node lookup
                                neighbor_full = self.netrom_ssid_map.get(neighbor, neighbor)
                                neighbor_info = nodes_data.get(neighbor_full, {})
                                if not neighbor_info:
                                    # Not found with SSID - try base callsign
                                    neighbor_base = neighbor_full.split('-')[0] if '-' in neighbor_full else neighbor_full
                                    neighbor_info = nodes_data.get(neighbor_base, {})
                                
                                neighbor_neighbors = neighbor_info.get('neighbors', [])
                                if self.verbose:
                                    print("    Checking {} neighbors: {} (looking for {})".format(neighbor, neighbor_neighbors[:5] if len(neighbor_neighbors) > 5 else neighbor_neighbors, target_base))
                                if target_base in neighbor_neighbors:
                                    # Target is neighbor of this node - path goes through this node
                                    starting_path = new_path
                                    if self.verbose:
                                        print("Found {} reachable via: {}".format(target_base, ' -> '.join(starting_path)))
                                    found_path = True
                                    break
                                
                                # Add to queue for further exploration
                                queue.append((neighbor, new_path))
                        
                        if not found_path:
                            # Target not found in neighbor lists - check direct neighbors from local node
                            local_node_info = nodes_data.get(self.callsign, {})
                            local_neighbors = local_node_info.get('neighbors', [])
                            local_routes = local_node_info.get('routes', {})
                            
                            # Find which direct neighbors have heard the target
                            direct_nodes_that_heard = []
                            for neighbor in local_neighbors:
                                neighbor_info = nodes_data.get(neighbor, {})
                                neighbor_neighbors = neighbor_info.get('neighbors', [])
                                if target_base in neighbor_neighbors:
                                    # Get route quality from local node to this neighbor
                                    quality = local_routes.get(neighbor, 0)
                                    direct_nodes_that_heard.append((neighbor, quality))
                            
                            if direct_nodes_that_heard:
                                if self.verbose:
                                    colored_print("Warning: {} not found in any known node's neighbor list".format(target_base), Colors.YELLOW)
                                
                                # Sort by route quality (best first), then alphabetically
                                sorted_nodes = sorted(direct_nodes_that_heard, key=lambda x: (-x[1], x[0]))
                                
                                print("")
                                print("{} has been heard by these direct neighbors:".format(target_base))
                                for i, (node, quality) in enumerate(sorted_nodes, 1):
                                    node_info = nodes_data.get(node, {})
                                    grid = node_info.get('location', {}).get('grid', 'unknown')
                                    print("  {}) {} ({}, quality {})".format(i, node, grid, quality))
                                print("")
                                
                                # In silent mode, auto-select best option (first in quality-sorted list)
                                if self.silent_mode:
                                    intermediate_node = sorted_nodes[0][0]
                                    print("Auto-selected: {} -> {}".format(intermediate_node, target_base))
                                    starting_path = [intermediate_node, target_ssid]
                                    if self.verbose:
                                        print("Built path: {}".format(' -> '.join(starting_path)))
                                    found_path = True
                                else:
                                    # Prompt user to choose intermediate node
                                    try:
                                        choice = input("Choose a node to connect through (1-{}, or blank to skip): ".format(len(sorted_nodes))).strip()
                                        
                                        if not choice:
                                            colored_print("Skipping {} - no path specified".format(target_base), Colors.YELLOW)
                                            return
                                        
                                        choice_idx = int(choice) - 1
                                        if choice_idx < 0 or choice_idx >= len(sorted_nodes):
                                            colored_print("Error: Invalid choice", Colors.RED)
                                            return
                                        
                                        intermediate_node = sorted_nodes[choice_idx][0]
                                        print("Selected: {} -> {}".format(intermediate_node, target_base))
                                        
                                        # Intermediate is a direct neighbor, so path is just [intermediate, target]
                                        starting_path = [intermediate_node, target_ssid]
                                        if self.verbose:
                                            print("Built path: {}".format(' -> '.join(starting_path)))
                                        found_path = True
                                            
                                    except (ValueError, KeyboardInterrupt, EOFError):
                                        print("")
                                        colored_print("Cancelled", Colors.YELLOW)
                                    return
                            else:
                                # No direct neighbors have heard it - search all nodes
                                all_nodes_that_heard = []
                                for node_call, node_info in nodes_data.items():
                                    if node_call == self.callsign:
                                        continue  # Already checked direct neighbors above
                                    neighbor_neighbors = node_info.get('neighbors', [])
                                    if target_base in neighbor_neighbors:
                                        all_nodes_that_heard.append(node_call)
                                
                                if all_nodes_that_heard:
                                    # Calculate hop distances for sorting
                                    node_hop_quality = []
                                    for node in all_nodes_that_heard:
                                        queue_dist = [(self.callsign, [], 0)]
                                        visited_dist = {self.callsign}
                                        
                                        while queue_dist:
                                            current, path, hops = queue_dist.pop(0)
                                            
                                            if current == node:
                                                node_hop_quality.append((node, hops, path))
                                                break
                                            
                                            current_info = nodes_data.get(current, {})
                                            current_routes = current_info.get('routes', {})
                                            for neighbor in current_info.get('neighbors', []):
                                                if neighbor not in visited_dist:
                                                    visited_dist.add(neighbor)
                                                    new_path = path + [neighbor]
                                                    queue_dist.append((neighbor, new_path, hops + 1))
                                    
                                    # Sort by hop count (closest first), then alphabetically
                                    sorted_nodes = sorted(node_hop_quality, key=lambda x: (x[1], x[0]))
                                    
                                    if sorted_nodes:
                                        print("")
                                        print("{} has been heard by these nodes:".format(target_base))
                                        for i, (node, hops, path) in enumerate(sorted_nodes, 1):
                                            node_info = nodes_data.get(node, {})
                                            grid = node_info.get('location', {}).get('grid', 'unknown')
                                            hop_str = "{} hop{}".format(hops, '' if hops == 1 else 's')
                                            print("  {}) {} ({}, {})".format(i, node, grid, hop_str))
                                        print("")
                                        
                                        # In silent mode, auto-select best option (first in sorted list)
                                        if self.silent_mode:
                                            intermediate_node, hops, intermediate_path = sorted_nodes[0]
                                            print("Auto-selected: {} -> {}".format(intermediate_node, target_base))
                                            starting_path = intermediate_path + [target_ssid]
                                            if self.verbose:
                                                print("Built path: {}".format(' -> '.join(starting_path)))
                                            found_path = True
                                        else:
                                            # Prompt user to choose intermediate node
                                            try:
                                                choice = input("Choose a node to connect through (1-{}, or blank to skip): ".format(len(sorted_nodes))).strip()
                                                
                                                if not choice:
                                                    colored_print("Skipping {} - no path specified".format(target_base), Colors.YELLOW)
                                                    return
                                            
                                                choice_idx = int(choice) - 1
                                                if choice_idx < 0 or choice_idx >= len(sorted_nodes):
                                                    colored_print("Error: Invalid choice", Colors.RED)
                                                    return
                                                
                                                intermediate_node, hops, intermediate_path = sorted_nodes[choice_idx]
                                                print("Selected: {} -> {}".format(intermediate_node, target_base))
                                                
                                                # Build complete path: intermediate_path + target
                                                starting_path = intermediate_path + [target_ssid]
                                                if self.verbose:
                                                    print("Built path: {}".format(' -> '.join(starting_path)))
                                                found_path = True
                                                    
                                            except (ValueError, KeyboardInterrupt, EOFError):
                                                print("")
                                                colored_print("Cancelled", Colors.YELLOW)
                                                return
                                    else:
                                        # No nodes heard it - continue to all-nodes fallback
                                        pass
                                else:
                                    # Truly unknown - not heard by anyone
                                    # Fall back to manual selection from all known nodes
                                    all_known_nodes = [(n, nodes_data.get(n, {}).get('location', {}).get('grid', 'unknown'), 
                                                       len(nodes_data.get(n, {}).get('neighbors', []))) 
                                                      for n in nodes_data.keys() if n != self.callsign and n != target_base]
                                    
                                    if all_known_nodes:
                                        colored_print("Warning: {} not found in any neighbor list in topology data".format(target_base), Colors.YELLOW)
                                        print("")
                                        print("Available nodes to route through:")
                                        # Sort by number of neighbors (most connected first)
                                        sorted_all = sorted(all_known_nodes, key=lambda x: (-x[2], x[0]))
                                        for i, (node, grid, num_neighbors) in enumerate(sorted_all, 1):
                                            print("  {}) {} ({}, {} neighbors)".format(i, node, grid, num_neighbors))
                                        print("")
                                        
                                        # In silent mode, auto-select best option (most connected)
                                        if self.silent_mode:
                                            intermediate_node = sorted_all[0][0]
                                            print("Auto-selected: {} -> {}".format(intermediate_node, target_base))
                                            
                                            # Find path to intermediate
                                            queue_to_int = [(self.callsign, [])]
                                            visited_to_int = {self.callsign}
                                            path_to_int = None
                                            
                                            while queue_to_int:
                                                curr, path = queue_to_int.pop(0)
                                                if curr == intermediate_node:
                                                    path_to_int = path
                                                    break
                                                curr_info = nodes_data.get(curr, {})
                                                for nbr in curr_info.get('neighbors', []):
                                                    if nbr not in visited_to_int:
                                                        visited_to_int.add(nbr)
                                                        queue_to_int.append((nbr, path + [nbr]))
                                            
                                            if path_to_int is not None:
                                                starting_path = path_to_int + [target_ssid]
                                                if self.verbose:
                                                    print("Built path: {}".format(' -> '.join(starting_path)))
                                                found_path = True
                                            else:
                                                colored_print("Error: Cannot find path to {}".format(intermediate_node), Colors.RED)
                                                return
                                        else:
                                            try:
                                                choice = input("Choose a node to connect through (1-{}, or blank to skip): ".format(len(sorted_all))).strip()
                                                
                                                if not choice:
                                                    colored_print("Skipping {} - no path specified".format(target_base), Colors.YELLOW)
                                                    return
                                                
                                                choice_idx = int(choice) - 1
                                                if choice_idx < 0 or choice_idx >= len(sorted_all):
                                                    colored_print("Error: Invalid choice", Colors.RED)
                                                    return
                                                
                                                intermediate_node = sorted_all[choice_idx][0]
                                                print("Selected: {} -> {}".format(intermediate_node, target_base))
                                                
                                                # Find path to intermediate
                                                queue_to_int = [(self.callsign, [])]
                                                visited_to_int = {self.callsign}
                                                path_to_int = None
                                                
                                                while queue_to_int:
                                                    curr, path = queue_to_int.pop(0)
                                                    if curr == intermediate_node:
                                                        path_to_int = path
                                                        break
                                                    curr_info = nodes_data.get(curr, {})
                                                    for nbr in curr_info.get('neighbors', []):
                                                        if nbr not in visited_to_int:
                                                            visited_to_int.add(nbr)
                                                            queue_to_int.append((nbr, path + [nbr]))
                                                
                                                if path_to_int is not None:
                                                    # Build complete path
                                                    starting_path = path_to_int + [target_ssid]
                                                    if self.verbose:
                                                        print("Built path: {}".format(' -> '.join(starting_path)))
                                                    found_path = True
                                                else:
                                                    colored_print("Error: Cannot find path to {}".format(intermediate_node), Colors.RED)
                                                    return
                                                    
                                            except (ValueError, KeyboardInterrupt, EOFError):
                                                print("")
                                                colored_print("Cancelled", Colors.YELLOW)
                                                return
                                    else:
                                        colored_print("Error: No nodes in topology to route through", Colors.RED)
                                        colored_print("Try crawling more nodes first to build the network topology", Colors.YELLOW)
                                        return
                                    
                                    # If we got here and still no path, allow manual callsign entry (skip in silent mode)
                                    if not found_path and not self.silent_mode:
                                        print("")
                                        colored_print("Unable to find automatic path to {}".format(target_base), Colors.YELLOW)
                                        print("You can manually specify an intermediate node callsign.")
                                        print("")
                                        
                                        try:
                                            manual_node = input("Enter intermediate node callsign (or blank to cancel): ").strip().upper()
                                            
                                            if not manual_node:
                                                colored_print("Cancelled", Colors.YELLOW)
                                                return
                                            
                                            # Validate it's in the topology
                                            if manual_node not in nodes_data:
                                                colored_print("Error: {} not found in network topology".format(manual_node), Colors.RED)
                                                return
                                            
                                            print("Selected: {} -> {}".format(manual_node, target_base))
                                            
                                            # Find path to manual node
                                            queue_to_manual = [(self.callsign, [])]
                                            visited_to_manual = {self.callsign}
                                            path_to_manual = None
                                            
                                            while queue_to_manual:
                                                curr, path = queue_to_manual.pop(0)
                                                if curr == manual_node:
                                                    path_to_manual = path
                                                    break
                                                curr_info = nodes_data.get(curr, {})
                                                for nbr in curr_info.get('neighbors', []):
                                                    if nbr not in visited_to_manual:
                                                        visited_to_manual.add(nbr)
                                                        queue_to_manual.append((nbr, path + [nbr]))
                                            
                                            if path_to_manual is not None:
                                                starting_path = path_to_manual + [target_ssid]
                                                if self.verbose:
                                                    print("Built path: {}".format(' -> '.join(starting_path)))
                                                found_path = True
                                            else:
                                                colored_print("Error: Cannot find path to {}".format(manual_node), Colors.RED)
                                                return
                                                
                                        except (KeyboardInterrupt, EOFError):
                                            print("")
                                            colored_print("Cancelled", Colors.YELLOW)
                                            return
                else:
                    if self.verbose:
                        print("No existing nodemap.json found or no nodes in it")
                        print("Will attempt NetRom discovery when connecting to local node")
            else:
                if not self.callsign:
                    colored_print("Error: Could not determine local node callsign from bpq32.cfg.", Colors.RED)
                    colored_print("Please ensure NODECALL is set in your bpq32.cfg file.", Colors.RED)
                    colored_print("Or provide a starting callsign: {} [MAX_HOPS] [START_NODE]".format(sys.argv[0]), Colors.RED)
                    return
                starting_callsign = self.callsign
                colored_print("Starting network crawl from local node: {}...".format(starting_callsign), Colors.GREEN)
            
            # Handle forced_target (from --callsign flag)
            # This means we want to crawl TO a specific target node
            if forced_target:
                target_base = forced_target
                target_ssid = self.cli_forced_ssids.get(target_base) or self.netrom_ssid_map.get(target_base)
                
                if not target_ssid:
                    colored_print("Error: No SSID found for {} in network data".format(target_base), Colors.RED)
                    colored_print("Use --callsign {}-SSID to specify the full callsign".format(target_base), Colors.YELLOW)
                    return
                
                # Enable target-only mode: only crawl the target, don't discover network
                self.target_only_mode = True
                self.target_callsign = target_ssid
                
                if self.verbose:
                    print("Target-only mode enabled: will only crawl {}".format(target_ssid))
                
                if start_node:
                    # Both start_node and forced_target provided
                    # Path: local -> start_node -> target
                    # Example: ./nodemap.py K1NYY-15 --callsign WD1O-15
                    #   start_node = K1NYY-15 (already resolved with path in starting_path)
                    #   forced_target = WD1O
                    # We need to extend starting_path to include start_node, then target is at end
                    
                    if self.verbose:
                        print("Building path through {} to target {}".format(start_node, target_ssid))
                    
                    # starting_path already contains path to start_node (from BFS above)
                    # The target is reachable from start_node
                    # New path = starting_path + [start_node] (start_node becomes intermediate)
                    # But starting_path might already include start_node if it was found via BFS
                    
                    # Check if start_node sees the target in its neighbors
                    start_base = start_node.split('-')[0] if '-' in start_node else start_node
                    start_ssid = self.netrom_ssid_map.get(start_base, start_node)
                    start_info = nodes_data.get(start_ssid, {}) if existing else {}
                    if not start_info:
                        start_info = nodes_data.get(start_node, {}) if existing else {}
                    
                    start_neighbors = start_info.get('neighbors', [])
                    if target_base not in start_neighbors and target_ssid.split('-')[0] not in start_neighbors:
                        colored_print("Warning: {} not in {}'s neighbor list".format(target_base, start_node), Colors.YELLOW)
                        colored_print("Target may not be reachable from start node", Colors.YELLOW)
                    
                    # Build final path: starting_path leads to start_node, add start_node as intermediate
                    if starting_path:
                        # starting_path doesn't include start_node itself
                        final_path = starting_path + [start_ssid]
                    else:
                        # start_node is direct neighbor of local node
                        final_path = [start_ssid]
                    
                    # Queue the TARGET (not the start_node)
                    starting_callsign = target_ssid
                    starting_path = final_path
                    
                    if self.verbose:
                        print("Queuing target {} with path: {}".format(target_ssid, ' -> '.join(final_path)))
                
                else:
                    # Only forced_target, no start_node - find path to target
                    if self.verbose:
                        print("Finding path to forced target: {} ({})".format(target_base, target_ssid))
                    
                    # Use the same BFS path-finding logic from start_node handling
                    nodes_data = existing.get('nodes', {}) if existing else {}
                    if not nodes_data:
                        colored_print("Error: No topology data available for path finding", Colors.RED)
                        colored_print("Run a full crawl first to build network map", Colors.YELLOW)
                        return
                    
                    # Populate netrom_ssid_map and route_ports from topology data
                    # Priority: 1) Node's own SSID (from routes where it's listed as direct neighbor)
                    #           2) netrom_ssids from other nodes
                    for node_call, node_info in nodes_data.items():
                        # First, store the node's own SSID (this is authoritative)
                        # The key in nodes_data IS the authoritative SSID (e.g., "KC1JMH-15")
                        base_node = node_call.split('-')[0] if '-' in node_call else node_call
                        if '-' in node_call and base_node not in self.netrom_ssid_map:
                            self.netrom_ssid_map[base_node] = node_call
                            self.ssid_source[base_node] = ('routes', time.time())
                        
                        # Then store SSIDs this node knows about (secondary)
                        for base_call, full_call in node_info.get('netrom_ssids', {}).items():
                            # Only set if we don't have an authoritative source already
                            if base_call not in self.netrom_ssid_map:
                                self.netrom_ssid_map[base_call] = full_call
                                self.ssid_source[base_call] = ('topology', time.time())
                        
                        # Store route ports (which port neighbors are heard on)
                        for neighbor_call, port_num in node_info.get('heard_on_ports', []):
                            if port_num is not None and neighbor_call not in self.route_ports:
                                self.route_ports[neighbor_call] = port_num
                    
                    if self.verbose:
                        print("Loaded {} SSID mappings and {} port mappings from topology".format(
                            len(self.netrom_ssid_map), len(self.route_ports)))
                    
                    # BFS to find shortest path
                    queue = [(self.callsign, [])]
                    visited = {self.callsign}
                    found_path = False
                    forced_path = []
                    
                    if self.verbose:
                        print("Starting BFS from {} (looking for {})".format(self.callsign, target_base))
                        print("Available nodes in topology: {}".format(', '.join(sorted(nodes_data.keys()))))
                    
                    while queue and not found_path:
                        current, path = queue.pop(0)
                        current_info = nodes_data.get(current, {})
                        neighbors = current_info.get('neighbors', [])
                        
                        if self.verbose and neighbors:
                            print("  Checking {} neighbors: {}".format(current, neighbors))
                        
                        for neighbor in neighbors:
                            if neighbor in visited:
                                continue
                            visited.add(neighbor)
                            new_path = path + [neighbor]
                            
                            if neighbor == target_base:
                                forced_path = path
                                found_path = True
                                if self.verbose:
                                    if forced_path:
                                        print("Found {} reachable via: {}".format(target_base, ' -> '.join(forced_path)))
                                    else:
                                        print("Found {} as direct neighbor".format(target_base))
                                break
                            
                            # Try to look up neighbor by name, or by resolved SSID if it's a base call
                            neighbor_info = nodes_data.get(neighbor, {})
                            if not neighbor_info and '-' not in neighbor:
                                # Neighbor is base call, try to resolve to SSID
                                neighbor_ssid = self.netrom_ssid_map.get(neighbor)
                                if neighbor_ssid:
                                    neighbor_info = nodes_data.get(neighbor_ssid, {})
                                    if self.verbose and neighbor_info:
                                        print("    Resolved {} to {}".format(neighbor, neighbor_ssid))
                            
                            neighbor_neighbors = neighbor_info.get('neighbors', [])
                            if self.verbose and neighbor_neighbors:
                                print("    {} has neighbors: {} (looking for {})".format(neighbor, neighbor_neighbors[:5] if len(neighbor_neighbors) > 5 else neighbor_neighbors, target_base))
                            if target_base in neighbor_neighbors:
                                forced_path = new_path
                                found_path = True
                                if self.verbose:
                                    print("Found {} reachable via: {}".format(target_base, ' -> '.join(forced_path)))
                                break
                            
                            queue.append((neighbor, new_path))
                    
                    if found_path:
                        # Queue the target with found path
                        starting_callsign = target_ssid
                        starting_path = forced_path
                        if self.verbose:
                            print("Queuing {} with path: {}".format(target_ssid, ' -> '.join(forced_path) if forced_path else "(direct)"))
                    else:
                        colored_print("Error: Cannot find path to {} in topology".format(target_base), Colors.RED)
                        return
            
            print("BPQ node: {}:{}".format(self.host, self.port))
            print("Max hops: {}".format(self.max_hops))
            if self.target_only_mode:
                print("Mode: Target-only (crawling {} only)".format(self.target_callsign))
            print("-" * 50)
            
            # Start with specified or local node (with path if remote)
            # path contains intermediate hops only (not the target node itself)
            queue_entry = (starting_callsign, starting_path if start_node or forced_target else [], 255)  # Default high quality
            if self.verbose and (start_node or forced_target):
                print("Queuing {} with path: {}".format(starting_callsign, starting_path if starting_path else "(direct)"))
            self.queue.append(queue_entry)

            # Fold in update mode's pre-seeded stubs: nodes already fully
            # known are in self.visited and will be skipped on contact, but
            # their previously recorded unexplored neighbours still need a
            # path to reach them, since crawl_node() never runs for the
            # known node that would otherwise have discovered them fresh.
            preseeded_count = 0
            for stub_callsign, stub_path in preseeded_unexplored:
                if len(stub_path) >= self.max_hops:
                    continue          # would exceed the requested depth
                stub_key = (stub_callsign, tuple(stub_path))
                if stub_key in self.queued_paths:
                    continue
                self.queue.append((stub_callsign, stub_path, 200))
                self.queued_paths.add(stub_key)
                preseeded_count += 1
            if preseeded_count:
                colored_print(
                    "Update mode: {} known node(s) will be skipped; queued {} "
                    "previously unexplored neighbor(s)".format(
                        len(self.visited), preseeded_count), Colors.CYAN)
        
        # BFS traversal with priority sorting:
        # 1. Route quality (higher = better, 0 = blocked)
        # 2. Hop count (fewer = faster/more reliable)
        # 3. MHEARD recency (more recent = likely still active)
        while self.queue:
            # Sort queue by quality (desc), then hop count (asc), then MHEARD recency (asc)
            # Quality 255 = excellent, 192 = good, 0 = blocked
            queue_list = list(self.queue)
            queue_list.sort(key=lambda x: (-x[2], len(x[1]), self.last_heard.get(x[0], 999999)))
            self.queue = deque(queue_list)
            
            callsign, path, quality = self.queue.popleft()
            
            # Limit depth to prevent excessive crawling from discovered neighbors
            # BUT: Don't apply limit to the initial starting node (even if remote)
            # max_hops means "explore neighbors to this depth FROM starting node"
            # not "can only reach nodes at this depth"
            # 
            # path contains intermediate hops, target node is not in path
            # Hop distance = path length + 1 (for the target node itself)
            # Example: WS1EC->KC1JMH->KS1R->W1LH: path=['KC1JMH','KS1R'], W1LH is at hop 3
            
            # Skip hop check for initial starting node (allow reaching it regardless of hops)
            is_starting_node = (starting_callsign is not None and 
                               callsign.split('-')[0] == starting_callsign.split('-')[0])
            
            if not is_starting_node:
                # Not the starting node - apply hop limit to neighbors discovered from it
                if starting_callsign is None:
                    # Resume mode: calculate from path length
                    if not path:
                        # Empty path: either local node (0 hops) or direct neighbor (1 hop)
                        hop_distance = 0 if callsign == self.callsign else 1
                    else:
                        # Path has intermediates: distance = path length + 1 for target
                        hop_distance = len(path) + 1
                else:
                    # Normal mode: compare with actual starting callsign
                    if not path:
                        hop_distance = 0 if callsign == starting_callsign else 1
                    else:
                        hop_distance = len(path) + 1
                
                if hop_distance > self.max_hops:
                    print("Skipping {} ({} hops > max {})".format(callsign, hop_distance, self.max_hops))
                    continue
            
            self.crawl_node(callsign, path)
            time.sleep(2)  # Be polite, don't hammer network
        
        print("-" * 50)
        colored_print("Crawl complete. Found {} nodes.".format(len(self.nodes)), Colors.GREEN)
        if self.failed:
            colored_print("Failed connections: {} nodes".format(len(self.failed)), Colors.YELLOW)
            print("  Failed: {}".format(', '.join(sorted(self.failed))))
        else:
            print("No failed connections.")
        
        # Report nodes skipped due to insufficient SSID data
        if self.skipped_no_ssid:
            colored_print("Skipped (insufficient SSID data): {} nodes".format(len(self.skipped_no_ssid)), Colors.YELLOW)
            for base_call, votes in sorted(self.skipped_no_ssid.items()):
                print("  {}: tied votes {}".format(base_call, votes))
            print("  Use --force-ssid BASE FULL to manually specify SSIDs for these nodes")
        
        # Report nodes skipped because not in any ROUTES table
        if self.skipped_no_route:
            colored_print("Skipped (not in ROUTES): {} nodes".format(len(self.skipped_no_route)), Colors.YELLOW)
            print("  Not in any ROUTES table: {}".format(', '.join(sorted(self.skipped_no_route))))
            print("  These are likely user stations, offline nodes, or packet loss artifacts")
        
        # Notify crawl completion
        total_skipped = len(self.skipped_no_ssid) + len(self.skipped_no_route)
        self._send_notification("Crawl complete: {} nodes, {} failed, {} skipped".format(
            len(self.nodes), len(self.failed), total_skipped))
        
        # Display summary table
        if self.nodes:
            print("\n" + "=" * 96)
            print("NETWORK SUMMARY")
            print("=" * 96)
            print("{:<10} {:<4} {:<6} {:<5} {:<5} {:<6} {:<6} {:<10} {:<30}".format(
                "CALLSIGN", "HOPS", "PORTS", "APPS", "CMDS", "NBRS", "FAILED", "UNEXPLRD", "GRID/LOCATION"
            ))
            print("-" * 96)
            
            for callsign in sorted(self.nodes.keys()):
                node = self.nodes[callsign]
                hop_dist = node.get('hop_distance', 0)
                ports = len([p for p in node.get('ports', []) if p.get('is_rf')])
                apps = len(node.get('applications', []))  # Apps from ? command (BBS, CHAT, RMS, etc.)
                commands = len(node.get('commands', []))  # All commands from ? (reliable)
                neighbors = len(node.get('neighbors', []))
                
                # Recalculate failed connections from intermittent_links
                # Count links where this node (callsign) tried to reach neighbors
                failed = 0
                for (from_call, to_call) in self.intermittent_links.keys():
                    if from_call == callsign:
                        failed += 1
                
                unexplored = len(node.get('unexplored_neighbors', []))
                location = node.get('location', {})
                grid = location.get('grid', '')
                city = location.get('city', '')
                state = location.get('state', '')
                
                # Build location string
                if grid:
                    loc_str = grid
                elif city and state:
                    loc_str = "{}, {}".format(city, state)
                else:
                    loc_str = ""
                
                print("{:<10} {:<4} {:<6} {:<5} {:<5} {:<6} {:<6} {:<10} {:<30}".format(
                    callsign,
                    hop_dist,
                    ports,
                    apps,
                    commands,
                    neighbors,
                    failed if failed > 0 else '',
                    unexplored if unexplored > 0 else '',
                    loc_str[:30]
                ))
            
            print("=" * 96)
            print("Total: {} nodes, {} connections".format(
                len(self.nodes),
                len(self.connections)
            ))
            print("=" * 96)
    
    # Fields that describe the node's history rather than its current state.
    # A crawl that does not re-visit a node must not blank these, and a crawl
    # that does re-visit it must not reset them to this run's values.
    _HISTORY_FIELDS = (
        'first_seen', 'last_seen', 'last_crawled', 'crawl_attempts',
        'crawl_successes', 'consecutive_failures', 'notes',
    )

    # Fields that are a point-in-time observation, not a durable fact: an
    # empty result here means "we checked and there is currently nothing",
    # not "we didn't check" - unlike a gridsquare, which stays true forever
    # once known, so a crawl finding nothing new for it must not blank it.
    # port_audit specifically is HF/IP awareness data (see --hf:audit /
    # --ip:audit): keeping a stale sighting around after the station has
    # gone quiet would defeat the point of auditing current conditions.
    _ALWAYS_FRESH_FIELDS = ('port_audit',)

    def _merge_node_record(self, callsign, fresh, existing):
        """Combine a freshly crawled node record with what we already had.

        Replacing the record wholesale is what used to lose hand-entered
        gridsquares: a node whose INFO text carries no locator re-exports with
        gridsquare=None, so the next write silently erased the value a sysop
        had typed in. Fresh observations win for anything the network reports,
        history fields are carried forward, and a field the crawl came back
        empty-handed on keeps its previous value rather than nulling it -
        except _ALWAYS_FRESH_FIELDS, which describe the present moment rather
        than an accumulated fact and so must be allowed to go back to empty.
        """
        if not existing:
            merged = dict(fresh)
        else:
            merged = dict(existing)
            for key, value in fresh.items():
                if key in self._HISTORY_FIELDS:
                    continue
                if key in self._ALWAYS_FRESH_FIELDS:
                    merged[key] = value
                    continue
                # An empty result means "this crawl learned nothing", not
                # "the previous value is now known to be wrong".
                if value in (None, '', [], {}) and existing.get(key) not in (None, '', [], {}):
                    continue
                merged[key] = value
            for key in self._HISTORY_FIELDS:
                if key in existing and key not in fresh:
                    merged[key] = existing[key]
        return merged

    def _apply_overrides(self, callsign, node):
        """Overlay sysop-entered facts. These outrank anything crawled."""
        grid = self.overrides.grid_for(callsign)
        if grid:
            node.setdefault('location', {})
            node['location']['grid'] = grid
            node['gridsquare'] = grid
            node['location_source'] = 'manual'
        location = self.overrides.location_for(callsign)
        if location:
            node.setdefault('location', {})
            for key in ('city', 'state'):
                if location.get(key):
                    node['location'][key] = location[key]
        return node

    def _connection_key(self, conn):
        return '{}>{}'.format(_base_call(conn.get('from')), _base_call(conn.get('to')))

    def _annotate_connections(self, connections):
        """Stamp first/last seen on links and drop the ones built from ghosts.

        Also flags asymmetry: A hearing B while B never hears A is a real and
        useful property of an RF path, not a defect in the data, and the map
        should be able to draw it differently.
        """
        seen_pairs = set()
        result = []
        fresh_keys = {self._connection_key(c) for c in self.connections}

        for conn in connections:
            from_call, to_call = _base_call(conn.get('from')), _base_call(conn.get('to'))
            if not from_call or not to_call:
                continue
            # A link to a callsign that never existed is not a link.
            if self.overrides.is_ignored(from_call) or self.overrides.is_ignored(to_call):
                continue
            if from_call in self.suspect_calls or to_call in self.suspect_calls:
                continue

            key = '{}>{}'.format(from_call, to_call)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            history = self.connection_history.get(key, {})
            record = dict(conn)
            record['first_seen'] = history.get('first_seen') or self.crawl_started
            if key in fresh_keys:
                record['last_seen'] = self.crawl_started
                record['observed_count'] = history.get('observed_count', 0) + 1
            else:
                record['last_seen'] = history.get('last_seen') or record['first_seen']
                record['observed_count'] = history.get('observed_count', 1)
            age = self._days_since(record['last_seen'])
            if age is not None:
                record['days_since_seen'] = round(age, 2)
                record['stale'] = age > self.STALE_AFTER_DAYS
            result.append(record)

        # Second pass for symmetry, once every link is in hand.
        present = {'{}>{}'.format(_base_call(r['from']), _base_call(r['to'])) for r in result}
        for record in result:
            reverse = '{}>{}'.format(_base_call(record['to']), _base_call(record['from']))
            record['asymmetric'] = reverse not in present

        self.connection_history = {
            '{}>{}'.format(_base_call(r['from']), _base_call(r['to'])): {
                'first_seen': r['first_seen'],
                'last_seen': r['last_seen'],
                'observed_count': r['observed_count'],
            } for r in result
        }
        return result

    def export_json(self, filename='nodemap.json', merge=False):
        """Export network map to JSON.
        
        Args:
            filename: Output filename
            merge: If True, merge with existing data instead of overwrite
        """
        nodes_data = {}
        connections_data = []
        
        # Load existing data if merge mode
        if merge:
            existing = self._load_existing_data(filename)
            if existing and 'nodes' in existing:
                nodes_data = existing['nodes']
                print("Merging with {} existing nodes...".format(len(nodes_data)))
            
            # Load existing connections and filter out connections from re-crawled nodes.
            # Deliberately self.freshly_crawled, not self.nodes.keys() - the latter also
            # contains every node _load_unexplored_nodes() preloaded from nodemap.json
            # before this run touched a single connection (in particular the local/start
            # node itself, on any 'update'-mode run after the first: it's already in
            # nodemap.json, so it's "known" without being re-crawled). Filtering on that
            # wider set drops a still-true old connection for a node this run never
            # actually re-crawled, with no fresh entry appended to replace it - the old
            # connection just vanishes, silently, and stays gone on every later merge too
            # since there's now nothing left in nodemap.json to carry forward.
            if 'connections' in existing:
                crawled_nodes = self.freshly_crawled
                for conn in existing.get('connections', []):
                    # Keep connection if neither endpoint was re-crawled
                    if conn['from'] not in crawled_nodes and conn['to'] not in crawled_nodes:
                        connections_data.append(conn)
        
        # Add new connections from current crawl
        connections_data.extend(self.connections)
        
        # Deduplicate nodes before merge: check if base callsign exists with different SSID
        # If N1QFY exists and we're adding N1QFY-15 (or vice versa), merge to SSID version
        for callsign, node_data in self.nodes.items():
            base_call = callsign.split('-')[0] if '-' in callsign else callsign
            
            # Check if a different SSID variant already exists
            existing_key = None
            if callsign in nodes_data:
                # Exact match - will overwrite
                existing_key = callsign
            else:
                # Check for base or SSID variants
                for existing_call in list(nodes_data.keys()):
                    existing_base = existing_call.split('-')[0] if '-' in existing_call else existing_call
                    if existing_base == base_call:
                        # Found variant - prefer SSID version over base
                        if '-' in callsign and '-' not in existing_call:
                            # New has SSID, existing is base - use new, delete existing
                            if self.verbose:
                                print("  Deduplicating: {} replaces {}".format(callsign, existing_call))
                            del nodes_data[existing_call]
                            existing_key = None
                        elif '-' in existing_call and '-' not in callsign:
                            # Existing has SSID, new is base - keep existing, skip new
                            if self.verbose:
                                print("  Deduplicating: keeping {} over {}".format(existing_call, callsign))
                            existing_key = existing_call
                        else:
                            # Both have SSID or both base - overwrite
                            existing_key = existing_call
                        break
            
            # Add or update node. Field-level merge, not replacement: a
            # crawl that comes back without a gridsquare must not erase one
            # that is already recorded.
            #
            # target_key is deliberately existing_key (the SSID-bearing key,
            # e.g. 'KS1R-15') rather than callsign (the base call this run
            # crawled under, e.g. 'KS1R') whenever the two differ. Writing
            # under callsign here used to silently create a second, wrong
            # entry - or with the old bare `continue`, drop this run's fresh
            # data on the floor entirely, since self.nodes is keyed by base
            # call but nodemap.json keys remote nodes with their SSID.
            target_key = existing_key or callsign
            nodes_data[target_key] = self._merge_node_record(
                target_key, node_data, nodes_data.get(target_key))
        
        # Convert intermittent_links keys to strings for JSON serialization
        intermittent_serialized = {}
        for (from_call, to_call), attempts in self.intermittent_links.items():
            key = "{}>{}".format(from_call, to_call)
            intermittent_serialized[key] = attempts

        # Drop quarantined ghosts from the map entirely, but keep the record
        # of them in a separate block so a false positive stays auditable and
        # can be lifted with --confirm-call.
        for callsign in list(nodes_data.keys()):
            base = _base_call(callsign)
            if not (base in self.suspect_calls or self.overrides.is_ignored(base)):
                continue
            # Proof of contact beats the heuristic that flagged it, and the
            # stale ignore entry is cleared so later crawls stop skipping it.
            if self._has_crawl_evidence(nodes_data[callsign]):
                self._clear_ignore(base, 'we have connected to it')
                continue
            del nodes_data[callsign]

        # Strip ghosts out of every neighbour list too, otherwise they survive
        # as phantom edges even after the node records are gone.
        for callsign, node in nodes_data.items():
            for field in ('neighbors', 'explored_neighbors',
                          'unexplored_neighbors', 'intermittent_neighbors'):
                values = node.get(field)
                if isinstance(values, list):
                    node[field] = [n for n in values
                                   if _base_call(n) not in self.suspect_calls
                                   and not self.overrides.is_ignored(n)]

        # Overlay sysop data and stamp the temporal fields across every node,
        # including ones this run never touched - otherwise a node goes
        # permanently statusless the moment it stops being re-crawled.
        for callsign, node in nodes_data.items():
            fix = self.location_fixes.get(callsign)
            if fix is not None:
                location = node.setdefault('location', {})
                for field in ('city', 'state'):
                    if fix[field]:
                        location[field] = fix[field]
                    else:
                        location.pop(field, None)
            self._apply_overrides(callsign, node)
            self._apply_temporal_fields(callsign, node)

        connections_data = self._annotate_connections(connections_data)

        status_counts = {}
        for node in nodes_data.values():
            status = node.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        data = {
            'metadata': {
                'nodemap_version': __version__,
                'generated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'generator': 'nodemap.py'
            },
            'nodes': nodes_data,
            'connections': connections_data,
            'intermittent_links': intermittent_serialized,  # Failed/unreliable connections
            'suspect_callsigns': self.suspect_calls,  # Quarantined: corrupt/ghost calls
            'connection_history': self.connection_history,
            'path_history': self.path_history,
            'crawl_info': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'start_node': self.callsign,
                'total_nodes': len(nodes_data),
                'total_connections': len(connections_data),
                'mode': 'merge' if merge else 'overwrite',
                'nodes_crawled_this_run': sorted(self.freshly_crawled),
                'status_counts': status_counts,
                'suspect_count': len(self.suspect_calls),
            }
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        # Persist the sidecars alongside the map.
        self.overrides.save()
        self.resolver.save_cache()

        mode_str = "Merged into" if merge else "Exported to"
        print("{} {} ({} nodes)".format(mode_str, filename, len(nodes_data)))
        if status_counts:
            print("  Status: {}".format(', '.join(
                '{} {}'.format(count, status)
                for status, count in sorted(status_counts.items()))))
        if self.suspect_calls:
            colored_print("  Quarantined {} suspect callsign(s)".format(
                len(self.suspect_calls)), Colors.YELLOW)
    
    def export_csv(self, filename='nodemap.csv'):
        """Export connections to CSV with frequency information for network mapping."""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            # Enhanced header with frequency fields for network mapping
            writer.writerow(['From', 'To', 'Port', 'Quality', 'Intermittent', 'To_Explored', 
                           'From_Grid', 'To_Grid', 'From_Type', 'To_Type', 
                           'From_Frequencies', 'To_Frequencies', 'From_Ports'])
            
            for conn in self.connections:
                from_node = self.nodes.get(conn['from'], {})
                to_node = self.nodes.get(conn['to'], {})
                to_call = conn['to']
                
                # Determine if 'to' node was explored
                to_explored = 'Yes' if to_call in self.visited else 'No'
                
                # Extract RF frequencies from 'from' node for operators to know connection options
                from_frequencies = []
                from_ports = []
                for port in from_node.get('ports', []):
                    if port['is_rf'] and port.get('frequency'):
                        from_frequencies.append(str(port['frequency']))
                        from_ports.append(str(port['number']))
                
                # Extract RF frequencies from 'to' node
                to_frequencies = []
                for port in to_node.get('ports', []):
                    if port['is_rf'] and port.get('frequency'):
                        to_frequencies.append(str(port['frequency']))
                
                writer.writerow([
                    conn['from'],
                    conn['to'],
                    conn['port'],
                    conn.get('quality', 0),
                    'Yes' if conn.get('intermittent', False) else 'No',
                    to_explored,
                    from_node.get('location', {}).get('grid', ''),
                    to_node.get('location', {}).get('grid', ''),
                    from_node.get('type', 'Unknown'),
                    to_node.get('type', 'Unknown'),
                    ';'.join(from_frequencies),  # Semicolon-separated frequencies (e.g., "433.3;145.05")
                    ';'.join(to_frequencies),
                    ';'.join(from_ports)         # Corresponding port numbers for frequency reference
                ])
        
        print("Exported to {}".format(filename))
    
    def merge_external_data(self, filename):
        """Merge data from another nodemap.json file.
        
        Args:
            filename: Path to external nodemap.json file
            
        Returns:
            Number of nodes merged, or -1 on error
        """
        try:
            external_data = self._load_existing_data(filename)
            if not external_data or 'nodes' not in external_data:
                colored_print("Error: Invalid or missing nodemap data in {}".format(filename), Colors.RED)
                return -1
            
            external_nodes = external_data['nodes']
            merged_count = 0
            new_count = 0
            
            for callsign, node_data in external_nodes.items():
                if callsign in self.nodes:
                    # Node exists, merge data intelligently
                    existing = self.nodes[callsign]
                    
                    # Keep most recent timestamp for same data
                    # Merge neighbor lists (union)
                    existing_neighbors = set(existing.get('neighbors', []))
                    external_neighbors = set(node_data.get('neighbors', []))
                    merged_neighbors = list(existing_neighbors | external_neighbors)
                    
                    # Merge intermittent_neighbors
                    existing_intermittent = set(existing.get('intermittent_neighbors', []))
                    external_intermittent = set(node_data.get('intermittent_neighbors', []))
                    merged_intermittent = list(existing_intermittent | external_intermittent)
                    
                    # Use external data if it has more recent info or more details
                    external_timestamp = external_data.get('crawl_info', {}).get('timestamp', '')
                    
                    # Update with merged data
                    self.nodes[callsign]['neighbors'] = merged_neighbors
                    self.nodes[callsign]['intermittent_neighbors'] = merged_intermittent
                    
                    # Merge other fields if external has more info
                    if len(node_data.get('applications', [])) > len(existing.get('applications', [])):
                        self.nodes[callsign]['applications'] = node_data['applications']
                    
                    if node_data.get('location', {}).get('grid') and not existing.get('location', {}).get('grid'):
                        self.nodes[callsign]['location'] = node_data['location']
                    
                    merged_count += 1
                else:
                    # New node, add it
                    self.nodes[callsign] = node_data
                    new_count += 1
            
            # Merge connections
            if 'connections' in external_data:
                external_connections = external_data['connections']
                
                # Create set of existing connections for deduplication
                existing_conn_keys = set()
                for conn in self.connections:
                    key = (conn['from'], conn['to'])
                    existing_conn_keys.add(key)
                
                # Add new connections
                for conn in external_connections:
                    key = (conn['from'], conn['to'])
                    if key not in existing_conn_keys:
                        self.connections.append(conn)
            
            # Merge intermittent_links
            if 'intermittent_links' in external_data:
                external_intermittent = external_data['intermittent_links']
                for link_key, attempts in external_intermittent.items():
                    # Convert back to tuple key format
                    if '>' in link_key:
                        from_call, to_call = link_key.split('>', 1)
                        tuple_key = (from_call, to_call)
                        
                        if tuple_key in self.intermittent_links:
                            # Merge attempt lists
                            self.intermittent_links[tuple_key].extend(attempts)
                        else:
                            self.intermittent_links[tuple_key] = attempts
            
            print("Merged {} nodes from {} ({} new, {} updated)".format(
                len(external_nodes), filename, new_count, merged_count))
            return len(external_nodes)
            
        except Exception as e:
            colored_print("Error merging {}: {}".format(filename, e), Colors.RED)
            return -1


def prompt_for_missing_grids(crawler, filename='nodemap.json'):
    """Walk the sysop through every node still missing a gridsquare.

    Reads the exported map rather than crawler.nodes. In update mode a known
    node is skipped and so never lands in crawler.nodes, which meant the old
    prompt could not see the nodes most likely to be missing a grid - the ones
    that have been in the map for months without one. The prompt was also
    suppressed entirely on resumed crawls.

    Answers go into nodemap-overrides.json, not just into the exported map, so
    the next crawl of that node cannot overwrite them.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except (IOError, ValueError):
        return 0
    nodes = data.get('nodes', {})

    missing = []
    for callsign, node in sorted(nodes.items()):
        grid = node.get('gridsquare') or (node.get('location') or {}).get('grid')
        if not grid:
            missing.append(callsign)
    if not missing:
        return 0

    print("")
    print("{} node(s) still missing a gridsquare:".format(len(missing)))
    print("  {}".format(', '.join(missing)))

    # Offer to look up whatever we can before asking a human to type it in.
    if crawler.resolver.enabled and not crawler.resolver.offline:
        try:
            answer = input("Try looking these up online first? (Y/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("")
            return 0
        if answer in ('', 'y', 'yes'):
            found = 0
            for callsign in list(missing):
                node = nodes[callsign]
                hit = None
                try:
                    hit = crawler.resolver.resolve(
                        callsign, info_text=node.get('info'),
                        existing=node.get('location'))
                except Exception:
                    hit = None
                if hit and hit.get('grid'):
                    crawler.overrides.set_grid(
                        callsign, hit['grid'],
                        source=hit.get('location_source', 'lookup'))
                    if hit.get('city') or hit.get('state'):
                        crawler.overrides.set_location(
                            callsign, hit.get('city'), hit.get('state'),
                            source=hit.get('location_source', 'lookup'))
                    print("  {:<10} {}  ({})".format(
                        callsign, hit['grid'], hit.get('location_source')))
                    missing.remove(callsign)
                    found += 1
            crawler.overrides.save()
            crawler.resolver.save_cache()
            print("  Resolved {} of them automatically.".format(found))
            if not missing:
                return found

    print("")
    try:
        answer = input("Enter gridsquares for the remaining {} by hand? (y/N): ".format(
            len(missing))).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("")
        return 0
    if answer not in ('y', 'yes'):
        return 0

    print("Enter a gridsquare, or press Enter to skip, or 'q' to stop.")
    updated = 0
    for callsign in missing:
        node = nodes[callsign]
        location = node.get('location') or {}
        # Show whatever context we have - the city, or the first line of the
        # node's own INFO text - so the sysop is not guessing from a callsign.
        context = ''
        if location.get('city'):
            context = ' ({}{})'.format(
                location['city'],
                ', ' + location['state'] if location.get('state') else '')
        elif node.get('info'):
            first = node['info'].strip().split('\n')[0][:48]
            if first:
                context = ' [{}]'.format(first)

        while True:
            try:
                value = input("  {}{}: ".format(callsign, context)).strip()
            except (KeyboardInterrupt, EOFError):
                print("")
                value = 'q'
            if value.lower() == 'q':
                crawler.overrides.save()
                return updated
            if not value:
                break
            if not re.match(r'^[A-R]{2}[0-9]{2}([a-x]{2})?$', value, re.IGNORECASE):
                print("    '{}' is not a gridsquare (expected FN43 or FN43vp).".format(value))
                try:
                    if input("    Use it anyway? (y/N): ").strip().lower() in ('y', 'yes'):
                        pass
                    else:
                        continue
                except (KeyboardInterrupt, EOFError):
                    print("")
                    continue
            value = value[:4].upper() + value[4:].lower()
            crawler.overrides.set_grid(callsign, value, source='manual')
            updated += 1
            break

    crawler.overrides.save()
    if updated:
        print("")
        print("Saved {} gridsquare(s) to {}.".format(
            updated, crawler.overrides.filename))
        print("These now override anything a future crawl parses.")
    return updated


def review_quarantined_callsigns(crawler):
    """Let the sysop confirm or reject each quarantined callsign.

    Anything confirmed is whitelisted permanently and will be crawled from
    now on; anything rejected stays on the ignore list so no future crawl
    spends RF time trying to reach a station that never existed.
    """
    suspects = crawler.suspect_calls
    if not suspects:
        return 0
    print("")
    print("{} callsign(s) quarantined as probable packet corruption:".format(len(suspects)))
    for callsign, detail in sorted(suspects.items()):
        print("  {:<10} {:<22} heard by {} node(s)".format(
            callsign, detail['reason'], detail.get('heard_by', 1)))
    print("")
    print("These are excluded from the map and will not be crawled again.")
    try:
        answer = input("Review them one by one? (y/N): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("")
        return 0
    if answer not in ('y', 'yes'):
        return 0

    print("y = real station (crawl it in future), Enter = confirm as junk, q = stop")
    restored = 0
    for callsign, detail in sorted(suspects.items()):
        try:
            answer = input("  {} [{}]: ".format(callsign, detail['reason'])).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("")
            break
        if answer == 'q':
            break
        if answer in ('y', 'yes'):
            crawler.overrides.add_confirm(callsign, reason='sysop reviewed')
            restored += 1
            print("    {} whitelisted - it will be crawled next run.".format(callsign))
    crawler.overrides.save()
    if restored:
        print("")
        print("Whitelisted {} callsign(s).".format(restored))
    return restored


def _parse_port_mode(argv, long_flag, short_flag):
    """Tri-state parse for --hf[:audit|:crawl] / --ip[:audit|:crawl].

    Bare --hf or -H means 'audit': list what is heard on that port type
    without ever connecting to it. --hf:crawl opts into the old, slower
    behaviour of actually dialing out and fully crawling through it. Absent
    entirely, the port type is skipped altogether ('off').
    """
    mode = 'off'
    prefix = long_flag + ':'
    for arg in argv:
        if arg == long_flag or arg == short_flag:
            mode = 'audit'
        elif arg.startswith(prefix):
            suffix = arg[len(prefix):].strip().lower()
            if suffix in ('audit', 'crawl'):
                mode = suffix
            else:
                colored_print("Warning: unknown mode '{}' for {} - use {}:audit or {}:crawl".format(
                    suffix, long_flag, long_flag, long_flag), Colors.YELLOW)
                mode = 'audit'
    return mode


def main():
    """Main entry point."""
    # Ignore-list management (fast exits, no crawl, no node connection)
    if '--list-ignored' in sys.argv:
        store = OverrideStore()
        if not store.ignore:
            print("No callsigns are being ignored.")
            sys.exit(0)
        print("{} ignored callsign(s) - these are skipped by every crawl:".format(
            len(store.ignore)))
        print("")
        print("  {:<10} {:<24} {:<10} {}".format('CALL', 'REASON', 'SOURCE', 'SEEN'))
        for call, detail in sorted(store.ignore.items()):
            print("  {:<10} {:<24} {:<10} {}".format(
                call, detail.get('reason', '')[:23],
                detail.get('source', ''), detail.get('hits', 1)))
        print("")
        print("Restore one with: {} --confirm-call CALLSIGN".format(sys.argv[0]))
        sys.exit(0)

    if '--ignore-call' in sys.argv:
        idx = sys.argv.index('--ignore-call')
        if idx + 1 >= len(sys.argv):
            colored_print("Error: --ignore-call requires a CALLSIGN", Colors.RED)
            sys.exit(1)
        store = OverrideStore()
        added = 0
        for call in sys.argv[idx + 1].split(','):
            call = call.strip().upper()
            if not call:
                continue
            store.add_ignore(call, 'sysop rejected', source='manual')
            print("Ignoring {} - it will not be crawled again.".format(call))
            added += 1
        store.save()
        sys.exit(0 if added else 1)

    if '--confirm-call' in sys.argv:
        idx = sys.argv.index('--confirm-call')
        if idx + 1 >= len(sys.argv):
            colored_print("Error: --confirm-call requires a CALLSIGN", Colors.RED)
            sys.exit(1)
        store = OverrideStore()
        for call in sys.argv[idx + 1].split(','):
            call = call.strip().upper()
            if not call:
                continue
            store.add_confirm(call, reason='sysop confirmed real')
            print("Confirmed {} as a real station - it will be crawled and mapped.".format(call))
        store.save()
        sys.exit(0)

    # Check for set-grid mode first (fast exit)
    if '--set-grid' in sys.argv or '-g' in sys.argv:
        set_grid_call = None
        set_grid_value = None
        for i, arg in enumerate(sys.argv):
            if (arg == '--set-grid' or arg == '-g') and i + 2 < len(sys.argv):
                set_grid_call = sys.argv[i + 1].upper()
                set_grid_value = sys.argv[i + 2]
                break
        
        if not set_grid_call or not set_grid_value:
            colored_print("Error: --set-grid requires CALLSIGN and GRIDSQUARE", Colors.RED)
            print("Example: {} --set-grid NG1P FN43vp".format(sys.argv[0]))
            sys.exit(1)
        
        # Validate gridsquare format (basic check)
        if not re.match(r'^[A-R]{2}[0-9]{2}([a-x]{2})?$', set_grid_value, re.IGNORECASE):
            colored_print("Warning: Gridsquare '{}' doesn't match standard format (e.g., FN43vp)".format(set_grid_value), Colors.YELLOW)
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                sys.exit(0)
        
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            colored_print("Run a crawl first to generate network data", Colors.RED)
            sys.exit(1)
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            base_call = set_grid_call.split('-')[0] if '-' in set_grid_call else set_grid_call
            
            # Find node by base callsign or exact match
            node_key = None
            if set_grid_call in nodes_data:
                node_key = set_grid_call
            else:
                # Try finding by base callsign
                matches = [k for k in nodes_data.keys() if k.split('-')[0] == base_call]
                if not matches:
                    colored_print("Node {} not found in nodemap.json".format(set_grid_call), Colors.RED)
                    colored_print("Available nodes: {}".format(', '.join(sorted(nodes_data.keys()))), Colors.YELLOW)
                    sys.exit(1)
                elif len(matches) > 1:
                    colored_print("Multiple SSIDs found for {}: {}".format(base_call, ', '.join(matches)), Colors.YELLOW)
                    response = input("Update all variants? (Y/n): ").strip().lower()
                    if response in ['', 'y', 'yes']:
                        # Update all variants
                        _store = OverrideStore()
                        for match in matches:
                            if 'location' not in nodes_data[match]:
                                nodes_data[match]['location'] = {}
                            nodes_data[match]['location']['grid'] = set_grid_value
                            nodes_data[match]['gridsquare'] = set_grid_value
                            # Also record it as a sysop override. Writing only
                            # to nodemap.json meant the value lasted exactly
                            # until the next crawl re-exported the node.
                            _store.set_grid(match, set_grid_value, source='manual')
                            print("Updated gridsquare for {}: {}".format(match, set_grid_value))
                        _store.save()
                        
                        # Save back to file
                        with open('nodemap.json', 'w') as f:
                            json.dump(data, f, indent=2)
                        colored_print("\nSaved to nodemap.json", Colors.GREEN)
                        sys.exit(0)
                    else:
                        node_key = matches[0]
                        print("Updating only: {}".format(node_key))
                else:
                    node_key = matches[0]
            
            # Update the node's gridsquare
            if 'location' not in nodes_data[node_key]:
                nodes_data[node_key]['location'] = {}
            
            old_grid = nodes_data[node_key]['location'].get('grid', 'N/A')
            nodes_data[node_key]['location']['grid'] = set_grid_value
            nodes_data[node_key]['gridsquare'] = set_grid_value
            # Record the override so a later crawl cannot overwrite it.
            _store = OverrideStore()
            _store.set_grid(node_key, set_grid_value, source='manual')
            _store.save()
            
            print("Updated gridsquare for {}: {} -> {}".format(node_key, old_grid, set_grid_value))
            
            # Save back to file
            with open('nodemap.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            colored_print("Saved to nodemap.json", Colors.GREEN)
            
            # Offer to regenerate maps
            # These paths are commonly scripted (cron, deploy hooks), where
            # stdin is closed; treat that as "no" rather than an error.
            try:
                response = input("\nRegenerate maps? (Y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("")
                response = "n"
            if response in ['', 'y', 'yes']:
                print("\nGenerating maps...")
                html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
                try:
                    import subprocess
                    result = subprocess.call(['python3', html_script, '--all'])
                    if result == 0:
                        colored_print("Maps generated successfully!", Colors.GREEN)
                    else:
                        colored_print("Warning: Map generation exited with code {}".format(result), Colors.YELLOW)
                except Exception as e:
                    colored_print("Error generating maps: {}".format(e), Colors.RED)
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error updating nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        
        sys.exit(0)
    
    # Check for note mode (add/update note for a node)
    if '--note' in sys.argv or '-N' in sys.argv:
        note_call = None
        note_text = None
        for i, arg in enumerate(sys.argv):
            if (arg == '--note' or arg == '-N') and i + 2 < len(sys.argv):
                note_call = sys.argv[i + 1].upper()
                note_text = sys.argv[i + 2]
                break
        
        if not note_call or note_text is None:
            colored_print("Error: --note requires CALLSIGN and \"NOTE TEXT\"", Colors.RED)
            print("Example: {} --note WD1O \"HF port: 7.101 MHz VARA\"".format(sys.argv[0]))
            print("Example: {} --note KS1R \"Offline weekdays, active weekends\"".format(sys.argv[0]))
            print("To clear a note, use empty string: --note WD1O \"\"")
            sys.exit(1)
        
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            colored_print("Run a crawl first to generate network data", Colors.RED)
            sys.exit(1)
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            base_call = note_call.split('-')[0] if '-' in note_call else note_call
            
            # Find node by base callsign or exact match
            node_key = None
            if note_call in nodes_data:
                node_key = note_call
            else:
                # Try finding by base callsign
                matches = [k for k in nodes_data.keys() if k.split('-')[0] == base_call]
                if not matches:
                    colored_print("Node {} not found in nodemap.json".format(note_call), Colors.RED)
                    colored_print("Available nodes: {}".format(', '.join(sorted(nodes_data.keys()))), Colors.YELLOW)
                    sys.exit(1)
                elif len(matches) > 1:
                    colored_print("Multiple SSIDs found for {}: {}".format(base_call, ', '.join(matches)), Colors.YELLOW)
                    response = input("Update all variants? (Y/n): ").strip().lower()
                    if response in ['', 'y', 'yes']:
                        # Update all variants
                        for match in matches:
                            if note_text:
                                nodes_data[match]['note'] = note_text
                                print("Updated note for {}: {}".format(match, note_text))
                            else:
                                # Clear note
                                if 'note' in nodes_data[match]:
                                    del nodes_data[match]['note']
                                print("Cleared note for {}".format(match))
                        
                        # Save back to file
                        with open('nodemap.json', 'w') as f:
                            json.dump(data, f, indent=2)
                        colored_print("\nSaved to nodemap.json", Colors.GREEN)
                        sys.exit(0)
                    else:
                        node_key = matches[0]
                        print("Updating only: {}".format(node_key))
                else:
                    node_key = matches[0]
            
            # Update/clear the node's note
            old_note = nodes_data[node_key].get('note', '')
            if note_text:
                nodes_data[node_key]['note'] = note_text
                if old_note:
                    print("Updated note for {}: \"{}\" -> \"{}\"".format(node_key, old_note, note_text))
                else:
                    print("Added note for {}: \"{}\"".format(node_key, note_text))
            else:
                # Clear note
                if 'note' in nodes_data[node_key]:
                    del nodes_data[node_key]['note']
                print("Cleared note for {} (was: \"{}\")".format(node_key, old_note))
            
            # Save back to file
            with open('nodemap.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            colored_print("Saved to nodemap.json", Colors.GREEN)
            
            # Offer to regenerate maps
            # These paths are commonly scripted (cron, deploy hooks), where
            # stdin is closed; treat that as "no" rather than an error.
            try:
                response = input("\nRegenerate maps? (Y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("")
                response = "n"
            if response in ['', 'y', 'yes']:
                print("\nGenerating maps...")
                html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
                try:
                    import subprocess
                    result = subprocess.call(['python3', html_script, '--all'])
                    if result == 0:
                        colored_print("Maps generated successfully!", Colors.GREEN)
                    else:
                        colored_print("Warning: Map generation exited with code {}".format(result), Colors.YELLOW)
                except Exception as e:
                    colored_print("Error generating maps: {}".format(e), Colors.RED)
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error updating nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        
        sys.exit(0)
    
    # Check for cleanup mode (nodes, connections, or all)
    if '--cleanup' in sys.argv or '-C' in sys.argv:
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            sys.exit(1)
        
        # Determine what to clean up
        cleanup_target = 'all'  # default
        for i, arg in enumerate(sys.argv):
            if (arg == '--cleanup' or arg == '-C') and i + 1 < len(sys.argv):
                next_arg = sys.argv[i + 1].lower()
                if next_arg in ['nodes', 'connections', 'unexplored', 'all']:
                    cleanup_target = next_arg
                    break
        
        print("BPQ Node Map Cleanup v{} - {}".format(__version__, cleanup_target))
        print("=" * 50)
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            connections = data.get('connections', [])
            changes_made = False
            
            # CONNECTIONS CLEANUP
            if cleanup_target in ['connections', 'all']:
                print("\nCleaning up connections...")
                if not connections:
                    print("  No connections to clean")
                else:
                    valid_connections = []
                    invalid_connections = []
                    
                    for conn in connections:
                        from_call = conn['from']
                        to_call = conn['to']
                        to_base = to_call.split('-')[0] if '-' in to_call else to_call
                        
                        from_node = nodes_data.get(from_call, {})
                        routes = from_node.get('routes', {})
                        
                        # Check if destination is in routes with non-zero quality
                        if to_base in routes and routes[to_base] > 0:
                            valid_connections.append(conn)
                        else:
                            invalid_connections.append(conn)
                    
                    if invalid_connections:
                        print("  Found {} invalid connections:".format(len(invalid_connections)))
                        for conn in invalid_connections[:5]:
                            print("    {} -> {} (quality: {})".format(conn['from'], conn['to'], conn.get('quality', 0)))
                        if len(invalid_connections) > 5:
                            print("    ... and {} more".format(len(invalid_connections) - 5))
                        
                        data['connections'] = valid_connections
                        changes_made = True
                        colored_print("  Removed {} invalid connections".format(len(invalid_connections)), Colors.YELLOW)
                        colored_print("  Kept {} valid connections".format(len(valid_connections)), Colors.GREEN)
                    else:
                        print("  All {} connections are valid".format(len(connections)))
            
            # NODES CLEANUP
            if cleanup_target in ['nodes', 'all']:
                print("\nCleaning up nodes...")
                removed = []
                
                # Find base callsigns with multiple SSID entries
                base_calls = {}
                for call in nodes_data.keys():
                    base = call.split('-')[0]
                    if base not in base_calls:
                        base_calls[base] = []
                    base_calls[base].append(call)
                
                # For each base call with duplicates, keep the best one
                for base, variants in base_calls.items():
                    if len(variants) > 1:
                        print("  Found duplicate entries for {}: {}".format(base, ', '.join(variants)))
                        
                        # Score each variant: neighbors count + (has_location ? 100 : 0) + (has_apps ? 50 : 0)
                        scored = []
                        for variant in variants:
                            node = nodes_data[variant]
                            score = len(node.get('neighbors', []))
                            if node.get('location', {}).get('grid'):
                                score += 100
                            if node.get('applications', []):
                                score += 50
                            scored.append((variant, score, node))
                        
                        # Sort by score (highest first)
                        scored.sort(key=lambda x: -x[1])
                        keep = scored[0][0]
                        
                        print("    Keeping: {} (score: {})".format(keep, scored[0][1]))
                        
                        for variant, score, node in scored[1:]:
                            print("    Removing: {} (score: {})".format(variant, score))
                            removed.append(variant)
                
                # Remove empty/incomplete nodes (no neighbors, no location, no apps)
                for call, node in list(nodes_data.items()):
                    if call in removed:
                        continue
                    neighbors = node.get('neighbors', [])
                    location = node.get('location', {})
                    apps = node.get('applications', [])
                    
                    if len(neighbors) == 0 and not location.get('grid') and len(apps) == 0:
                        print("  Removing incomplete: {} (no data)".format(call))
                        removed.append(call)
                
                if removed:
                    # Remove nodes
                    for call in removed:
                        del nodes_data[call]
                    data['nodes'] = nodes_data
                    changes_made = True
                    colored_print("  Removed {} duplicate/incomplete nodes".format(len(removed)), Colors.YELLOW)
                else:
                    print("  No duplicate or incomplete nodes found")
            
            # UNEXPLORED NEIGHBORS CLEANUP - upgrade base callsigns to full SSIDs
            if cleanup_target in ['unexplored', 'all']:
                print("\nCleaning up unexplored_neighbors (upgrading to full SSIDs)...")
                
                # Build SSID map from all nodes' own_aliases and seen_aliases (consensus approach)
                ssid_map = {}  # base_call -> full_ssid
                for node_call, node_info in nodes_data.items():
                    # own_aliases are authoritative for that node
                    for alias, full_ssid in node_info.get('own_aliases', {}).items():
                        if '-' in full_ssid:
                            base = full_ssid.split('-')[0]
                            if base not in ssid_map:
                                ssid_map[base] = {}
                            if full_ssid not in ssid_map[base]:
                                ssid_map[base][full_ssid] = 0
                            ssid_map[base][full_ssid] += 1
                    
                    # seen_aliases from this node's NODES table
                    for alias, full_ssid in node_info.get('seen_aliases', {}).items():
                        if '-' in full_ssid:
                            base = full_ssid.split('-')[0]
                            if base not in ssid_map:
                                ssid_map[base] = {}
                            if full_ssid not in ssid_map[base]:
                                ssid_map[base][full_ssid] = 0
                            ssid_map[base][full_ssid] += 1
                    
                    # netrom_ssids from MHEARD
                    for base, full_ssid in node_info.get('netrom_ssids', {}).items():
                        if '-' in full_ssid:
                            if base not in ssid_map:
                                ssid_map[base] = {}
                            if full_ssid not in ssid_map[base]:
                                ssid_map[base][full_ssid] = 0
                            ssid_map[base][full_ssid] += 1
                
                # Pick most common SSID for each base call (consensus)
                best_ssid = {}
                for base, ssid_counts in ssid_map.items():
                    if ssid_counts:
                        best = max(ssid_counts.items(), key=lambda x: x[1])[0]
                        best_ssid[base] = best
                
                # Now upgrade unexplored_neighbors in each node
                upgraded_count = 0
                for node_call, node_info in nodes_data.items():
                    unexplored = node_info.get('unexplored_neighbors', [])
                    if not unexplored:
                        continue
                    
                    new_unexplored = []
                    node_upgraded = 0
                    for neighbor in unexplored:
                        if '-' in neighbor:
                            # Already has SSID
                            new_unexplored.append(neighbor)
                        else:
                            # Base callsign - try to upgrade
                            if neighbor in best_ssid:
                                new_unexplored.append(best_ssid[neighbor])
                                node_upgraded += 1
                            else:
                                # No SSID found - keep as-is
                                new_unexplored.append(neighbor)
                    
                    if node_upgraded > 0:
                        node_info['unexplored_neighbors'] = new_unexplored
                        upgraded_count += node_upgraded
                        if upgraded_count <= 10:  # Show first 10
                            print("  {}: upgraded {} entries".format(node_call, node_upgraded))
                
                if upgraded_count > 0:
                    data['nodes'] = nodes_data
                    changes_made = True
                    colored_print("  Upgraded {} unexplored_neighbors to full SSIDs".format(upgraded_count), Colors.YELLOW)
                else:
                    print("  All unexplored_neighbors already have SSIDs")
            
            if not changes_made:
                print("\nNo cleanup needed!")
                sys.exit(0)
            
            # Save changes
            with open('nodemap.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            colored_print("\nSaved cleaned data to nodemap.json", Colors.GREEN)
            
            # Offer to regenerate maps
            # These paths are commonly scripted (cron, deploy hooks), where
            # stdin is closed; treat that as "no" rather than an error.
            try:
                response = input("\nRegenerate maps? (Y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("")
                response = "n"
            if response in ['', 'y', 'yes']:
                print("\nGenerating maps...")
                html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
                try:
                    import subprocess
                    result = subprocess.call(['python3', html_script, '--all'])
                    if result == 0:
                        colored_print("Maps generated successfully!", Colors.GREEN)
                    else:
                        colored_print("Warning: Map generation exited with code {}".format(result), Colors.YELLOW)
                except Exception as e:
                    colored_print("Error generating maps: {}".format(e), Colors.RED)
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error cleaning up nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        
        sys.exit(0)
    
    # Check for help flag first
    if '-h' in sys.argv or '--help' in sys.argv or '/?' in sys.argv:
        print("NAME")
        print("       nodemap - BPQ packet radio network topology crawler")
        print("")
        print("SYNOPSIS")
        print("       nodemap.py [MAX_HOPS] [START_NODE] [OPTIONS]")
        print("")
        print("VERSION")
        print("       {}".format(__version__))
        print("")
        print("DESCRIPTION")
        print("       Automatically crawls packet radio network to discover topology.")
        print("       Connects to nodes via NetRom, retrieves MHEARD/INFO data, and")
        print("       builds a map of node connectivity for visualization.")
        print("")
        print("ARGUMENTS")
        print("       MAX_HOPS")
        print("              Maximum RF hops from start node. Default: 4, or 0 with -c.")
        print("              0=local only, 1=direct neighbors, 2=neighbors+their neighbors.")
        print("")
        print("       START_NODE")
        print("              Callsign to begin crawl from. Default: local node.")
        print("")
        print("OPTIONS")
        print("   Crawl Control:")
        print("       -o, --overwrite")
        print("              Overwrite existing data. Default: merge with existing.")
        print("")
        print("       -r, --resume [FILE]")
        print("              Resume from unexplored nodes. Auto-finds nodemap_partial*.json")
        print("              if nodemap.json missing. Optionally specify FILE to resume from.")
        print("")
        print("       -m, --merge FILE")
        print("              Merge another nodemap.json into current data. Supports wildcards.")
        print("")
        print("       -M, --mode MODE")
        print("              Crawl mode: update (default), reaudit, new-only.")
        print("                update   - Skip nodes already fully known, but still")
        print("                           grow the map from their recorded stubs (fastest")
        print("                           useful default; start node always re-crawled)")
        print("                reaudit  - Re-crawl every reachable node from scratch")
        print("                new-only - Auto-load nodemap.json, queue unexplored neighbors")
        print("                           only - no live walk from the start node")
        print("")
        print("       -x, --exclude [CALLS|FILE]")
        print("              Exclude callsigns from crawling. CALLS: comma-separated list or")
        print("              filename. Default: exclusions.txt if no argument given.")
        print("")
        print("       -H, --hf[:audit|:crawl]")
        print("              HF ports (VARA, ARDOP, PACTOR). Default: skip entirely.")
        print("              --hf or --hf:audit lists what MHEARD reports, never connects.")
        print("              --hf:crawl also connects and fully crawls - slow at 300 baud.")
        print("")
        print("       -t, --timeout SECONDS")
        print("              Override per-node operation timeout. Default: 360 + hop_count*240.")
        print("              Increase for nodes with huge ROUTES tables or poor RF paths.")
        print("              Example: --timeout 1800 (30 minutes per node).")
        print("")
        print("       -I, --ip[:audit|:crawl]")
        print("              IP ports (AXIP, TCP, Telnet). Default: skip entirely.")
        print("              --ip or --ip:audit lists what MHEARD reports, never connects.")
        print("              --ip:crawl also connects and fully crawls over IP.")
        print("")
        print("   Node Operations:")
        print("       -c, --callsign CALL")
        print("              Force specific SSID for connection (e.g., -c NG1P-4).")
        print("")
        print("       --force-ssid BASE FULL")
        print("              Force SSID mapping (can be used multiple times).")
        print("              Example: --force-ssid W1DTX W1DTX-7 --force-ssid N1LJK N1LJK-5")
        print("              Resolves tied SSID votes and fixes consensus conflicts.")
        print("")
        print("       -g, --set-grid CALL GRID")
        print("              Set gridsquare for callsign (e.g., -g NG1P FN43vp).")
        print("              Saved to nodemap-overrides.json; survives re-crawls.")
        print("       --list-ignored")
        print("              List callsigns excluded as packet corruption.")
        print("       --ignore-call CALL[,CALL...]")
        print("              Never crawl or map these callsigns again.")
        print("       --confirm-call CALL[,CALL...]")
        print("              Mark a quarantined callsign as a real station.")
        print("       --no-lookup")
        print("              Do not use the internet to fill in missing locations.")
        print("       --no-auto-ignore")
        print("              Quarantine corrupt callsigns but keep retrying them.")
        print("")
        print("       -N, --note CALL [TEXT]")
        print("              Add/update note for node. Without TEXT, removes existing note.")
        print("")
        print("       -q, --query CALL")
        print("              Query info about node (neighbors, apps, best route).")
        print("")
        print("       -d, --display-nodes")
        print("              Display nodes table from nodemap.json and exit.")
        print("")
        print("       -C, --cleanup [TARGET]")
        print("              Clean up nodemap.json. TARGET: nodes, connections, unexplored, all.")
        print("              Default: all.")
        print("")
        print("   Authentication:")
        print("       -u, --user USERNAME")
        print("              Telnet login username. Default: prompt if needed.")
        print("")
        print("       -p, --pass PASSWORD")
        print("              Telnet login password. Default: prompt if needed.")
        print("")
        print("   Logging & Debug:")
        print("       -v, --verbose")
        print("              Show detailed command/response output.")
        print("")
        print("       -l, --log [FILE]")
        print("              Log telnet traffic. Default: telnet.log.")
        print("")
        print("       -D, --debug-log [FILE]")
        print("              Log verbose debug output (implies -v). Default: debug.log.")
        print("")
        print("       -n, --notify URL")
        print("              Send notifications to webhook URL.")
        print("")
        print("       -y, --yes")
        print("              Silent/autonomous mode. Assumes 'yes' to all prompts.")
        print("              Requires -u and -p for authentication. Auto-generates maps.")
        print("")
        print("       -h, --help, /?")
        print("              Show this help message.")
        print("")
        print("EXAMPLES")
        print("       nodemap.py 5")
        print("              Crawl 5 hops, merge with existing data.")
        print("")
        print("       nodemap.py 10 WS1EC")
        print("              Crawl from WS1EC, merge results.")
        print("")
        print("       nodemap.py -r")
        print("              Resume crawl from unexplored nodes.")
        print("")
        print("       nodemap.py -m *.json")
        print("              Merge all JSON files in current directory.")
        print("")
        print("       nodemap.py -c NG1P-4")
        print("              Force connection to specific SSID.")
        print("")
        print("       nodemap.py -q NG1P")
        print("              Query what we know about NG1P.")
        print("")
        print("       nodemap.py -g NG1P FN43vp")
        print("              Set gridsquare for NG1P.")
        print("")
        print("       nodemap.py -N NG1P \"HF 7.101 MHz\"")
        print("              Add note to NG1P.")
        print("")
        print("       nodemap.py 10 -y -u KC1JMH -p mypass")
        print("              Autonomous mode: crawl 10 hops, no prompts, auto-generate maps.")
        print("")
        print("FILES")
        print("       nodemap.json    Complete network topology and node information")
        print("       nodemap.csv     Connection list for spreadsheet analysis")
        print("       exclusions.txt  Default exclusion list (one callsign per line)")
        print("")
        print("ENVIRONMENT")
        print("       Reads NODECALL and TCPPORT from ../linbpq/bpq32.cfg")
        print("")
        print("SEE ALSO")
        print("       nodemap-html.py - Generate visual maps from nodemap.json")
        sys.exit(0)
    
    # Check for display-nodes mode first (fast exit)
    if '--display-nodes' in sys.argv or '-d' in sys.argv:
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            colored_print("Run a crawl first to generate network data", Colors.RED)
            sys.exit(1)
        
        # Parse exclusions if -x flag present (before display)
        exclude_nodes = set()
        if '--exclude' in sys.argv or '-x' in sys.argv:
            try:
                x_idx = sys.argv.index('--exclude') if '--exclude' in sys.argv else sys.argv.index('-x')
                # Check if next arg exists and isn't another option
                if x_idx + 1 < len(sys.argv) and not sys.argv[x_idx + 1].startswith('-'):
                    exclude_file = sys.argv[x_idx + 1]
                else:
                    exclude_file = 'exclusions.txt'
                
                if os.path.isfile(exclude_file):
                    with open(exclude_file, 'r') as f:
                        content = f.read()
                    for line in content.replace(',', '\n').split('\n'):
                        call = line.strip().upper()
                        if call and not call.startswith('#'):
                            call = call.split('#')[0].strip()
                            if call:
                                exclude_nodes.add(call)
                    if verbose or '-v' in sys.argv or '--verbose' in sys.argv:
                        print("Loaded {} exclusions from {}".format(len(exclude_nodes), exclude_file))
            except Exception as e:
                pass  # Ignore exclusion errors in display mode
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            netrom_data = data.get('netrom_nodes', {})
            if not nodes_data:
                print("No nodes found in nodemap.json")
                sys.exit(0)
            
            # Build set of explored base callsigns (without SSID)
            explored = set()
            for callsign in nodes_data.keys():
                base = callsign.split('-')[0] if '-' in callsign else callsign
                explored.add(base)
            
            # Build set of all mentioned neighbor base callsigns
            all_neighbors = set()
            for node in nodes_data.values():
                for neighbor in node.get('neighbors', []):
                    base = neighbor.split('-')[0] if '-' in neighbor else neighbor
                    all_neighbors.add(base)
            
            # Unexplored = neighbor base callsigns not in explored base callsigns
            unexplored = all_neighbors - explored
            
            # Filter out excluded nodes from unexplored list (case-insensitive)
            if exclude_nodes:
                unexplored = {call for call in unexplored if call.upper() not in exclude_nodes}
            
            # Print nodes table
            print("\nNodes in nodemap.json ({} total):\n".format(len(nodes_data)))
            print("{:<12} {:<6} {:<10} {:<12} {:<25} {:<25}".format(
                "Callsign", "Hops", "Alias", "Gridsquare", "Neighbors", "Unexplored"))
            print("-" * 105)
            
            # Sort by callsign for consistent display
            for callsign in sorted(nodes_data.keys()):
                node = nodes_data[callsign]
                
                # Get alias - prefer top-level field, fallback to own_aliases or netrom data
                alias = node.get('alias', '')
                if not alias:
                    own_aliases = node.get('own_aliases', {})
                    alias = list(own_aliases.keys())[0] if own_aliases else ''
                if not alias:
                    alias = netrom_data.get(callsign, {}).get('alias', '')
                
                hops = node.get('hop_distance', '')
                
                # Get gridsquare - prefer top-level field, fallback to location dict or netrom data
                grid = node.get('gridsquare', '')
                if not grid:
                    location = node.get('location', {})
                    grid = location.get('grid', '')
                if not grid:
                    grid = netrom_data.get(callsign, {}).get('gridsquare', '')
                
                neighbors = node.get('neighbors', [])
                
                # Find unexplored neighbors (base callsigns, case-insensitive)
                # Convert neighbors to base callsigns and check against unexplored set
                unexplored_neighbors = []
                unexplored_upper = {u.upper() for u in unexplored}
                for n in neighbors:
                    n_base = n.split('-')[0] if '-' in n else n
                    if n_base.upper() in unexplored_upper:
                        unexplored_neighbors.append(n)
                
                # Format neighbors list (first 2, then count)
                if len(neighbors) == 0:
                    neighbor_str = '-'
                elif len(neighbors) <= 2:
                    neighbor_str = ', '.join(neighbors)
                else:
                    neighbor_str = '{} (+{})'.format(
                        ', '.join(neighbors[:2]),
                        len(neighbors) - 2
                    )
                
                # Format unexplored list (first 2, then count)
                if len(unexplored_neighbors) == 0:
                    unexplored_str = '-'
                elif len(unexplored_neighbors) <= 2:
                    unexplored_str = ', '.join(unexplored_neighbors)
                else:
                    unexplored_str = '{} (+{})'.format(
                        ', '.join(unexplored_neighbors[:2]),
                        len(unexplored_neighbors) - 2
                    )
                
                print("{:<12} {:<6} {:<10} {:<12} {:<25} {:<25}".format(
                    callsign,
                    str(hops) if hops != '' else '-',
                    alias[:10],
                    grid[:12],
                    neighbor_str[:25],
                    unexplored_str[:25]
                ))
            
            print("\nTotal nodes: {}".format(len(nodes_data)))
            print("Unexplored neighbors: {}".format(len(unexplored)))
            if unexplored:
                print("Unexplored: {}".format(', '.join(sorted(unexplored))))
            print("Total connections: {}".format(len(data.get('connections', []))))
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error reading nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        
        sys.exit(0)
    
    # Check for query mode first (fast exit)
    if '--query' in sys.argv or '-q' in sys.argv:
        query_call = None
        for i, arg in enumerate(sys.argv):
            if (arg == '--query' or arg == '-q') and i + 1 < len(sys.argv):
                query_call = sys.argv[i + 1].upper()
                break
        
        if not query_call:
            colored_print("Error: --query requires a callsign", Colors.RED)
            sys.exit(1)
        
        if not os.path.exists('nodemap.json'):
            colored_print("Error: nodemap.json not found", Colors.RED)
            colored_print("Run a crawl first to generate network data", Colors.RED)
            sys.exit(1)
        
        # Parse exclusions if -x flag present
        exclude_nodes = set()
        if '--exclude' in sys.argv or '-x' in sys.argv:
            try:
                x_idx = sys.argv.index('--exclude') if '--exclude' in sys.argv else sys.argv.index('-x')
                # Check if next arg exists and isn't another option
                if x_idx + 1 < len(sys.argv) and not sys.argv[x_idx + 1].startswith('-'):
                    exclude_file = sys.argv[x_idx + 1]
                else:
                    exclude_file = 'exclusions.txt'
                
                if os.path.isfile(exclude_file):
                    with open(exclude_file, 'r') as f:
                        content = f.read()
                    for line in content.replace(',', '\n').split('\n'):
                        call = line.strip().upper()
                        if call and not call.startswith('#'):
                            call = call.split('#')[0].strip()
                            if call:
                                exclude_nodes.add(call)
                    if '-v' in sys.argv or '--verbose' in sys.argv:
                        print("Loaded {} exclusions from {}".format(len(exclude_nodes), exclude_file))
            except Exception as e:
                pass  # Ignore exclusion errors in query mode
        
        try:
            with open('nodemap.json', 'r') as f:
                data = json.load(f)
            
            nodes_data = data.get('nodes', {})
            base_call = query_call.split('-')[0] if '-' in query_call else query_call
            
            # Find node by base callsign or exact match
            node_data = nodes_data.get(query_call)
            if not node_data:
                # Try base callsign
                matches = [k for k in nodes_data.keys() if k.split('-')[0] == base_call]
                if not matches:
                    colored_print("Node {} not found in nodemap.json".format(query_call), Colors.RED)
                    colored_print("Hint: Run crawl with --callsign {}-SSID to force specific SSID".format(base_call), Colors.YELLOW)
                    sys.exit(1)
                elif len(matches) > 1:
                    colored_print("Multiple SSIDs found for {}: {}".format(base_call, ', '.join(matches)), Colors.YELLOW)
                    query_call = matches[0]
                    node_data = nodes_data[query_call]
                    print("Showing: {}".format(query_call))
                else:
                    query_call = matches[0]
                    node_data = nodes_data[query_call]
            
            # Display node info
            print("\n" + "=" * 60)
            print("Node: {}".format(query_call))
            print("=" * 60)
            
            # Basic info
            alias = node_data.get('alias', 'N/A')
            node_type = node_data.get('type', 'Unknown')
            hop_distance = node_data.get('hop_distance', '?')
            print("Alias: {}".format(alias))
            print("Type: {}".format(node_type))
            print("Hop Distance: {}".format(hop_distance))
            
            # Location
            location = node_data.get('location', {})
            if location:
                grid = location.get('grid', 'N/A')
                city = location.get('city', '')
                state = location.get('state', '')
                print("Grid Square: {}".format(grid))
                if city or state:
                    print("Location: {}{}".format(city, ', ' + state if state else ''))
            
            # Best route
            successful_path = node_data.get('successful_path')
            if successful_path:
                if successful_path:
                    print("Best Route: {}".format(' > '.join(successful_path + [query_call])))
                else:
                    print("Best Route: Direct")
            
            # Applications
            applications = node_data.get('applications', [])
            if applications:
                # Filter out NetRom aliases
                apps = [a for a in applications if ':' not in a and '}' not in a]
                if apps:
                    print("\nApplications ({}):\n  {}".format(len(apps), ', '.join(apps)))
            
            # Neighbors
            neighbors = node_data.get('neighbors', [])
            explored = node_data.get('explored_neighbors', [])
            unexplored = node_data.get('unexplored_neighbors', [])
            
            # Filter out excluded nodes from unexplored list
            if exclude_nodes and unexplored:
                unexplored = [n for n in unexplored if n.upper() not in exclude_nodes and 
                              (n.split('-')[0].upper() if '-' in n else n.upper()) not in exclude_nodes]
            
            print("\nNeighbors ({} total):".format(len(neighbors)))
            if explored:
                print("  Explored: {}".format(', '.join(sorted(explored))))
            if unexplored:
                print("  Unexplored: {}".format(', '.join(sorted(unexplored))))
            
            # Routes with quality
            routes = node_data.get('routes', {})
            if routes:
                print("\nRoutes ({} reachable nodes):".format(len(routes)))
                # Show top 10 by quality
                sorted_routes = sorted(routes.items(), key=lambda x: (-x[1], x[0]))[:10]
                for route_call, quality in sorted_routes:
                    print("  {:<15} quality: {}".format(route_call, quality))
                if len(routes) > 10:
                    print("  ... ({} more)".format(len(routes) - 10))
            
            # Ports
            ports = node_data.get('ports', [])
            rf_ports = [p for p in ports if p.get('is_rf')]
            if rf_ports:
                print("\nRF Ports ({}):".format(len(rf_ports)))
                for port in rf_ports:
                    port_num = port.get('number')
                    freq = port.get('frequency')
                    desc = port.get('description', '')
                    port_type = port.get('port_type', 'rf')
                    if freq:
                        print("  Port {}: {} MHz".format(port_num, freq))
                    elif port_type == 'hf':
                        print("  Port {}: {} (HF)".format(port_num, desc))
                    else:
                        print("  Port {}: {}".format(port_num, desc))
            
            # Known SSIDs - helps decide which SSID to use for recrawl
            print("\nKnown SSIDs for {}:".format(base_call))
            ssid_sources = {}
            
            # 1. Current node's SSID (what we crawled)
            if '-' in query_call:
                ssid = query_call.split('-')[1]
                ssid_sources[query_call] = ['Current node (crawled)']
            
            # 2. SSIDs from this node's own netrom_ssids (MHEARD data)
            netrom_ssids = node_data.get('netrom_ssids', {})
            if base_call in netrom_ssids:
                self_ssid = netrom_ssids[base_call]
                if self_ssid not in ssid_sources:
                    ssid_sources[self_ssid] = []
                ssid_sources[self_ssid].append('Own MHEARD')
            
            # 3. SSIDs other nodes use to refer to this node
            for other_call, other_data in nodes_data.items():
                if other_call == query_call:
                    continue
                
                # Check other node's netrom_ssids
                other_netrom = other_data.get('netrom_ssids', {})
                if base_call in other_netrom:
                    found_ssid = other_netrom[base_call]
                    if found_ssid not in ssid_sources:
                        ssid_sources[found_ssid] = []
                    ssid_sources[found_ssid].append('MHEARD by {}'.format(other_call))
                
                # Check other node's routes (most authoritative)
                other_routes = other_data.get('routes', {})
                for route_call, quality in other_routes.items():
                    if route_call == base_call or (route_call.startswith(base_call) and 
                                                    (len(route_call) == len(base_call) or 
                                                     route_call[len(base_call)] == '-')):
                        # Found this callsign in routes
                        if route_call not in ssid_sources:
                            ssid_sources[route_call] = []
                        ssid_sources[route_call].append('ROUTES in {} (q={})'.format(other_call, quality))
            
            if ssid_sources:
                # Sort by: 1) SSIDs with base only, 2) SSIDs by number
                sorted_ssids = sorted(ssid_sources.items(), 
                                     key=lambda x: (0 if '-' not in x[0] else 1, x[0]))
                for ssid_call, sources in sorted_ssids:
                    # Deduplicate and limit sources shown
                    unique_sources = []
                    source_types = {}
                    for src in sources:
                        src_type = src.split()[0]  # "ROUTES", "MHEARD", "Current", "Own"
                        if src_type not in source_types:
                            source_types[src_type] = []
                        source_types[src_type].append(src)
                    
                    # Show summary
                    for src_type, src_list in sorted(source_types.items()):
                        if src_type == 'ROUTES':
                            # Show which nodes have this in ROUTES
                            nodes = [s.split('in ')[1].split()[0] for s in src_list if 'in ' in s]
                            unique_sources.append('ROUTES in {} nodes'.format(len(set(nodes))))
                        elif src_type == 'MHEARD':
                            nodes = [s.split('by ')[1] for s in src_list if 'by ' in s]
                            if len(nodes) <= 3:
                                unique_sources.append('MHEARD by {}'.format(', '.join(nodes)))
                            else:
                                unique_sources.append('MHEARD by {} nodes'.format(len(set(nodes))))
                        else:
                            unique_sources.append(src_list[0])
                    
                    print("  {:<15} ({})".format(ssid_call, '; '.join(unique_sources)))
                
                print("\nHint: Use --callsign {} to force recrawl with specific SSID".format(
                    sorted_ssids[0][0] if sorted_ssids else base_call))
            else:
                print("  No SSIDs found")
                print("\nHint: Use --callsign {}-SSID to force recrawl".format(base_call))
            
            print("=" * 60)
            
        except json.JSONDecodeError as e:
            colored_print("Error parsing nodemap.json: {}".format(e), Colors.RED)
            sys.exit(1)
        except Exception as e:
            colored_print("Error reading nodemap.json: {}".format(e), Colors.RED)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        sys.exit(0)
    
    # Print header for normal operation (after fast-exit modes)
    print("BPQ Node Map Crawler v{}".format(__version__))
    print("=" * 50)
    
    # Parse command line args
    max_hops = 4  # Default reduced from 10 to 4 (realistic for 1200 baud RF)
    max_hops_explicit = False  # Track if user explicitly set max_hops
    start_node = None
    forced_ssid = None  # User-specified SSID to override discovery
    forced_ssids = {}  # Multiple forced SSIDs: {base_call: full_ssid}
    username = None
    password = None
    notify_url = None
    log_file = None
    debug_log = None
    crawl_mode = 'update'  # Default to 'update' mode
    exclude_nodes = set()  # Nodes to exclude from crawling
    merge_files = []  # List of files to merge
    resume_file = None  # File to resume from (None = auto-detect)
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    resume = '--resume' in sys.argv or '-r' in sys.argv
    op_timeout = None  # Per-node operation timeout override (seconds)
    generate_maps = False  # Will be set by user prompt or silent mode
    silent_mode = '--yes' in sys.argv or '-y' in sys.argv  # Autonomous mode - no prompts
    hf_mode = _parse_port_mode(sys.argv, '--hf', '-H')  # 'off', 'audit', or 'crawl'
    ip_mode = _parse_port_mode(sys.argv, '--ip', '-I')   # 'off', 'audit', or 'crawl'
    # Location lookups reach the internet; --no-lookup keeps a crawl entirely
    # on-net, which matters when the uplink is the thing that just failed.
    resolve_locations = '--no-lookup' not in sys.argv
    auto_ignore = '--no-auto-ignore' not in sys.argv
    
    # Parse positional and optional arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith('-'):
            break
        if i == 1:
            if arg.isdigit():
                max_hops = int(arg)
                max_hops_explicit = True  # User explicitly set max_hops
            else:
                # First positional arg is not a digit, treat as START_NODE
                start_node = arg.upper()
        elif i == 2:
            start_node = arg.upper()
        i += 1
    
    # Parse options
    i = 1
    unknown_args = []
    while i < len(sys.argv):
        arg = sys.argv[i]
        if (arg == '--user' or arg == '-u') and i + 1 < len(sys.argv):
            username = sys.argv[i + 1]
            i += 2
        elif (arg == '--pass' or arg == '-p') and i + 1 < len(sys.argv):
            password = sys.argv[i + 1]
            i += 2
        elif (arg == '--notify' or arg == '-n') and i + 1 < len(sys.argv):
            notify_url = sys.argv[i + 1]
            i += 2
        elif (arg == '--log' or arg == '-l'):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                log_file = sys.argv[i + 1]
                i += 2
            else:
                log_file = 'telnet.log'
                i += 1
        elif arg == '--debug-log' or arg == '-D':
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                debug_log = sys.argv[i + 1]
                i += 2
            else:
                debug_log = 'debug.log'
                i += 1
            # Debug mode automatically enables verbose output
            verbose = True
        elif arg == '--exclude' or arg == '-x':
            # Exclusion list: can be comma-separated callsigns, a file, or default to exclusions.txt
            # Check if next arg exists and isn't another option
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                exclude_arg = sys.argv[i + 1]
                # Check if it's a file
                if os.path.isfile(exclude_arg):
                    # Load from file (comma or newline delimited)
                    try:
                        with open(exclude_arg, 'r') as f:
                            content = f.read()
                        # Split by commas and newlines
                        for line in content.replace(',', '\n').split('\n'):
                            call = line.strip().upper()
                            # Skip empty lines and comments
                            if call and not call.startswith('#'):
                                # Handle inline comments
                                call = call.split('#')[0].strip()
                                if call:
                                    exclude_nodes.add(call)
                        print("Loaded {} exclusions from {}".format(len(exclude_nodes), exclude_arg))
                    except Exception as e:
                        colored_print("Error reading exclusion file {}: {}".format(exclude_arg, e), Colors.RED)
                        sys.exit(1)
                else:
                    # Treat as comma-separated list of callsigns
                    for call in exclude_arg.split(','):
                        call = call.strip().upper()
                        if call:
                            exclude_nodes.add(call)
                i += 2
            else:
                # No argument provided - use default exclusions.txt
                default_exclude_file = 'exclusions.txt'
                if os.path.isfile(default_exclude_file):
                    try:
                        with open(default_exclude_file, 'r') as f:
                            content = f.read()
                        for line in content.replace(',', '\n').split('\n'):
                            call = line.strip().upper()
                            if call and not call.startswith('#'):
                                call = call.split('#')[0].strip()
                                if call:
                                    exclude_nodes.add(call)
                        print("Loaded {} exclusions from {}".format(len(exclude_nodes), default_exclude_file))
                    except Exception as e:
                        colored_print("Error reading {}: {}".format(default_exclude_file, e), Colors.RED)
                        sys.exit(1)
                else:
                    colored_print("Warning: No exclusions.txt found and no callsigns specified", Colors.YELLOW)
                i += 1
        elif (arg == '--mode' or arg == '-M') and i + 1 < len(sys.argv):
            mode_arg = sys.argv[i + 1].lower()
            if mode_arg in ['update', 'reaudit', 'new-only']:
                crawl_mode = mode_arg
                i += 2
            else:
                colored_print("Error: Invalid mode '{}'. Must be 'update', 'reaudit', or 'new-only'.".format(sys.argv[i + 1]), Colors.RED)
                print("Run '{} --help' for usage information.".format(sys.argv[0]))
                sys.exit(1)
        elif (arg == '--resume' or arg == '-r'):
            resume = True
            # Check if next arg is a filename (not another option)
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                resume_file = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        elif (arg == '--merge' or arg == '-m') and i + 1 < len(sys.argv):
            pattern = sys.argv[i + 1]
            # Handle wildcard patterns like *.json
            if '*' in pattern or '?' in pattern:
                matched_files = glob.glob(pattern)
                if matched_files:
                    # Filter out the default output file to avoid self-merge
                    filtered_files = [f for f in matched_files if f != 'nodemap.json']
                    if len(filtered_files) != len(matched_files):
                        excluded = [f for f in matched_files if f == 'nodemap.json']
                        print("Wildcard '{}' matched {} files, excluding output file: {}".format(
                            pattern, len(matched_files), ', '.join(excluded)))
                    merge_files.extend(filtered_files)
                    if filtered_files:
                        print("Wildcard '{}' matched {} files: {}".format(pattern, len(filtered_files), ', '.join(filtered_files)))
                    else:
                        colored_print("Warning: Wildcard pattern '{}' matched no usable files (output file excluded)".format(pattern), Colors.YELLOW)
                else:
                    colored_print("Warning: Wildcard pattern '{}' matched no files".format(pattern), Colors.YELLOW)
            else:
                # For explicit filenames, also check if it's the output file
                if pattern != 'nodemap.json':
                    merge_files.append(pattern)
                else:
                    colored_print("Warning: Skipping '{}' - cannot merge output file into itself".format(pattern), Colors.YELLOW)
            i += 2
        elif (arg == '--callsign' or arg == '-c') and i + 1 < len(sys.argv):
            forced_ssid = sys.argv[i + 1].upper()
            # Validate format: CALL-SSID
            if '-' not in forced_ssid:
                colored_print("Error: --callsign requires SSID (e.g., NG1P-4)", Colors.RED)
                sys.exit(1)
            # If max_hops wasn't explicitly set AND no START_NODE specified, default to 0 for --callsign (correction mode)
            # --callsign alone is a correction tool to fix one node's SSID, not a full crawl
            # But if START_NODE is specified, user wants a normal crawl with forced SSID
            if not max_hops_explicit and not start_node:
                max_hops = 0
            i += 2
        elif arg == '--force-ssid':
            # Parse multiple --force-ssid pairs: --force-ssid BASE FULL
            if i + 2 < len(sys.argv):
                base = sys.argv[i + 1].upper()
                full = sys.argv[i + 2].upper()
                # Validate base callsign format (without SSID)
                if not NodeCrawler._is_valid_callsign(base) and '-' not in base:
                    # Allow base without SSID validation for wildcards
                    pass
                # Validate full callsign has SSID
                if '-' not in full:
                    colored_print("Error: --force-ssid requires full SSID (e.g., W1DTX-7)", Colors.RED)
                    sys.exit(1)
                forced_ssids[base] = full
                colored_print("Forced SSID: {} -> {}".format(base, full), Colors.CYAN)
                i += 3
            else:
                colored_print("Error: --force-ssid requires BASE and FULL arguments", Colors.RED)
                sys.exit(1)
        elif (arg == '--timeout' or arg == '-t') and i + 1 < len(sys.argv):
            try:
                op_timeout = int(sys.argv[i + 1])
                if op_timeout < 60:
                    colored_print("Error: --timeout must be at least 60 seconds", Colors.RED)
                    sys.exit(1)
            except ValueError:
                colored_print("Error: --timeout requires an integer (seconds)", Colors.RED)
                sys.exit(1)
            i += 2
        elif arg in ['--verbose', '-v', '--overwrite', '-o', '--display-nodes', '-d', '--hf', '-H', '--ip', '-I', '--yes', '-y'] or arg.startswith('--hf:') or arg.startswith('--ip:'):
            # Known flags without arguments
            i += 1
        elif arg.startswith('-') and not arg.isdigit():
            # Unknown option
            unknown_args.append(arg)
            i += 1
        else:
            i += 1
    
    # Check for unknown arguments
    if unknown_args:
        colored_print("Error: Unknown argument(s): {}".format(', '.join(unknown_args)), Colors.RED)
        print("Run '{} --help' for usage information.".format(sys.argv[0]))
        sys.exit(1)
    
    # Silent mode validation: requires username and password
    if silent_mode:
        if not username or not password:
            colored_print("Error: Silent mode (-y/--yes) requires -u USERNAME and -p PASSWORD", Colors.RED)
            sys.exit(1)
        generate_maps = True  # Auto-generate maps in silent mode
    
    # Merge mode is default; use --overwrite to disable
    merge_mode = '--overwrite' not in sys.argv and '-o' not in sys.argv
    
    # Create crawler with specified crawl mode and exclusions
    crawler = NodeCrawler(max_hops=max_hops, username=username, password=password, verbose=verbose, notify_url=notify_url, log_file=log_file, debug_log=debug_log, resume=resume, crawl_mode=crawl_mode, exclude=exclude_nodes, hf_mode=hf_mode, ip_mode=ip_mode, op_timeout=op_timeout, resolve_locations=resolve_locations, auto_ignore=auto_ignore)
    crawler.silent_mode = silent_mode  # Set silent mode for skipping interactive prompts
    
    # Set resume file if specified
    if resume_file:
        crawler.resume_file = resume_file
    
    # Display excluded nodes if any
    if exclude_nodes:
        print("Excluding nodes: {}".format(', '.join(sorted(exclude_nodes))))
    
    # Display logging status
    if log_file or debug_log:
        log_status = []
        if log_file:
            log_status.append("telnet -> {}".format(log_file))
        if debug_log:
            log_status.append("debug -> {}".format(debug_log))
        print("Logging: {}".format(", ".join(log_status)))
    
    # Handle merge-only mode (no crawling, just merge files)
    if merge_files and not resume and not start_node and max_hops == 10:
        print("Merge mode: Combining data from {} file(s)".format(len(merge_files)))
        
        # Load existing data if available
        if merge_mode:
            existing = crawler._load_existing_data('nodemap.json')
            if existing and 'nodes' in existing:
                crawler.nodes = existing['nodes']
                crawler.connections = existing.get('connections', [])
                # Reload intermittent_links from serialized format
                intermittent_serialized = existing.get('intermittent_links', {})
                for key_str, attempts in intermittent_serialized.items():
                    if '>' in key_str:
                        from_call, to_call = key_str.split('>', 1)
                        crawler.intermittent_links[(from_call, to_call)] = attempts
                print("Loaded {} existing nodes".format(len(crawler.nodes)))
        
        # Merge each file
        total_merged = 0
        for merge_file in merge_files:
            result = crawler.merge_external_data(merge_file)
            if result > 0:
                total_merged += result
        
        if total_merged > 0:
            # Export merged results
            crawler.export_json(merge=merge_mode)
            crawler.export_csv()
            print("\nMerge complete! Combined data from {} files.".format(len(merge_files)))
            print("Total nodes: {}".format(len(crawler.nodes)))
            print("Total connections: {}".format(len(crawler.connections)))
        else:
            print("No data was merged.")
        
        return
    
    # Only require local callsign if no start_node provided and not in resume mode
    if not start_node and not crawler.callsign and not resume:
        print("\nError: Could not determine local node callsign.")
        print("Ensure NODECALL is set in bpq32.cfg or provide a starting callsign.")
        print("\nUsage: {} [MAX_HOPS] [START_NODE] [OPTIONS]".format(sys.argv[0]))
        print("  MAX_HOPS: Maximum traversal depth (default: 4, auto-set to 0 with --callsign)")
        print("  START_NODE: Callsign to begin crawl (default: local node)")
        print("  --overwrite, -o: Overwrite existing data (default: merge)")
        print("  --user USERNAME: Telnet login username (default: NODECALL)")
        print("  --pass PASSWORD: Telnet login password (default: empty)")
        print("\nExamples:")
        print("  {} 5              # Crawl 5 hops, merge with existing".format(sys.argv[0]))
        print("  {} 10 WS1EC       # Crawl from WS1EC, merge results".format(sys.argv[0]))
        print("  {} 5 --overwrite  # Crawl and completely replace data".format(sys.argv[0]))
        print("  {} 10 --user KC1JMH --pass ****  # With authentication".format(sys.argv[0]))
        print("\nInstallation:")
        print("  Place in ~/utilities/ or ~/apps/ adjacent to ~/linbpq/")
        sys.exit(1)
    
    if resume:
        print("Mode: Resume (crawling unexplored nodes from nodemap.json)")
    elif merge_mode:
        print("Mode: Merge (updating existing nodemap.json)")
    else:
        print("Mode: Overwrite (replacing all data)")
    
    # Display crawl mode
    mode_descriptions = {
        'update': 'Update (skip visited nodes)',
        'reaudit': 'Reaudit (re-crawl all nodes)',
        'new-only': 'New-Only (queue unexplored neighbors from nodemap.json)'
    }
    print("Crawl Mode: {}".format(mode_descriptions.get(crawl_mode, crawl_mode)))
    
    # Crawl network
    try:
        # If user forced specific SSIDs, pre-populate the map
        # Save it to restore after resume (which rebuilds map from JSON)
        cli_forced_ssids = {}
        forced_target = None  # Target node to crawl (for --callsign)
        
        # Handle --force-ssid arguments (multiple allowed)
        if forced_ssids:
            for base_call, full_ssid in forced_ssids.items():
                crawler.netrom_ssid_map[base_call] = full_ssid
                crawler.ssid_source[base_call] = ('cli', time.time())
                cli_forced_ssids[base_call] = full_ssid
            colored_print("Forcing {} SSID mappings (will update map for future crawls)".format(len(forced_ssids)), Colors.GREEN)
        
        # Handle --callsign argument (single, legacy)
        if forced_ssid:
            base_call = forced_ssid.split('-')[0]
            crawler.netrom_ssid_map[base_call] = forced_ssid
            crawler.ssid_source[base_call] = ('cli', time.time())
            cli_forced_ssids[base_call] = forced_ssid
            colored_print("Forcing SSID: {} (will update SSID map for future crawls)".format(forced_ssid), Colors.GREEN)
            # --callsign means crawl TO this specific node only (target-only mode)
            # Always set forced_target - works with or without start_node
            forced_target = base_call
        
        # Pass CLI-forced SSIDs to crawler so they survive resume
        crawler.cli_forced_ssids = cli_forced_ssids
        
        crawler.crawl_network(start_node=start_node, forced_target=forced_target)
        
        # Export results
        crawler.export_json(merge=merge_mode)
        crawler.export_csv()
        
        # Merge additional files if specified
        if merge_files:
            print("\\nMerging additional data files...")
            for merge_file in merge_files:
                result = crawler.merge_external_data(merge_file)
                if result > 0:
                    colored_print("Successfully merged {} nodes from {}".format(result, merge_file), Colors.GREEN)
            
            # Re-export with merged data
            crawler.export_json(merge=merge_mode)
            crawler.export_csv()
            print("Final merged data exported.")
        
        print("\nNetwork map complete!")
        print("Nodes discovered: {}".format(len(crawler.nodes)))
        print("Connections found: {}".format(len(crawler.connections)))
        
        # Prompt to generate maps (after seeing results)
        html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
        if os.path.isfile(html_script) and not silent_mode:
            print("")
            try:
                response = input("Generate HTML/SVG maps? (Y/n): ").strip().lower()
                if response == '' or response == 'y' or response == 'yes':
                    generate_maps = True
            except (KeyboardInterrupt, EOFError):
                print("")
                print("Skipping map generation")
        
        # Review quarantined callsigns and fill in missing gridsquares.
        # Both read the exported map, so they see every node in it - not just
        # the handful this run happened to re-crawl.
        if not silent_mode:
            try:
                review_quarantined_callsigns(crawler)
                if prompt_for_missing_grids(crawler):
                    # Re-export so the manual entries land in nodemap.json
                    # immediately rather than waiting for the next crawl.
                    crawler.export_json(merge=merge_mode)
                    crawler.export_csv()
            except (KeyboardInterrupt, EOFError):
                print("")
                print("Skipping review.")

        # Generate HTML/SVG maps if user opted in
        if generate_maps:
            print("\nGenerating maps...")
            html_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodemap-html.py')
            try:
                import subprocess
                result = subprocess.call(['python3', html_script, '--all'])
                if result == 0:
                    colored_print("Maps generated successfully!", Colors.GREEN)
                else:
                    colored_print("Warning: Map generation exited with code {}".format(result), Colors.YELLOW)
            except Exception as e:
                colored_print("Error generating maps: {}".format(e), Colors.RED)
        
        # Notify successful completion
        crawler._send_notification("Successfully crawled {} nodes!".format(len(crawler.nodes)))
        
        # Close log file if open
        if crawler.log_handle:
            crawler.log_handle.close()
        
    except KeyboardInterrupt:
        print("\n\nCrawl interrupted by user.")
        print("Partial results:")
        print("  Nodes: {}".format(len(crawler.nodes)))
        print("  Connections: {}".format(len(crawler.connections)))
        
        # Export partial results
        if crawler.nodes:
            partial_name = 'nodemap_partial_{}'.format(start_node) if start_node else 'nodemap_partial'
            crawler.export_json('{}.json'.format(partial_name))
            crawler.export_csv('{}.csv'.format(partial_name))
        
        # Close log file if open
        if crawler.log_handle:
            crawler.log_handle.close()


if __name__ == '__main__':
    main()
