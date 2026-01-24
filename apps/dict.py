#!/usr/bin/env python
"""
Dictionary Lookup Application for BPQ32 Packet Radio

Uses the Linux 'dict' command to query dictd servers for word definitions.
Provides simple interface for amateur radio operators to look up word meanings.

Version: 1.4
Author: Brad Brown, KC1JMH
Date: January 24, 2026
"""

import sys
import subprocess
import os
import tempfile
import stat

VERSION = "1.4"

# ASCII Art Logo (lowercase "dict" from asciiart.eu)
LOGO = r"""
     _ _      _   
  __| (_) ___| |_ 
 / _` | |/ __| __|
| (_| | | (__| |_ 
 \__,_|_|\___|\__|
"""


def compare_versions(v1, v2):
    """
    Compare two version strings (e.g., '1.0' vs '1.1').
    Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    try:
        parts1 = tuple(int(x) for x in v1.split('.'))
        parts2 = tuple(int(x) for x in v2.split('.'))
        if parts1 < parts2:
            return -1
        elif parts1 > parts2:
            return 1
        else:
            return 0
    except (ValueError, AttributeError):
        return 0


def check_for_app_update(current_version, script_name):
    """
    Check GitHub for updates to this script. If newer version exists,
    download and replace current script atomically.
    
    Fails silently if GitHub is unreachable (3-second timeout).
    """
    try:
        import urllib.request as urllib2
    except ImportError:
        import urllib2
    
    github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
    
    try:
        # 3-second timeout for GitHub check
        response = urllib2.urlopen(github_url, timeout=3)
        remote_content = response.read()
        if isinstance(remote_content, bytes):
            remote_content = remote_content.decode('utf-8')
        
        # Extract version from remote content
        remote_version = None
        for line in remote_content.split('\n'):
            if line.strip().startswith('Version:'):
                remote_version = line.split('Version:')[1].strip()
                break
        
        if remote_version and compare_versions(current_version, remote_version) < 0:
            # Download update
            script_path = os.path.abspath(__file__)
            temp_fd, temp_path = tempfile.mkstemp(suffix='.py', dir=os.path.dirname(script_path))
            
            try:
                # Write new content to temp file
                os.write(temp_fd, remote_content.encode('utf-8'))
                os.close(temp_fd)
                
                # Preserve executable permissions
                current_mode = os.stat(script_path).st_mode
                os.chmod(temp_path, current_mode)
                
                # Atomic replace
                os.rename(temp_path, script_path)
            except Exception:
                # Cleanup on failure
                try:
                    os.close(temp_fd)
                except Exception:
                    pass
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    except Exception:
        # Silent failure - continue with existing version
        pass


def check_dict_installed():
    """
    Check if 'dict' command is available on the system.
    Returns True if installed, False otherwise.
    """
    try:
        subprocess.check_output(['which', 'dict'], stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False


def lookup_word(word):
    """
    Look up word definition using dict command.
    Returns tuple: (success, output_text)
    """
    try:
        # Python 3.5.3 compatible: check_output doesn't support timeout
        proc = subprocess.Popen(
            ['dict', word],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        output, _ = proc.communicate()
        
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='replace')
        
        # Check for "No definitions found"
        if 'No definitions found' in output:
            return False, "No definitions found for '{}'".format(word)
        
        return True, output.strip()
    
    except subprocess.CalledProcessError as e:
        output = e.output
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='replace')
        if 'No definitions found' in output:
            return False, "No definitions found for '{}'".format(word)
        return False, "Error: {}".format(output)
    except Exception as e:
        return False, "Error: {}".format(str(e))


def format_output(text, width):
    """
    Format text output to fit within specified width with word wrapping.
    Adds pagination for long output (20 lines per page).
    Returns tuple: (formatted_lines, user_quit)
    """
    lines = []
    for line in text.split('\n'):
        if len(line) <= width:
            lines.append(line)
        else:
            # Word wrap at terminal width
            words = line.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= width:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
    return lines


def paginate_output(lines):
    """
    Display lines with pagination (20 lines per page).
    Returns True if user quit, False if completed normally.
    """
    line_count = 0
    for line in lines:
        print(line)
        sys.stdout.flush()
        line_count += 1
        
        # Paginate every 20 lines
        if line_count % 20 == 0 and line_count < len(lines):
            try:
                sys.stdout.write("(press Enter, Q to quit) ")
                sys.stdout.flush()
                response = sys.stdin.readline().strip().upper()
                if response == 'Q':
                    return True
            except (EOFError, KeyboardInterrupt):
                return True
    return False


def main():
    """Main application loop"""
    # Check for updates
    check_for_app_update(VERSION, "dict.py")
    
    # Get terminal width
    try:
        width = os.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        width = 40
    
    # Ensure minimum 40-char width for packet radio
    if width < 40:
        width = 40
    
    # Display header
    print(LOGO)
    print("")
    print("DICT v{} - Dictionary Lookup".format(VERSION))
    print("-" * 40)
    print("")
    sys.stdout.flush()
    
    # Check if dict command is installed
    if not check_dict_installed():
        print("Error: 'dict' command not found.")
        print("")
        print("Sysop: Install with:")
        print("  sudo apt-get install dictd dict")
        print("")
        print("Exiting...")
        sys.stdout.flush()
        return 1
    
    # Main loop
    while True:
        try:
            print("")
            sys.stdout.write("Word (or Q to quit) :> ")
            sys.stdout.flush()
            word = sys.stdin.readline().strip()
            
            if not word:
                continue
            
            if word.upper() == 'Q':
                print("")
                print("Exiting...")
                sys.stdout.flush()
                break
            
            print("")
            print("-" * 40)
            
            # Look up word
            success, output = lookup_word(word)
            
            # Format and display output with pagination
            lines = format_output(output, width)
            user_quit = paginate_output(lines)
            
            print("-" * 40)
            sys.stdout.flush()
            
            if user_quit:
                print("")
                print("Exiting...")
                sys.stdout.flush()
                break
        
        except KeyboardInterrupt:
            print("")
            print("")
            print("Exiting...")
            sys.stdout.flush()
            break
        except EOFError:
            print("")
            print("")
            print("Exiting...")
            sys.stdout.flush()
            break
        except Exception as e:
            print("")
            print("Error: {}".format(str(e)))
            print("")
            print("Exiting...")
            sys.stdout.flush()
            break
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
