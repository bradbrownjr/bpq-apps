#!/usr/bin/env python3
"""
Gopher Protocol Client for Packet Radio
----------------------------------------
A simple text-based Gopher client designed for use over
AX.25 packet radio via linbpq BBS software.

Features:
- Plain ASCII text interface (no control codes)
- Article size prefetch with pagination option
- Download text and binary files via YAPP protocol
- View or download options for all file types
- Configurable home page and bookmarks
- Simple command-based navigation

Author: Brad Brown KC1JMH
Version: 1.8
Date: January 2026
"""

import sys
import os

# Import YAPP for file downloads
try:
    from yapp import create_stdio_yapp
    YAPP_AVAILABLE = True
except ImportError:
    YAPP_AVAILABLE = False

VERSION = "1.8"
APP_NAME = "gopher.py"

# Check Python version
if sys.version_info < (3, 5):
    print("Error: This script requires Python 3.5 or later.")
    print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ))
    print("\nPlease run with: python3 gopher.py")
    sys.exit(1)

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
        import re
        import os
        import stat
        
        # Get the version from GitHub (silent check with short timeout)
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read().decode('utf-8')
        
        # Extract version from docstring
        version_match = re.search(r'Version:\s*([0-9.]+)', content)
        if version_match:
            github_version = version_match.group(1)
            
            if compare_versions(github_version, current_version) > 0:
                print("\nUpdate available: v{} -> v{}".format(current_version, github_version))
                print("Downloading new version...")
                
                # Download the new version
                script_path = os.path.abspath(__file__)
                try:
                    # Write to temporary file first, then replace
                    temp_path = script_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    # Ensure file is executable (Python script should be executable)
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    
                    # Replace old file with new one
                    os.replace(temp_path, script_path)
                    
                    print("\nUpdate installed successfully!")
                    print("Please re-run this command to use the updated version.")
                    print("\nQuitting...")
                    return  # Return instead of sys.exit to avoid disconnecting BPQ
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    # Clean up temp file if it exists
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
    except Exception as e:
        # Don't block startup if update check fails (no internet, etc.)
        pass

def compare_versions(version1, version2):
    """
    Compare two version strings (e.g., '1.0', '1.2', '2.0')
    Returns: 
        1 if version1 > version2
        0 if version1 == version2
       -1 if version1 < version2
    """
    try:
        # Split versions into parts and convert to integers
        parts1 = [int(x) for x in str(version1).split('.')]
        parts2 = [int(x) for x in str(version2).split('.')]
        
        # Pad shorter version with zeros
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        
        # Compare each part
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0
    except (ValueError, AttributeError):
        return 0

import socket
import textwrap
import os
from urllib.parse import urlparse

def get_line_width():
    """Get terminal width from COLUMNS env var, default to 80"""
    try:
        if 'COLUMNS' in os.environ:
            width = int(os.environ['COLUMNS'])
            if width > 0:
                return width
    except (ValueError, KeyError, TypeError):
        pass
    return 80  # Default width for packet radio terminals

# Configuration
# -------------
DEFAULT_HOME = "gopher://gopher.floodgap.com"  # Default home page
BOOKMARKS = [
    ("Wikipedia", "gopher://gopherpedia.com"),
    ("Floodgap", "gopher://gopher.floodgap.com"),
    ("SDF Gopher", "gopher://sdf.org"),
]
PAGE_SIZE = 20  # Lines per page for pagination
MAX_ARTICLE_SIZE_KB = 100  # Warn if article is larger than this
SOCKET_TIMEOUT = 30  # Timeout for socket connections in seconds
LINE_WIDTH = get_line_width()  # Dynamic terminal width with 40-char fallback


