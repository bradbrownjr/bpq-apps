#!/usr/bin/env python3
"""
RSS Feed Reader for Packet Radio
---------------------------------
A simple text-based RSS feed reader designed for use over
AX.25 packet radio via linbpq BBS software.

Features:
- Plain ASCII text interface (no control codes)
- Categorized feeds from configuration file
- Article size prefetch with pagination option
- Clean text extraction from web articles
- Simple command-based navigation

Author: Brad Brown KC1JMH
Version: 1.3
Date: January 2026
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
    print("\nPlease run with: python3 rss-news.py")
    sys.exit(1)

import os
import csv
import re
import textwrap
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from html import unescape
from datetime import datetime
import subprocess
import tempfile

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
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
                    sys.exit(0)
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
    """Compare two version strings"""
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

# Configuration
# -------------
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "rss-news.conf")
PAGE_SIZE = 20  # Lines per page for pagination
MAX_ARTICLE_SIZE_KB = 100  # Warn if article is larger than this
SOCKET_TIMEOUT = 30  # Timeout for requests in seconds

def get_line_width():
    """Get terminal width, fallback to 40 for piped input"""
    try:
        return os.get_terminal_size().columns
    except (OSError, ValueError):
        return 40  # Fallback for piped input or non-terminal

LINE_WIDTH = get_line_width()  # Dynamic terminal width
MAX_ARTICLES = 15  # Maximum number of articles to display per feed


class HTMLStripper(HTMLParser):
    """Strip HTML tags and extract plain text"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
        
    def handle_data(self, data):
        self.text.append(data)
        
    def get_text(self):
        return ''.join(self.text)


