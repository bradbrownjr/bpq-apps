#!/usr/bin/env python3
"""
Gopher Protocol Client for Packet Radio
----------------------------------------
A simple text-based Gopher client designed for use over
AX.25 packet radio via linbpq BBS software.

Features:
- Plain ASCII text interface (no control codes)
- Article size prefetch with pagination option
- Configurable home page and bookmarks
- Simple command-based navigation

Author: Brad Brown KC1JMH
Date: October 2025
"""

import sys

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

import socket
import textwrap
from urllib.parse import urlparse

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
LINE_WIDTH = 80  # Maximum line width for wrapping


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
        print("\n" + "=" * LINE_WIDTH)
        
        item_num = 1
        for item in items:
            item_type = item['type']
            display = item['display']
            
            # Get type label
            type_label = self.ITEM_TYPES.get(item_type, '???')
            
            # Info lines don't get numbers
            if item_type == 'i':
                print("    {}".format(display))
            # Skip non-readable types for packet radio
            elif item_type in ['2', '4', '5', '6', '8', '9', 'g', 'I', 's', 'T']:
                print("    [{}] {} (not supported)".format(type_label, display))
            else:
                # Wrap long lines
                if len(display) > LINE_WIDTH - 12:
                    wrapped = textwrap.fill(display, width=LINE_WIDTH - 12,
                                          subsequent_indent=' ' * 12)
                    lines = wrapped.split('\n')
                    print("{:3}) [{}] {}".format(item_num, type_label, lines[0]))
                    for line in lines[1:]:
                        print(line)
                else:
                    print("{:3}) [{}] {}".format(item_num, type_label, display))
                item_num += 1
                
        print("=" * LINE_WIDTH)
    
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
                # Wrap long lines
                if len(line) > LINE_WIDTH:
                    wrapped = textwrap.fill(line, width=LINE_WIDTH)
                    print(wrapped)
                else:
                    print(line)
            return
        
        # Paginated display
        page_num = 1
        total_pages = (len(lines) + PAGE_SIZE - 1) // PAGE_SIZE
        
        for i in range(0, len(lines), PAGE_SIZE):
            chunk = lines[i:i + PAGE_SIZE]
            
            print("\n" + "-" * LINE_WIDTH)
            print("Page {}/{}".format(page_num, total_pages))
            print("-" * LINE_WIDTH)
            
            for line in chunk:
                if len(line) > LINE_WIDTH:
                    wrapped = textwrap.fill(line, width=LINE_WIDTH)
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
        print("\n" + "=" * LINE_WIDTH)
        print("BOOKMARKS")
        print("=" * LINE_WIDTH)
        for i, (name, url) in enumerate(BOOKMARKS, 1):
            print("{}) {}".format(i, name))
            print("   {}".format(url))
        print("=" * LINE_WIDTH)
    
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
            
            # Offer pagination for large articles
            if size_kb > MAX_ARTICLE_SIZE_KB:
                print("Warning: This article is large ({:.1f} KB)".format(size_kb))
                print("This may take significant time over packet radio.")
                
            response = input("Display: A)ll at once, P)aginated, C)ancel :> ").strip().lower()
            
            if response.startswith('c'):
                self.current_state = 'menu'
                return True
            elif response.startswith('p'):
                self.display_article(content, paginate=True)
            else:  # Default to all at once (including empty/Enter)
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
            
        else:
            print("Item type '{}' not supported in text mode".format(item_type))
            return False
    
    def show_help(self):
        """Display help/commands menu"""
        print("\n" + "=" * LINE_WIDTH)
        print("COMMANDS")
        print("=" * LINE_WIDTH)
        print("  [number] - Select menu item by number")
        print("  H)ome    - Go to home page")
        print("  B)ack    - Go back to previous page")
        print("  M)arks   - Show bookmarks")
        print("  G)o URL  - Go to specific Gopher URL")
        print("  A)bout   - About Gopher protocol")
        print("  ?)       - Show this help")
        print("  Q)uit    - Exit (works from any menu)")
        print("\nPrompts are context-aware and show available commands.")
        print("=" * LINE_WIDTH)
    
    def show_about(self):
        """Display information about Gopher"""
        print("\n" + "=" * LINE_WIDTH)
        print("ABOUT GOPHER")
        print("=" * LINE_WIDTH)
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
        print("=" * LINE_WIDTH)
    
    def show_startup_menu(self):
        """Display startup menu with command descriptions"""
        print("\n" + "=" * LINE_WIDTH)
        print("GETTING STARTED")
        print("=" * LINE_WIDTH)
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
        print("=" * LINE_WIDTH)
    
    def run(self):
        """Main program loop"""
        print("")
        print("   _____  ____  _____  _    _ ______ _____  ")
        print("  / ____|/ __ \\|  __ \\| |  | |  ____|  __ \\ ")
        print(" | |  __| |  | | |__) | |__| | |__  | |__) |")
        print(" | | |_ | |  | |  ___/|  __  |  __| |  _  / ")
        print(" | |__| | |__| | |    | |  | | |____| | \\ \\ ")
        print("  \\_____|\____/|_|    |_|  |_|______|_|  \\_\\")
        print("")
        print("A simple text-based Gopher protocol client.")
        print("Designed for AX.25 packet radio terminals.")
        print("\nCommands:")
        print("  H)ome    - Go to home page")
        print("  M)arks   - Show bookmarks")
        print("  A)bout   - About Gopher protocol")
        print("  G)o URL  - Go to specific Gopher URL")
        print("  ?)       - Show help")
        print("  Q)uit    - Exit the client")
        print("=" * LINE_WIDTH)
        
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
                    
                    # Filter out info and unsupported items
                    selectable = [item for item in self.last_menu 
                                 if item['type'] not in ['i', '2', '4', '5', '6', '8', '9', 'g', 'I', 's', 'T']]
                    
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
    client = GopherClient()
    try:
        client.run()
    except Exception as e:
        print("\nFatal error: {}".format(str(e)))
        sys.exit(1)