class GopherClient:
    """Simple Gopher protocol client"""
    
    # Gopher item type codes
    ITEM_TYPES = {
        '0': 'TXT',  # Text file
        '1': 'DIR',  # Directory/menu
        '2': 'CSO',  # CSO phone book
        '3': 'ERR',  # Error
        '4': 'BHX',  # BinHex file
        '5': 'BIN',  # Binary archive
        '6': 'UUE',  # UUEncoded file
        '7': 'SRH',  # Search query
        '8': 'TEL',  # Telnet session
        '9': 'BIN',  # Binary file
        '+': 'MIR',  # Mirror
        'g': 'GIF',  # GIF image
        'I': 'IMG',  # Image file
        'T': 'TN3',  # Telnet 3270
        'h': 'HTM',  # HTML file
        'i': 'INF',  # Informational text
        's': 'SND',  # Sound file
    }
    
    def __init__(self):
        self.history = []
        self.current_url = DEFAULT_HOME
        self.last_menu = []
        self.current_state = 'start'  # start, menu, article
        
    def parse_gopher_url(self, url):
        """Parse a Gopher URL into components"""
        if not url.startswith('gopher://'):
            url = 'gopher://' + url
            
        parsed = urlparse(url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 70
        path = parsed.path or '/'
        
        # Gopher path format: /[type][selector]
        if len(path) > 1:
            item_type = path[1]
            selector = path[2:] if len(path) > 2 else ''
        else:
            item_type = '1'
            selector = ''
            
        return host, port, item_type, selector
    
    def fetch_gopher(self, host, port, selector=''):
        """Fetch content from a Gopher server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((host, port))
            
            # Send the selector (Gopher protocol)
            request = selector + '\r\n'
            sock.sendall(request.encode('utf-8'))
            
            # Receive the response
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                
            sock.close()
            return response.decode('utf-8', errors='replace')
            
        except socket.timeout:
            return None, "Connection timed out"
        except socket.gaierror:
            return None, "Could not resolve host"
        except ConnectionRefusedError:
            return None, "Connection refused"
        except Exception as e:
            return None, "Error: {}".format(str(e))
    
    def parse_gopher_menu(self, content):
        """Parse a Gopher menu/directory listing"""
        items = []
        lines = content.split('\n')
        
        for line in lines:
            if not line or line == '.':
                continue
                
            # Gopher menu format: TypeDisplay\tSelector\tHost\tPort
            if '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 4:
                    type_and_display = parts[0]
                    if not type_and_display:
                        continue
                        
                    item_type = type_and_display[0]
                    display = type_and_display[1:]
                    selector = parts[1]
                    host = parts[2]
                    port = parts[3].strip()
                    
                    items.append({
                        'type': item_type,
                        'display': display,
                        'selector': selector,
                        'host': host,
                        'port': port
                    })
            else:
                # Informational line without tabs
                if line.startswith('i'):
                    items.append({
                        'type': 'i',
                        'display': line[1:],
                        'selector': '',
                        'host': '',
                        'port': ''
                    })
                    
        return items
    
    def display_menu(self, items):
        """Display a Gopher menu with numbered items"""
        self.last_menu = items
        print("\n" + "-" * 40)
        
        item_num = 1
        for item in items:
            item_type = item['type']
            display = item['display']
            
            # Get type label
            type_label = self.ITEM_TYPES.get(item_type, '???')
            
            # Info lines don't get numbers
            if item_type == 'i':
                print("    {}".format(display))
            # All file types now get numbers for download capability
            else:
                # Wrap long lines at word boundaries
                if len(display) > LINE_WIDTH - 12:
                    wrapped = textwrap.fill(display, width=LINE_WIDTH - 12,
                                          subsequent_indent=' ' * 12, break_long_words=False)
                    lines = wrapped.split('\n')
                    print("{:3}) [{}] {}".format(item_num, type_label, lines[0]))
                    for line in lines[1:]:
                        print(line)
                else:
                    print("{:3}) [{}] {}".format(item_num, type_label, display))
                item_num += 1
                
        print("-" * 40)
    
    def get_article_size(self, host, port, selector):
        """Prefetch to determine article size in KB"""
        content = self.fetch_gopher(host, port, selector)
        if isinstance(content, tuple):  # Error occurred
            return None
        size_bytes = len(content.encode('utf-8'))
        size_kb = size_bytes / 1024
        return size_kb, content
    
    def display_article(self, content, paginate=True):
        """Display text content with optional pagination"""
        lines = content.split('\n')
        
        if not paginate:
            for line in lines:
                # Wrap long lines at word boundaries
                if len(line) > LINE_WIDTH:
                    wrapped = textwrap.fill(line, width=LINE_WIDTH, break_long_words=False)
                    print(wrapped)
                else:
                    print(line)
            return
        
        # Paginated display
        page_num = 1
        total_pages = (len(lines) + PAGE_SIZE - 1) // PAGE_SIZE
        
        for i in range(0, len(lines), PAGE_SIZE):
            chunk = lines[i:i + PAGE_SIZE]
            
            print("\n" + "-" * 40)
            print("Page {}/{}".format(page_num, total_pages))
            print("-" * 40)
            
            for line in chunk:
                if len(line) > LINE_WIDTH:
                    wrapped = textwrap.fill(line, width=LINE_WIDTH, break_long_words=False)
                    print(wrapped)
                else:
                    print(line)
            
            page_num += 1
            
            if i + PAGE_SIZE < len(lines):
                response = input("\n[Enter]=Next page, Q)uit :> ").strip().lower()
                if response.startswith('q'):
                    break
    
    def show_bookmarks(self):
        """Display bookmarks menu"""
        print("\n" + "-" * 40)
        print("BOOKMARKS")
        print("-" * 40)
        for i, (name, url) in enumerate(BOOKMARKS, 1):
            print("{}) {}".format(i, name))
            print("   {}".format(url))
        print("-" * 40)
    
    def navigate_to(self, url):
        """Navigate to a Gopher URL"""
        print("\nConnecting to {}...".format(url))
        
        host, port, item_type, selector = self.parse_gopher_url(url)
        
        # Save to history
        if self.current_url:
            self.history.append(self.current_url)
        self.current_url = url
        
        # Directory/menu
        if item_type == '1' or item_type == '':
            content = self.fetch_gopher(host, port, selector)
            if isinstance(content, tuple):
                print("Error: {}".format(content[1]))
                return False
                
            items = self.parse_gopher_menu(content)
            self.display_menu(items)
            self.current_state = 'menu'
            return True
            
        # Text file
        elif item_type == '0':
            # Prefetch to get size
            result = self.get_article_size(host, port, selector)
            if result is None:
                print("Error: Could not fetch article")
                return False
                
            size_kb, content = result
            print("\nArticle size: {:.1f} KB".format(size_kb))
            
            # Offer view or download options
            if YAPP_AVAILABLE:
                response = input("V)iew, D)ownload, C)ancel :> ").strip().lower()
                
                if response.startswith('d'):
                    # Download via YAPP
                    filename = selector.split('/')[-1] if '/' in selector else 'gopher.txt'
                    if not filename or filename == '':
                        filename = 'gopher.txt'
                    
                    print("\nDownloading: {}".format(filename))
                    print("Initiating YAPP transfer...")
                    
                    try:
                        yapp = create_stdio_yapp(debug=False)
                        filedata = content.encode('utf-8')
                        success, msg = yapp.send_file(filename, filedata)
                        
                        if success:
                            print("\nTransfer complete: {}".format(msg))
                        else:
                            print("\nTransfer failed: {}".format(msg))
                    except Exception as e:
                        print("\nYAPP error: {}".format(str(e)))
                    
                    self.current_state = 'menu'
                    return True
                    
                elif response.startswith('c'):
                    self.current_state = 'menu'
                    return True
            else:
                response = input("Display: A)ll at once, P)aginated, C)ancel :> ").strip().lower()
                if response.startswith('c'):
                    self.current_state = 'menu'
                    return True
            
            # View the content
            if size_kb > MAX_ARTICLE_SIZE_KB:
                print("Warning: This article is large ({:.1f} KB)".format(size_kb))
                print("This may take significant time over packet radio.")
            
            if response.startswith('p'):
                self.display_article(content, paginate=True)
            else:  # Default to all at once (including 'v' or 'a' or empty/Enter)
                self.display_article(content, paginate=False)
            
            self.current_state = 'article'
            return True
            
        # Search
        elif item_type == '7':
            query = input("Enter search terms :> ").strip()
            if query:
                search_selector = selector + '\t' + query
                content = self.fetch_gopher(host, port, search_selector)
                if isinstance(content, tuple):
                    print("Error: {}".format(content[1]))
                    return False
                    
                items = self.parse_gopher_menu(content)
                self.display_menu(items)
                self.current_state = 'menu'
            return True
            
        # HTML (just show the URL)
        elif item_type == 'h':
            if selector.startswith('URL:'):
                url = selector[4:]
                print("\nHTML link: {}".format(url))
                print("(Cannot display HTML in text mode)")
            self.current_state = 'menu'
            return True
        
        # Binary files and other types - offer download
        elif item_type in ['4', '5', '6', '9', 'g', 'I', 's']:
            if not YAPP_AVAILABLE:
                print("\nBinary file type '{}' requires YAPP for download.".format(item_type))
                print("YAPP module not available.")
                return False
            
            # Fetch the binary content
            print("\nFetching binary file...")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(SOCKET_TIMEOUT)
                sock.connect((host, int(port)))
                
                request = selector + '\r\n'
                sock.sendall(request.encode('utf-8'))
                
                # Receive binary data
                filedata = b''
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    filedata += chunk
                
                sock.close()
                
                size_kb = len(filedata) / 1024
                print("File size: {:.1f} KB".format(size_kb))
                
                # Extract filename from selector
                filename = selector.split('/')[-1] if '/' in selector else 'download.bin'
                if not filename or filename == '':
                    filename = 'download.bin'
                
                response = input("D)ownload or C)ancel :> ").strip().lower()
                
                if response.startswith('d'):
                    print("\nDownloading: {}".format(filename))
                    print("Initiating YAPP transfer...")
                    
                    try:
                        yapp = create_stdio_yapp(debug=False)
                        success, msg = yapp.send_file(filename, filedata)
                        
                        if success:
                            print("\nTransfer complete: {}".format(msg))
                        else:
                            print("\nTransfer failed: {}".format(msg))
                    except Exception as e:
                        print("\nYAPP error: {}".format(str(e)))
                
                self.current_state = 'menu'
                return True
                
            except Exception as e:
                print("Error fetching binary: {}".format(str(e)))
                return False
        
        # Unsupported types
        elif item_type in ['2', '8', 'T']:
            print("Item type '{}' not supported".format(item_type))
            return False
            
        else:
            print("Item type '{}' not supported in text mode".format(item_type))
            return False
    
    def show_help(self):
        """Display help/commands menu"""
        print("\n" + "-" * 40)
        print("COMMANDS")
        print("-" * 40)
        print("  [number] - Select menu item by number")
        print("  H)ome    - Go to home page")
        print("  B)ack    - Go back to previous page")
        print("  M)arks   - Show bookmarks")
        print("  G)o URL  - Go to specific Gopher URL")
        print("  A)bout   - About Gopher protocol")
        print("  ?)       - Show this help")
        print("  Q)uit    - Exit (works from any menu)")
        print("\nWhen viewing files:")
        print("  V)iew    - Display text in terminal")
        if YAPP_AVAILABLE:
            print("  D)ownload - Transfer file via YAPP protocol")
        print("\nPrompts are context-aware and show available commands.")
        print("-" * 40)
    
    def show_about(self):
        """Display information about Gopher"""
        print("\n" + "-" * 40)
        print("ABOUT GOPHER")
        print("-" * 40)
        print("\nGopher is a protocol developed in 1991 at the University of")
        print("Minnesota (home of the Golden Gophers mascot). It predates the")
        print("World Wide Web and was designed for distributing documents over")
        print("the internet in a simple, hierarchical menu system.")
        print("\nKey concepts:")
        print("- GOPHER HOLES: Individual Gopher servers (like websites)")
        print("- GOPHERSPACE: The entire network of interconnected servers")
        print("- MENUS: Directory listings that link to other menus or files")
        print("- TEXT-BASED: Perfect for low-bandwidth connections like packet")
        print("  radio! No images, scripts, or ads - just pure content.")
        print("\nGopher uses simple item types:")
        print("- [DIR] Menus/directories to browse")
        print("- [TXT] Plain text documents")
        print("- [SRH] Search services")
        print("\nWhy Gopher for packet radio?")
        print("- Minimal bandwidth usage (typically <10KB per page)")
        print("- No graphics or multimedia overhead")
        print("- Clean, structured text perfect for simple terminals")
        print("- Still actively maintained by enthusiasts worldwide")
        print("\nGopher experienced a revival in recent years among users who")
        print("appreciate its simplicity and efficiency. Perfect for ham radio!")
        print("-" * 40)
    
    def show_startup_menu(self):
        """Display startup menu with command descriptions"""
        print("\n" + "-" * 40)
        print("GETTING STARTED")
        print("-" * 40)
        print("\nWelcome to Gopherspace! Here's how to explore:")
        print("")
        print("  H)ome - Connect to the default home gopher server")
        print("  M)arks - View and select from your bookmarks")
        print("  G)o URL - Navigate to a specific gopher URL")
        print("  A)bout - Learn about the Gopher protocol")
        print("  ?)Help - Show complete command reference")
        print("  Q)uit - Exit the gopher client")
        print("")
        print("TIP: Start by typing 'H' to visit the home server, or 'M' to")
        print("     browse bookmarks. Once viewing a gopher menu, you can")
        print("     select items by number.")
        print("-" * 40)
    
    def run(self):
        """Main program loop"""
        print("")
        print(r"                   _               ")
        print(r"  __ _  ___  _ __ | |__   ___ _ __ ")
        print(r" / _` |/ _ \| '_ \| '_ \ / _ \ '__|")
        print(r"| (_| | (_) | |_) | | | |  __/ |   ")
        print(r" \__, |\___/| .__/|_| |_|\___|_|   ")
        print(r" |___/      |_|                    ")
        print("")
        print("GOPHER v{} - Gopher Protocol Client".format(VERSION))
        print("Designed for AX.25 packet radio terminals.")
        if YAPP_AVAILABLE:
            print("YAPP file download support: Enabled")
        else:
            print("YAPP file download support: Disabled (yapp.py not found)")
        print("\nCommands:")
        print("  H)ome    - Go to home page")
        print("  M)arks   - Show bookmarks")
        print("  A)bout   - About Gopher protocol")
        print("  G)o URL  - Go to specific Gopher URL")
        print("  ?)       - Show help")
        print("  Q)uit    - Exit the client")
        
        # Main command loop
        while True:
            try:
                # Context-aware prompt
                if self.current_state == 'menu':
                    prompt = "\nMenu: [#] or H)ome, B)ack, M)arks, G)o, A)bout, ?)Help, Q)uit :> "
                elif self.current_state == 'article':
                    prompt = "\nArticle: B)ack, H)ome, M)arks, G)o, ?)Help, Q)uit :> "
                else:
                    prompt = "\nGopher: H)ome, M)arks, A)bout, G)o, ?)Help, Q)uit :> "
                
                command = input(prompt).strip()
                
                if not command:
                    continue
                    
                cmd_lower = command.lower()
                
                # Quit - works from anywhere
                if cmd_lower.startswith('q'):
                    print("\nGoodbye! 73\n")
                    break
                
                # Home
                elif cmd_lower.startswith('h'):
                    self.history = []
                    self.navigate_to(DEFAULT_HOME)
                
                # Back
                elif cmd_lower.startswith('b'):
                    if self.history:
                        prev_url = self.history.pop()
                        self.current_url = prev_url
                        self.navigate_to(prev_url)
                    else:
                        print("No previous page in history")
                
                # Bookmarks
                elif cmd_lower.startswith('m'):
                    self.show_bookmarks()
                    sel = input("Select bookmark # or [Enter] to cancel :> ").strip()
                    if sel.isdigit():
                        idx = int(sel) - 1
                        if 0 <= idx < len(BOOKMARKS):
                            self.navigate_to(BOOKMARKS[idx][1])
                        else:
                            print("Invalid bookmark number")
                
                # About
                elif cmd_lower.startswith('a'):
                    self.show_about()
                
                # Go to URL
                elif cmd_lower.startswith('g'):
                    parts = command.split(None, 1)
                    if len(parts) > 1:
                        url = parts[1].strip()
                        self.navigate_to(url)
                    else:
                        url = input("Enter Gopher URL :> ").strip()
                        if url:
                            self.navigate_to(url)
                
                # Help
                elif command == '?' or cmd_lower == 'help':
                    self.show_help()
                
                # Select menu item by number
                elif command.isdigit():
                    item_num = int(command)
                    
                    # Filter out info items only
                    selectable = [item for item in self.last_menu 
                                 if item['type'] != 'i']
                    
                    if 1 <= item_num <= len(selectable):
                        item = selectable[item_num - 1]
                        
                        # Build URL for the selected item
                        url = "gopher://{}:{}/{}{}".format(
                            item['host'], item['port'], item['type'], item['selector'])
                        self.navigate_to(url)
                    else:
                        print("Invalid selection. Choose 1-{}".format(len(selectable)))
                
                else:
                    print("Unknown command. Type ? for help")
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Use Q to quit.\n")
                continue
            except EOFError:
                print("\n\nConnection closed. Goodbye! 73\n")
                break
            except Exception as e:
                print("\nError: {}".format(str(e)))
                continue


if __name__ == '__main__':
    try:
        # Check for app updates
        check_for_app_update(VERSION, APP_NAME)
        client = GopherClient()
        client.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except EOFError:
        print("\n\nExiting...")
    except Exception as e:
        print("\nError: {}".format(str(e)))
        print("Please report this issue if it persists.")
