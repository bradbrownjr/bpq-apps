#!/usr/bin/env python3
"""
Wikipedia Browser for Packet Radio
-----------------------------------
Browse Wikipedia and sister projects over AX.25 packet radio via linbpq BBS.

Features:
- Search Wikipedia, Simple Wikipedia, Wiktionary, Wikiquote, Wikinews, Wikivoyage
- Article summaries with full text option
- Numbered link navigation (recursive browsing)
- Pagination for long content
- Smart word wrapping for terminal width
- Offline caching (last 10 summaries, 24-hour expiry)
- Random articles

Author: Brad Brown KC1JMH
Version: 2.11
Date: February 2026
"""

import sys
import os
import json
import shutil
import time
import re
import textwrap
import socket

# Try to import htmlview module (auto-downloaded if needed)
try:
    import htmlview
except ImportError:
    htmlview = None

VERSION = "2.11"
APP_NAME = "wiki.py"

# Check Python version
if sys.version_info < (3, 5):
    print("Error: This script requires Python 3.5 or later.")
    print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ))
    print("\nPlease run with: python3 wiki.py")
    sys.exit(1)

def ensure_htmlview_module():
    """Ensure htmlview module is available and up-to-date"""
    try:
        if htmlview:
            htmlview.ensure_htmlview_available()
    except:
        pass

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
                    
                    print("Updated to v{}. Restarting...".format(github_version))
                    print()
                    sys.stdout.flush()
                    restart_args = [script_path] + sys.argv[1:]
                    os.execv(script_path, restart_args)
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    # Clean up temp file if it exists
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
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
    try:
        parts1 = [int(x) for x in str(version1).split('.')]
        parts2 = [int(x) for x in str(version2).split('.')]
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0
    except (ValueError, AttributeError):
        return 0

def is_internet_available():
    """Quick check if internet is available"""
    try:
        socket.create_connection(('8.8.8.8', 53), timeout=2)
        return True
    except (socket.timeout, socket.error, OSError):
        return False

def get_line_width():
    """Get current terminal width dynamically"""
    try:
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        return columns if columns > 0 else 80
    except Exception:
        return 80

def sanitize_for_ascii(text):
    """Remove non-ASCII and special Unicode characters for terminal display"""
    if not text:
        return text
    
    # Keep basic ASCII printable chars and common symbols
    result = ""
    for char in text:
        # Keep ASCII printable (32-126) plus newline, tab
        if ord(char) < 127 or char == '\n':
            result += char
        elif ord(char) > 127:
            # Replace non-ASCII with placeholder or skip
            # Skip it entirely to keep output clean
            pass
    
    # Clean up multiple spaces
    result = re.sub(r' +', ' ', result)
    # Remove extra newlines
    result = re.sub(r'\n\n\n+', '\n\n', result)
    
    return result.strip()

# Configuration
PAGE_SIZE = 20  # Lines per page for pagination
MAX_LINKS = 50  # Max links to show initially
CACHE_FILE = "wiki_cache.json"
CACHE_MAX_ENTRIES = 10
CACHE_EXPIRY_HOURS = 24

# Wiki project configurations
WIKI_PROJECTS = {
    '1': {
        'name': 'Wikipedia',
        'domain': 'en.wikipedia.org',
        'description': 'Free encyclopedia'
    },
    '2': {
        'name': 'Simple Wikipedia',
        'domain': 'simple.wikipedia.org',
        'description': 'Easier reading level'
    },
    '3': {
        'name': 'Random Article',
        'domain': 'en.wikipedia.org',
        'description': 'Surprise me!'
    },
    '4': {
        'name': 'Wiktionary',
        'domain': 'en.wiktionary.org',
        'description': 'Dictionary'
    },
    '5': {
        'name': 'Wikiquote',
        'domain': 'en.wikiquote.org',
        'description': 'Quotations'
    },
    '6': {
        'name': 'Wikinews',
        'domain': 'en.wikinews.org',
        'description': 'Current events'
    },
    '7': {
        'name': 'Wikivoyage',
        'domain': 'en.wikivoyage.org',
        'description': 'Travel guides'
    }
}


