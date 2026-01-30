#!/usr/bin/env python3
"""
WWW Browser for Packet Radio
------------------------------
A text-mode web browser for AX.25 packet radio via linbpq BBS.
Designed for low-bandwidth, ASCII-only browsing with numbered links.

Features:
- Text-mode HTML rendering (strips JavaScript, CSS)
- Numbered link navigation (recursive browsing)
- Pagination at 24 lines per page
- Bookmarks for packet-radio-friendly sites
- Search via FrogFind.com (text-only search engine)
- Offline caching (last 10 pages, 24-hour expiry)
- Smart word wrapping for terminal width

Author: Brad Brown KC1JMH
Version: 1.0
Date: January 2026
"""

import sys
import os
import json
import time
import re
import textwrap
import socket
try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse

VERSION = "1.0"
APP_NAME = "www.py"

# Check Python version
if sys.version_info < (3, 5):
    print("Error: This script requires Python 3.5 or later.")
    print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ))
    print("\nPlease run with: python3 www.py")
    sys.exit(1)

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
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
                    
                    # Ensure file is executable
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    
                    # Replace old file with new one
                    os.replace(temp_path, script_path)
                    
                    print("\nUpdate installed successfully!")
                    print("Please re-run this command to use the updated version.")
                    print("\nExiting...")
                    sys.exit(0)
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    # Clean up temp file if it exists
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
        
        # Check if www.conf is missing and download it (don't overwrite existing)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'www.conf')
        if not os.path.exists(config_path):
            try:
                config_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/www.conf"
                with urllib.request.urlopen(config_url, timeout=3) as response:
                    config_content = response.read()
                with open(config_path, 'wb') as f:
                    f.write(config_content)
            except:
                # Silently ignore if config download fails - app will use defaults
                pass
    except Exception:
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
    v1_parts = [int(x) for x in version1.split('.')]
    v2_parts = [int(x) for x in version2.split('.')]
    
    # Pad shorter version with zeros
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts += [0] * (max_len - len(v1_parts))
    v2_parts += [0] * (max_len - len(v2_parts))
    
    for i in range(max_len):
        if v1_parts[i] > v2_parts[i]:
            return 1
        elif v1_parts[i] < v2_parts[i]:
            return -1
    return 0

def is_internet_available():
    """Check if internet is available by testing DNS connectivity"""
    try:
        # Try to connect to Google's DNS server
        socket.create_connection(('8.8.8.8', 53), timeout=2)
        return True
    except OSError:
        return False

def get_terminal_width():
    """Get terminal width with fallback to 80 chars"""
    try:
        return os.get_terminal_size().columns
    except (AttributeError, OSError):
        pass
    
    # Try environment variable
    try:
        if 'COLUMNS' in os.environ:
            width = int(os.environ['COLUMNS'])
            if width > 0:
                return width
    except (ValueError, KeyError, TypeError):
        pass
    return 80

def load_config():
    """Load configuration from www.conf JSON file with fallback to defaults"""
    defaults = {
        'home': 'https://frogfind.com',
        'search_url': 'https://frogfind.com/?q={}',
        'bookmarks': [
            {'name': 'WS1SM Club', 'url': 'http://ws1sm.com'},
            {'name': 'Maine Packet Radio', 'url': 'https://mainepacketradio.org'},
            {'name': 'ARRL Home', 'url': 'http://www.arrl.org'},
            {'name': 'ARRL News', 'url': 'http://www.arrl.org/news'},
            {'name': 'FrogFind Search', 'url': 'https://frogfind.com'}
        ],
        'page_size': 24,
        'max_page_size_kb': 200,
        'socket_timeout': 15,
        'user_agent': 'Mozilla/5.0 (compatible; WWW/1.0; +packet-radio)'
    }
    
    # Try to load from config file in same directory as script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'www.conf')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            # Merge with defaults (use config values, fall back to defaults)
            for key in defaults:
                if key not in config:
                    config[key] = defaults[key]
            return config
    except (IOError, OSError, json.JSONDecodeError):
        # File doesn't exist or is invalid - use defaults
        return defaults

# Load configuration
_CONFIG = load_config()
HOME_URL = _CONFIG['home']
SEARCH_URL = _CONFIG['search_url']
BOOKMARKS = [(b['name'], b['url']) for b in _CONFIG['bookmarks']]
PAGE_SIZE = _CONFIG['page_size']
MAX_PAGE_SIZE_KB = _CONFIG['max_page_size_kb']
SOCKET_TIMEOUT = _CONFIG['socket_timeout']
USER_AGENT = _CONFIG['user_agent']
TERM_WIDTH = get_terminal_width()


