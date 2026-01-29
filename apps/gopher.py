#!/usr/bin/env python3
"""
Gopher Protocol Client for Packet Radio
----------------------------------------
A simple text-based Gopher client designed for use over
AX.25 packet radio via linbpq BBS software.

Features:
- Plain ASCII text interface (no control codes)
- Article size prefetch with pagination option
- View text files with configurable pagination
- Configurable home page and bookmarks
- Simple command-based navigation

Author: Brad Brown KC1JMH
Version: 1.34
Date: January 2026
"""

import sys
import os

VERSION = "1.34"
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
                print("\n{} update available: v{} -> v{}".format(script_name, current_version, github_version))
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
                    print("Please reconnect to use the updated version.")
                    print("\n73!")
                    sys.exit(0)  # Exit cleanly so user reconnects with new version
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
from html.parser import HTMLParser

class HTMLStripper(HTMLParser):
    """Strip HTML tags and convert to plain text"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
        self.in_script = False
        self.in_style = False
    
    def handle_starttag(self, tag, attrs):
        """Handle HTML start tags"""
        if tag.lower() in ['script', 'style']:
            self.in_script = True if tag.lower() == 'script' else False
            self.in_style = True if tag.lower() == 'style' else False
        # Add newlines after block elements for readability
        elif tag.lower() in ['p', 'div', 'br', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
            if self.text and self.text[-1] != '\n':
                self.text.append('\n')
    
    def handle_endtag(self, tag):
        """Handle HTML end tags"""
        if tag.lower() in ['script', 'style']:
            self.in_script = False
            self.in_style = False
        # Add double newlines after block elements for spacing
        elif tag.lower() in ['p', 'div', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
            # Remove trailing spaces, add double newline for paragraph spacing
            while self.text and self.text[-1] == ' ':
                self.text.pop()
            if self.text and self.text[-1] != '\n':
                self.text.append('\n')
            if not self.text or self.text[-1] != '\n':
                self.text.append('\n')
            else:
                self.text.append('\n')
    
    def handle_data(self, data):
        """Handle text data"""
        if not self.in_script and not self.in_style:
            # Clean up whitespace but preserve structure
            lines = data.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped:
                    self.text.append(stripped + ' ')
                elif self.text and self.text[-1] != '\n':
                    self.text.append('\n')
    
    def get_data(self):
        """Get the stripped text"""
        result = ''.join(self.text)
        # Clean up excessive newlines (more than 2 blank lines)
        while '\n\n\n\n' in result:
            result = result.replace('\n\n\n\n', '\n\n\n')
        return result.strip()

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
PAGE_SIZE = 24  # Lines per page for pagination (standard terminal height)
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
        'p': 'PNG',  # PNG image
        'T': 'TN3',  # Telnet 3270
        'h': 'HTM',  # HTML file
        'i': 'INF',  # Informational text
        's': 'SND',  # Sound file
        ':': 'BMP',  # Bitmap image
        ';': 'MOV',  # Movie file
        'd': 'DOC',  # Document/PDF
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
        """Display a Gopher menu with numbered items and pagination"""
        self.last_menu = items
        
        # Count selectable items (non-info lines)
        selectable_count = sum(1 for item in items if item['type'] != 'i')
        
        # Check if menu is empty or only has info
        if selectable_count == 0:
            print("\nNo selectable items available on this page.")
            if items:
                print("-" * 40)
                for item in items:
                    if item['type'] == 'i':
                        print(item['display'])
                print("-" * 40)
            return None
        
        # Build output lines first
        output_lines = []
        item_num = 1
        
        for item in items:
            item_type = item['type']
            display = item['display']
            
            # Get type label
            type_label = self.ITEM_TYPES.get(item_type, 'UNK')
            
            # Info lines don't get numbers
            if item_type == 'i':
                output_lines.append("    {}".format(display))
            # All file types now get numbers for download capability
            else:
                # Wrap long lines at word boundaries
                if len(display) > LINE_WIDTH - 12:
                    wrapped = textwrap.fill(display, width=LINE_WIDTH - 12,
                                          subsequent_indent=' ' * 12, break_long_words=False)
                    lines = wrapped.split('\n')
                    output_lines.append("{:3}) [{}] {}".format(item_num, type_label, lines[0]))
                    for line in lines[1:]:
                        output_lines.append(line)
                else:
                    output_lines.append("{:3}) [{}] {}".format(item_num, type_label, display))
                item_num += 1
        
        # Paginate output
        total_lines = len(output_lines)
        total_pages = (total_lines + PAGE_SIZE - 1) // PAGE_SIZE
        current_page = 0
        
        while current_page < total_pages:
            start = current_page * PAGE_SIZE
            end = min(start + PAGE_SIZE, total_lines)
            
            print("\n" + "-" * 40)
            if total_pages > 1:
                print("Page {}/{}".format(current_page + 1, total_pages))
                print("-" * 40)
            
            for line in output_lines[start:end]:
                print(line)
            
            print("-" * 40)
            
            # Build prompt based on context
            if end < total_lines:
                # More pages available
                if selectable_count > 0:
                    if current_page > 0:
                        prompt = "\n[Enter]=Next Page P)rev [1-{}] W)here B)ack H)ome M)arks Q)uit :> ".format(selectable_count)
                    else:
                        prompt = "\n[Enter]=Next Page [1-{}] W)here B)ack H)ome M)arks Q)uit :> ".format(selectable_count)
                else:
                    if current_page > 0:
                        prompt = "\n[Enter]=Next Page P)rev W)here B)ack H)ome M)arks Q)uit :> "
                    else:
                        prompt = "\n[Enter]=Next Page W)here B)ack H)ome M)arks Q)uit :> "
            else:
                # Last page
                if selectable_count > 0:
                    if current_page > 0:
                        prompt = "\nP)rev [1-{}] B)ack H)ome M)arks Q)uit :> ".format(selectable_count)
                    else:
                        prompt = "\n[1-{}] B)ack H)ome M)arks Q)uit :> ".format(selectable_count)
                else:
                    if current_page > 0:
                        prompt = "\nP)rev B)ack H)ome M)arks Q)uit :> "
                    else:
                        prompt = "\nB)ack H)ome M)arks Q)uit :> "
            
            response = input(prompt).strip().lower()
            
            # Handle commands
            if not response:
                # Empty = next page or exit pagination if on last page
                if end < total_lines:
                    current_page += 1
                else:
                    # On last page, empty means done viewing
                    break
            elif response.startswith('w'):
                # Show current URL and wait for acknowledgment
                print("\nCurrent URL: {}".format(self.current_url))
                input("\nPress Enter to continue...")
                # Don't continue - will redisplay page after break from loop
            elif response.startswith('b'):
                # Back - navigate to previous page in history
                return 'back'
            elif response.startswith('p'):
                # Previous page
                if current_page > 0:
                    current_page -= 1
            elif response.startswith('h'):
                # Home
                return 'home'
            elif response.startswith('m'):
                # Marks/bookmarks
                return 'marks'
            elif response.startswith('q'):
                # Quit
                return 'quit'
            elif response.isdigit():
                # Link number
                return int(response)
            else:
                # Invalid command, stay on current page
                pass
        
        return None
    
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
            return None
        
        # Paginated display
        total_pages = (len(lines) + PAGE_SIZE - 1) // PAGE_SIZE
        current_page = 0
        
        while current_page < total_pages:
            start = current_page * PAGE_SIZE
            end = min(start + PAGE_SIZE, len(lines))
            chunk = lines[start:end]
            
            print("\n" + "-" * 40)
            print("Page {}/{}".format(current_page + 1, total_pages))
            print("-" * 40)
            
            for line in chunk:
                if len(line) > LINE_WIDTH:
                    wrapped = textwrap.fill(line, width=LINE_WIDTH, break_long_words=False)
                    print(wrapped)
                else:
                    print(line)
            
            print("-" * 40)
            
            # Build prompt based on context
            if end < len(lines):
                # More pages available
                if current_page > 0:
                    prompt = "\n[Enter]=Next Page P)rev W)here B)ack H)ome M)arks Q)uit :> "
                else:
                    prompt = "\n[Enter]=Next Page W)here B)ack H)ome M)arks Q)uit :> "
            else:
                # Last page
                if current_page > 0:
                    prompt = "\nP)rev W)here B)ack H)ome M)arks Q)uit :> "
                else:
                    prompt = "\nW)here B)ack H)ome M)arks Q)uit :> "
            
            response = input(prompt).strip().lower()
            
            # Handle commands
            if not response:
                # Empty = next page or exit if on last page
                if end < len(lines):
                    current_page += 1
                else:
                    break
            elif response.startswith('b'):
                # Back to menu
                return 'back'
            elif response.startswith('w'):
                # Show current URL and wait for acknowledgment
                print("\nCurrent URL: {}".format(self.current_url))
                input("\nPress Enter to continue...")
                # Don't continue - will redisplay page after break from loop
            elif response.startswith('p'):
                # Previous page
                if current_page > 0:
                    current_page -= 1
            elif response.startswith('h'):
                # Home
                return 'home'
            elif response.startswith('m'):
                # Marks/bookmarks
                return 'marks'
            elif response.startswith('q'):
                # Quit
                return 'quit'
            else:
                # Invalid command, stay on current page
                pass
        
        return None
    
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
        
        # Save to history (will be undone if navigation fails)
        saved_url = self.current_url
        if self.current_url:
            self.history.append(self.current_url)
        self.current_url = url
        
        def handle_nav_error(msg):
            """Handle navigation error - restore context and offer to go back"""
            print(msg)
            # Restore previous state
            if saved_url:
                self.history.pop() if self.history else None
                self.current_url = saved_url
            print("\nPress Enter to go back, or Q to quit")
            resp = input(":> ").strip().lower()
            if resp.startswith('q'):
                print("\nGoodbye! 73\n")
                sys.exit(0)
            # Auto-return to previous page if we have one
            if saved_url:
                self.navigate_to(saved_url)
            return False
        
        # Directory/menu
        if item_type == '1' or item_type == '':
            content = self.fetch_gopher(host, port, selector)
            if isinstance(content, tuple):
                return handle_nav_error("Error: {}".format(content[1]))
                
            items = self.parse_gopher_menu(content)
            result = self.display_menu(items)
            self.current_state = 'menu'
            
            # Handle return commands from pagination
            if result == 'quit':
                print("\nGoodbye! 73\n")
                sys.exit(0)
            elif result == 'home':
                self.history = []
                self.navigate_to(DEFAULT_HOME)
                return True
            elif result == 'marks':
                self.show_bookmarks()
                sel = input("Select bookmark # or [Enter] to cancel :> ").strip()
                if sel.isdigit():
                    idx = int(sel) - 1
                    if 0 <= idx < len(BOOKMARKS):
                        self.navigate_to(BOOKMARKS[idx][1])
                    else:
                        print("Invalid bookmark number")
                return True
            elif result == 'back':
                # Navigate back in history (clear current_url so it won't be re-added)
                if self.history:
                    prev_url = self.history.pop()
                    self.current_url = None
                    self.navigate_to(prev_url)
                else:
                    print("No previous page in history")
                return True
            elif isinstance(result, int):
                # User selected item by number
                selectable = [item for item in items if item['type'] != 'i']
                if 1 <= result <= len(selectable):
                    item = selectable[result - 1]
                    url = "gopher://{}:{}/{}{}".format(
                        item['host'], item['port'], item['type'], item['selector'])
                    self.navigate_to(url)
                else:
                    print("Invalid selection. Choose 1-{}".format(len(selectable)))
            
            return True
            
        # Text file
        elif item_type == '0':
            # Prefetch to get size
            result = self.get_article_size(host, port, selector)
            if result is None:
                return handle_nav_error("Error: Could not fetch article")
                
            size_kb, content = result
            print("\nArticle size: {:.1f} KB".format(size_kb))
            
            # Offer view options
            response = input("Display: A)ll at once, P)aginated, C)ancel :> ").strip().lower()
            if response.startswith('c'):
                self.current_state = 'menu'
                return True
            
            # View the content
            if size_kb > MAX_ARTICLE_SIZE_KB:
                print("Warning: This article is large ({:.1f} KB)".format(size_kb))
                print("This may take significant time over packet radio.")
            
            if response.startswith('p'):
                result = self.display_article(content, paginate=True)
            else:  # Default to all at once (including 'v' or 'a' or empty/Enter)
                result = self.display_article(content, paginate=False)
            
            self.current_state = 'article'
            
            # Handle return commands from article pagination
            if result == 'quit':
                print("\nGoodbye! 73\n")
                sys.exit(0)
            elif result == 'home':
                self.history = []
                self.navigate_to(DEFAULT_HOME)
                return True
            elif result == 'marks':
                self.show_bookmarks()
                sel = input("Select bookmark # or [Enter] to cancel :> ").strip()
                if sel.isdigit():
                    idx = int(sel) - 1
                    if 0 <= idx < len(BOOKMARKS):
                        self.navigate_to(BOOKMARKS[idx][1])
                    else:
                        print("Invalid bookmark number")
                return True
            elif result == 'back':
                # Return to previous page (back in history)
                if self.history:
                    prev_url = self.history.pop()
                    self.current_url = None
                    self.navigate_to(prev_url)
                return True
            
            return True
            
        # Search
        elif item_type == '7':
            query = input("Enter search terms :> ").strip()
            if query:
                search_selector = selector + '\t' + query
                content = self.fetch_gopher(host, port, search_selector)
                if isinstance(content, tuple):
                    return handle_nav_error("Error: {}".format(content[1]))
                    
                items = self.parse_gopher_menu(content)
                result = self.display_menu(items)
                self.current_state = 'menu'
                
                # Handle return commands from pagination
                if result == 'quit':
                    print("\nGoodbye! 73\n")
                    sys.exit(0)
                elif result == 'home':
                    self.history = []
                    self.navigate_to(DEFAULT_HOME)
                    return True
                elif result == 'marks':
                    self.show_bookmarks()
                    sel = input("Select bookmark # or [Enter] to cancel :> ").strip()
                    if sel.isdigit():
                        idx = int(sel) - 1
                        if 0 <= idx < len(BOOKMARKS):
                            self.navigate_to(BOOKMARKS[idx][1])
                        else:
                            print("Invalid bookmark number")
                    return True
                elif result == 'back':
                    # Navigate back in history (clear current_url so it won't be re-added)
                    if self.history:
                        prev_url = self.history.pop()
                        self.current_url = None
                        self.navigate_to(prev_url)
                    else:
                        print("No previous page in history")
                    return True
                elif isinstance(result, int):
                    # User selected item by number
                    selectable = [item for item in items if item['type'] != 'i']
                    if 1 <= result <= len(selectable):
                        item = selectable[result - 1]
                        url = "gopher://{}:{}/{}{}".format(
                            item['host'], item['port'], item['type'], item['selector'])
                        self.navigate_to(url)
                    else:
                        print("Invalid selection. Choose 1-{}".format(len(selectable)))
            return True
            
        # HTML - fetch and render as plain text
        elif item_type == 'h':
            if selector.startswith('URL:'):
                url = selector[4:]
                print("\nFetching HTML from: {}".format(url))
                
                try:
                    import urllib.request
                    # Fetch the HTML with timeout
                    with urllib.request.urlopen(url, timeout=30) as response:
                        html_content = response.read().decode('utf-8', errors='ignore')
                    
                    # Strip HTML tags and convert to plain text
                    stripper = HTMLStripper()
                    stripper.feed(html_content)
                    text_content = stripper.get_data()
                    
                    if not text_content:
                        print("Error: No text content found in HTML page")
                        return False
                    
                    # Display as article with pagination
                    result = self.display_article(text_content, paginate=True)
                    self.current_state = 'article'
                    
                    # Handle return commands from article pagination
                    if result == 'quit':
                        print("\nGoodbye! 73\n")
                        sys.exit(0)
                    elif result == 'home':
                        self.history = []
                        self.navigate_to(DEFAULT_HOME)
                        return True
                    elif result == 'marks':
                        self.show_bookmarks()
                        sel = input("Select bookmark # or [Enter] to cancel :> ").strip()
                        if sel.isdigit():
                            idx = int(sel) - 1
                            if 0 <= idx < len(BOOKMARKS):
                                self.navigate_to(BOOKMARKS[idx][1])
                            else:
                                print("Invalid bookmark number")
                        return True
                    elif result == 'back':
                        # Return to previous page (back in history)
                        if self.history:
                            prev_url = self.history.pop()
                            self.current_url = None
                            self.navigate_to(prev_url)
                        return True
                    
                    return True
                    
                except Exception as e:
                    return handle_nav_error("Error fetching HTML: {}\nURL: {}".format(str(e), url))
            else:
                return handle_nav_error("HTML link: {}\n(Cannot parse HTML URL from selector)".format(selector))
        
        # Binary files and other types - not supported without downloads
        elif item_type in ['4', '5', '6', '9', 'g', 'I', 'p', 's']:
            return handle_nav_error("Binary file type '{}' not supported.\n(Binary downloads not available - YAPP protocol disabled)".format(item_type))

        
        # Unsupported types
        elif item_type in ['2', '8', 'T']:
            return handle_nav_error("Item type '{}' not supported".format(item_type))
            
        else:
            return handle_nav_error("Item type '{}' not supported in text mode".format(item_type))
    
    def show_help(self):
        """Display help/commands menu"""
        print("\n" + "-" * 40)
        print("COMMANDS")
        print("-" * 40)
        print("  [number] - Select menu item by number")
        print("  H)ome    - Go to home page")
        print("  P)rev    - Previous page (within results)")
        print("  W)here   - Show current URL")
        print("  B)ack    - Back to previous view")
        print("  M)arks   - Show bookmarks")
        print("  G)o URL  - Go to specific Gopher URL")
        print("  A)bout   - About Gopher protocol")
        print("  ?)       - Show this help")
        print("  Q)uit    - Exit (works from any menu)")
        print("\nWhen viewing files:")
        print("  V)iew    - Display text in terminal")
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
        print("\nCommands:")
        print("  H)ome    - Go to home page")
        print("  M)arks   - Show bookmarks")
        print("  S)earch  - Search Gopherspace (Veronica-2)")
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
                    prompt = "\nGopher: H)ome, M)arks, S)earch, A)bout, G)o, ?)Help, Q)uit :> "
                
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
                
                # Search Veronica-2
                elif cmd_lower.startswith('s'):
                    self.navigate_to('gopher://gopher.floodgap.com:70/7/v2/vs')
                
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
