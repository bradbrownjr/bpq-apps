#!/usr/bin/env python3
"""
Application Menu Launcher for BPQ Packet Radio
Displays categorized menu of installed applications and launches them.

Version: 1.6
Author: Brad Brown Jr (KC1JMH)
Date: 2026-02-05
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import re
from datetime import datetime
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

VERSION = "1.6"

def compare_versions(v1, v2):
    """Compare two version strings. Returns True if v2 > v1."""
    try:
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        return parts2 > parts1
    except (ValueError, AttributeError):
        return False

def check_for_app_update(current_version, script_name):
    """Check GitHub for updates and auto-download if available."""
    try:
        url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        response = urlopen(url, timeout=3)
        content = response.read()
        if sys.version_info[0] >= 3:
            content = content.decode('utf-8')
        
        for line in content.split('\n'):
            if line.strip().startswith('Version:'):
                latest_version = line.split('Version:')[1].strip()
                if compare_versions(current_version, latest_version):
                    print("Update available: v{} -> v{}".format(current_version, latest_version))
                    print("Downloading...")
                    sys.stdout.flush()
                    
                    script_path = os.path.abspath(__file__)
                    current_mode = os.stat(script_path).st_mode
                    
                    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(script_path))
                    try:
                        with os.fdopen(fd, 'wb') as f:
                            if sys.version_info[0] >= 3:
                                f.write(content.encode('utf-8'))
                            else:
                                f.write(content)
                        
                        os.chmod(temp_path, current_mode)
                        os.rename(temp_path, script_path)
                        print("Updated to v{}. Restarting...".format(latest_version))
                        print()
                        sys.stdout.flush()
                        os.execv(script_path, [script_path] + sys.argv[1:])
                    except Exception:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        raise
                break
    except Exception:
        pass

def get_terminal_width():
    """Get terminal width, fallback to 80 for non-TTY/inetd."""
    try:
        return shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        return 80

def extract_base_call(callsign):
    """Remove SSID from callsign."""
    if not callsign:
        return ""
    return callsign.split('-')[0]

def get_sysop_callsigns():
    """Parse bpq32.cfg to extract sysop callsigns."""
    config_paths = [
        "/home/ect/linbpq/bpq32.cfg",
        "/home/pi/linbpq/bpq32.cfg",
        os.path.expanduser("~/linbpq/bpq32.cfg")
    ]
    
    sysops = []
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    for line in f:
                        # Match USER=CALLSIGN,password,call,"",SYSOP
                        match = re.match(r'\s*USER=([A-Z0-9]+),.*,.*,.*,SYSOP', line, re.IGNORECASE)
                        if match:
                            sysops.append(match.group(1))
            except Exception:
                pass
            break
    
    return sysops

def is_sysop(callsign):
    """Check if callsign is a sysop."""
    if not callsign:
        return False
    base_call = extract_base_call(callsign).upper()
    sysops = get_sysop_callsigns()
    return base_call in sysops

def load_apps_config():
    """Load apps.json configuration file."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps.json")
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print("Error loading apps.json: {}".format(str(e)))
        return {"categories": {}}

def check_app_installed(executable_path):
    """Check if an app executable exists and is executable."""
    # If path is relative, make it relative to apps directory
    if not os.path.isabs(executable_path):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        executable_path = os.path.join(app_dir, executable_path)
    
    return os.path.isfile(executable_path) and os.access(executable_path, os.X_OK)

def get_installed_apps(config):
    """Filter apps.json to only show installed apps."""
    installed = {}
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    for category, apps in config.get("categories", {}).items():
        installed_in_category = []
        for app in apps:
            executable = app.get("executable", "")
            if not os.path.isabs(executable):
                executable = os.path.join(app_dir, executable)
            
            if check_app_installed(executable):
                app_copy = app.copy()
                app_copy["executable"] = executable  # Store absolute path
                installed_in_category.append(app_copy)
        
        if installed_in_category:
            installed[category] = installed_in_category
    
    return installed

def display_logo():
    """Display ASCII art logo."""
    logo = r"""
  __ _ _ __  _ __  ___
 / _` | '_ \| '_ \/ __|
| (_| | |_) | |_) \__ \
 \__,_| .__/| .__/|___/
      |_|   |_|
"""
    print(logo)