class PageCache:
    """Simple cache for recently viewed pages"""
    
    def __init__(self, max_size=10, expiry_hours=24):
        self.max_size = max_size
        self.expiry_hours = expiry_hours
        self.cache_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '.www_cache.json'
        )
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Load cache from disk"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (IOError, OSError, json.JSONDecodeError):
            return {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except (IOError, OSError):
            pass
    
    def get(self, key):
        """Get cached item if not expired"""
        if key in self.cache:
            timestamp, data = self.cache[key]
            age_hours = (time.time() - timestamp) / 3600
            if age_hours < self.expiry_hours:
                return data
            else:
                del self.cache[key]
                self._save_cache()
        return None
    
    def set(self, key, data):
        """Set cache item with current timestamp"""
        # Enforce max cache size
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]
        
        self.cache[key] = (time.time(), data)
        self._save_cache()


class HTMLSimplifier:
    """Convert HTML to plain text with numbered links"""
    
    def __init__(self):
        self.links = []
        self.link_counter = 0
    
    def html_to_text(self, html):
        """Convert HTML to plain text with numbered links"""
        self.links = []
        self.link_counter = 0
        
        # Remove script and style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert common block elements to newlines
        html = re.sub(r'</(p|div|h[1-6]|li|tr|br)>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<(p|div|h[1-6]|li|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
        
        # Extract and number links
        def replace_link(match):
            href = match.group(1)
            text = match.group(2)
            
            # Skip empty links, anchors, javascript
            if not href or href.startswith('#') or href.startswith('javascript:'):
                return text
            
            self.link_counter += 1
            self.links.append((self.link_counter, href, text))
            return "{} [{}]".format(text, self.link_counter)
        
        html = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', replace_link, html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&mdash;', '--')
        text = text.replace('&ndash;', '-')
        text = text.replace('&hellip;', '...')
        
        # Remove extra whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        
        return '\n'.join(lines)
    
    def get_links(self):
        """Return list of extracted links"""
        return self.links


class WebBrowser:
    """Simple web browser with text rendering"""
    
    def __init__(self):
        self.cache = PageCache()
        self.history = []
        self.current_url = HOME_URL
        self.current_links = []
        self.current_page = []
        
        try:
            import urllib.request
            self.urllib = urllib.request
        except ImportError:
            print("Error: urllib.request not available")
            sys.exit(1)
    
    def fetch_url(self, url):
        """Fetch URL and return HTML content"""
        # Check cache first
        cached = self.cache.get(url)
        if cached:
            return cached
        
        # Check internet connectivity
        if not is_internet_available():
            print("\nInternet appears to be unavailable.")
            print("Try again later.")
            return None
        
        try:
            # Create request with user agent
            req = self.urllib.Request(url, headers={'User-Agent': USER_AGENT})
            
            with self.urllib.urlopen(req, timeout=SOCKET_TIMEOUT) as response:
                # Check content length
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_kb = int(content_length) / 1024
                    if size_kb > MAX_PAGE_SIZE_KB:
                        print("\nPage too large: {:.1f} KB (max {} KB)".format(size_kb, MAX_PAGE_SIZE_KB))
                        return None
                
                html = response.read().decode('utf-8', errors='ignore')
                
                # Cache the result
                self.cache.set(url, html)
                return html
        except Exception as e:
            if is_internet_available():
                print("\nError fetching page: {}".format(str(e)))
            else:
                print("\nInternet appears to be unavailable.")
                print("Try again later.")
            return None
    
    def render_page(self, url):
        """Fetch and render a web page"""
        html = self.fetch_url(url)
        if not html:
            return False
        
        # Convert HTML to text with numbered links
        simplifier = HTMLSimplifier()
        text = simplifier.html_to_text(html)
        self.current_links = simplifier.get_links()
        
        # Wrap text to terminal width
        wrapped_lines = []
        for line in text.split('\n'):
            if line:
                wrapped = textwrap.wrap(line, width=TERM_WIDTH)
                wrapped_lines.extend(wrapped if wrapped else [''])
            else:
                wrapped_lines.append('')
        
        self.current_page = wrapped_lines
        self.current_url = url
        
        # Add to history
        if not self.history or self.history[-1] != url:
            self.history.append(url)
        
        return True
    
    def display_page(self, start_line=0):
        """Display page with pagination"""
        if not self.current_page:
            print("\nNo page loaded.")
            return
        
        total_lines = len(self.current_page)
        end_line = min(start_line + PAGE_SIZE, total_lines)
        
        # Display page content
        for i in range(start_line, end_line):
            print(self.current_page[i])
        
        # Show pagination info and links if any
        if end_line < total_lines:
            print("\n--- More --- ({}/{} lines)".format(end_line, total_lines))
        
        if self.current_links:
            print("\n{} links available on this page.".format(len(self.current_links)))
    
    def show_links(self):
        """Display numbered links from current page"""
        if not self.current_links:
            print("\nNo links found on current page.")
            return
        
        print("\nLinks on this page:")
        print("-" * 40)
        for num, url, text in self.current_links:
            # Truncate long link text
            text = text[:35] + '...' if len(text) > 35 else text
            print("{}. {}".format(num, text))
    
    def follow_link(self, link_num):
        """Follow a numbered link"""
        for num, url, text in self.current_links:
            if num == link_num:
                # Resolve relative URLs
                full_url = self._resolve_url(url)
                return self.render_page(full_url)
        
        print("\nInvalid link number.")
        return False
    
    def _resolve_url(self, url):
        """Resolve relative URLs to absolute"""
        if url.startswith('http://') or url.startswith('https://'):
            return url
        
        # Resolve relative URLs using urljoin
        return urljoin(self.current_url, url)
    
    def go_back(self):
        """Go back to previous page in history"""
        if len(self.history) > 1:
            self.history.pop()  # Remove current page
            prev_url = self.history[-1]
            return self.render_page(prev_url)
        else:
            print("\nNo previous page in history.")
            return False
    
    def search(self, query):
        """Search using configured search engine"""
        search_url = SEARCH_URL.format(query.replace(' ', '+'))
        return self.render_page(search_url)


