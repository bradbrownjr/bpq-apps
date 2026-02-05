#!/usr/bin/env python3
"""
Application Menu Launcher for BPQ Packet Radio
Displays categorized menu of installed applications and launches them.

Version: 1.0
Author: Brad Brown Jr (KC1JMH)
Date: 2026-02-02
"""

import os
import sys
import json
import subprocess
import tempfile
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

VERSION = "1.0"

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
    """Get terminal width, fallback to 80 for non-TTY."""
    try:
        import fcntl
        import struct
        import termios
        data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '1234')
        return struct.unpack('hh', data)[1]
    except Exception:
        return 80

def extract_base_call(callsign):
    """Remove SSID from callsign."""
    if not callsign:
        return ""
    return callsign.split('-')[0]

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
    os.system('clear' if os.name != 'nt' else 'cls')
    
    display_logo()
    print("APPS v{} - Application Launcher".format(VERSION))
    if callsign:
        print("User: {}".format(extract_base_call(callsign)))
    print("-" * 67)
    print()
    
    if not installed_apps:
        print("No applications installed.")
        print()
        return {}
    
    # Build menu with numbered options
    app_index = {}
    
    # Define left and right column categories
    left_categories = ["Main", "Weather", "Tools"]
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
    """Launch selected app with callsign passed via stdin."""
    executable = app["executable"]
    needs_callsign = app.get("needs_callsign", False)
    
    try:
        # Create subprocess with pipes
        process = subprocess.Popen(
            [executable],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0
        )
        
        # If app needs callsign, write it to stdin (mimicking BPQ behavior)
        if needs_callsign and callsign:
            if sys.version_info[0] >= 3:
                process.stdin.write((callsign + '\n').encode('utf-8'))
            else:
                process.stdin.write(callsign + '\n')
            process.stdin.flush()
        
        # Stream output line by line
        while True:
            if sys.version_info[0] >= 3:
                line = process.stdout.readline().decode('utf-8', errors='replace')
            else:
                line = process.stdout.readline()
            
            if not line:
                break
            
            sys.stdout.write(line)
            sys.stdout.flush()
        
        # Wait for completion
        process.wait()
        process.stdin.close()
        process.stdout.close()
        
    except Exception as e:
        print("\nError launching {}: {}".format(app["name"], str(e)))
        print()

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
    
    while True:
        app_index = display_menu(installed_apps, callsign)
        
        if not app_index:
            print("Press Enter to exit...")
            try:
                raw_input() if sys.version_info[0] < 3 else input()
            except (EOFError, KeyboardInterrupt):
                pass
            break
        
        print("Q)uit")
        try:
            if sys.version_info[0] < 3:
                choice = raw_input("Select [1-{} Q] :> ".format(len(app_index))).strip().upper()
            else:
                choice = input("Select [1-{} Q] :> ".format(len(app_index))).strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if choice == 'Q':
            break
        
        if choice in app_index:
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
