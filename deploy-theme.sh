#!/usr/bin/env bash
# deploy-theme.sh — Deploy LinBPQ modern web theme
#
# Installs/updates the nginx reverse proxy configuration and theme assets
# (CSS, JS, files browser) for the LinBPQ web interface.
#
# Usage:
#   ./deploy-theme.sh [options]
#
# Options:
#   -h HOST       Remote hostname (default: ws1ec.mainepacketradio.org)
#   -u USER       SSH user on the remote host (default: ect)
#   -p PORT       SSH port (default: 4722)
#   -l LINPORT    LinBPQ HTTP port in bpq32.cfg HTTPPORT= (default: 9123)
#   -f FILESPATH  Absolute path to LinBPQ BBS Files directory on remote
#                 (default: /home/$USER/linbpq/Files)
#   --assets-only Skip nginx config update; only push CSS/JS/HTML assets
#   --help        Show this help
#
# Examples:
#   ./deploy-theme.sh
#   ./deploy-theme.sh -u pi -f /home/pi/linbpq/Files
#   ./deploy-theme.sh --assets-only

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
REMOTE_HOST="ws1ec.mainepacketradio.org"
REMOTE_USER="ect"
SSH_PORT="4722"
LINBPQ_PORT="9123"
BBS_FILES_USER=""   # derived from REMOTE_USER if empty
ASSETS_ONLY=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="${SCRIPT_DIR}/html-theme"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
print_help() {
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h)  REMOTE_HOST="$2"; shift 2 ;;
        -u)  REMOTE_USER="$2"; shift 2 ;;
        -p)  SSH_PORT="$2"; shift 2 ;;
        -l)  LINBPQ_PORT="$2"; shift 2 ;;
        -f)  BBS_FILES_PATH="$2"; shift 2 ;;
        --assets-only) ASSETS_ONLY=true; shift ;;
        --help) print_help ;;
        *) echo "Unknown option: $1"; print_help ;;
    esac
done

# Derive BBS files path from user if not explicitly set
if [[ -z "${BBS_FILES_PATH:-}" ]]; then
    BBS_FILES_USER="${BBS_FILES_USER:-$REMOTE_USER}"
    BBS_FILES_PATH="/home/${BBS_FILES_USER}/linbpq/Files"
fi

SSH_OPTS="-p ${SSH_PORT} -o StrictHostKeyChecking=accept-new"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()    { echo "  [INFO] $*"; }
success() { echo "    [OK] $*"; }
warn()    { echo "  [WARN] $*"; }
fatal()   { echo " [ERROR] $*" >&2; exit 1; }

ssh_run() {
    # Run a command on the remote host
    ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "$@"
}