def display_menu(installed_apps, callsign):
    """Display categorized app menu."""
    print()
    print()
    display_logo()
    print("APPS v{} - Application Launcher".format(VERSION))
    if callsign:
        utc_time = datetime.utcnow().strftime("%H:%M")
        print("Welcome {}, the current time is {} UTC".format(extract_base_call(callsign), utc_time))
    print("-" * 67)
    print()
    
    if not installed_apps:
        print("No applications installed.")
        print()
        return {}
    
    # Build menu with numbered options
    app_index = {}
    
    # Define left and right column categories
    left_categories = ["Info", "Main", "Weather", "Tools"]
    right_categories = ["Reference", "Browsers"]
    
    # Build left column data (numbered first)
    option_num = 1
    left_lines = []
    for i, category in enumerate(left_categories):
        if category not in installed_apps:
            continue
        left_lines.append(("header", category + ":"))
        for app in installed_apps[category]:
            left_lines.append(("app", option_num, app))
            app_index[str(option_num)] = app
            option_num += 1
        # Add blank line between categories (except after last)
        if i < len(left_categories) - 1 and category in installed_apps:
            left_lines.append(("blank",))
    
    # Build right column data (numbered after left)
    right_lines = []
    for i, category in enumerate(right_categories):
        if category not in installed_apps:
            continue
        right_lines.append(("header", category + ":"))
        for app in installed_apps[category]:
            right_lines.append(("app", option_num, app))
            app_index[str(option_num)] = app
            option_num += 1
        # Add blank line between categories (except after last)
        if i < len(right_categories) - 1 and category in installed_apps:
            right_lines.append(("blank",))
    
    # Display both columns side by side
    max_rows = max(len(left_lines), len(right_lines))
    for row in range(max_rows):
        left_text = ""
        left_is_blank = False
        if row < len(left_lines):
            item = left_lines[row]
            if item[0] == "blank":
                left_is_blank = True
            elif item[0] == "header":
                left_text = item[1]
            else:
                num, app = item[1], item[2]
                left_text = "{:2}) {:9} {}".format(num, app["name"], app["description"])
        
        right_text = ""
        right_is_blank = False
        if row < len(right_lines):
            item = right_lines[row]
            if item[0] == "blank":
                right_is_blank = True
            elif item[0] == "header":
                right_text = item[1]
            else:
                num, app = item[1], item[2]
                right_text = "{:2}) {:9} {}".format(num, app["name"], app["description"])
        
        if right_text:
            print("{:<36}{}".format(left_text, right_text))
        elif left_is_blank and right_is_blank:
            print("")
        elif left_text or not left_is_blank:
            print(left_text)
    
    print("-" * 67)
    return app_index

def launch_app(app, callsign):
    """Launch selected app with callsign via CLI arg and env var."""
    executable = app["executable"]
    
    try:
        env = os.environ.copy()
        args = [executable]
        if callsign:
            env["BPQ_CALLSIGN"] = callsign
            args.extend(["--callsign", callsign])
        
        # Run fully interactive - child inherits stdin/stdout/stderr
        subprocess.call(args, env=env)
        
    except Exception as e:
        print("\nError launching {}: {}".format(app["name"], str(e)))
        print()

