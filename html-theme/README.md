# LinBPQ Modern Web Theme

A modern, responsive web theme for the LinBPQ node management interface, deployed via an nginx reverse proxy. LinBPQ's HTML is generated dynamically by the binary — there are no template files to edit. This theme intercepts every response and injects custom CSS and JavaScript without touching LinBPQ's configuration or source code.

## Why a reverse proxy?

LinBPQ's management pages (Routes, Nodes, Terminal, Mail, etc.) are baked into the `linbpq` binary. The `HTML/` directory in the LinBPQ data folder only overrides the home page and background image — not any of the management pages. A reverse proxy using nginx's `sub_filter` module injects `<link>` and `<script>` tags into every HTML response before the browser sees it. LinBPQ binary updates have no effect on the theme because there are no HTML files to overwrite.

## What it does

- **Modern CSS** — clean typography, responsive layout, ARES navy/red colour scheme with light/dark mode
- **Grouped navigation** — LinBPQ's flat row of buttons is reorganised into three labelled sections: **Node**, **BBS**, and **Sysop**
- **BBS Files browser** — a styled file listing at `/files/` backed by nginx's JSON autoindex; subdirectory navigation, file size/date columns, live search filter, sortable columns
- **Terminal enhancements** — up/down arrow command history, auto-scroll on new output
- **Theme toggle** — sun/moon button in the header; respects `prefers-color-scheme` automatically, with a manual override persisted in `localStorage`
- **Logo slot** — drop `logo.png` in the theme directory to show your club or ARES logo

## Files

```
html-theme/
├── bpq-proxy.conf      nginx config template (variables substituted by deploy-theme.sh)
├── bpq-modern.css      Stylesheet — all colours are CSS custom properties at the top
├── bpq-terminal.js     Header/nav/terminal JS — vanilla, no dependencies
├── files-browser.html  BBS Files single-page browser
├── logo.png            (optional) Logo shown in the header — replace with your own
└── README.md           This file
```

## Prerequisites

On the LinBPQ host:
- Linux (Debian/Ubuntu/Raspbian)
- `nginx` — installed automatically by `deploy-theme.sh` if missing
- `certbot` — for HTTPS (manual step, instructions printed by deploy script)
- SSH access from your development machine

Router/firewall:
- Port **80** forwarded to the LinBPQ host
- Port **443** forwarded to the LinBPQ host

LinBPQ itself stays on its original port (default `9123`). No changes to `bpq32.cfg` are required.

## First-time setup

From the `bpq-apps/` repository root:

```bash
./deploy-theme.sh
```

Default values assume `ect@ws1ec.mainepacketradio.org` on SSH port 4722 with LinBPQ on port 9123 and BBS files at `/home/ect/linbpq/Files`. Override any of these:

```bash
./deploy-theme.sh -u pi -f /home/pi/linbpq/Files
./deploy-theme.sh -h mynode.example.com -p 22 -l 9123
```

The script will:
1. Check for nginx and install it if missing
2. Substitute your hostname, LinBPQ port, and files path into `bpq-proxy.conf`
3. Install the config at `/etc/nginx/sites-available/bpq-proxy.conf` and enable it
4. Set read permissions on the BBS Files directory
5. Upload `bpq-modern.css`, `bpq-terminal.js`, `files-browser.html` (and `logo.png` if present) to `/var/www/bpq-theme/`
6. Reload nginx
7. Print instructions for certbot and port forwards

## HTTPS / certbot

After the first deploy, SSH into the host and run:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_HOSTNAME
```

Certbot edits the nginx config to add TLS certificates and sets up automatic renewal via a systemd timer or cron job. You do not need to run it again — renewals are automatic.

## Updating the theme

After editing CSS, JS, or HTML locally:

```bash
./deploy-theme.sh --assets-only
```

This skips the nginx config step and only pushes the updated asset files.

## Customising the colour scheme

All colours are CSS custom properties at the top of `bpq-modern.css` inside the `:root { }` block. To reskin for a different club, edit only those variables — nothing else in the file needs to change.

```css
:root {
    --color-primary: #002868;   /* Nav background, headings */
    --color-accent:  #bf0000;   /* Group labels, hover accents */
    /* ... */
}
```

Dark mode overrides follow in the same file under `@media (prefers-color-scheme: dark)` and `[data-theme="dark"]`.

## Adding a logo

Place a `logo.png` file in `html-theme/` and re-run the deploy script. Recommended size: 200×50 px or similar landscape format. The header scales it to 44 px tall. If no logo is present, the header shows the node callsign parsed from the page title.

## BBS Files directory permissions

nginx runs as `www-data`. The deploy script runs `chmod o+rx` on the Files directory so nginx can read it. If files are added to the BBS and are not world-readable, run the deploy script again or set permissions manually:

```bash
chmod o+rx /home/ect/linbpq/Files
find /home/ect/linbpq/Files -type d -exec chmod o+rx {} +
find /home/ect/linbpq/Files -type f -exec chmod o+r {} +
```

## Optional — WebTermCSS

LinBPQ's config supports a `WebTermCSS` parameter that applies inline styles to the terminal element before the page is sent. This is independent of the theme but complements it for terminal sessions. Add to the `TELNET` section of `bpq32.cfg`:

```
WebTermCSS=font-family:'Courier New',monospace;background-color:#0d1117;color:#d4d4d4;font-size:14px;
```

Restart LinBPQ after editing.

## Terminal element selectors

LinBPQ's terminal page markup varies by version. The JS uses a list of fallback selectors and uses the first match. If command history or auto-scroll are not working after a LinBPQ update, SSH into the host and inspect the terminal page source:

```bash
curl -s http://127.0.0.1:9123/Node/Term.html | grep -i 'textarea\|input\|id='
```

Then update `TERM_OUTPUT_SELECTORS` and `TERM_INPUT_SELECTORS` near the top of `bpq-terminal.js`.

## Architecture

```
Browser (port 443)
    ↓ HTTPS
nginx
    ├── /bpq-theme/*    → /var/www/bpq-theme/  (static assets)
    ├── /files/         → redirect to /bpq-theme/files-browser.html
    ├── /files-data/*   → /home/ect/linbpq/Files/  (JSON autoindex)
    └── /*              → proxy_pass http://127.0.0.1:9123  (LinBPQ)
                          sub_filter injects CSS + JS into every HTML response
```

LinBPQ is never exposed directly — all traffic passes through nginx. Port 9123 can remain open for local/debug access or be firewalled as preferred.