scp_file() {
    local src="$1" dst="$2"
    scp -P "${SSH_PORT}" "$src" "${REMOTE_USER}@${REMOTE_HOST}:${dst}"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  LinBPQ Theme Deployer"
echo "============================================================"
echo "  Target : ${REMOTE_USER}@${REMOTE_HOST}:${SSH_PORT}"
echo "  LinBPQ : 127.0.0.1:${LINBPQ_PORT}"
echo "  Files  : ${BBS_FILES_PATH}"
echo "  Mode   : $(${ASSETS_ONLY} && echo 'assets only' || echo 'full install')"
echo ""

if [[ ! -d "${THEME_DIR}" ]]; then
    fatal "html-theme/ directory not found at ${THEME_DIR}"
fi

for f in bpq-proxy.conf bpq-modern.css bpq-terminal.js files-browser.html; do
    [[ -f "${THEME_DIR}/${f}" ]] || fatal "Missing theme file: html-theme/${f}"
done

# Test SSH connectivity before doing anything
info "Testing SSH connection…"
ssh_run "echo connected" > /dev/null || fatal "SSH connection failed. Check host, user, and port."
success "SSH connection OK"

# ---------------------------------------------------------------------------
# Phase 1: nginx check / install (skipped with --assets-only)
# ---------------------------------------------------------------------------
if [[ "${ASSETS_ONLY}" == false ]]; then
    echo ""
    echo "── Phase 1: nginx ─────────────────────────────────────────"

    info "Checking for nginx on remote host…"
    if ssh_run "command -v nginx > /dev/null 2>&1"; then
        success "nginx already installed"
    else
        info "nginx not found — installing via apt…"
        ssh_run "sudo apt-get update -qq && sudo apt-get install -y nginx" \
            || fatal "nginx install failed. Try manually: sudo apt install nginx"
        success "nginx installed"
    fi

    # Create /var/www/bpq-theme/
    info "Creating /var/www/bpq-theme/ on remote…"
    ssh_run "sudo mkdir -p /var/www/bpq-theme && sudo chown ${REMOTE_USER}:${REMOTE_USER} /var/www/bpq-theme"
    success "Asset directory ready"

    # Apply variable substitutions to nginx config and upload
    info "Uploading nginx proxy config…"
    local_conf=$(mktemp /tmp/bpq-proxy-XXXXX.conf)
    sed \
        -e "s|%%HOSTNAME%%|${REMOTE_HOST}|g" \
        -e "s|%%LINBPQ_PORT%%|${LINBPQ_PORT}|g" \
        -e "s|%%BBS_FILES_PATH%%|${BBS_FILES_PATH}|g" \
        "${THEME_DIR}/bpq-proxy.conf" > "${local_conf}"

    scp_file "${local_conf}" "/tmp/bpq-proxy.conf"
    rm -f "${local_conf}"

    ssh_run "sudo mv /tmp/bpq-proxy.conf /etc/nginx/sites-available/bpq-proxy.conf"

    # Enable site (remove default if it's still there and would conflict on 80)
    ssh_run "
        if [[ -f /etc/nginx/sites-enabled/default ]]; then
            sudo rm -f /etc/nginx/sites-enabled/default
        fi
        sudo ln -sf /etc/nginx/sites-available/bpq-proxy.conf /etc/nginx/sites-enabled/bpq-proxy.conf
    "
    success "nginx config installed"

    # Set BBS files directory readable by www-data (nginx worker)
    info "Setting read permissions on BBS files directory…"
    ssh_run "
        if [[ -d '${BBS_FILES_PATH}' ]]; then
            chmod o+rx '${BBS_FILES_PATH}'
            find '${BBS_FILES_PATH}' -type d -exec chmod o+rx {} +
            find '${BBS_FILES_PATH}' -type f -exec chmod o+r {} +
            echo 'ok'
        else
            echo 'NOTFOUND'
        fi
    " | grep -q 'NOTFOUND' && warn "BBS Files directory not found at ${BBS_FILES_PATH} — /files/ browser will 404 until it exists." || true

    # Test nginx config
    info "Testing nginx configuration…"
    ssh_run "sudo nginx -t" || fatal "nginx config test failed. Check /etc/nginx/sites-available/bpq-proxy.conf"
    success "nginx config valid"

    # Reload nginx
    if ssh_run "sudo systemctl is-active nginx > /dev/null 2>&1"; then
        info "Reloading nginx…"
        ssh_run "sudo nginx -s reload"
    else
        info "Starting nginx…"
        ssh_run "sudo systemctl start nginx && sudo systemctl enable nginx"
    fi
    success "nginx running"
fi

# ---------------------------------------------------------------------------
# Phase 2: Upload theme assets
# ---------------------------------------------------------------------------
echo ""
echo "── Phase 2: Theme assets ──────────────────────────────────"

THEME_DEST_DIR="/var/www/bpq-theme"

if [[ "${ASSETS_ONLY}" == true ]]; then
    # Ensure the directory exists (may have been created by a previous full run)
    ssh_run "sudo mkdir -p ${THEME_DEST_DIR} && sudo chown ${REMOTE_USER}:${REMOTE_USER} ${THEME_DEST_DIR}" \
        || fatal "Could not access ${THEME_DEST_DIR}. Run without --assets-only first."
fi

for asset in bpq-modern.css bpq-terminal.js files-browser.html; do
    info "Uploading ${asset}…"
    scp_file "${THEME_DIR}/${asset}" "${THEME_DEST_DIR}/${asset}"
    success "${asset}"
done

# Upload logo.png if it exists
if [[ -f "${THEME_DIR}/logo.png" ]]; then
    info "Uploading logo.png…"
    scp_file "${THEME_DIR}/logo.png" "${THEME_DEST_DIR}/logo.png"
    success "logo.png"
else
    warn "No logo.png in html-theme/ — header will show callsign text only."
    warn "To add a logo: place logo.png in html-theme/ and re-run this script."
fi

# Reload nginx to serve new assets with updated cache headers
if [[ "${ASSETS_ONLY}" == true ]]; then
    info "Reloading nginx…"
    ssh_run "sudo nginx -s reload" && success "nginx reloaded" || warn "nginx reload failed — assets are live but old cached versions may persist briefly."
fi

# ---------------------------------------------------------------------------
# Done — print next steps
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  Deploy complete!"
echo "============================================================"
echo ""
echo "  NEXT STEPS:"
echo ""
echo "  1. Port forwards — ensure your router forwards:"
echo "       External port 80  → ${REMOTE_HOST} port 80"
echo "       External port 443 → ${REMOTE_HOST} port 443"
echo "     (LinBPQ stays on port ${LINBPQ_PORT} — no change needed in bpq32.cfg)"
echo ""
echo "  2. SSL certificate — run on the remote host:"
echo "       sudo apt install certbot python3-certbot-nginx"
echo "       sudo certbot --nginx -d ${REMOTE_HOST}"
echo "     Certbot will auto-configure HTTPS and schedule renewal."
echo ""
echo "  3. Verify the themed interface:"
echo "       https://${REMOTE_HOST}/Node/NodeIndex.html"
echo ""
echo "  4. Optional — WebTermCSS for the built-in terminal:"
echo "     Add to bpq32.cfg in the TELNET section:"
echo "       WebTermCSS=font-family:'Courier New',monospace;background-color:#0d1117;color:#d4d4d4;font-size:14px;"
echo "     Then restart LinBPQ."
echo ""
echo "  To push theme asset updates later:"
echo "       ./deploy-theme.sh --assets-only"
echo ""
