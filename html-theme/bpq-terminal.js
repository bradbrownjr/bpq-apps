/**
 * bpq-terminal.js — LinBPQ Web Interface Enhancement
 *
 * Injected into every LinBPQ page by the nginx reverse proxy (sub_filter).
 * Runs after DOM ready. Does three things on ALL pages:
 *   1. Injects a branded header (logo + callsign + theme toggle)
 *   2. Restructures LinBPQ's flat nav into three labeled groups
 *   3. Wraps wide tables in overflow-x containers for mobile
 *
 * Does two additional things on TERMINAL pages only (/Node/Term*):
 *   4. Adds up/down arrow command history to the input field
 *   5. Auto-scrolls the output area when new content arrives
 *
 * NOTE on element selectors:
 * LinBPQ's terminal page markup must be inspected via SSH after first deploy
 * to confirm actual IDs/classes for the output textarea and input field.
 * Fallback selectors cover the most common patterns; update TERM_SELECTORS
 * if LinBPQ uses different element identifiers on your version.
 */

(function () {
    'use strict';

    /* -----------------------------------------------------------------------
       CONFIGURATION
       ----------------------------------------------------------------------- */

    // Nav groups: order and membership define the rendered layout
    // Keys are display labels; values are arrays of link textContent to match
    // (case-insensitive, trimmed)
    var NAV_GROUPS = [
        {
            label: 'Node',
            links: ['routes', 'nodes', 'ports', 'links', 'users', 'stats',
                    'driver windows', 'stream status']
        },
        {
            label: 'BBS',
            links: ['webmail', 'terminal'],
            extra: [{ text: 'Files', href: '/files/', cls: 'bpq-nav-files' }]
        },
        {
            label: 'Sysop',
            links: ['mail mgmt', 'chat mgmt', 'sysop signin', 'edit config', 'view logs']
        }
    ];

    // Terminal page detection — true if URL path matches any of these patterns
    var TERMINAL_URL_PATTERNS = [/\/Node\/Term/i, /\/terminal/i];

    // Terminal element selectors (try each in order, use first match)
    var TERM_OUTPUT_SELECTORS = [
        '#term',
        '#termout',
        'textarea[name="term"]',
        'textarea[id*="term"]',
        '.term',
        'textarea'
    ];
    var TERM_INPUT_SELECTORS = [
        '#termin',
        'input[name="cmd"]',
        'input[name="termin"]',
        'input[type="text"]'
    ];

    /* -----------------------------------------------------------------------
       UTILITIES
       ----------------------------------------------------------------------- */

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    function qs(sel, root) {
        return (root || document).querySelector(sel);
    }

    function qsa(sel, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    }

    function firstMatch(selectors, root) {
        for (var i = 0; i < selectors.length; i++) {
            var el = qs(selectors[i], root);
            if (el) return el;
        }
        return null;
    }

    function isTerminalPage() {
        var path = window.location.pathname;
        for (var i = 0; i < TERMINAL_URL_PATTERNS.length; i++) {
            if (TERMINAL_URL_PATTERNS[i].test(path)) return true;
        }
        return false;
    }

    /* -----------------------------------------------------------------------
       THEME TOGGLE
       Reads localStorage on load; falls back to prefers-color-scheme.
       Toggle button cycles: system → light → dark → system.
       ----------------------------------------------------------------------- */

    var THEME_KEY = 'bpq-theme';

    function getStoredTheme() {
        try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
    }

    function setStoredTheme(val) {
        try {
            if (val) { localStorage.setItem(THEME_KEY, val); }
            else      { localStorage.removeItem(THEME_KEY); }
        } catch (e) {}
    }

    function applyTheme(theme) {
        // theme: 'light' | 'dark' | null (system)
        var body = document.body;
        if (theme === 'dark') {
            body.setAttribute('data-theme', 'dark');
        } else if (theme === 'light') {
            body.setAttribute('data-theme', 'light');
        } else {
            body.removeAttribute('data-theme');
        }
    }

    function themeToggleLabel(currentTheme) {
        if (currentTheme === 'dark')  return '☀';   // currently dark → click for light
        if (currentTheme === 'light') return '⚙';   // currently light → click for system
        return '☾';                                  // currently system → click for dark
    }

    function nextTheme(current) {
        if (current === null)    return 'dark';
        if (current === 'dark')  return 'light';
        return null; // light → back to system
    }

    /* -----------------------------------------------------------------------
       HEADER INJECTION
       ------------------------------------------------------------------- */

    function injectHeader() {
        var stored = getStoredTheme();
        applyTheme(stored);

        var header = document.createElement('div');
        header.className = 'bpq-header';

        // Logo (hidden via onerror if file is missing)
        var logo = document.createElement('img');
        logo.src = '/bpq-theme/logo.png';
        logo.alt = '';
        logo.className = 'bpq-header-logo';
        logo.onerror = function () { this.style.display = 'none'; };
        header.appendChild(logo);

        // Title: parse callsign from <title> tag
        // LinBPQ titles look like "BPQ32 Node WS1EC-15" or similar
        var titleText = document.title || 'BPQ32 Node';
        var callsignMatch = titleText.match(/([A-Z0-9]{1,3}[0-9][A-Z]{1,4}(?:-\d{1,2})?)/);
        var callsign = callsignMatch ? callsignMatch[1] : titleText;

        var titleEl = document.createElement('span');
        titleEl.className = 'bpq-header-title';
        titleEl.textContent = callsign;

        var subtitle = document.createElement('span');
        subtitle.className = 'bpq-subtitle';
        subtitle.textContent = 'Packet Radio Node';
        titleEl.appendChild(subtitle);
        header.appendChild(titleEl);

        // Theme toggle button
        var toggleBtn = document.createElement('button');
        toggleBtn.className = 'bpq-theme-toggle';
        toggleBtn.setAttribute('aria-label', 'Toggle colour theme');
        toggleBtn.textContent = themeToggleLabel(stored);
        toggleBtn.addEventListener('click', function () {
            var current = getStoredTheme();
            var next = nextTheme(current);
            setStoredTheme(next);
            applyTheme(next);
            toggleBtn.textContent = themeToggleLabel(next);
        });
        header.appendChild(toggleBtn);

        // Insert before everything else in <body>
        document.body.insertBefore(header, document.body.firstChild);
    }

    /* -----------------------------------------------------------------------
       NAV RESTRUCTURE
       Finds LinBPQ's original nav (a table or row of <a> / input[type=button]
       elements near the top of the page), hides it, and renders a grouped
       replacement above it.
       ----------------------------------------------------------------------- */

    function findNavLinks() {
        // Strategy 1: a table immediately after the page heading that contains links
        var tables = qsa('table');
        for (var i = 0; i < tables.length; i++) {
            var anchors = qsa('a, input[type="button"]', tables[i]);
            if (anchors.length >= 5) {
                return { container: tables[i], links: anchors };
            }
        }
        // Strategy 2: a block of consecutive <a> elements near the top
        var allLinks = qsa('a');
        if (allLinks.length >= 5) {
            return { container: null, links: allLinks.slice(0, 20) };
        }
        return null;
    }

    function buildNav(navLinks) {
        var nav = document.createElement('nav');
        nav.className = 'bpq-nav';
        nav.setAttribute('aria-label', 'BPQ Navigation');

        // Index link elements by normalised text
        var linkMap = {};
        navLinks.links.forEach(function (el) {
            var text = (el.textContent || el.value || '').trim().toLowerCase();
            if (text) linkMap[text] = el;
        });

        var currentPath = window.location.pathname.toLowerCase();

        NAV_GROUPS.forEach(function (group) {
            var groupEl = document.createElement('div');
            groupEl.className = 'bpq-navgroup';

            var labelEl = document.createElement('span');
            labelEl.className = 'bpq-navlabel';
            labelEl.textContent = group.label;
            groupEl.appendChild(labelEl);

            var linksEl = document.createElement('div');
            linksEl.className = 'bpq-navlinks';

            // Matched links from LinBPQ's original nav
            group.links.forEach(function (name) {
                var orig = linkMap[name.toLowerCase()];
                if (!orig) return;

                var a = document.createElement('a');
                a.textContent = (orig.textContent || orig.value || name).trim();
                a.href = orig.href || orig.getAttribute('onclick') || '#';

                // Handle input[type="button"] with onclick
                if (orig.tagName === 'INPUT') {
                    a.href = '#';
                    a.addEventListener('click', function (e) {
                        e.preventDefault();
                        orig.click();
                    });
                }

                // Mark current page active
                if (a.href && a.href !== '#' &&
                    currentPath === new URL(a.href, window.location.href).pathname.toLowerCase()) {
                    a.className = 'bpq-nav-active';
                }

                linksEl.appendChild(a);
            });

            // Extra injected links (e.g. Files)
            if (group.extra) {
                group.extra.forEach(function (item) {
                    var a = document.createElement('a');
                    a.textContent = item.text;
                    a.href = item.href;
                    if (item.cls) a.className = item.cls;
                    linksEl.appendChild(a);
                });
            }

            groupEl.appendChild(linksEl);
            nav.appendChild(groupEl);
        });

        return nav;
    }

    function injectNav() {
        var found = findNavLinks();
        if (!found) return;

        // Hide LinBPQ's original nav container
        if (found.container) {
            found.container.classList.add('bpq-nav-original');
        }

        var nav = buildNav(found);

        // Insert after .bpq-header
        var header = qs('.bpq-header');
        if (header && header.nextSibling) {
            document.body.insertBefore(nav, header.nextSibling);
        } else if (found.container) {
            found.container.parentNode.insertBefore(nav, found.container);
        } else {
            document.body.insertBefore(nav, document.body.firstChild);
        }
    }

    /* -----------------------------------------------------------------------
       TABLE OVERFLOW WRAPPERS
       Wraps all tables that are wider than the viewport in a scrollable div.
       ----------------------------------------------------------------------- */

    function wrapTables() {
        qsa('table').forEach(function (tbl) {
            // Skip tables already wrapped or inside the nav
            if (tbl.parentNode.classList &&
                tbl.parentNode.classList.contains('bpq-table-wrap')) return;
            if (tbl.closest('.bpq-nav')) return;
            if (tbl.classList.contains('bpq-nav-original')) return;

            var wrap = document.createElement('div');
            wrap.className = 'bpq-table-wrap';
            tbl.parentNode.insertBefore(wrap, tbl);
            wrap.appendChild(tbl);
        });
    }

    /* -----------------------------------------------------------------------
       TERMINAL ENHANCEMENTS (terminal pages only)
       ----------------------------------------------------------------------- */

    var cmdHistory = [];
    var historyIndex = -1;

    function initTerminal() {
        var outputEl = firstMatch(TERM_OUTPUT_SELECTORS);
        var inputEl  = firstMatch(TERM_INPUT_SELECTORS);

        if (!outputEl && !inputEl) return; // not a terminal page after all

        // Auto-scroll output when new content arrives
        if (outputEl) {
            var observer = new MutationObserver(function () {
                outputEl.scrollTop = outputEl.scrollHeight;
            });
            observer.observe(outputEl, { childList: true, subtree: true, characterData: true });
            // Initial scroll to bottom
            outputEl.scrollTop = outputEl.scrollHeight;
        }

        // Command history on input field
        if (inputEl) {
            inputEl.addEventListener('keydown', function (e) {
                if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (historyIndex < cmdHistory.length - 1) {
                        historyIndex++;
                        inputEl.value = cmdHistory[cmdHistory.length - 1 - historyIndex];
                    }
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (historyIndex > 0) {
                        historyIndex--;
                        inputEl.value = cmdHistory[cmdHistory.length - 1 - historyIndex];
                    } else if (historyIndex === 0) {
                        historyIndex = -1;
                        inputEl.value = '';
                    }
                } else if (e.key === 'Enter') {
                    var cmd = inputEl.value.trim();
                    if (cmd) {
                        // Avoid duplicate consecutive entries
                        if (cmdHistory.length === 0 ||
                            cmdHistory[cmdHistory.length - 1] !== cmd) {
                            cmdHistory.push(cmd);
                            // Cap history at 50 entries
                            if (cmdHistory.length > 50) cmdHistory.shift();
                        }
                        historyIndex = -1;
                    }
                }
            });
        }
    }

    /* -----------------------------------------------------------------------
       ENTRY POINT
       ----------------------------------------------------------------------- */

    ready(function () {
        injectHeader();
        injectNav();
        wrapTables();
        if (isTerminalPage()) {
            initTerminal();
        }
    });

})();
