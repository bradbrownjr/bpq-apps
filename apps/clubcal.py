#!/usr/bin/env python3
"""
Club Calendar - Display ham radio club events from iCal feed
Version: 1.0

Fetches and displays upcoming events from an iCalendar (.ics) URL.
Designed for BPQ32 packet radio networks with ASCII-only output.
Internet-optional with graceful offline fallback.

Usage:
    clubcal.py                    # Interactive menu
    clubcal.py --help             # Show help
    clubcal.py --config <path>    # Use custom config file

BPQ32 APPLICATION line:
    APPLICATION 6,CALENDAR,C 9 HOST # NOCALL K,CALLSIGN,FLAGS
"""

import sys
import os
import json
import socket
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
import re


VERSION = "1.0"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "clubcal.conf")


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
    """Parse iCalendar date/datetime string to datetime object"""
    # Remove TZID parameter if present
    date_str = re.sub(r'^[^:]+:', '', date_str)
    
    # Try parsing as datetime with time
    for fmt in ['%Y%m%dT%H%M%S', '%Y%m%dT%H%M%SZ', '%Y%m%d']:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def parse_ical(ical_data):
    """Parse iCalendar data and extract events"""
    events = []
    current_event = {}
    in_event = False
    
    for line in ical_data.split('\n'):
        line = line.strip()
        
        if line == 'BEGIN:VEVENT':
            in_event = True
            current_event = {}
        elif line == 'END:VEVENT':
            if current_event.get('dtstart') and current_event.get('summary'):
                events.append(current_event)
            in_event = False
            current_event = {}
        elif in_event and ':' in line:
            key, value = line.split(':', 1)
            key = key.split(';')[0]  # Remove parameters
            
            if key == 'DTSTART':
                dt = parse_ical_date(value)
                if dt:
                    current_event['dtstart'] = dt
            elif key == 'DTEND':
                dt = parse_ical_date(value)
                if dt:
                    current_event['dtend'] = dt
            elif key == 'SUMMARY':
                current_event['summary'] = value.replace('\\,', ',').replace('\\n', ' ')
            elif key == 'DESCRIPTION':
                current_event['description'] = value.replace('\\,', ',').replace('\\n', ' ')
            elif key == 'LOCATION':
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


def display_events(events, show_all=False):
    """Display events in formatted list"""
    width = get_terminal_width()
    now = datetime.now()
    
    if show_all:
        display_list = events
        print("\nAll Events:")
    else:
        # Filter to upcoming events (next 90 days)
        future_cutoff = now + timedelta(days=90)
        display_list = [e for e in events if e.get('dtstart', datetime.min) >= now and e.get('dtstart', datetime.min) <= future_cutoff]
        print("\nUpcoming Events (next 90 days):")
    
    if not display_list:
        print("No events found.")
        return
    
    print("-" * 40)
    
    for idx, event in enumerate(display_list, 1):
        dt = event.get('dtstart')
        summary = event.get('summary', 'Untitled Event')
        location = event.get('location', '')
        description = event.get('description', '')
        
        # Display event header
        if event.get('dtend') and event['dtend'].date() != dt.date():
            # Multi-day event
            date_str = "{} - {}".format(format_date_short(dt), format_date_short(event['dtend']))
        elif dt.hour == 0 and dt.minute == 0:
            # All-day event
            date_str = format_date_short(dt)
        else:
            # Timed event
            date_str = format_date(dt)
        
        print("\n{}. {}".format(idx, date_str))
        
        # Wrap summary to terminal width
        summary_lines = wrap_text(summary, width - 3)
        for line in summary_lines:
            print("   {}".format(line))
        
        # Display location if present
        if location:
            loc_lines = wrap_text("Location: {}".format(location), width - 3)
            for line in loc_lines:
                print("   {}".format(line))
        
        # Display description if present
        if description:
            desc_lines = wrap_text(description, width - 3)
            for line in desc_lines:
                print("   {}".format(line))
    
    print("-" * 40)
    print("\nTotal: {} event(s)".format(len(display_list)))


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


def main_menu(events):
    """Display main menu and handle user input"""
    while True:
        print("\n" + "-" * 40)
        print("Main Menu:")
        print("1) View Upcoming Events")
        print("2) View All Events")
        print("3) Refresh Calendar")
        print("\nA) About  Q) Quit")
        print("-" * 40)
        
        try:
            choice = input("Menu: [1-3,A,Q] :> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            sys.exit(0)
        
        if choice == '1':
            display_events(events, show_all=False)
        elif choice == '2':
            display_events(events, show_all=True)
        elif choice == '3':
            return 'refresh'
        elif choice == 'A':
            show_about()
        elif choice == 'Q':
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice. Try again.")


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
    check_for_app_update(VERSION, "clubcal.py")
    
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
    while True:
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
        
        result = main_menu(events)
        
        if result != 'refresh':
            break


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
