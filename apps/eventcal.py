#!/usr/bin/env python3
"""
Club Calendar - Display ham radio club events from iCal feed
Version: 1.0

Fetches and displays upcoming events from an iCalendar (.ics) URL.
Designed for BPQ32 packet radio networks with ASCII-only output.
Internet-optional with graceful offline fallback.

Usage:
    eventcal.py                    # Interactive menu
    eventcal.py --help             # Show help
    eventcal.py --config <path>    # Use custom config file

BPQ32 APPLICATION line:
    APPLICATION 6,CALENDAR,C 9 HOST # NOCALL K,CALLSIGN,FLAGS
"""

import sys
import os
import json
import socket
import subprocess
import time
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
import re


VERSION = "2.0"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "eventcal.conf")


def show_logo():
    """Display ASCII art logo"""
    logo = r"""
           _                _            
  ___ __ _| | ___ _ __   __| | __ _ _ __ 
 / __/ _` | |/ _ \ '_ \ / _` |/ _` | '__|
| (_| (_| | |  __/ | | | (_| | (_| | |   
 \___\__,_|_|\___|_| |_|\__,_|\__,_|_|   
"""
    print(logo)


def is_internet_available():
    """Check if internet is available via DNS lookup"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def get_local_timezone():
    """Get local timezone abbreviation"""
    try:
        # Try reading /etc/timezone
        if os.path.exists('/etc/timezone'):
            with open('/etc/timezone', 'r') as f:
                tz = f.read().strip()
                # Convert to abbreviation
                tz_map = {
                    'America/New_York': 'ET',
                    'America/Chicago': 'CT',
                    'America/Denver': 'MT',
                    'America/Los_Angeles': 'PT',
                    'America/Phoenix': 'MST',
                    'America/Anchorage': 'AKT',
                    'Pacific/Honolulu': 'HST'
                }
                return tz_map.get(tz, tz.split('/')[-1])
        
        # Try using date command
        result = subprocess.check_output(['date', '+%Z'], stderr=subprocess.DEVNULL)
        return result.decode('utf-8').strip()
    except Exception:
        return None


def utc_to_local(dt):
    """Convert UTC datetime to local time"""
    # Convert datetime to timestamp
    timestamp = dt.timestamp() if hasattr(dt, 'timestamp') else time.mktime(dt.timetuple())
    # Convert to local time
    local_time = time.localtime(timestamp)
    return datetime.fromtimestamp(time.mktime(local_time))


def check_for_app_update(current_version, script_name):
    """Check GitHub for newer version and auto-update if available"""
    try:
        url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        req = Request(url, headers={"User-Agent": "BPQ-Apps-Updater"})
        response = urlopen(req, timeout=3)
        remote_content = response.read().decode('utf-8')
        
        # Extract version from remote file
        version_match = re.search(r'Version:\s*([\d.]+)', remote_content)
        if version_match:
            remote_version = version_match.group(1)
            if compare_versions(remote_version, current_version) > 0:
                # Atomic update with temp file
                temp_file = script_name + ".tmp"
                try:
                    with open(temp_file, 'w') as f:
                        f.write(remote_content)
                    
                    # Preserve executable permission
                    if os.path.exists(script_name):
                        os.chmod(temp_file, os.stat(script_name).st_mode)
                    
                    os.replace(temp_file, script_name)
                    print("Updated to version {}".format(remote_version))
                except Exception:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
    except Exception:
        pass  # Silent failure on network issues


def compare_versions(v1, v2):
    """Compare version strings. Returns: 1 if v1>v2, -1 if v1<v2, 0 if equal"""
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    return 0


def load_config(config_path):
    """Load calendar URL from config file"""
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            return data.get('ical_url')
    except Exception:
        return None


def save_config(config_path, ical_url):
    """Save calendar URL to config file"""
    try:
        with open(config_path, 'w') as f:
            json.dump({'ical_url': ical_url}, f, indent=2)
        return True
    except Exception:
        return False


def fetch_ical(url):
    """Fetch iCalendar data from URL with timeout"""
    try:
        req = Request(url, headers={"User-Agent": "BPQ-Calendar/1.0"})
        response = urlopen(req, timeout=5)
        return response.read().decode('utf-8', errors='ignore')
    except URLError:
        return None


def parse_ical_date(date_str):
    """Parse iCalendar date/datetime string to datetime object
    Returns: (datetime_obj, timezone_str) or (datetime_obj, None)
    """
    tz = None
    
    # Extract TZID parameter if present (e.g., TZID=America/New_York:20260123)
    if ';' in date_str and ':' in date_str:
        params_part = date_str.split(':', 1)[0]
        if 'TZID=' in params_part:
            tz = params_part.split('TZID=')[1].split(';')[0]
            # Shorten common US timezones
            tz_map = {
                'America/New_York': 'ET',
                'America/Chicago': 'CT',
                'America/Denver': 'MT',
                'America/Los_Angeles': 'PT',
                'America/Phoenix': 'MST',
                'America/Anchorage': 'AKT',
                'Pacific/Honolulu': 'HST'
            }
            tz = tz_map.get(tz, tz.split('/')[-1])
        date_str = date_str.split(':', 1)[1]
    elif ':' in date_str and '=' in date_str.split(':', 1)[0]:
        date_str = date_str.split(':', 1)[1]
    
    # Try parsing as datetime with time
    for fmt in ['%Y%m%dT%H%M%S', '%Y%m%dT%H%M%SZ', '%Y%m%d']:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Z suffix means UTC
            if date_str.endswith('Z'):
                tz = 'UTC'
            return (dt, tz)
        except ValueError:
            continue
    
    return (None, None)


def expand_rrule(event, rrule_str, until_date):
    """Expand a recurring event based on RRULE.
    Returns list of expanded events up to until_date.
    Supports: FREQ=MONTHLY;BYDAY=nTH (nth weekday of month)
    """
    expanded = []
    dtstart = event.get('dtstart')
    dtend = event.get('dtend')
    duration = (dtend - dtstart) if dtend else timedelta(hours=2)
    
    # Parse RRULE components
    parts = {}
    for part in rrule_str.split(';'):
        if '=' in part:
            k, v = part.split('=', 1)
            parts[k] = v
    
    freq = parts.get('FREQ', '')
    byday = parts.get('BYDAY', '')
    until_str = parts.get('UNTIL', '')
    
    # Parse UNTIL date if present
    rrule_until = None
    if until_str:
        try:
            if 'T' in until_str:
                rrule_until = datetime.strptime(until_str[:15], '%Y%m%dT%H%M%S')
            else:
                rrule_until = datetime.strptime(until_str[:8], '%Y%m%d')
        except ValueError:
            pass
    
    # Only expand MONTHLY with BYDAY (e.g., "2TH" = 2nd Thursday)
    if freq != 'MONTHLY' or not byday:
        return [event]  # Can't expand, return original
    
    # Parse BYDAY: "2TH" -> week_num=2, day="TH"
    import re as re_module
    match = re_module.match(r'(-?\d)?(MO|TU|WE|TH|FR|SA|SU)', byday)
    if not match:
        return [event]
    
    week_num = int(match.group(1)) if match.group(1) else 1
    day_abbr = match.group(2)
    day_map = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
    target_weekday = day_map.get(day_abbr, 0)
    
    # Start from event's original date and generate instances
    current_date = dtstart
    
    # Generate for 2 years back and 1 year forward from today
    today = datetime.now()
    start_window = today - timedelta(days=730)  # 2 years back
    end_window = min(until_date, today + timedelta(days=365))  # 1 year forward
    if rrule_until and rrule_until < end_window:
        end_window = rrule_until
    
    # Start from beginning of start_window month
    current_month = datetime(start_window.year, start_window.month, 1, 
                             dtstart.hour, dtstart.minute, dtstart.second)
    
    while current_month <= end_window:
        # Find the nth weekday of current month
        if week_num > 0:
            # Positive: count from start of month
            first_of_month = datetime(current_month.year, current_month.month, 1,
                                     dtstart.hour, dtstart.minute, dtstart.second)
            # Find first target weekday
            days_until = (target_weekday - first_of_month.weekday()) % 7
            first_target = first_of_month + timedelta(days=days_until)
            # Add weeks to get to nth occurrence
            target_date = first_target + timedelta(weeks=week_num - 1)
        else:
            # Negative: count from end of month (e.g., -1 = last)
            # Find last day of month
            if current_month.month == 12:
                next_month = datetime(current_month.year + 1, 1, 1)
            else:
                next_month = datetime(current_month.year, current_month.month + 1, 1)
            last_of_month = next_month - timedelta(days=1)
            # Find last target weekday
            days_back = (last_of_month.weekday() - target_weekday) % 7
            last_target = last_of_month - timedelta(days=days_back)
            # Subtract weeks for earlier occurrences
            target_date = last_target + timedelta(weeks=week_num + 1)
            target_date = target_date.replace(hour=dtstart.hour, minute=dtstart.minute,
                                              second=dtstart.second)
        
        # Check if this instance is within our window
        if start_window <= target_date <= end_window:
            new_event = event.copy()
            new_event['dtstart'] = target_date
            if dtend:
                new_event['dtend'] = target_date + duration
            new_event['is_recurring'] = True
            expanded.append(new_event)
        
        # Move to next month
        if current_month.month == 12:
            current_month = datetime(current_month.year + 1, 1, 1,
                                    dtstart.hour, dtstart.minute, dtstart.second)
        else:
            current_month = datetime(current_month.year, current_month.month + 1, 1,
                                    dtstart.hour, dtstart.minute, dtstart.second)
    
    return expanded if expanded else [event]


def parse_ical(ical_data):
    """Parse iCalendar data and extract events"""
    events = []
    current_event = {}
    in_event = False
    
    # Handle iCal line continuations (lines starting with space/tab)
    raw_lines = ical_data.split('\n')
    lines = []
    for raw_line in raw_lines:
        # Line continuation: starts with space or tab
        if raw_line.startswith(' ') or raw_line.startswith('\t'):
            if lines:
                lines[-1] += raw_line[1:]  # Append without the leading whitespace
        else:
            lines.append(raw_line)
    
    # Expansion window: 2 years back to 1 year forward
    until_date = datetime.now() + timedelta(days=365)
    
    for line in lines:
        line = line.strip()
        
        if line == 'BEGIN:VEVENT':
            in_event = True
            current_event = {}
        elif line == 'END:VEVENT':
            if current_event.get('dtstart') and current_event.get('summary'):
                # Check for RRULE and expand recurring events
                if current_event.get('rrule'):
                    expanded = expand_rrule(current_event, current_event['rrule'], until_date)
                    events.extend(expanded)
                else:
                    events.append(current_event)
            in_event = False
            current_event = {}
        elif in_event and ':' in line:
            key, value = line.split(':', 1)
            key_base = key.split(';')[0]  # Remove parameters
            
            if key_base == 'DTSTART':
                dt, tz = parse_ical_date(line)  # Pass full line for timezone parsing
                if dt:
                    current_event['dtstart'] = dt
                    if tz:
                        current_event['timezone'] = tz
            elif key_base == 'DTEND':
                dt, tz = parse_ical_date(line)
                if dt:
                    current_event['dtend'] = dt
            elif key_base == 'RRULE':
                current_event['rrule'] = value
            elif key_base == 'SUMMARY':
                current_event['summary'] = value.replace('\\,', ',').replace('\\n', ' ')
            elif key_base == 'DESCRIPTION':
                # Preserve newlines in description
                current_event['description'] = value.replace('\\,', ',')
            elif key_base == 'LOCATION':
                current_event['location'] = value.replace('\\,', ',').replace('\\n', ' ')
    
    # Sort by start date
    events.sort(key=lambda x: x.get('dtstart', datetime.max))
    
    return events


def format_date(dt):
    """Format datetime for display"""
    return dt.strftime('%Y-%m-%d %H:%M')


def format_date_short(dt):
    """Format date for display (no time)"""
    return dt.strftime('%Y-%m-%d')


def wrap_text(text, width):
    """Wrap text to specified width, preserving words"""
    if not text:
        return []
    
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word)
        if current_length + word_length + len(current_line) <= width:
            current_line.append(word)
            current_length += word_length
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def get_terminal_width():
    """Get terminal width with fallback"""
    try:
        return os.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        return 40


def clean_location(location):
    """Strip zipcode and country from location for cleaner display"""
    if not location:
        return location
    
    # Strip country (USA, United States, etc.)
    location = re.sub(r',\s*(USA|United States|US)\s*$', '', location, flags=re.IGNORECASE)
    # Strip zipcode (5 digits or 5+4 format)
    location = re.sub(r',?\s*\d{5}(-\d{4})?\s*,?', ',', location)
    # Clean up any trailing/leading commas or spaces
    location = re.sub(r',\s*$', '', location)
    location = re.sub(r'^\s*,', '', location)
    return location.strip()


def strip_html(text):
    """Remove HTML tags from text"""
    if not text:
        return text
    # Convert escaped newlines to actual newlines
    text = text.replace('\\n', '\n')
    # Replace <br>, <br/>, <br />, <p>, </p> with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?p>', '\n', text, flags=re.IGNORECASE)
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    # Clean up multiple consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def display_events(events, show_all=False, page=0, page_size=5, start_at_today=False):
    """Display events in formatted list with pagination
    Returns: (action, event_num, event_list, actual_page)
    """
    width = get_terminal_width()
    now = datetime.now()
    today = now.date()
    local_tz = get_local_timezone()
    
    # Filter events
    if show_all:
        # Show ALL events (no date filter) - sorted by date
        display_list = events
        
        # Find the page containing today's date if starting fresh
        if start_at_today and page == 0:
            for idx, e in enumerate(display_list):
                event_date = e.get('dtstart')
                if event_date and event_date.date() >= today:
                    page = idx // page_size
                    break
        
        print("\nAll Events:")
    else:
        # Filter to upcoming events (today through next 90 days)
        future_cutoff = today + timedelta(days=90)
        display_list = []
        for e in events:
            event_date = e.get('dtstart')
            if event_date:
                event_day = event_date.date()
                if today <= event_day <= future_cutoff:
                    display_list.append(e)
        print("\nUpcoming Events (next 90 days):")
    
    if not display_list:
        print("No events found.")
        return (None, None, None, page)
    
    # Calculate page bounds
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(display_list))
    page_events = display_list[start_idx:end_idx]
    
    print("-" * 40)
    
    # Find the index of the next upcoming event (for marker)
    next_event_idx = None
    for i, e in enumerate(display_list):
        event_date = e.get('dtstart')
        if event_date and event_date.date() >= today:
            next_event_idx = i
            break
    
    for idx, event in enumerate(page_events, start_idx + 1):
        dt = event.get('dtstart')
        summary = event.get('summary', 'Untitled Event')
        location = event.get('location', '')
        timezone = event.get('timezone', '')
        
        # Add marker for next upcoming event
        actual_idx = start_idx + (idx - start_idx - 1)
        marker = " <" if show_all and actual_idx == next_event_idx else ""
        
        # Display title first
        print("\n{}. {}{}".format(idx, summary, marker))
        
        # Display location if present
        if location:
            clean_loc = clean_location(location)
            if clean_loc:
                loc_lines = wrap_text("Location: {}".format(clean_loc), width - 3)
                for line in loc_lines:
                    print("   {}".format(line))
        
        # Display dates with timezone conversion
        utc_line = None
        if event.get('dtend') and event['dtend'].date() != dt.date():
            # Multi-day event
            if dt.hour == 0 and dt.minute == 0:
                # All-day multi-day
                date_str = "   {} - {}".format(format_date_short(dt), format_date_short(event['dtend']))
            else:
                # Timed multi-day
                if timezone == 'UTC' and local_tz:
                    local_dt = utc_to_local(dt)
                    local_end = utc_to_local(event['dtend'])
                    date_str = "   {} - {} {}".format(
                        format_date(local_dt), format_date(local_end), local_tz
                    )
                    utc_line = "   {} - {} UTC".format(
                        format_date(dt), format_date(event['dtend'])
                    )
                else:
                    date_str = "   {} - {}".format(format_date(dt), format_date(event['dtend']))
                    if timezone:
                        date_str = "{} {}".format(date_str, timezone)
        elif dt.hour == 0 and dt.minute == 0:
            # All-day event
            date_str = "   {}".format(format_date_short(dt))
        else:
            # Timed event
            if timezone == 'UTC' and local_tz:
                local_dt = utc_to_local(dt)
                date_str = "   {} {}".format(format_date(local_dt), local_tz)
                utc_line = "   {} UTC".format(format_date(dt))
            else:
                date_str = "   {}".format(format_date(dt))
                if timezone:
                    date_str = "{} {}".format(date_str, timezone)
        
        print(date_str)
        if utc_line:
            print(utc_line)
    
    print("-" * 40)
    
    # Show pagination controls
    if show_all:
        has_next = end_idx < len(display_list)
        has_prev = page > 0
        total_pages = (len(display_list) + page_size - 1) // page_size
        
        print("Page {} of {}".format(page + 1, total_pages))
        prompt_parts = []
        prompt_parts.append("#)Detail")
        if has_prev:
            prompt_parts.append("P)rev")
        if has_next:
            prompt_parts.append("N)ext")
        prompt_parts.append("B)ack")
        prompt_parts.append("Q)uit")
        
        try:
            response = input("{} :> ".format(" ".join(prompt_parts))).strip().upper()
            if response.isdigit():
                return ('detail', int(response), display_list, page)
            elif response == 'N' and has_next:
                return ('next', None, None, page)
            elif response == 'P' and has_prev:
                return ('prev', None, None, page)
            elif response == 'B':
                return ('back', None, None, page)
            elif response == 'Q':
                return ('quit', None, None, page)
        except (EOFError, KeyboardInterrupt):
            return ('back', None, None, page)
    else:
        # Main upcoming view - allow event selection
        print("")
        try:
            response = input("#)Detail M)ore A)bout Q)uit :> ").strip().upper()
            if response.isdigit():
                return ('detail', int(response), display_list, page)
            elif response == 'M':
                return ('more', None, None, page)
            elif response == 'A':
                return ('about', None, None, page)
            elif response == 'Q':
                return ('quit', None, None, page)
        except (EOFError, KeyboardInterrupt):
            return ('quit', None, None, page)
    
    return (None, None, None, page)


def show_about():
    """Display about information"""
    width = get_terminal_width()
    print("\n" + "-" * 40)
    print("CLUB CALENDAR v{}".format(VERSION))
    print("-" * 40)
    
    about_text = (
        "Displays upcoming club events from iCalendar feeds. "
        "Fetches event data from online .ics files and presents "
        "upcoming meetings, nets, and activities in an easy-to-read "
        "format optimized for packet radio bandwidth."
    )
    
    lines = wrap_text(about_text, width)
    for line in lines:
        print(line)
    
    print("\nPart of BPQ-Apps suite")
    print("github.com/bradbrownjr/bpq-apps")
    print("-" * 40)


def show_event_detail(event):
    """Display detailed information for a single event"""
    width = get_terminal_width()
    local_tz = get_local_timezone()
    
    dt = event.get('dtstart')
    summary = event.get('summary', 'Untitled Event')
    location = event.get('location', '')
    description = event.get('description', '')
    timezone = event.get('timezone', '')
    
    print("\n" + "-" * 40)
    print(summary)
    print("-" * 40)
    
    # Display location
    if location:
        clean_loc = clean_location(location)
        if clean_loc:
            print("Location: {}".format(clean_loc))
            print("")
    
    # Display dates with timezone
    utc_line = None
    if event.get('dtend') and event['dtend'].date() != dt.date():
        # Multi-day event
        if dt.hour == 0 and dt.minute == 0:
            date_str = "{} - {}".format(format_date_short(dt), format_date_short(event['dtend']))
        else:
            if timezone == 'UTC' and local_tz:
                local_dt = utc_to_local(dt)
                local_end = utc_to_local(event['dtend'])
                date_str = "{} - {} {}".format(
                    format_date(local_dt), format_date(local_end), local_tz
                )
                utc_line = "{} - {} UTC".format(
                    format_date(dt), format_date(event['dtend'])
                )
            else:
                date_str = "{} - {}".format(format_date(dt), format_date(event['dtend']))
                if timezone:
                    date_str = "{} {}".format(date_str, timezone)
    elif dt.hour == 0 and dt.minute == 0:
        date_str = format_date_short(dt)
    else:
        if timezone == 'UTC' and local_tz:
            local_dt = utc_to_local(dt)
            date_str = "{} {}".format(format_date(local_dt), local_tz)
            utc_line = "{} UTC".format(format_date(dt))
        else:
            date_str = format_date(dt)
            if timezone:
                date_str = "{} {}".format(date_str, timezone)
    
    print(date_str)
    if utc_line:
        print(utc_line)
    
    # Display description
    if description:
        print("")
        # Strip HTML tags and convert escaped newlines
        clean_desc = strip_html(description)
        if clean_desc:
            # Handle multi-paragraph text
            paragraphs = clean_desc.split('\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    para_lines = wrap_text(para, width)
                    for line in para_lines:
                        print(line)
                else:
                    print("")  # Preserve blank lines between paragraphs
    
    print("-" * 40)
    try:
        input("Press ENTER to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def main_menu(events):
    """Display main menu and handle user input"""
    
    while True:
        # Display upcoming events by default
        action, event_num, event_list, _ = display_events(events, show_all=False, page=0)
        
        if action == 'detail' and event_num is not None and event_list:
            if 1 <= event_num <= len(event_list):
                show_event_detail(event_list[event_num - 1])
            # After showing detail, loop back to show upcoming events again
        elif action == 'more':
            # Navigate through all events, starting at today
            page = 0
            first_view = True
            while True:
                action2, event_num2, event_list2, actual_page = display_events(
                    events, show_all=True, page=page, start_at_today=first_view
                )
                page = actual_page  # Track actual page (may have jumped to today)
                first_view = False
                if action2 == 'next':
                    page += 1
                elif action2 == 'prev':
                    page = max(0, page - 1)
                elif action2 == 'detail' and event_num2 is not None and event_list2:
                    if 1 <= event_num2 <= len(event_list2):
                        show_event_detail(event_list2[event_num2 - 1])
                    else:
                        print("Invalid event number.")
                elif action2 == 'back':
                    break
                elif action2 == 'quit':
                    print("Exiting...")
                    sys.exit(0)
        elif action == 'about':
            show_about()
        elif action == 'quit':
            print("Exiting...")
            sys.exit(0)


def prompt_for_url():
    """Prompt user for iCalendar URL"""
    print("\n" + "-" * 40)
    print("Configuration Required")
    print("-" * 40)
    print("Enter the URL to your club's iCalendar")
    print("(.ics) file. Example:")
    print("https://example.com/calendar.ics")
    print("\nPress Q to quit.")
    print("-" * 40)
    
    while True:
        try:
            url = input("iCal URL :> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            sys.exit(0)
        
        if url.upper() == 'Q':
            print("Exiting...")
            sys.exit(0)
        
        if url.startswith('http://') or url.startswith('https://'):
            return url
        else:
            print("Invalid URL. Must start with http:// or https://")


def main():
    """Main application entry point"""
    # Handle command-line arguments
    config_path = CONFIG_FILE
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', '/?']:
            print(__doc__)
            sys.exit(0)
        elif sys.argv[1] in ['-c', '--config'] and len(sys.argv) > 2:
            config_path = sys.argv[2]
    
    # Check for updates
    check_for_app_update(VERSION, "eventcal.py")
    
    # Display logo and header
    show_logo()
    print("CLUB CALENDAR v{} - Event Listings".format(VERSION))
    
    # Load or prompt for configuration
    ical_url = load_config(config_path)
    
    if not ical_url:
        ical_url = prompt_for_url()
        if save_config(config_path, ical_url):
            print("Configuration saved.")
        else:
            print("Warning: Could not save configuration.")
    
    # Main loop
    print("\nFetching calendar data...")
    
    ical_data = fetch_ical(ical_url)
    
    if not ical_data:
        if is_internet_available():
            print("Error: Could not fetch calendar.")
            print("Check URL in {}".format(config_path))
        else:
            print("Internet appears to be unavailable.")
            print("Try again later.")
        sys.exit(1)
    
    events = parse_ical(ical_data)
    
    if not events:
        print("No events found in calendar.")
        sys.exit(0)
    
    print("Loaded {} event(s).".format(len(events)))
    
    # Display upcoming events by default
    display_events(events, show_all=False)
    
    # Then show menu
    main_menu(events)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        if is_internet_available():
            print("Error: {}".format(str(e)))
        else:
            print("Internet appears to be unavailable.")
            print("Try again later.")
        sys.exit(1)
