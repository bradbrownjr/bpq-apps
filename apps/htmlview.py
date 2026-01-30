#!/usr/bin/env python3
"""
HTML Viewer Module for Packet Radio
------------------------------------
Reusable text-mode HTML rendering with intelligent link separation.
Separates navigation menus from content links for cleaner viewing.

Features:
- Detects and separates nav links from content links
- Strips JavaScript, CSS, images for text-only rendering
- Numbered link navigation
- Pagination with P)age menu, L)inks, N)ext, B)ack, Q)uit
- Smart word wrapping for terminal width
- Importable by other apps (www.py, gopher.py, wiki.py, rss-news.py)

Author: Brad Brown KC1JMH
Version: 1.4
Date: January 2026
"""

import sys
import os
import re
import textwrap

VERSION = "1.4"
MODULE_NAME = "htmlview.py"

# Default settings (can be overridden)
DEFAULT_PAGE_SIZE = 20  # Content lines per page (accounts for title/prompt overhead)
DEFAULT_TERM_WIDTH = 80
DEFAULT_TITLE_WIDTH = 40  # Max width for page title and separators (BPQ standard)
NAV_LINK_THRESHOLD = 5  # Min consecutive links to consider as nav menu
NAV_SCAN_LINES = 50     # Lines to scan for nav detection


def check_htmlview_update():
    """Check if htmlview module has an update available on GitHub"""
    try:
        import urllib.request
        import stat
        
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(MODULE_NAME)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read().decode('utf-8')
        
        version_match = re.search(r'Version:\s*([0-9.]+)', content)
        if version_match:
            github_version = version_match.group(1)
            
            if _compare_versions(github_version, VERSION) > 0:
                # Download the new version
                script_path = os.path.abspath(__file__)
                try:
                    temp_path = script_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                             stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    os.replace(temp_path, script_path)
                    return True  # Updated
                except Exception:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
    except Exception:
        pass
    return False


def ensure_htmlview_available(app_dir=None):
    """
    Ensure htmlview.py is available and up-to-date.
    Call this from consuming apps at startup.
    
    Args:
        app_dir: Directory where htmlview.py should be located.
                 Defaults to same directory as calling script.
    
    Returns:
        True if module is available, False if download failed
    """
    if app_dir is None:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    module_path = os.path.join(app_dir, MODULE_NAME)
    
    # Check if module exists
    if os.path.exists(module_path):
        # Module exists, check for updates silently
        try:
            check_htmlview_update()
        except:
            pass
        return True
    
    # Module doesn't exist, try to download
    try:
        import urllib.request
        import stat
        
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(MODULE_NAME)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read()
        
        with open(module_path, 'wb') as f:
            f.write(content)
        
        os.chmod(module_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                 stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return True
    except Exception:
        return False


def _compare_versions(version1, version2):
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


def decode_html_entities(text):
    """Decode common HTML entities to ASCII"""
    entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'",
        '&mdash;': '--',
        '&ndash;': '-',
        '&hellip;': '...',
        '&copy;': '(c)',
        '&reg;': '(R)',
        '&trade;': '(TM)',
        '&bull;': '*',
        '&middot;': '-',
        '&laquo;': '<<',
        '&raquo;': '>>',
        '&ldquo;': '"',
        '&rdquo;': '"',
        '&lsquo;': "'",
        '&rsquo;': "'",
        '&deg;': ' deg',
        '&plusmn;': '+/-',
        '&times;': 'x',
        '&divide;': '/',
        '&frac12;': '1/2',
        '&frac14;': '1/4',
        '&frac34;': '3/4',
    }
    
    for entity, replacement in entities.items():
        text = text.replace(entity, replacement)
    
    # Handle numeric entities
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))) if int(m.group(1)) < 128 else '?', text)
    text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) < 128 else '?', text)
    
    return text


