#!/usr/bin/env python3
"""
WWW Browser for Packet Radio
------------------------------
A text-mode web browser for AX.25 packet radio via linbpq BBS.
Designed for low-bandwidth, ASCII-only browsing with numbered links.

Features:
- Text-mode HTML rendering (strips JavaScript, CSS)
- Intelligent nav/content link separation (S for site menu)
- Numbered link navigation (recursive browsing)
- Pagination at 24 lines per page
- Bookmarks for packet-radio-friendly sites
- Search via FrogFind.com (text-only search engine)
- Offline caching (last 10 pages, 24-hour expiry)
- Smart word wrapping for terminal width

Author: Brad Brown KC1JMH
Version: 1.8
Date: January 2026
"""

import sys
import os
import json
import shutil
import time
import re
import socket
try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse

VERSION = "1.8"
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
        
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read().decode('utf-8')
        
        version_match = re.search(r'Version:\s*([0-9.]+)', content)
        if version_match:
            github_version = version_match.group(1)
            
            if compare_versions(github_version, current_version) > 0:
                print("\nUpdate available: v{} -> v{}".format(current_version, github_version))
                print("Downloading new version...")
                
                script_path = os.path.abspath(__file__)
                try:
                    temp_path = script_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                             stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    os.replace(temp_path, script_path)
                    
                    print("Updated to v{}. Restarting...".format(github_version))
                    print()
                    sys.stdout.flush()
                    restart_args = [script_path] + sys.argv[1:]
                    os.execv(script_path, restart_args)
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
        
        # Check if www.conf is missing and download it
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
                pass
    except Exception:
        pass


def ensure_htmlview_module():
    """Ensure htmlview.py module is available and up-to-date"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(script_dir, 'htmlview.py')
    
    try:
        import urllib.request
        import stat
        
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/htmlview.py"
        
        # Check if module exists
        if os.path.exists(module_path):
            # Read current version
            try:
                with open(module_path, 'r') as f:
                    local_content = f.read()
                local_match = re.search(r'Version:\s*([0-9.]+)', local_content)
                local_version = local_match.group(1) if local_match else "0.0"
            except:
                local_version = "0.0"
            
            # Check for update
            try:
                with urllib.request.urlopen(github_url, timeout=3) as response:
                    remote_content = response.read().decode('utf-8')
                remote_match = re.search(r'Version:\s*([0-9.]+)', remote_content)
                remote_version = remote_match.group(1) if remote_match else "0.0"
                
                if compare_versions(remote_version, local_version) > 0:
                    # Update available
                    temp_path = module_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(remote_content.encode('utf-8'))
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                             stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    os.replace(temp_path, module_path)
            except:
                pass  # Update check failed, use existing
        else:
            # Download module
            with urllib.request.urlopen(github_url, timeout=3) as response:
                content = response.read()
            with open(module_path, 'wb') as f:
                f.write(content)
            os.chmod(module_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                     stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    except Exception:
        pass  # Silent failure - will use fallback if needed


def compare_versions(version1, version2):
    """Compare two version strings"""
    v1_parts = [int(x) for x in version1.split('.')]
    v2_parts = [int(x) for x in version2.split('.')]
    
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
        socket.create_connection(('8.8.8.8', 53), timeout=2)
        return True
    except OSError:
        return False


def get_terminal_width():
    """Get terminal width, fallback to 80 for non-TTY/inetd."""
    try:
        return shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        return 80


def load_config():
    """Load configuration from www.conf JSON file with fallback to defaults"""
    defaults = {
        'home': 'http://ws1sm.com',
        'search_url': 'https://frogfind.com/?q={}',
        'bookmarks': [
            {'name': 'WS1SM Club', 'url': 'http://ws1sm.com'},
            {'name': 'Maine Packet Radio', 'url': 'https://mainepacketradio.org'},
            {'name': 'ARRL Home', 'url': 'http://www.arrl.org'},
            {'name': 'ARRL News', 'url': 'http://www.arrl.org/news'},
            {'name': 'eHam.net', 'url': 'http://www.eham.net'},
            {'name': 'Textfiles.com', 'url': 'http://www.textfiles.com'}
        ],
        'page_size': 24,
        'max_page_size_kb': 200,
        'socket_timeout': 15,
        'user_agent': 'Mozilla/5.0 (compatible; WWW/1.2; +packet-radio)'
    }
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'www.conf')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            for key in defaults:
                if key not in config:
                    config[key] = defaults[key]
            return config
    except (IOError, OSError, ValueError):
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
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (IOError, OSError, ValueError):
            return {}
    
    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except (IOError, OSError):
            pass
    
    def get(self, key):
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
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]
        self.cache[key] = (time.time(), data)
        self._save_cache()


class WebBrowser:
    """Web browser using htmlview module for rendering"""
    
    def __init__(self):
        self.cache = PageCache()
        self.history = []
        self.current_url = HOME_URL
        self.current_html = ""
        self.viewer = None
        self.htmlview = None
        
        # Try to import htmlview module
        try:
            import htmlview
            self.htmlview = htmlview
            self.viewer = htmlview.HTMLViewer(term_width=TERM_WIDTH, page_size=PAGE_SIZE)
        except ImportError:
            self.htmlview = None
            self.viewer = None
        
        try:
            import urllib.request
            self.urllib = urllib.request
        except ImportError:
            print("Error: urllib.request not available")
            sys.exit(1)
    
    def fetch_url(self, url):
        """Fetch URL and return HTML content"""
        cached = self.cache.get(url)
        if cached:
            return cached
        
        if not is_internet_available():
            print("\nInternet appears to be unavailable.")
            print("Try again later.")
            return None
        
        try:
            req = self.urllib.Request(url, headers={'User-Agent': USER_AGENT})
            
            with self.urllib.urlopen(req, timeout=SOCKET_TIMEOUT) as response:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_kb = int(content_length) / 1024
                    if size_kb > MAX_PAGE_SIZE_KB:
                        print("\nPage too large: {:.1f} KB (max {} KB)".format(size_kb, MAX_PAGE_SIZE_KB))
                        return None
                
                html = response.read().decode('utf-8', errors='ignore')
                self.cache.set(url, html)
                return html
        except Exception as e:
            if is_internet_available():
                print("\nError fetching page: {}".format(str(e)))
            else:
                print("\nInternet appears to be unavailable.")
                print("Try again later.")
            return None
    
    def browse(self, url):
        """Browse to a URL using htmlview module"""
        html = self.fetch_url(url)
        if not html:
            # Fetch failed - return to previous page if available
            if len(self.history) > 0:
                resp = input("\n[Q)uit Enter=back] :> ").strip().lower()
                if resp.startswith('q'):
                    print("\nExiting...")
                    sys.exit(0)
                prev_url = self.history[-1] if self.history else None
                return prev_url
            return None
        
        self.current_html = html
        self.current_url = url
        
        # Add to history
        if not self.history or self.history[-1] != url:
            self.history.append(url)
        
        # Use htmlview module if available
        if self.viewer:
            selected_url = self.viewer.view(html, base_url=url)
            
            if self.viewer.go_back:
                return self.go_back()
            
            return selected_url
        else:
            # Fallback: basic display without htmlview
            print("\n[htmlview module not available - basic mode]")
            print(html[:2000])
            return None
    
    def go_back(self):
        """Go back to previous page in history"""
        if len(self.history) > 1:
            self.history.pop()
            prev_url = self.history[-1]
            return prev_url
        else:
            print("\nNo previous page in history.")
            return None
    
    def search(self, query):
        """Search using configured search engine"""
        search_url = SEARCH_URL.format(query.replace(' ', '+'))
        return search_url


def show_logo():
    """Display ASCII art logo"""
    logo = r"""