class RSSReader:
    """RSS Feed Reader with categorization"""
    
    def __init__(self):
        self.feeds = {}  # {category: [(name, url), ...]}
        self.current_category = None
        self.current_feed = None
        self.current_articles = []
        self.load_config()
        
    def load_config(self):
        """Load RSS feeds from configuration file"""
        if not os.path.exists(CONFIG_FILE):
            print("Error: Configuration file not found: {}".format(CONFIG_FILE))
            print("Please create rss-news.conf with your RSS feeds.")
            sys.exit(1)
            
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    # Skip comments and empty lines
                    if not row or row[0].strip().startswith('#'):
                        continue
                    
                    if len(row) >= 3:
                        category = row[0].strip()
                        name = row[1].strip()
                        url = row[2].strip()
                        
                        if category not in self.feeds:
                            self.feeds[category] = []
                        self.feeds[category].append((name, url))
                        
            if not self.feeds:
                print("Error: No feeds found in configuration file")
                sys.exit(1)
                
            print("Loaded {} categories with {} total feeds".format(
                len(self.feeds), sum(len(feeds) for feeds in self.feeds.values())))
                
        except Exception as e:
            print("Error loading configuration: {}".format(str(e)))
            sys.exit(1)
    
    def strip_html(self, html_text):
        """Strip HTML tags from text, converting breaks and paragraphs to newlines"""
        if not html_text:
            return ""
        
        # Convert common spacing/break tags to newlines before stripping
        # Match <br>, <br/>, <br />, </p>, <p> with case-insensitive matching
        html_text = re.sub(r'<br\s*/?>', '\n', html_text, flags=re.IGNORECASE)
        html_text = re.sub(r'</p>', '\n\n', html_text, flags=re.IGNORECASE)
        html_text = re.sub(r'<p>', '\n', html_text, flags=re.IGNORECASE)
        
        # Strip remaining HTML tags
        stripper = HTMLStripper()
        stripper.feed(html_text)
        text = stripper.get_text()
        
        # Clean up excessive whitespace while preserving single newlines
        # Replace multiple spaces with single space
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = ' '.join(line.split())  # Collapse multiple spaces
            cleaned_lines.append(line)
        
        # Join lines and collapse multiple consecutive newlines to max 2
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n\n\n+', '\n\n', text)  # Max 2 consecutive newlines
        
        return unescape(text.strip())
    
    def fetch_feed(self, url):
        """Fetch and parse an RSS feed"""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'RSS-Reader/1.0 (Packet Radio)')
            
            with urllib.request.urlopen(req, timeout=SOCKET_TIMEOUT) as response:
                data = response.read()
                
            # Parse XML
            root = ET.fromstring(data)
            
            articles = []
            
            # Try RSS 2.0 format first
            for item in root.findall('.//item'):
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pubDate = item.find('pubDate')
                
                article = {
                    'title': title.text if title is not None else 'No title',
                    'link': link.text if link is not None else '',
                    'description': self.strip_html(description.text) if description is not None else '',
                    'date': pubDate.text if pubDate is not None else ''
                }
                articles.append(article)
            
            # Try Atom format if no items found
            if not articles:
                # Handle Atom namespace
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('.//atom:entry', ns):
                    title = entry.find('atom:title', ns)
                    link = entry.find('atom:link', ns)
                    summary = entry.find('atom:summary', ns)
                    content = entry.find('atom:content', ns)
                    updated = entry.find('atom:updated', ns)
                    
                    # Get link href attribute
                    link_url = ''
                    if link is not None:
                        link_url = link.get('href', '')
                    
                    # Prefer content over summary
                    desc_elem = content if content is not None else summary
                    
                    article = {
                        'title': title.text if title is not None else 'No title',
                        'link': link_url,
                        'description': self.strip_html(desc_elem.text) if desc_elem is not None else '',
                        'date': updated.text if updated is not None else ''
                    }
                    articles.append(article)
                
                # Also try without namespace (some feeds don't use proper namespaces)
                if not articles:
                    for entry in root.findall('.//entry'):
                        title = entry.find('title')
                        link = entry.find('link')
                        summary = entry.find('summary')
                        content = entry.find('content')
                        updated = entry.find('updated')
                        
                        link_url = ''
                        if link is not None:
                            link_url = link.get('href', '')
                        
                        desc_elem = content if content is not None else summary
                        
                        article = {
                            'title': title.text if title is not None else 'No title',
                            'link': link_url,
                            'description': self.strip_html(desc_elem.text) if desc_elem is not None else '',
                            'date': updated.text if updated is not None else ''
                        }
                        articles.append(article)
            
            return articles
            
        except urllib.error.HTTPError as e:
            print("HTTP Error {}: {}".format(e.code, e.reason))
            return None
        except urllib.error.URLError as e:
            print("URL Error: {}".format(str(e.reason)))
            return None
        except ET.ParseError:
            print("Error: Could not parse RSS feed (invalid XML)")
            return None
        except Exception as e:
            print("Error fetching feed: {}".format(str(e)))
            return None
    
    def fetch_article_text(self, url):
        """Fetch full article text from URL using w3m for text extraction"""
        try:
            # Try using w3m if available for clean text extraction
            try:
                result = subprocess.run(
                    ['w3m', '-dump', url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    timeout=SOCKET_TIMEOUT
                )
                if result.returncode == 0 and result.stdout:
                    return result.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # Fallback: fetch HTML and strip tags manually
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'RSS-Reader/1.0 (Packet Radio)')
            
            with urllib.request.urlopen(req, timeout=SOCKET_TIMEOUT) as response:
                data = response.read()
                
            # Decode HTML
            html = data.decode('utf-8', errors='replace')
            
            # Try to extract just the body content
            # Remove script and style tags
            import re
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # Strip remaining HTML
            text = self.strip_html(html)
            
            return text
            
        except Exception as e:
            return "Error fetching article: {}".format(str(e))
    
    def display_categories(self):
        """Display available feed categories"""
        print("\n" + "=" * 40)
        print("RSS FEED CATEGORIES")
        print("=" * 40)
        
        categories = sorted(self.feeds.keys())
        for i, category in enumerate(categories, 1):
            count = len(self.feeds[category])
            print("{:3}) {} ({} feeds)".format(i, category, count))
            
        print("=" * 40)
        return categories
    
    def display_feeds(self, category):
        """Display feeds in a category"""
        if category not in self.feeds:
            print("Error: Category not found")
            return
        
        print("\n" + "=" * 40)
        print("FEEDS: {}".format(category))
        print("-" * 40)
        
        feeds = self.feeds[category]
        for i, (name, url) in enumerate(feeds, 1):
            print("{:3}) {}".format(i, name))
            
        print("-" * 40)
    
    def parse_date(self, date_string):
        """Extract just the date portion from RSS date strings"""
        if not date_string:
            return ""
        
        # Try to parse common RSS date formats
        # RFC 822 format: "Wed, 09 Oct 2025 14:30:00 GMT"
        # ISO 8601 format: "2025-10-09T14:30:00Z"
        
        try:
            # For RFC 822 (RSS 2.0) - extract date portion
            if ',' in date_string:
                # Format: "Day, DD Mon YYYY HH:MM:SS TZ"
                parts = date_string.split(',', 1)[1].strip().split()
                if len(parts) >= 3:
                    # Return "DD Mon YYYY"
                    return "{} {} {}".format(parts[0], parts[1], parts[2])
            
            # For ISO 8601 (Atom) - extract date portion
            elif 'T' in date_string:
                # Format: "YYYY-MM-DDTHH:MM:SSZ"
                date_part = date_string.split('T')[0]
                # Convert YYYY-MM-DD to more readable format
                dt = datetime.strptime(date_part, '%Y-%m-%d')
                return dt.strftime('%d %b %Y')
            
            # Fallback: just take first 11 characters
            return date_string[:11].strip()
            
        except:
            # If parsing fails, return truncated original
            return date_string[:11].strip()
    
    def display_articles(self, feed_name):
        """Display articles from a feed"""
        if not self.current_articles:
            print("No articles available")
            return
        
        # Limit number of articles displayed
        total_articles = len(self.current_articles)
        articles_to_show = self.current_articles[:MAX_ARTICLES]
        
        print("\n" + "-" * 40)
        print("ARTICLES: {}".format(feed_name))
        if total_articles > MAX_ARTICLES:
            print("Showing {} of {} articles (most recent)".format(MAX_ARTICLES, total_articles))
        print("-" * 40)
        
        for i, article in enumerate(articles_to_show, 1):
            title = article['title']
            date = self.parse_date(article['date'])
            
            # Build display line with date in parentheses
            if date:
                display_line = "{} ({})".format(title, date)
            else:
                display_line = title
            
            # Display with minimal formatting (let terminal handle width)
            print("{:3}) {}".format(i, display_line))
        
        print("-" * 40)
    
    def display_text(self, text, paginate=True):
        """Display text content with optional pagination"""
        # Split into lines and wrap long lines intelligently
        lines = []
        for line in text.split('\n'):
            if len(line) > LINE_WIDTH:
                # Wrap at word boundaries without breaking long words
                wrapped = textwrap.fill(line, width=LINE_WIDTH, break_long_words=False)
                lines.extend(wrapped.split('\n'))
            else:
                lines.append(line)
        
        if not paginate:
            for line in lines:
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
                print(line)
            
            page_num += 1
            
            if i + PAGE_SIZE < len(lines):
                response = input("\n[Enter]=Next page, Q)uit :> ").strip().lower()
                if response.startswith('q'):
                    break
    
    def show_help(self):
        """Display help/commands menu"""
        print("\n" + "-" * 40)
        print("COMMANDS")
        print("-" * 40)
        print("  [number] - Select item by number")
        print("  C)ategories - Show feed categories")
        print("  B)ack    - Go back to previous menu")
        print("  R)efresh - Reload current feed (when viewing articles)")
        print("  ?)       - Show this help")
        print("  Q)uit    - Exit (works from any menu)")
        print("\nNavigation:")
        print("  1. Select a category")
        print("  2. Select a feed to view article list")
        print("  3. Select an article to view description")
        print("  4. Choose to load full article from web (optional)")
        print("\nPrompts are context-aware and show available commands.")
        print("\nNote: Only the {} most recent articles are shown per feed".format(MAX_ARTICLES))
        print("to optimize bandwidth usage over packet radio.")
        print("=" * 40)
    
    def show_about(self):
        """Display information about RSS"""
        print("\n" + "=" * 40)
        print("ABOUT RSS FEEDS")
        print("=" * 40)
        print("\nRSS (Really Simple Syndication) is a web feed format used to")
        print("publish frequently updated content like news articles, blog posts,")
        print("and podcasts.")
        print("\nKey features:")
        print("- Standardized XML format for content distribution")
        print("- Allows aggregation of multiple sources in one place")
        print("- Delivers headlines, summaries, and links to full content")
        print("\nThis RSS reader is optimized for packet radio:")
        print("- Text-only interface with no graphics")
        print("- Pagination for large articles")
        print("- Article size warnings for bandwidth management")
        print("- Clean text extraction from web pages")
        print("\nFeeds are organized by category for easy browsing.")
        print("You can add your own feeds by editing rss-news.conf")
        print("-" * 40)
    
    def run(self):
        """Main program loop"""
        print()
        print(r" _ __   _____      ___ ")
        print(r"| '_ \ / _ \ \ /\ / / __|")
        print("| | | |  __/\\ V  V /\\__ \\")
        print(r"|_| |_|\___| \_/\_/ |___/")
        print()
        print("RSS v1.2 - Feed Reader")
                
        state = 'categories'  # categories, feeds, articles, description
        
        # Display category list on startup
        self.display_categories()
        
        # Main command loop
        while True:
            try:
                # Context-aware prompt
                if state == 'categories':
                    prompt = "\nCategories: [#] or C)ategory list, A)bout RSS, ?)Help, Q)uit :> "
                elif state == 'feeds':
                    prompt = "\nFeeds: [#] or B)ack, C)ategory list, ?)Help, Q)uit :> "
                elif state == 'articles':
                    prompt = "\nArticles: [#] or B)ack, C)ategory list, R)efresh, ?)Help, Q)uit :> "
                else:
                    prompt = "\nCommand or Q)uit :> "
                
                command = input(prompt).strip()
                
                if not command:
                    continue
                    
                cmd_lower = command.lower()
                
                # Quit - works from anywhere
                if cmd_lower.startswith('q'):
                    print("\nExiting...")
                    break
                
                # Categories
                elif cmd_lower.startswith('c'):
                    categories = self.display_categories()
                    state = 'categories'
                
                # Back
                elif cmd_lower.startswith('b'):
                    if state == 'feeds':
                        categories = self.display_categories()
                        state = 'categories'
                    elif state == 'articles':
                        self.display_feeds(self.current_category)
                        state = 'feeds'
                    elif state == 'description':
                        self.display_articles(self.current_feed)
                        state = 'articles'
                    else:
                        print("Already at top level")
                
                # Refresh
                elif cmd_lower.startswith('r'):
                    if state == 'articles' and self.current_feed:
                        print("\nRefreshing feed...")
                        feed_url = None
                        for name, url in self.feeds[self.current_category]:
                            if name == self.current_feed:
                                feed_url = url
                                break
                        if feed_url:
                            self.current_articles = self.fetch_feed(feed_url)
                            if self.current_articles:
                                self.display_articles(self.current_feed)
                            else:
                                print("Error: Could not refresh feed")
                    else:
                        print("Nothing to refresh (not viewing a feed)")
                
                # About
                elif cmd_lower.startswith('a'):
                    self.show_about()
                
                # Help
                elif command == '?' or cmd_lower == 'help':
                    self.show_help()
                
                # Select item by number
                elif command.isdigit():
                    item_num = int(command)
                    
                    if state == 'categories':
                        categories = sorted(self.feeds.keys())
                        if 1 <= item_num <= len(categories):
                            self.current_category = categories[item_num - 1]
                            self.display_feeds(self.current_category)
                            state = 'feeds'
                        else:
                            print("Invalid selection. Choose 1-{}".format(len(categories)))
                    
                    elif state == 'feeds':
                        feeds = self.feeds[self.current_category]
                        if 1 <= item_num <= len(feeds):
                            feed_name, feed_url = feeds[item_num - 1]
                            self.current_feed = feed_name
                            print("\nFetching feed: {}...".format(feed_name))
                            self.current_articles = self.fetch_feed(feed_url)
                            
                            if self.current_articles:
                                self.display_articles(feed_name)
                                state = 'articles'
                            else:
                                print("Error: Could not load feed")
                        else:
                            print("Invalid selection. Choose 1-{}".format(len(feeds)))
                    
                    elif state == 'articles':
                        # Only allow selection from the displayed articles
                        max_selectable = min(len(self.current_articles), MAX_ARTICLES)
                        if 1 <= item_num <= max_selectable:
                            article = self.current_articles[item_num - 1]
                            
                            # Display article description
                            print("\n" + "-" * 40)
                            print(article['title'])
                            print("-" * 40)
                            
                            if article['date']:
                                print("Date: {}".format(article['date']))
                                print("")
                            
                            description = article['description']
                            
                            if description:
                                # Calculate size
                                desc_size_kb = len(description.encode('utf-8')) / 1024
                                print("Description size: {:.1f} KB".format(desc_size_kb))
                                
                                # Offer pagination
                                if desc_size_kb > 5:
                                    response = input("Display: A)ll at once, P)aginated, S)kip :> ").strip().lower()
                                    if response.startswith('s'):
                                        pass
                                    elif response.startswith('p'):
                                        self.display_text(description, paginate=True)
                                    else:
                                        self.display_text(description, paginate=False)
                                else:
                                    self.display_text(description, paginate=False)
                            else:
                                print("(No description available)")
                            
                            # Show link
                            if article['link']:
                                print("\n" + "-" * 40)
                                print("Source: {}".format(article['link']))
                                print("-" * 40)
                                
                                # Offer to fetch full article
                                response = input("\nFetch full article? Y)es, N)o :> ").strip().lower()
                                if response.startswith('y'):
                                    print("\nFetching full article (this may take a while)...")
                                    full_text = self.fetch_article_text(article['link'])
                                    
                                    if full_text:
                                        text_size_kb = len(full_text.encode('utf-8')) / 1024
                                        print("Article size: {:.1f} KB".format(text_size_kb))
                                        
                                        if text_size_kb > MAX_ARTICLE_SIZE_KB:
                                            print("Warning: Large article ({:.1f} KB)".format(text_size_kb))
                                            print("This may take significant time over packet radio.")
                                        
                                        response = input("Display: A)ll at once, P)aginated, C)ancel :> ").strip().lower()
                                        
                                        if response.startswith('c'):
                                            pass
                                        elif response.startswith('p'):
                                            self.display_text(full_text, paginate=True)
                                        else:
                                            self.display_text(full_text, paginate=False)
                                        
                                        print("\n" + "-" * 40)
                                        print("End of article")
                                        print("-" * 40)
                            
                            state = 'articles'
                        else:
                            max_selectable = min(len(self.current_articles), MAX_ARTICLES)
                            print("Invalid selection. Choose 1-{}".format(max_selectable))
                
                else:
                    print("Unknown command. Type ? for help, C for categories")
                    
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
    # Check for app updates
    check_for_app_update("1.3", "rss-news.py")
    reader = RSSReader()
    try:
        reader.run()
    except Exception as e:
        print("\nFatal error: {}".format(str(e)))
        sys.exit(1)