def show_about():
    """Display About screen with project info."""
    print()
    print()
    print("=" * 67)
    print("ABOUT BPQ-APPS")
    print("=" * 67)
    print()
    print("BPQ-Apps is a collection of packet radio applications designed for")
    print("AX.25 networks via LinBPQ BBS. These apps run on Raspberry Pi nodes")
    print("and provide enhanced functionality for emergency communications,")
    print("ham radio operators, and packet radio enthusiasts.")
    print()
    print("KEY FEATURES:")
    print()
    print("  * Self-Updating: Apps automatically check GitHub for updates")
    print("    and download new versions when available (3-second timeout)")
    print()
    print("  * Offline-First: All apps work without internet connectivity")
    print("    Apps cache data locally and gracefully handle network failures")
    print()
    print("  * Bandwidth Optimized: Designed for 1200 baud packet radio")
    print("    - ASCII text only (no Unicode, ANSI, or control codes)")
    print("    - 40-character width for mobile/older terminals")
    print("    - Compressed menus and prompts")
    print()
    print("  * Emergency Ready: Forms for ICS-213, radiograms, severe weather")
    print("    reports, ARRL bulletins, and MARS/SHARES formats")
    print()
    print("  * Open Source: MIT License, contributions welcome")
    print()
    print("REPOSITORY:")
    print()
    print("  https://github.com/bradbrownjr/bpq-apps")
    print()
    print("  - Full documentation and installation guide")
    print("  - Example configurations for BPQ32, inetd, services")
    print("  - Utilities for node management and monitoring")
    print()
    print("DEVELOPED BY:")
    print()
    print("  Brad Brown Jr, KC1JMH")
    print("  Wireless Society of Southern Maine - Emergency Comms Team")
    print()
    print("=" * 67)
    print()
    try:
        raw_input("Press Enter to continue...") if sys.version_info[0] < 3 else input("Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass

def get_system_stats():
    """Retrieve system statistics."""
    stats = {}
    
    try:
        # CPU Load Average
        with open('/proc/loadavg', 'r') as f:
            load = f.read().split()[:3]
            stats['load_avg'] = "{} {} {}".format(load[0], load[1], load[2])
    except Exception:
        stats['load_avg'] = "N/A"
    
    try:
        # Memory
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    meminfo[key] = int(value)
        
        total = meminfo.get('MemTotal', 0) / 1024
        available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0)) / 1024
        used = total - available
        stats['mem_total'] = "{:.1f}M".format(total)
        stats['mem_used'] = "{:.1f}M".format(used)
        stats['mem_percent'] = "{:.0f}%".format((used / total * 100) if total > 0 else 0)
    except Exception:
        stats['mem_total'] = "N/A"
        stats['mem_used'] = "N/A"
        stats['mem_percent'] = "N/A"
    
    try:
        # Disk Usage
        stat = os.statvfs('/')
        total = (stat.f_blocks * stat.f_frsize) / (1024**3)
        available = (stat.f_bavail * stat.f_frsize) / (1024**3)
        used = total - available
        stats['disk_total'] = "{:.1f}G".format(total)
        stats['disk_used'] = "{:.1f}G".format(used)
        stats['disk_percent'] = "{:.0f}%".format((used / total * 100) if total > 0 else 0)
    except Exception:
        stats['disk_total'] = "N/A"
        stats['disk_used'] = "N/A"
        stats['disk_percent'] = "N/A"
    
    try:
        # Uptime
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            if days > 0:
                stats['uptime'] = "{}d {}h {}m".format(days, hours, minutes)
            elif hours > 0:
                stats['uptime'] = "{}h {}m".format(hours, minutes)
            else:
                stats['uptime'] = "{}m".format(minutes)
    except Exception:
        stats['uptime'] = "N/A"
    
    # Process status
    try:
        linbpq_running = subprocess.call(['pgrep', '-x', 'linbpq'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0
        stats['linbpq'] = "Running" if linbpq_running else "Stopped"
    except Exception:
        stats['linbpq'] = "Unknown"
    
    try:
        direwolf_running = subprocess.call(['pgrep', '-x', 'direwolf'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0
        stats['direwolf'] = "Running" if direwolf_running else "Stopped"
    except Exception:
        stats['direwolf'] = "Unknown"
    
    return stats

def view_log_paginated(log_path, title):
    """View log file with pagination in reverse chronological order."""
    if not os.path.exists(log_path):
        print("Log file not found: {}".format(log_path))
        return
    
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            print("Log file is empty.")
            return
        
        # Start from end of file, show newest first (reverse order)
        page_size = 20
        total_lines = len(lines)
        end_idx = total_lines  # Start at the very end
        
        while True:
            print()
            print("=" * 67)
            print(title + " (Newest First)")
            print("=" * 67)
            print()
            
            start_idx = max(0, end_idx - page_size)
            
            # Display lines in REVERSE order (newest first)
            for i in range(end_idx - 1, start_idx - 1, -1):
                line = lines[i].rstrip()
                if len(line) > 65:
                    line = line[:62] + "..."
                print(line)
            
            print()
            print("-" * 67)
            print("Showing lines {}-{} of {} (newest first)".format(start_idx + 1, end_idx, total_lines))
            
            # O)lder goes back in time, N)ewer goes forward in time
            if start_idx > 0 and end_idx < total_lines:
                prompt = "[O)lder N)ewer Q)uit] :> "
            elif start_idx > 0:
                prompt = "[O)lder Q)uit] :> "
            elif end_idx < total_lines:
                prompt = "[N)ewer Q)uit] :> "
            else:
                prompt = "[Q)uit] :> "
            
            try:
                choice = (raw_input(prompt) if sys.version_info[0] < 3 else input(prompt)).strip().upper()
            except (EOFError, KeyboardInterrupt):
                break
            
            if choice == 'Q':
                break
            elif choice == 'O' and start_idx > 0:
                # Go back in time (older entries)
                end_idx = start_idx
            elif choice == 'N' and end_idx < total_lines:
                # Go forward in time (newer entries)
                end_idx = min(end_idx + page_size, total_lines)
    
    except Exception as e:
        print("Error reading log: {}".format(str(e)))

def list_available_apps_github():
    """Fetch list of available apps from GitHub."""
    try:
        url = "https://api.github.com/repos/bradbrownjr/bpq-apps/contents/apps"
        response = urlopen(url, timeout=5)
        content = response.read()
        if sys.version_info[0] >= 3:
            content = content.decode('utf-8')
        
        files = json.loads(content)
        python_apps = []
        for item in files:
            if item.get('type') == 'file' and item.get('name', '').endswith('.py'):
                name = item['name']
                if name not in ['__init__.py', 'config.py']:
                    python_apps.append({
                        'name': name,
                        'download_url': item.get('download_url', ''),
                        'size': item.get('size', 0)
                    })
        
        return sorted(python_apps, key=lambda x: x['name'])
    
    except Exception as e:
        print("Error fetching app list: {}".format(str(e)))
        return []

def install_app_from_github(app_info):
    """Download and install an app from GitHub."""
    try:
        app_name = app_info['name']
        url = app_info['download_url']
        
        print("Downloading {}...".format(app_name))
        sys.stdout.flush()
        
        response = urlopen(url, timeout=10)
        content = response.read()
        
        app_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(app_dir, app_name)
        
        # Write file
        with open(app_path, 'wb') as f:
            f.write(content)
        
        # Make executable
        os.chmod(app_path, 0o755)
        
        print("Installed {} successfully.".format(app_name))
        return True
    
    except Exception as e:
        print("Error installing {}: {}".format(app_info['name'], str(e)))
        return False

def sysop_menu(callsign):
    """Sysop-only menu for system management."""
    while True:
        print()
        print("=" * 67)
        print("SYSOP MENU - {}".format(extract_base_call(callsign)))
        print("=" * 67)
        print()
        
        stats = get_system_stats()
        
        print("SYSTEM STATUS:")
        print()
        print("  Uptime:     {}".format(stats['uptime']))
        print("  Load Avg:   {}".format(stats['load_avg']))
        print("  Memory:     {} / {} ({})".format(stats['mem_used'], stats['mem_total'], stats['mem_percent']))
        print("  Disk:       {} / {} ({})".format(stats['disk_used'], stats['disk_total'], stats['disk_percent']))
        print()
        print("PROCESSES:")
        print()
        print("  LinBPQ:     {}".format(stats['linbpq']))
        print("  Direwolf:   {}".format(stats['direwolf']))
        print()
        print("-" * 67)
        print()
        print("1) List/Install Apps from GitHub")
        print("2) View System Log (/var/log/syslog)")
        print("3) View BPQ Log (~/linbpq/debug.log)")
        print("4) Refresh Status")
        print()
        print("R) Restart LinBPQ Service")
        print("Q) Return to Main Menu")
        print()
        
        try:
            choice = (raw_input("Select [1-4 R Q] :> ") if sys.version_info[0] < 3 else input("Select [1-4 R Q] :> ")).strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if choice == 'Q':
            break
        elif choice == '1':
            sysop_manage_apps()
        elif choice == '2':
            view_log_paginated('/var/log/syslog', 'SYSTEM LOG')
        elif choice == '3':
            log_paths = [
                os.path.expanduser('~/linbpq/debug.log'),
                '/home/ect/linbpq/debug.log',
                '/home/pi/linbpq/debug.log'
            ]
            for log_path in log_paths:
                if os.path.exists(log_path):
                    view_log_paginated(log_path, 'BPQ DEBUG LOG')
                    break
            else:
                print("BPQ log not found.")
                try:
                    raw_input("Press Enter to continue...") if sys.version_info[0] < 3 else input("Press Enter to continue...")
                except (EOFError, KeyboardInterrupt):
                    pass
        elif choice == '4':
            continue
        elif choice == 'R':
            print()
            print("Restarting LinBPQ service...")
            try:
                result = subprocess.call(['sudo', 'systemctl', 'restart', 'linbpq'])
                if result == 0:
                    print("Service restarted successfully.")
                else:
                    print("Failed to restart service (may require password).")
            except Exception as e:
                print("Error: {}".format(str(e)))
            print()
            try:
                raw_input("Press Enter to continue...") if sys.version_info[0] < 3 else input("Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                pass

def sysop_manage_apps():
    """List and install apps from GitHub."""
    print()
    print("=" * 67)
    print("MANAGE APPS FROM GITHUB")
    print("=" * 67)
    print()
    print("Fetching app list...")
    sys.stdout.flush()
    
    apps = list_available_apps_github()
    
    if not apps:
        print("No apps found or network error.")
        print()
        try:
            raw_input("Press Enter to continue...") if sys.version_info[0] < 3 else input("Press Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    
    # Check which are installed
    app_dir = os.path.dirname(os.path.abspath(__file__))
    for app in apps:
        app_path = os.path.join(app_dir, app['name'])
        app['installed'] = os.path.exists(app_path)
    
    while True:
        print()
        print("=" * 67)
        print("AVAILABLE APPS FROM GITHUB")
        print("=" * 67)
        print()
        
        for i, app in enumerate(apps, 1):
            status = "[INSTALLED]" if app['installed'] else ""
            print("{:2}) {:20} {:>8} bytes {}".format(i, app['name'], app['size'], status))
        
        print()
        print("-" * 67)
        print()
        print("Enter number to install/reinstall, or Q to return")
        print()
        
        try:
            choice = (raw_input("Select [1-{} Q] :> ".format(len(apps))) if sys.version_info[0] < 3 else input("Select [1-{} Q] :> ".format(len(apps)))).strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if choice == 'Q':
            break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(apps):
                print()
                if install_app_from_github(apps[idx]):
                    apps[idx]['installed'] = True
                print()
                try:
                    raw_input("Press Enter to continue...") if sys.version_info[0] < 3 else input("Press Enter to continue...")
                except (EOFError, KeyboardInterrupt):
                    pass
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")


def main():
    """Main application loop."""
    check_for_app_update(VERSION, "apps.py")
    
    # Read callsign from stdin (BPQ passes it)
    callsign = ""
    if not sys.stdin.isatty():
        try:
            callsign = sys.stdin.readline().strip()
        except Exception:
            pass
    
    # Load and filter apps
    config = load_apps_config()
    installed_apps = get_installed_apps(config)
    
    # Check if user is sysop
    user_is_sysop = is_sysop(callsign)
    
    while True:
        app_index = display_menu(installed_apps, callsign)
        
        if not app_index:
            print("Press Enter to exit...")
            try:
                raw_input() if sys.version_info[0] < 3 else input()
            except (EOFError, KeyboardInterrupt):
                pass
            break
        
        # Build options string
        if user_is_sysop:
            print("A)bout S)ysop Q)uit")
            options_str = "Select [1-{} A S Q] :> ".format(len(app_index))
        else:
            print("A)bout Q)uit")
            options_str = "Select [1-{} A Q] :> ".format(len(app_index))
        
        try:
            if sys.version_info[0] < 3:
                choice = raw_input(options_str).strip().upper()
            else:
                choice = input(options_str).strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if choice == 'Q':
            break
        elif choice == 'A':
            show_about()
        elif choice == 'S' and user_is_sysop:
            sysop_menu(callsign)
        elif choice in app_index:
            print()
            print("Launching {}...".format(app_index[choice]["name"]))
            print("-" * 40)
            sys.stdout.flush()
            
            launch_app(app_index[choice], callsign)
            
            print()
            print("-" * 40)
            print("Press Enter to continue...")
            try:
                raw_input() if sys.version_info[0] < 3 else input()
            except (EOFError, KeyboardInterrupt):
                pass
        else:
            print("Invalid selection.")
            print()
    
    print()
    print("Exiting...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Exiting...")
        sys.exit(0)