__      ____      ____      __
\ \ /\ / /\ \ /\ / /\ \ /\ / /
 \ V  V /  \ V  V /  \ V  V / 
  \_/\_/    \_/\_/    \_/\_/  
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
    print("- S)ite menu separates nav from content")
    print("- Numbered link navigation")
    print("- Text-only rendering")
    print("- Offline page caching")
    print("- Smart word wrapping")
    print("\nPage Navigation:")
    print("  Enter = next page")
    print("  S = site menu (site navigation)")
    print("  L = content links")
    print("  # = follow link by number")
    print("  B = back, Q = quit to menu")
    print("\nAuthor: Brad Brown KC1JMH")
    print("License: MIT")
    resp = input("\n[Q)uit Enter=continue] :> ").strip().upper()
    if resp == 'Q':
        print("\nExiting...")
        sys.exit(0)


def main():
    """Main application loop"""
    # Check for updates and ensure htmlview module
    check_for_app_update(VERSION, APP_NAME)
    ensure_htmlview_module()
    
    # Display logo and header
    show_logo()
    print("\nWWW v{} - Web Browser".format(VERSION))
    print("-" * 40)
    
    browser = WebBrowser()
    current_url = None
    
    while True:
        print("\nMain Menu:")
        print("1) Home Page")
        print("2) Bookmarks")
        print("3) Search")
        print("4) Enter URL")
        print("5) Back")
        print("\nA) About  Q) Quit")
        
        choice = input("Menu: [1-5,A,Q] :> ").strip().lower()
        
        if choice == 'q':
            print("\nExiting...")
            break
        elif choice == 'a':
            show_about()
        elif choice == '1':
            print("\nLoading home page...")
            sys.stdout.flush()
            current_url = HOME_URL
        elif choice == '2':
            print("\nBookmarks:")
            print("-" * 40)
            for i, (name, url) in enumerate(BOOKMARKS, 1):
                print("{}. {}".format(i, name))
            
            bookmark_choice = input("\nQ)uit M)ain [1-{}] :> ".format(len(BOOKMARKS))).strip().lower()
            if bookmark_choice == 'q':
                print("\nExiting...")
                sys.exit(0)
            elif bookmark_choice == 'm' or bookmark_choice == '':
                current_url = None
            elif bookmark_choice.isdigit():
                idx = int(bookmark_choice) - 1
                if 0 <= idx < len(BOOKMARKS):
                    name, url = BOOKMARKS[idx]
                    print("\nLoading {}...".format(name))
                    sys.stdout.flush()
                    current_url = url
                else:
                    current_url = None
            else:
                current_url = None
        elif choice == '3':
            query = input("\nSearch query :> ").strip()
            if query:
                print("\nSearching...")
                sys.stdout.flush()
                current_url = browser.search(query)
            else:
                current_url = None
        elif choice == '4':
            url = input("\nEnter URL :> ").strip()
            if url:
                if not url.startswith('http'):
                    url = 'http://' + url
                print("\nLoading...")
                sys.stdout.flush()
                current_url = url
            else:
                current_url = None
        elif choice == '5':
            back_url = browser.go_back()
            if back_url:
                print("\nGoing back...")
                sys.stdout.flush()
                current_url = back_url
            else:
                current_url = None
        else:
            current_url = None
        
        # Browse loop - follow links until user returns to menu
        while current_url:
            next_url = browser.browse(current_url)
            if next_url == '__EXIT__':
                # User pressed Q)uit - exit app
                print("\nExiting...")
                sys.exit(0)
            elif next_url == '__MAIN__':
                # User pressed M)ain - return to main menu
                current_url = None
            elif next_url:
                print("\nLoading...")
                sys.stdout.flush()
                current_url = next_url
            else:
                current_url = None


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