def paginate_text(lines, page_size=PAGE_SIZE):
    """Display text with pagination"""
    total_lines = len(lines)
    start = 0
    
    while start < total_lines:
        end = min(start + page_size, total_lines)
        
        for i in range(start, end):
            print(lines[i])
        
        if end < total_lines:
            response = input("\n(press Enter, Q to quit) :> ").strip().lower()
            if response == 'q':
                break
        
        start = end


def show_logo():
    """Display ASCII art logo"""
    logo = r"""
 __      ____      ____      ____      __
/\ \  __/\  _`\   /\  _`\   /\  _`\   /\ \
\ \ \/\ \ \ \/\ \ \ \ \/\ \ \ \ \/\ \ \ \ \
 \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \
  \ \ \_/ \ \ \_\ \ \ \ \_\ \ \ \ \_\ \ \ \_\
   \ `\___/\ \____/  \ \____/  \ \____/  \/\_\
    `\/__/  \/___/    \/___/    \/___/    \/_/
"""
    print(logo)


def show_about():
    """Display about information"""
    print("\n" + "-" * 40)
    print("WWW v{} - Web Browser for Packet Radio".format(VERSION))
    print("-" * 40)
    print("\nA text-mode web browser designed for")
    print("low-bandwidth AX.25 packet radio.")
    print("\nFeatures:")
    print("- Numbered link navigation")
    print("- Text-only rendering")
    print("- Offline page caching")
    print("- Smart word wrapping")
    print("\nAuthor: Brad Brown KC1JMH")
    print("License: MIT")
    print("\nPress Enter to continue...")
    input()


def main():
    """Main application loop"""
    # Check for updates
    check_for_app_update(VERSION, APP_NAME)
    
    # Display logo and header
    show_logo()
    print("\nWWW v{} - Web Browser".format(VERSION))
    print("-" * 40)
    
    browser = WebBrowser()
    current_line = 0
    
    while True:
        print("\nMain Menu:")
        print("1) Home Page")
        print("2) Bookmarks")
        print("3) Search")
        print("4) Enter URL")
        print("5) View Links")
        print("6) Follow Link")
        print("7) Back")
        print("\nA) About  Q) Quit")
        
        choice = input("Menu: [1-7,A,Q] :> ").strip().lower()
        
        if choice == 'q':
            print("\nExiting...")
            break
        elif choice == 'a':
            show_about()
        elif choice == '1':
            print("\nLoading home page...")
            if browser.render_page(HOME_URL):
                browser.display_page()
                current_line = 0
        elif choice == '2':
            print("\nBookmarks:")
            print("-" * 40)
            for i, (name, url) in enumerate(BOOKMARKS, 1):
                print("{}. {}".format(i, name))
            
            bookmark_choice = input("\nSelect [1-{}], Q :> ".format(len(BOOKMARKS))).strip()
            if bookmark_choice.isdigit():
                idx = int(bookmark_choice) - 1
                if 0 <= idx < len(BOOKMARKS):
                    name, url = BOOKMARKS[idx]
                    print("\nLoading {}...".format(name))
                    if browser.render_page(url):
                        browser.display_page()
                        current_line = 0
        elif choice == '3':
            query = input("\nSearch query :> ").strip()
            if query:
                print("\nSearching...")
                if browser.search(query):
                    browser.display_page()
                    current_line = 0
        elif choice == '4':
            url = input("\nEnter URL :> ").strip()
            if url:
                if not url.startswith('http'):
                    url = 'http://' + url
                print("\nLoading...")
                if browser.render_page(url):
                    browser.display_page()
                    current_line = 0
        elif choice == '5':
            browser.show_links()
        elif choice == '6':
            link_num = input("\nLink number :> ").strip()
            if link_num.isdigit():
                print("\nFollowing link {}...".format(link_num))
                if browser.follow_link(int(link_num)):
                    browser.display_page()
                    current_line = 0
        elif choice == '7':
            if browser.go_back():
                browser.display_page()
                current_line = 0


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        if is_internet_available():
            print("\nError: {}".format(str(e)))
        else:
            print("\nInternet appears to be unavailable.")
            print("Try again later.")
        sys.exit(1)