class HTMLParser:
    """
    Parse HTML and extract text with intelligent link separation.
    
    Separates navigation links (menus, sidebars) from content links
    based on link density and position in the document.
    """
    
    def __init__(self, nav_threshold=NAV_LINK_THRESHOLD, nav_scan_lines=NAV_SCAN_LINES):
        self.nav_threshold = nav_threshold
        self.nav_scan_lines = nav_scan_lines
        self.reset()
    
    def reset(self):
        """Reset parser state"""
        self.nav_links = []      # Navigation menu links
        self.content_links = []  # In-content links
        self.text_lines = []     # Parsed text content
        self.raw_html = ""
    
    def parse(self, html):
        """
        Parse HTML and separate nav links from content.
        
        Returns:
            tuple: (text_lines, nav_links, content_links)
        """
        self.reset()
        self.raw_html = html
        
        # Remove script, style, and other non-content tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Try to identify and extract nav sections
        nav_html, content_html = self._separate_nav_content(html)
        
        # Remove dropdown buttons from content (CSS menu labels)
        content_html = re.sub(r'<button[^>]*class=["\'][^"\']*dropbtn[^"\']*["\'][^>]*>.*?</button>', '', 
                              content_html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove dropdown wrapper divs (the menu container structure)
        content_html = re.sub(r'<div[^>]*class=["\'][^"\']*dropdown[^"\']*["\'][^>]*>\s*</div>', '', 
                              content_html, flags=re.DOTALL | re.IGNORECASE)
        
        # Parse nav links (don't number them in text, store separately)
        self._extract_nav_links(nav_html)
        
        # ALSO extract simple nav-like links from top of content (Home, About, Contact, etc.)
        # These are often missed by structural detection
        simple_nav_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{2,15})</a>'
        top_content = content_html[:4000]  # Scan first 4KB for nav links
        for match in re.finditer(simple_nav_pattern, top_content, flags=re.IGNORECASE):
            href = match.group(1)
            text = match.group(2).strip()
            # Check if it's a simple site nav link (same domain, short text, common nav words)
            nav_words = ['home', 'about', 'contact', 'members', 'join', 'login', 'register']
            if (text.lower() in nav_words or 
                (len(text) < 12 and (href.startswith('/') or 'ws1sm.com' in href))):
                # Add to nav links if not already there
                if (href, text) not in self.nav_links:
                    self.nav_links.append((href, text))
        
        # Remove any nav link URLs from content to prevent duplicate numbering
        # This ensures links already in nav menu don't appear in content
        nav_hrefs = set()
        for href, text in self.nav_links:
            nav_hrefs.add(href)
        
        # Remove nav links from content HTML
        for href in nav_hrefs:
            # Match links with this href (handle both " and ' quotes)
            escaped_href = re.escape(href)
            content_html = re.sub(r'<a[^>]+href=["\']' + escaped_href + r'["\'][^>]*>.*?</a>',
                                 '', content_html, flags=re.DOTALL | re.IGNORECASE)
        
        # Parse content with numbered links
        text = self._html_to_text(content_html, number_links=True)
        
        # Wrap and clean text
        self.text_lines = self._clean_text(text)
        
        return self.text_lines, self.nav_links, self.content_links
    
    def _separate_nav_content(self, html):
        """
        Separate navigation elements from main content.
        
        Looks for:
        - <nav> tags
        - <header> tags with multiple links
        - <div> with nav/menu/dropdown/container in class/id
        - CSS dropdown menus (dropdown-content class)
        - Dense link clusters at top of document
        """
        nav_parts = []
        content_html = html
        
        # Extract <nav> tags
        nav_matches = re.findall(r'<nav[^>]*>.*?</nav>', html, flags=re.DOTALL | re.IGNORECASE)
        for match in nav_matches:
            nav_parts.append(match)
            content_html = content_html.replace(match, '')
        
        # Extract <header> tags
        header_matches = re.findall(r'<header[^>]*>.*?</header>', html, flags=re.DOTALL | re.IGNORECASE)
        for match in header_matches:
            link_count = len(re.findall(r'<a[^>]+href=', match, re.IGNORECASE))
            if link_count >= self.nav_threshold:
                nav_parts.append(match)
                content_html = content_html.replace(match, '')
        
        # Extract CSS dropdown menu structures (div.dropdown containing button + dropdown-content)
        # These are complete nav menu items that should be removed entirely
        dropdown_wrapper_pattern = r'<div[^>]+class=["\'][^"\']*dropdown[^"\']*["\'][^>]*>'
        for match in re.finditer(dropdown_wrapper_pattern, content_html, flags=re.IGNORECASE):
            div_content = self._extract_balanced_tag(content_html, match.start(), 'div')
            if div_content:
                # Check if it contains dropdown-content (actual menu) or links
                if 'dropdown-content' in div_content.lower() or len(re.findall(r'<a[^>]+href=', div_content, re.IGNORECASE)) >= 2:
                    nav_parts.append(div_content)
        
        # Remove identified dropdown wrappers from content
        for nav_part in nav_parts:
            if nav_part in content_html:
                content_html = content_html.replace(nav_part, '', 1)
        
        # Extract divs with nav/menu/sidebar/header classes (but not dropdown - already handled)
        nav_class_keywords = r'(?:nav|menu|sidebar|header|container)'
        nav_div_pattern = r'<div[^>]+(?:class|id)=["\'][^"\']*' + nav_class_keywords + r'[^"\']*["\'][^>]*>'
        
        # For each matching div start, extract links only (not whole div - too greedy)
        for match in re.finditer(nav_div_pattern, content_html, flags=re.IGNORECASE):
            # Find the extent of this div by counting nested divs
            div_start = match.start()
            div_content = self._extract_balanced_tag(content_html, div_start, 'div')
            if div_content:
                link_count = len(re.findall(r'<a[^>]+href=', div_content, re.IGNORECASE))
                # Only treat as nav if link-dense (many links, short text)
                text_only = re.sub(r'<[^>]+>', ' ', div_content)
                text_only = re.sub(r'\s+', ' ', text_only).strip()
                if link_count >= 3 and (len(text_only) < link_count * 60 or link_count >= self.nav_threshold):
                    nav_parts.append(div_content)
        
        # Remove identified nav divs from content
        for nav_part in nav_parts:
            content_html = content_html.replace(nav_part, '', 1)
        
        # Detect standalone top-level nav links (common pattern: few links before main content)
        # Match links to site pages (with common web extensions or root paths)
        top_link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{3,30})</a>'
        top_links = []
        for match in re.finditer(top_link_pattern, content_html[:3000], flags=re.IGNORECASE):
            href = match.group(1)
            text = match.group(2).strip()
            # Only consider links that look like navigation (not external, not long text)
            if (not href.startswith('http') or href.startswith('http://www.ws1sm.com') or 
                href.startswith('https://www.ws1sm.com')) and len(text) < 30 and text.lower() not in ['click here', 'read more']:
                top_links.append((match.group(0), href, text))
        
        # If we found 2-8 links at the top, they're likely nav
        if 2 <= len(top_links) <= 8:
            for link_html, href, text in top_links:
                nav_parts.append(link_html)
                content_html = content_html.replace(link_html, '', 1)
        
        # Detect dense link clusters at top (fallback heuristic)
        if not nav_parts:
            nav_parts, content_html = self._detect_link_cluster(content_html)
        
        nav_html = '\n'.join(nav_parts)
        return nav_html, content_html
    
    def _extract_balanced_tag(self, html, start_pos, tag_name):
        """
        Extract content of a tag with balanced nesting.
        Returns the full tag content including opening and closing tags.
        """
        open_tag = '<{}'.format(tag_name)
        close_tag = '</{}>'.format(tag_name)
        
        # Find the end of the opening tag
        tag_end = html.find('>', start_pos)
        if tag_end == -1:
            return None
        
        pos = tag_end + 1
        depth = 1
        max_search = min(len(html), start_pos + 50000)  # Limit search depth
        
        while pos < max_search and depth > 0:
            # Find next open or close tag
            next_open = html.lower().find(open_tag.lower(), pos)
            next_close = html.lower().find(close_tag.lower(), pos)
            
            if next_close == -1:
                return None  # Malformed HTML
            
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + len(open_tag)
            else:
                depth -= 1
                pos = next_close + len(close_tag)
        
        if depth == 0:
            return html[start_pos:pos]
        return None
    
    def _detect_link_cluster(self, html):
        """
        Detect dense link clusters at the beginning of content.
        
        Heuristic: If we find N+ consecutive lines that are mostly links
        with little other text, treat them as navigation.
        """
        nav_parts = []
        
        # Convert to text temporarily to analyze structure
        temp_text = re.sub(r'<[^>]+>', '\n', html)
        temp_lines = [l.strip() for l in temp_text.split('\n') if l.strip()]
        
        # Find links in the original HTML with their positions
        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        links_with_pos = [(m.start(), m.group(0), m.group(1), m.group(2)) 
                         for m in re.finditer(link_pattern, html, flags=re.DOTALL | re.IGNORECASE)]
        
        if len(links_with_pos) < self.nav_threshold:
            return [], html  # Not enough links to have a nav section
        
        # Check if first N links are clustered (within first portion of doc)
        scan_limit = len(html) // 4  # First quarter of document
        early_links = [l for l in links_with_pos if l[0] < scan_limit]
        
        if len(early_links) >= self.nav_threshold:
            # Check link density - are these links close together?
            if len(early_links) >= 2:
                first_pos = early_links[0][0]
                last_pos = early_links[min(self.nav_threshold - 1, len(early_links) - 1)][0]
                region = html[first_pos:last_pos + len(early_links[-1][1])]
                
                # Calculate text-to-link ratio
                text_only = re.sub(r'<[^>]+>', ' ', region)
                text_only = re.sub(r'\s+', ' ', text_only).strip()
                
                # If the region is mostly links (short text between them), it's nav
                avg_text_per_link = len(text_only) / len(early_links) if early_links else 999
                
                if avg_text_per_link < 50:  # Less than 50 chars avg between links = nav
                    # Extract this region as nav
                    nav_end = last_pos + len(early_links[-1][1]) + 100  # Buffer
                    nav_html = html[:nav_end]
                    content_html = html[nav_end:]
                    return [nav_html], content_html
        
        return [], html
    
    def _extract_nav_links(self, nav_html):
        """Extract links from navigation sections"""
        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        
        for match in re.finditer(link_pattern, nav_html, flags=re.DOTALL | re.IGNORECASE):
            href = match.group(1)
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            
            # Skip empty, anchors, javascript
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Clean up link text
            text = decode_html_entities(text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            if text and len(text) < 100:  # Skip overly long "links"
                self.nav_links.append((href, text))
    
    def _html_to_text(self, html, number_links=True):
        """Convert HTML to text, optionally numbering links"""
        # First, normalize whitespace (HTML source newlines are just whitespace)
        html = re.sub(r'\s+', ' ', html)
        
        # Now convert paragraph breaks to markers
        # Double br tags = paragraph break
        html = re.sub(r'<br\s*/?>\s*<br\s*/?>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<br\s*/?>\s*<span[^>]*>\s*<br\s*/?>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<br\s*/?>\s*</span>\s*<br\s*/?>', '\n\n', html, flags=re.IGNORECASE)
        
        # Block elements create paragraph breaks
        html = re.sub(r'</(p|div|h[1-6]|article|section)>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<(p|div|h[1-6]|article|section)[^>]*>', '\n\n', html, flags=re.IGNORECASE)
        
        # List items and table rows are line breaks
        html = re.sub(r'</(li|tr)>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<(li|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
        
        # Single br = line break
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        
        # Handle lists
        html = re.sub(r'<[ou]l[^>]*>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</[ou]l>', '\n', html, flags=re.IGNORECASE)
        
        # Extract and number content links
        link_counter = [0]  # Use list to allow modification in nested function
        
        def replace_link(match):
            href = match.group(1)
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            
            # Skip empty, anchors, javascript
            if not href or href.startswith('#') or href.startswith('javascript:'):
                return text
            
            text = decode_html_entities(text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            if not text:
                return ''
            
            if number_links:
                link_counter[0] += 1
                self.content_links.append((link_counter[0], href, text))
                return "{} [{}]".format(text, link_counter[0])
            else:
                return text
        
        html = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', 
                      replace_link, html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Decode entities
        text = decode_html_entities(text)
        
        return text
    
    def _clean_text(self, text):
        """Clean up text - preserve paragraph breaks, merge only obvious fragments"""
        # Split into chunks separated by blank lines (paragraphs)
        paragraphs = []
        current_para = []
        
        for line in text.split('\n'):
            line = re.sub(r'\s+', ' ', line).strip()
            if line:
                current_para.append(line)
            elif current_para:
                # Blank line = paragraph break
                paragraphs.append(current_para)
                current_para = []
        if current_para:
            paragraphs.append(current_para)
        
        # Process each paragraph: merge fragment lines
        result_lines = []
        for para in paragraphs:
            if not para:
                continue
                
            # Merge lines within paragraph that are fragments
            merged = []
            i = 0
            while i < len(para):
                line = para[i]
                
                # Merge with next if this line ends with dangling word
                while i + 1 < len(para):
                    next_line = para[i + 1]
                    # Only merge if line ends with article/preposition/conjunction
                    # and next line starts lowercase (continuation)
                    if (line.endswith(('with', 'and', 'or', 'the', 'a', 'an', 
                                       'in', 'on', 'at', 'to', 'for', 'of', 'by')) and
                        next_line and next_line[0].islower()):
                        i += 1
                        line = line + ' ' + next_line
                    else:
                        break
                
                merged.append(line)
                i += 1
            
            # Add merged paragraph lines
            result_lines.extend(merged)
            # Add blank line after paragraph (except last)
            result_lines.append('')
        
        # Remove trailing blank line
        while result_lines and not result_lines[-1]:
            result_lines.pop()
        
        return result_lines


class HTMLViewer:
    """
    Interactive HTML viewer with pagination and link navigation.
    
    Usage:
        viewer = HTMLViewer(term_width=80, page_size=24)
        viewer.view(html_content, base_url="http://example.com")
        
        # Get selected link URL (if user chose to follow a link)
        if viewer.selected_link:
            next_url = viewer.selected_link
    """
    
    def __init__(self, term_width=DEFAULT_TERM_WIDTH, page_size=DEFAULT_PAGE_SIZE):
        self.term_width = term_width
        self.page_size = page_size
        self.parser = HTMLParser()
        
        # State
        self.text_lines = []
        self.wrapped_lines = []
        self.nav_links = []
        self.content_links = []
        self.base_url = ""
        self.selected_link = None  # URL user chose to follow
        self.go_back = False       # User chose to go back
    
    def view(self, html, base_url=""):
        """
        View HTML content with interactive pagination.
        
        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            str or None: URL to navigate to, or None if user quit/back
        """
        self.base_url = base_url
        self.selected_link = None
        self.go_back = False
        
        # Extract page title before parsing
        title = self._extract_title(html)
        
        # Parse HTML
        self.text_lines, self.nav_links, self.content_links = self.parser.parse(html)
        
        # Remove title from text_lines if it appears (avoid duplication)
        if title:
            # Remove first occurrence of the full title or truncated title
            full_title = title
            trunc_title = title[:DEFAULT_TITLE_WIDTH - 3] + '...' if len(title) > DEFAULT_TITLE_WIDTH else title
            
            cleaned_lines = []
            removed = False
            for line in self.text_lines:
                # Skip first line that matches the title (full or truncated version)
                if not removed and (line.strip() == full_title.strip() or 
                                   line.strip() == trunc_title.strip() or
                                   line.strip().startswith(full_title[:20])):
                    removed = True
                    continue
                cleaned_lines.append(line)
            self.text_lines = cleaned_lines
        
        # Wrap lines to terminal width
        self.wrapped_lines = []
        for line in self.text_lines:
            wrapped = textwrap.wrap(line, width=self.term_width)
            self.wrapped_lines.extend(wrapped if wrapped else [''])
        
        # Display with pagination
        self._paginate(title)
        
        return self.selected_link
    
    def _extract_title(self, html):
        """Extract page title from HTML, capped at title width"""
        # Try <title> tag first
        match = re.search(r'<title[^>]*>(.*?)</title>', html, flags=re.DOTALL | re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'<[^>]+>', '', title)  # Remove any tags
            title = decode_html_entities(title)
            title = re.sub(r'\s+', ' ', title).strip()
            if title:
                # Truncate to title width
                if len(title) > DEFAULT_TITLE_WIDTH:
                    title = title[:DEFAULT_TITLE_WIDTH - 3] + '...'
                return title
        
        # Fallback: try first h1 or h2
        for tag in ['h1', 'h2', 'h3']:
            match = re.search(r'<{0}[^>]*>(.*?)</{0}>'.format(tag), html, 
                            flags=re.DOTALL | re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                title = re.sub(r'<[^>]+>', '', title)
                title = decode_html_entities(title)
                title = re.sub(r'\s+', ' ', title).strip()
                if title and len(title) < 100:  # Reasonable length
                    # Truncate to title width
                    if len(title) > DEFAULT_TITLE_WIDTH:
                        title = title[:DEFAULT_TITLE_WIDTH - 3] + '...'
                    return title
        
        return None
    
    def _paginate(self, title=None):
        """Display content with pagination and navigation options"""
        total_lines = len(self.wrapped_lines)
        current_pos = 0
        
        # Display page header with title (capped at title width)
        if title:
            # Use actual title length, but cap separator to DEFAULT_TITLE_WIDTH
            sep_width = min(len(title), DEFAULT_TITLE_WIDTH)
            sep_line = "-" * sep_width
            print(sep_line)
            print(title)
            print(sep_line)
        
        while current_pos < total_lines:
            end_pos = min(current_pos + self.page_size, total_lines)
            
            # Display current page
            for i in range(current_pos, end_pos):
                print(self.wrapped_lines[i])
            
            # Build prompt based on available options
            has_more = end_pos < total_lines
            has_nav = len(self.nav_links) > 0
            has_links = len(self.content_links) > 0
            
            if has_more or has_nav or has_links:
                print("")
                prompt_parts = []
                
                # Prompt order: furthest to closest from current page
                # Exit/Nav (furthest) -> Local content (closest)
                prompt_parts.append("Q)uit")
                prompt_parts.append("M)ain")
                prompt_parts.append("B)ack")
                if has_nav:
                    prompt_parts.append("P)age menu")
                if has_links:
                    prompt_parts.append("L)inks")
                    prompt_parts.append("#=follow")
                if has_more:
                    prompt_parts.append("Enter=more")
                
                # Calculate page numbers instead of line numbers
                page_size = self.page_size
                current_page = (current_pos // page_size) + 1
                total_pages = (total_lines + page_size - 1) // page_size
                status = "({}/{})".format(current_page, total_pages)
                prompt = "{} [{}] :> ".format(status, " ".join(prompt_parts))
                
                try:
                    response = input(prompt).strip().lower()
                except EOFError:
                    break
                
                if response == 'q':
                    self.selected_link = '__EXIT__'  # Signal to exit app
                    break
                elif response == 'm':
                    self.selected_link = '__MAIN__'  # Signal to go to main menu
                    break
                elif response == 'b':
                    self.go_back = True
                    break
                elif response == 'p' and has_nav:
                    nav_result = self._show_nav_menu()
                    if nav_result == '__EXIT__':
                        self.selected_link = '__EXIT__'
                        break
                    elif nav_result == '__MAIN__':
                        self.selected_link = '__MAIN__'
                        break
                    elif nav_result:
                        self.selected_link = self._resolve_url(nav_result)
                        break
                elif response == 'l' and has_links:
                    link_result = self._show_content_links()
                    if link_result == '__EXIT__':
                        self.selected_link = '__EXIT__'
                        break
                    elif link_result == '__MAIN__':
                        self.selected_link = '__MAIN__'
                        break
                    elif link_result:
                        self.selected_link = self._resolve_url(link_result)
                        break
                elif response.isdigit() and has_links:
                    link_num = int(response)
                    url = self._get_content_link(link_num)
                    if url:
                        self.selected_link = self._resolve_url(url)
                        break
                    else:
                        print("Invalid link number.")
                elif response == '' and has_more:
                    current_pos = end_pos  # Next page
                else:
                    current_pos = end_pos  # Default: next page
            else:
                # No more content, no links
                break
    
    def _show_nav_menu(self):
        """Display page navigation menu with pagination"""
        total_links = len(self.nav_links)
        links_per_page = self.page_size - 4  # Leave room for header/footer
        start = 0
        
        while True:
            end = min(start + links_per_page, total_links)
            
            print("\n" + "-" * 40)
            print("PAGE MENU ({}-{} of {})".format(start + 1, end, total_links))
            print("-" * 40)
            
            for i in range(start, end):
                url, text = self.nav_links[i]
                display_text = text[:35] + '...' if len(text) > 35 else text
                print("{}. {}".format(i + 1, display_text))
            
            print("-" * 40)
            
            # Build prompt based on position (furthest to closest)
            if end < total_links:
                prompt = "Select [1-{}], Q)uit, M)ain, B)ack, Enter=more :> ".format(total_links)
            else:
                prompt = "Select [1-{}], Q)uit, M)ain, B)ack :> ".format(total_links)
            
            try:
                response = input(prompt).strip().lower()
            except EOFError:
                return None
            
            if response == 'q':
                return None
            elif response == 'b':
                return None  # Back to content
            elif response == 'm':
                return None  # Return to content
            elif response == '' and end < total_links:
                start = end  # Next page
                continue
            elif response == '':
                return None  # At end, return to content
            elif response.isdigit():
                idx = int(response) - 1
                if 0 <= idx < total_links:
                    return self.nav_links[idx][0]
            
            # Invalid input, stay on current page
        
        return None
    
    def _show_content_links(self):
        """Display numbered content links"""
        print("\n" + "-" * 40)
        print("CONTENT LINKS ({} items)".format(len(self.content_links)))
        print("-" * 40)
        
        # Paginate links list
        links_per_page = self.page_size - 4
        total_links = len(self.content_links)
        start = 0
        
        while start < total_links:
            end = min(start + links_per_page, total_links)
            
            for num, url, text in self.content_links[start:end]:
                display_text = text[:35] + '...' if len(text) > 35 else text
                print("{}. {}".format(num, display_text))
            
            if end < total_links:
                try:
                    response = input("\n(Q)uit, M)ain, B)ack, #=select, Enter=more) :> ").strip().lower()
                except EOFError:
                    return None
                
                if response == 'q':
                    return '__EXIT__'  # Signal to exit app
                elif response == 'm':
                    return '__MAIN__'  # Signal to go to main menu
                elif response == 'b':
                    return None  # Back to content
                elif response == '':
                    start = end
                    continue
                elif response.isdigit():
                    return self._get_content_link(int(response))
            else:
                try:
                    response = input("\nSelect [1-{}], Q)uit, M)ain, B)ack :> ".format(total_links)).strip().lower()
                except EOFError:
                    return None
                
                if response == 'q':
                    return '__EXIT__'  # Signal to exit app
                elif response == 'm':
                    return '__MAIN__'  # Signal to go to main menu
                elif response == 'b':
                    return None  # Back to content
                elif response.isdigit():
                    return self._get_content_link(int(response))
                return None
            
            start = end
        
        return None
    
    def _get_content_link(self, link_num):
        """Get URL for a content link by number"""
        for num, url, text in self.content_links:
            if num == link_num:
                return url
        return None
    
    def _resolve_url(self, url):
        """Resolve relative URL to absolute"""
        if not url:
            return url
        
        if url.startswith('http://') or url.startswith('https://') or url.startswith('gopher://'):
            return url
        
        if not self.base_url:
            return url
        
        try:
            from urllib.parse import urljoin
        except ImportError:
            from urlparse import urljoin
        
        return urljoin(self.base_url, url)


# Convenience function for quick viewing
def view_html(html, base_url="", term_width=DEFAULT_TERM_WIDTH, page_size=DEFAULT_PAGE_SIZE):
    """
    Quick function to view HTML content.
    
    Args:
        html: Raw HTML content
        base_url: Base URL for resolving relative links
        term_width: Terminal width for wrapping
        page_size: Lines per page
        
    Returns:
        tuple: (selected_url, go_back) - URL if link selected, or None; whether back was chosen
    """
    viewer = HTMLViewer(term_width=term_width, page_size=page_size)
    selected = viewer.view(html, base_url)
    return selected, viewer.go_back


# Test/demo when run directly
if __name__ == '__main__':
    test_html = """
    <html>
    <head><title>Test Page</title></head>
    <body>
    <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
        <a href="/products">Products</a>
        <a href="/services">Services</a>
        <a href="/blog">Blog</a>
    </nav>
    <main>
        <h1>Welcome to Test Page</h1>
        <p>This is a test paragraph with a <a href="/page1">link to page 1</a> 
        and another <a href="/page2">link to page 2</a>.</p>
        <p>More content here with <a href="http://example.com">external link</a>.</p>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do 
        eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
        <p>Another paragraph with some <a href="/more">more info</a> available.</p>
    </main>
    </body>
    </html>
    """
    
    print("HTMLView Module v{} - Test".format(VERSION))
    print("-" * 40)
    
    selected, go_back = view_html(test_html, base_url="http://example.com", term_width=60, page_size=10)
    
    print("\n" + "-" * 40)
    if selected:
        print("Selected URL: {}".format(selected))
    elif go_back:
        print("User chose to go back")
    else:
        print("User quit")