class WikiCache:
    """Simple cache for article summaries"""
    
    def __init__(self, cache_file):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Load cache from disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass
    
    def get(self, key):
        """Get cached entry if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            age_hours = (time.time() - entry['timestamp']) / 3600
            if age_hours < CACHE_EXPIRY_HOURS:
                return entry['data']
        return None
    
    def set(self, key, data):
        """Set cache entry with timestamp"""
        # Remove oldest entry if cache is full
        if len(self.cache) >= CACHE_MAX_ENTRIES:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'timestamp': time.time(),
            'data': data
        }
        self._save_cache()


class WikiClient:
    """MediaWiki API client for Wikipedia and sister projects"""
    
    def __init__(self):
        self.cache = WikiCache(CACHE_FILE)
        self.current_project = 'en.wikipedia.org'
        self.current_article = None
        self.current_links = []
        self.session_history = []
        self.history_index = -1  # Track position in history
        self.should_quit = False  # Flag to exit app
        
        # Import requests library
        try:
            import requests
            # Use session with proper User-Agent (required by Wikipedia)
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'WikiTermBrowser/{} (https://github.com/bradbrownjr/bpq-apps; text terminal client)'.format(VERSION)
            })
        except ImportError:
            print("Error: requests library not found.")
            print("Install with: pip3 install requests")
            sys.exit(1)
    
    def _make_request(self, url, params, timeout=10):
        """Make HTTP request with timeout and error handling"""
        import requests
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print("\nRequest timed out. Try again later.")
            return None
        except requests.exceptions.RequestException as e:
            if not is_internet_available():
                print("\nInternet appears to be unavailable.")
                print("Try again later.")
            else:
                print("\nError fetching data: {}".format(str(e)))
            return None
    
    def search_wiki(self, query, limit=20):
        """Search wiki for articles matching query"""
        cache_key = "search:{}:{}".format(self.current_project, query)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        url = "https://{}/w/api.php".format(self.current_project)
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'format': 'json',
            'srlimit': limit
        }
        
        data = self._make_request(url, params)
        if data and 'query' in data and 'search' in data['query']:
            results = data['query']['search']
            self.cache.set(cache_key, results)
            return results
        return []
    
    def get_random(self):
        """Get random article title"""
        url = "https://{}/w/api.php".format(self.current_project)
        params = {
            'action': 'query',
            'list': 'random',
            'rnnamespace': 0,
            'rnlimit': 1,
            'format': 'json'
        }
        
        data = self._make_request(url, params)
        if data and 'query' in data and 'random' in data['query']:
            return data['query']['random'][0]['title']
        return None
    
    def get_summary(self, title):
        """Get article summary (first paragraph)"""
        cache_key = "summary:{}:{}".format(self.current_project, title)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Try REST API first (works best for Wikipedia)
        if 'wikipedia' in self.current_project:
            url = "https://{}/api/rest_v1/page/summary/{}".format(
                self.current_project, 
                title.replace(' ', '_')
            )
            
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                summary = {
                    'title': data.get('title', title),
                    'extract': sanitize_for_ascii(data.get('extract', '')),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
                }
                
                self.cache.set(cache_key, summary)
                return summary
            except Exception:
                pass
        
        # Fallback: Use MediaWiki API extract for Wiktionary and other projects
        url = "https://{}/w/api.php".format(self.current_project)
        params = {
            'action': 'query',
            'prop': 'extracts',
            'titles': title,
            'exintro': 1,  # Only intro section
            'explaintext': 1,
            'format': 'json'
        }
        
        data = self._make_request(url, params)
        if data and 'query' in data and 'pages' in data['query']:
            pages = data['query']['pages']
            page_id = list(pages.keys())[0]
            if page_id != '-1':
                extract = pages[page_id].get('extract', '')
                summary = {
                    'title': title,
                    'extract': sanitize_for_ascii(extract),
                    'url': ''
                }
                self.cache.set(cache_key, summary)
                return summary
        
        if not is_internet_available():
            print("\nInternet appears to be unavailable.")
            print("Try again later.")
        return None
    
    def get_full_text(self, title):
        """Get full article text (plain text)"""
        url = "https://{}/w/api.php".format(self.current_project)
        params = {
            'action': 'query',
            'prop': 'extracts',
            'titles': title,
            'explaintext': 1,
            'format': 'json'
        }
        
        data = self._make_request(url, params)
        if data and 'query' in data and 'pages' in data['query']:
            pages = data['query']['pages']
            page_id = list(pages.keys())[0]
            if page_id != '-1':  # -1 means page not found
                text = pages[page_id].get('extract', '')
                return sanitize_for_ascii(text)
        return None
    
    def get_links(self, title, limit=500):
        """Get internal links from article"""
        url = "https://{}/w/api.php".format(self.current_project)
        params = {
            'action': 'query',
            'prop': 'links',
            'titles': title,
            'pllimit': limit,
            'plnamespace': 0,  # Only article links (no categories, files, etc.)
            'format': 'json'
        }
        
        data = self._make_request(url, params)
        if data and 'query' in data and 'pages' in data['query']:
            pages = data['query']['pages']
            page_id = list(pages.keys())[0]
            if page_id != '-1' and 'links' in pages[page_id]:
                return [link['title'] for link in pages[page_id]['links']]
        return []
    
    def filter_links_in_text(self, all_links, text):
        """Filter links to only those whose titles appear in the text"""
        text_lower = text.lower()
        found_links = []
        seen = set()
        
        for link in all_links:
            link_lower = link.lower()
            # Check if link title appears in text (as whole word or phrase)
            if link_lower in text_lower and link_lower not in seen:
                found_links.append(link)
                seen.add(link_lower)
        
        # Sort by order of appearance in text
        found_links.sort(key=lambda x: text_lower.find(x.lower()))
        return found_links
    
    def insert_link_markers(self, text, links):
        """Insert [#] markers after link terms in text"""
        if not links:
            return text
        
        # Build a mapping of link -> number
        # Process longer links first to avoid partial matches
        sorted_links = sorted(links, key=len, reverse=True)
        link_nums = {link.lower(): links.index(link) + 1 for link in links}
        
        result = text
        marked = set()  # Track positions we've already marked
        
        for link in sorted_links:
            link_lower = link.lower()
            num = link_nums[link_lower]
            
            # Find all occurrences (case-insensitive)
            search_text = result.lower()
            pos = 0
            new_result = ""
            last_end = 0
            
            while True:
                idx = search_text.find(link_lower, pos)
                if idx == -1:
                    break
                
                # Check if this is a word boundary match
                before_ok = idx == 0 or not result[idx-1].isalnum()
                after_idx = idx + len(link)
                after_ok = after_idx >= len(result) or not result[after_idx].isalnum()
                
                # Check if not already marked (look for existing [#])
                already_marked = after_idx < len(result) and result[after_idx:after_idx+1] == '['
                
                if before_ok and after_ok and not already_marked and idx not in marked:
                    # Insert marker after first occurrence only
                    new_result += result[last_end:after_idx] + "[{}]".format(num)
                    last_end = after_idx
                    marked.add(idx)
                    # Only mark first occurrence of each link
                    break
                
                pos = idx + 1
            
            if new_result:
                new_result += result[last_end:]
                result = new_result
                search_text = result.lower()
        
        return result
    
    def wrap_text(self, text, width=None, add_paragraph_spacing=False):
        """Wrap text to terminal width with proper word wrapping"""
        if width is None:
            width = get_line_width()
        
        wrapped_lines = []
        paragraphs = text.split('\n')
        
        for i, para in enumerate(paragraphs):
            if not para.strip():
                wrapped_lines.append('')
            elif len(para) <= width:
                wrapped_lines.append(para)
            else:
                wrapped = textwrap.fill(para, width=width, 
                                      break_long_words=False,
                                      break_on_hyphens=False)
                wrapped_lines.append(wrapped)
            
            # Add blank line between paragraphs for readability
            if add_paragraph_spacing and para.strip() and i < len(paragraphs) - 1:
                wrapped_lines.append('')
        
        return '\n'.join(wrapped_lines)
    
    def display_article(self, content, title=None, paginate=True, add_paragraph_spacing=False):
        """Display article with optional pagination"""
        width = get_line_width()
        if title:
            print("\n" + "=" * min(40, width))
            print(title)
            print("=" * min(40, width))
        
        wrapped = self.wrap_text(content, add_paragraph_spacing=add_paragraph_spacing)
        lines = wrapped.split('\n')
        
        if not paginate or len(lines) <= PAGE_SIZE:
            print(wrapped)
            return
        
        # Paginated display
        page_num = 1
        total_pages = (len(lines) + PAGE_SIZE - 1) // PAGE_SIZE
        
        for i in range(0, len(lines), PAGE_SIZE):
            chunk = lines[i:i + PAGE_SIZE]
            
            if i > 0:  # Not first page
                print("\n" + "-" * min(40, get_line_width()))
                print("Page {}/{}".format(page_num, total_pages))
                print("-" * min(40, get_line_width()))
            
            print('\n'.join(chunk))
            
            page_num += 1
            if i + PAGE_SIZE < len(lines):
                # Show link navigation prompt during pagination
                if self.current_links:
                    prompt = "\nQ)uit M)enu [1-{}] Enter=more :> ".format(len(self.current_links))
                else:
                    prompt = "\nQ)uit M)enu Enter=more :> "
                
                response = input(prompt).strip()
                
                if response.upper() == 'Q':
                    self.should_quit = True  # Signal to exit app
                    break
                elif response.upper() == 'M':
                    return
                elif response.isdigit() and self.current_links:
                    # Handle link navigation
                    link_num = int(response)
                    if 1 <= link_num <= len(self.current_links):
                        return ('link', link_num - 1)
                    else:
                        print("Invalid link number.")
                        resp = input("[Q)uit Enter=continue] :> ").strip().upper()
                        if resp == 'Q':
                            self.should_quit = True
                            break
    
    def display_links(self, links, max_display=MAX_LINKS):
        """Display numbered list of links"""
        if not links:
            print("\nNo links found in this article.")
            return
        
        display_links = links[:max_display]
        has_more = len(links) > max_display
        
        print("\n" + "-" * min(40, get_line_width()))
        print("Article Links ({} total)".format(len(links)))
        print("-" * min(40, get_line_width()))
        
        width = get_line_width()
        for i, link in enumerate(display_links, 1):
            # Wrap long link titles
            if len(link) > width - 6:
                wrapped = textwrap.fill(link, width=width - 6,
                                      initial_indent="{}. ".format(i),
                                      subsequent_indent="   ")
                print(wrapped)
            else:
                print("{}. {}".format(i, link))
        
        if has_more:
            print("\n[M]ore links available ({} more)".format(len(links) - max_display))
    
    def display_search_results(self, results, page_size=5):
        """Display paginated search results, return selected article or None"""
        if not results:
            print("\nNo results found.")
            return None
        
        page = 0
        total = len(results)
        
        while True:
            start = page * page_size
            end = min(start + page_size, total)
            page_results = results[start:end]
            
            width = get_line_width()
            print("\n" + "-" * min(40, width))
            print("Search Results ({}-{} of {})".format(start + 1, end, total))
            print("-" * min(40, width))
            
            for i, result in enumerate(page_results, start + 1):
                title = result['title']
                # Strip HTML tags and sanitize for ASCII terminal
                snippet = re.sub(r'<[^>]+>', '', result.get('snippet', ''))
                snippet = sanitize_for_ascii(snippet)
                
                print("\n{}. {}".format(i, title))
                # Wrap snippet
                if snippet:
                    wrapped = textwrap.fill(snippet, width=width - 3,
                                          initial_indent="   ",
                                          subsequent_indent="   ")
                    print(wrapped)
            
            # Build prompt
            has_next = end < total
            if has_next:
                prompt = "\nQ)uit M)enu [1-{}] Enter=next :> ".format(total)
            else:
                prompt = "\nQ)uit M)enu [1-{}] :> ".format(total)
            
            choice = input(prompt).strip().upper()
            
            if choice == 'Q':
                return None
            elif choice == 'M':
                return None
            elif choice == 'N' and has_next:
                page += 1
            elif choice == '' and has_next:
                page += 1
            elif choice.isdigit():
                num = int(choice)
                if 1 <= num <= total:
                    return results[num - 1]
                else:
                    print("Invalid selection (1-{}).".format(total))
            else:
                print("Invalid input.")
    
    def handle_article_view(self, title, add_to_history=True):
        """Handle article viewing with summary/full/links options"""
        # Check if user quit from previous screen
        if self.should_quit:
            return
        
        # Store current article
        self.current_article = title
        
        # Track history
        if add_to_history:
            # Remove any forward history when navigating to a new article
            self.session_history = self.session_history[:self.history_index + 1]
            self.session_history.append(title)
            self.history_index = len(self.session_history) - 1
        
        # Get summary
        print("\nFetching article...")
        summary_data = self.get_summary(title)
        
        if not summary_data:
            print("Could not fetch article.")
            return
        
        # Display summary
        width = get_line_width()
        print("\n" + "=" * min(40, width))
        print(summary_data['title'])
        print("=" * min(40, width))
        summary_text = summary_data['extract']
        
        # Get links that appear in the summary text
        all_links = self.get_links(title)
        self.current_links = self.filter_links_in_text(all_links, summary_text)
        self.all_article_links = all_links  # Keep all links for full article
        
        # For Wiktionary and other non-Wikipedia projects, skip blank summary and go straight to full article
        if not summary_text.strip() and 'wikipedia' not in self.current_project:
            print("\nFetching full article...")
            full_text = self.get_full_text(title)
            if full_text:
                # Update links to those found in full article
                self.current_links = self.filter_links_in_text(self.all_article_links, full_text)
                # Insert inline link markers
                marked_text = self.insert_link_markers(full_text, self.current_links)
                result = self.display_article(marked_text, title, paginate=True, add_paragraph_spacing=True)
                # Check if user quit during pagination
                if self.should_quit:
                    return
                # Handle link navigation during pagination
                if isinstance(result, tuple) and result[0] == 'link':
                    link_title = self.current_links[result[1]]
                    self.handle_article_view(link_title)
            else:
                print("Could not fetch full article.")
            return
        
        # Insert inline link markers and display summary (for Wikipedia)
        marked_text = self.insert_link_markers(summary_text, self.current_links)
        print(self.wrap_text(marked_text))
        
        # Article menu loop
        while True:
            print("\n" + "-" * min(40, width))
            if self.current_links:
                can_back = self.history_index > 0
                if can_back:
                    prompt = "Q)uit M)enu B)ack [F]ull [L]inks [1-{}] :> ".format(len(self.current_links))
                else:
                    prompt = "Q)uit M)enu [F]ull [L]inks [1-{}] :> ".format(len(self.current_links))
            else:
                can_back = self.history_index > 0
                if can_back:
                    prompt = "Q)uit M)enu B)ack [F]ull :> "
                else:
                    prompt = "Q)uit M)enu [F]ull :> "
            
            choice = input(prompt).strip().upper()
            
            if choice == 'Q':
                self.should_quit = True
                break
            elif choice == 'M':
                break
            elif choice == 'B' and self.history_index > 0:
                # Go back to previous article
                self.history_index -= 1
                prev_title = self.session_history[self.history_index]
                self.handle_article_view(prev_title, add_to_history=False)
                break
            elif choice == 'F':
                # Show full article
                print("\nFetching full article...")
                full_text = self.get_full_text(title)
                if full_text:
                    # Update links to those found in full article
                    self.current_links = self.filter_links_in_text(self.all_article_links, full_text)
                    # Insert inline link markers
                    marked_text = self.insert_link_markers(full_text, self.current_links)
                    result = self.display_article(marked_text, title, paginate=True, add_paragraph_spacing=True)
                    # Check if user quit during pagination
                    if self.should_quit:
                        break
                    # Handle link navigation during pagination
                    if isinstance(result, tuple) and result[0] == 'link':
                        link_title = self.current_links[result[1]]
                        self.handle_article_view(link_title)
                        break
                else:
                    print("Could not fetch full article.")
            elif choice == 'L' and self.current_links:
                # Show links
                self.display_links(self.current_links)
            elif choice.isdigit() and self.current_links:
                # Navigate to numbered link
                link_num = int(choice)
                if 1 <= link_num <= len(self.current_links):
                    link_title = self.current_links[link_num - 1]
                    self.handle_article_view(link_title)
                    break
                else:
                    print("Invalid link number (1-{}).".format(len(self.current_links)))
            elif choice == 'M' and len(self.current_links) > MAX_LINKS:
                # Show more links
                self.display_links(self.current_links, max_display=len(self.current_links))
            else:
                print("Invalid choice.")
    
    def handle_search(self):
        """Handle search interface"""
        query = input("\nSearch query :> ").strip()
        if not query:
            return
        
        print("\nSearching...")
        results = self.search_wiki(query)
        
        # Display paginated results and get selection
        selected = self.display_search_results(results)
        
        if selected:
            self.handle_article_view(selected['title'], add_to_history=True)
    
    def handle_random(self):
        """Handle random article"""
        print("\nFetching random article...")
        title = self.get_random()
        if title:
            self.handle_article_view(title, add_to_history=True)
        else:
            print("Could not fetch random article.")
    
    def show_menu(self):
        """Display main menu"""
        logo = r"""
          _ _    _ 
__      _(_) | _(_)
\ \ /\ / / | |/ / |
 \ V  V /| |   <| |
  \_/\_/ |_|_|\_\_|
"""
        print(logo)
        print("WIKI v{} - Wikipedia for Packet Radio".format(VERSION))
        print("-" * min(40, get_line_width()))
        print("1) Search Wikipedia")
        print("2) Simple Wikipedia (easier reading)")
        print("3) Random Article")
        print("4) Wiktionary (dictionary)")
        print("5) Wikiquote (quotations)")
        print("6) Wikinews (current events)")
        print("7) Wikivoyage (travel guides)")
        print("\nA) About  Q) Quit")
    
    def show_about(self):
        """Show about information"""
        about = """
WIKI v{} - Wikipedia for Packet Radio

Browse Wikipedia and sister projects over AX.25
packet radio networks.

Features:
- Search and browse articles
- Smart word wrapping
- Numbered link navigation
- Article summaries with full text option
- Random articles
- Offline caching

Projects: Wikipedia, Simple Wikipedia,
Wiktionary, Wikiquote, Wikinews, Wikivoyage

Author: Brad Brown KC1JMH
GitHub: bradbrownjr/bpq-apps
""".format(VERSION)
        print(about)
    
    def run(self):
        """Main application loop"""
        while True:
            # Exit if quit flag was set
            if self.should_quit:
                print("\nExiting...")
                break
            
            self.show_menu()
            choice = input("\nMenu :> ").strip().upper()
            
            if choice == 'Q':
                print("\nExiting...")
                break
            elif choice == 'A':
                self.show_about()
            elif choice in ['1', '2', '4', '5', '6', '7']:
                # Switch project
                if choice in WIKI_PROJECTS:
                    project = WIKI_PROJECTS[choice]
                    self.current_project = project['domain']
                    print("\n{} - {}".format(project['name'], project['description']))
                    self.handle_search()
            elif choice == '3':
                # Random article (always from main Wikipedia)
                self.current_project = 'en.wikipedia.org'
                self.handle_random()
            else:
                print("\nInvalid choice. Enter 1-7, A, or Q.")


def main():
    """Main entry point"""
    # Handle command-line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--check-update', '-u']:
            # Explicit update check with error reporting
            print("Checking for updates...")
            try:
                import urllib.request
                github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(APP_NAME)
                print("Fetching: {}".format(github_url))
                with urllib.request.urlopen(github_url, timeout=5) as response:
                    content = response.read().decode('utf-8')
                
                # Extract version from docstring
                version_match = re.search(r'Version:\s*([0-9.]+)', content)
                if version_match:
                    github_version = version_match.group(1)
                    print("GitHub version: {}".format(github_version))
                    print("Local version: {}".format(VERSION))
                    
                    cmp = compare_versions(github_version, VERSION)
                    if cmp > 0:
                        print("\nUpdate available! v{} -> v{}".format(VERSION, github_version))
                        print("Restart the app to download and install.")
                    elif cmp == 0:
                        print("\nAlready on latest version: {}".format(VERSION))
                    else:
                        print("\nLocal version is newer than GitHub: {} > {}".format(VERSION, github_version))
                else:
                    print("ERROR: Could not find Version in GitHub file")
            except Exception as e:
                print("ERROR: {}".format(str(e)))
            sys.exit(0)
        elif sys.argv[1] in ['-h', '--help', '/?']:
            print("Usage: {} [OPTIONS]".format(APP_NAME))
            print("\nOPTIONS:")
            print("  -u, --check-update   Check for updates from GitHub")
            print("  -h, --help          Show this help message")
            sys.exit(0)
    
    # Check for updates (runs in background, 3-second timeout)
    ensure_htmlview_module()
    check_for_app_update(VERSION, APP_NAME)
    
    # Run application
    client = WikiClient()
    client.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        if is_internet_available():
            print("\nError: {}".format(str(e)))
            print("Please report this issue if it persists.")
        else:
            print("\nInternet appears to be unavailable.")
            print("Try again later.")
