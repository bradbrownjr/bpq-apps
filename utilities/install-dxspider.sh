#!/bin/bash
# install-dxspider.sh - DX Spider Cluster Installation for LinBPQ
# Version: 1.0
# Author: KC1JMH
# Date: 2026-01-24
#
# Installs DX Spider as an isolated Perl service with dedicated user (sysop),
# integrating with linbpq via telnet port 7300. Configures upstream cluster
# connectivity for spot sharing.
#
# Usage: sudo ./install-dxspider.sh
#
# References:
#   https://github.com/glaukos78/dxspider_installation_v2
#   https://www.cantab.net/users/john.wiseman/Documents/LinBPQtoSpider.html

set -e

#------------------------------------------------------------------------------
# Configuration - Edit these values for your station
#------------------------------------------------------------------------------
CLUSTER_CALL="WS1EC-6"          # Cluster callsign (SSID -6 available)
SYSOP_CALL="KC1JMH"             # Primary sysop callsign
SYSOP_NAME="Brad"               # Sysop first name
SYSOP_EMAIL="kc1jmh@arrl.net"   # Sysop email (escape @ with \@)
LOCATOR="FN43SR"                # Maidenhead grid square
QTH="Windham, ME"               # QTH description

# Upstream clusters for spot sharing
UPSTREAM_1="dxc.nc7j.com"
UPSTREAM_1_PORT="7373"
UPSTREAM_2="w3lpl.net"
UPSTREAM_2_PORT="7373"

# Local ports
SPIDER_PORT="7300"              # DX Spider telnet port
BPQ_USER="ect"                  # Existing BPQ user (for group membership)

#------------------------------------------------------------------------------
# Validate root
#------------------------------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    echo "Usage: sudo $0"
    exit 1
fi

echo "========================================"
echo "DX Spider Installation for LinBPQ"
echo "Cluster: $CLUSTER_CALL"
echo "Location: $QTH ($LOCATOR)"
echo "========================================"
echo ""

#------------------------------------------------------------------------------
# Check for existing installation
#------------------------------------------------------------------------------
if [ -d "/spider" ] || [ -d "/home/sysop/spider" ]; then
    echo "WARNING: Existing DX Spider installation detected!"
    read -p "Continue and overwrite? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Aborted."
        exit 1
    fi
fi

#------------------------------------------------------------------------------
# Install dependencies
#------------------------------------------------------------------------------
echo "[1/8] Installing Perl dependencies..."

# Fix Raspbian stretch (Debian 9) EOL repository issue
if grep -q "stretch" /etc/os-release 2>/dev/null; then
    if grep -qE "raspbian\.raspberrypi\.org|archive\.raspbian\.org" /etc/apt/sources.list 2>/dev/null; then
        echo "    Detected Raspbian Stretch with EOL repositories."
        echo "    Switching to legacy.raspbian.org..."
        cp /etc/apt/sources.list /etc/apt/sources.list.bak
        sed -i 's|raspbian.raspberrypi.org|legacy.raspbian.org|g' /etc/apt/sources.list
        sed -i 's|archive.raspbian.org|legacy.raspbian.org|g' /etc/apt/sources.list
        echo "    Backup saved to /etc/apt/sources.list.bak"
    fi
fi

apt-get update -qq
apt-get install -y -qq \
    perl \
    libtimedate-perl \
    libnet-telnet-perl \
    libcurses-perl \
    libdigest-sha-perl \
    libdata-dumper-simple-perl \
    libjson-perl \
    libmath-round-perl \
    libnet-cidr-lite-perl \
    git \
    procps \
    curl \
    2>/dev/null

echo "    Dependencies installed."

#------------------------------------------------------------------------------
# Create sysop user and spider group
#------------------------------------------------------------------------------
echo "[2/8] Creating sysop user and spider group..."

# Create spider group if not exists
if ! getent group spider >/dev/null 2>&1; then
    groupadd -g 251 spider
    echo "    Created group: spider (gid 251)"
else
    echo "    Group spider already exists"
fi

# Create sysop user if not exists
if ! id -u sysop >/dev/null 2>&1; then
    useradd -m -s /bin/bash -g spider sysop
    echo "    Created user: sysop"
else
    echo "    User sysop already exists"
    usermod -g spider sysop 2>/dev/null || true
fi

# Add root and BPQ user to spider group
usermod -aG spider root 2>/dev/null || true
if id -u "$BPQ_USER" >/dev/null 2>&1; then
    usermod -aG spider "$BPQ_USER" 2>/dev/null || true
    echo "    Added $BPQ_USER to spider group"
fi

#------------------------------------------------------------------------------
# Clone DX Spider
#------------------------------------------------------------------------------
echo "[3/8] Downloading DX Spider..."

# Remove old installation if exists
rm -rf /home/sysop/spider 2>/dev/null || true
rm -f /spider 2>/dev/null || true

# Clone repository - try GitHub mirror first (official server often down)
cd /home/sysop
SPIDER_REPO="https://github.com/dad98253/spider.git"
SPIDER_REPO_ALT="git://scm.dxcluster.org/scm/spider"

echo "    Trying GitHub mirror..."
if ! sudo -u sysop git clone --quiet "$SPIDER_REPO" spider 2>/dev/null; then
    echo "    GitHub mirror failed, trying official server..."
    if ! sudo -u sysop git clone --quiet "$SPIDER_REPO_ALT" spider 2>/dev/null; then
        echo "ERROR: Could not clone DX Spider from any source."
        echo "Try manually: git clone $SPIDER_REPO /home/sysop/spider"
        exit 1
    fi
fi

# Create symlink
ln -sf /home/sysop/spider /spider

echo "    DX Spider downloaded to /home/sysop/spider"
echo "    Symlink created: /spider -> /home/sysop/spider"

#------------------------------------------------------------------------------
# Set permissions
#------------------------------------------------------------------------------
echo "[4/8] Setting permissions..."

chown -R sysop:spider /home/sysop/spider
find /spider -type d -exec chmod 2775 {} \;
find /spider -type f -exec chmod 775 {} \;

# Create local directories
sudo -u sysop mkdir -p /spider/local /spider/local_cmd /spider/connect

echo "    Permissions configured."

#------------------------------------------------------------------------------
# Configure DX Spider
#------------------------------------------------------------------------------
echo "[5/8] Configuring DX Spider..."

# Create DXVars.pm configuration
cat > /spider/local/DXVars.pm << DXVARS_EOF
# DXVars.pm - Local configuration for $CLUSTER_CALL
# Generated by install-dxspider.sh on $(date)

package main;

# Cluster identification
\$mycall = "$CLUSTER_CALL";
\$myalias = "$SYSOP_CALL";
\$myname = "$SYSOP_NAME";
\$myemail = "$SYSOP_EMAIL";
\$mylocator = "$LOCATOR";
\$myqth = "$QTH";

# Latitude/Longitude (derived from grid square - approximate)
# FN43SR = ~43.77N, 70.45W
\$mylatitude = 43.77;
\$mylongitude = -70.45;

# Allow telnet connections
\$allow_resolve = 1;

# Sysop privileges
@main::sysop = qw($SYSOP_CALL);

# Cluster settings
\$pinginterval = 300;          # Ping upstream every 5 minutes
\$obscount = 5;                # Observation count before timeout

1;
DXVARS_EOF

# Create Listeners.pm for telnet access
cat > /spider/local/Listeners.pm << LISTENERS_EOF
# Listeners.pm - Network listeners for $CLUSTER_CALL
# Generated by install-dxspider.sh on $(date)

package main;

@listen = (
    ["0.0.0.0", $SPIDER_PORT],    # Telnet access on port $SPIDER_PORT
);

1;
LISTENERS_EOF

# Create upstream connection file for primary cluster
cat > /spider/connect/$UPSTREAM_1 << UPSTREAM1_EOF
# Connection script for $UPSTREAM_1
# This connects to the upstream DX cluster network

timeout 60
abort (Busy|Sorry|Fail)
connect telnet $UPSTREAM_1 $UPSTREAM_1_PORT
client $UPSTREAM_1 telnet
UPSTREAM1_EOF

# Create upstream connection file for backup cluster
cat > /spider/connect/$UPSTREAM_2 << UPSTREAM2_EOF
# Connection script for $UPSTREAM_2
# Backup upstream DX cluster

timeout 60
abort (Busy|Sorry|Fail)
connect telnet $UPSTREAM_2 $UPSTREAM_2_PORT
client $UPSTREAM_2 telnet
UPSTREAM2_EOF

chown -R sysop:spider /spider/local /spider/connect
chmod 644 /spider/local/*.pm
chmod 644 /spider/connect/*

echo "    Configuration files created:"
echo "      /spider/local/DXVars.pm"
echo "      /spider/local/Listeners.pm"
echo "      /spider/connect/$UPSTREAM_1"
echo "      /spider/connect/$UPSTREAM_2"

#------------------------------------------------------------------------------
# Initialize sysop user in Spider
#------------------------------------------------------------------------------
echo "[6/8] Initializing sysop user database..."

cd /spider/perl
sudo -u sysop perl create_sysop.pl "$SYSOP_CALL" "$SYSOP_NAME" "$LOCATOR" 2>/dev/null || true

echo "    Sysop user initialized."

#------------------------------------------------------------------------------
# Create systemd service
#------------------------------------------------------------------------------
echo "[7/8] Creating systemd service..."

cat > /lib/systemd/system/dxspider.service << SERVICE_EOF
[Unit]
Description=DX Spider DX Cluster ($CLUSTER_CALL)
After=network.target

[Service]
Type=simple
User=sysop
Group=spider
WorkingDirectory=/spider/perl
ExecStart=/usr/bin/perl -w /spider/perl/cluster.pl
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable dxspider

echo "    Systemd service created and enabled."

#------------------------------------------------------------------------------
# Configure inetd and services
#------------------------------------------------------------------------------
echo "[8/8] Configuring network services..."

# Add to /etc/services if not present
if ! grep -q "^dxspider" /etc/services 2>/dev/null; then
    echo "" >> /etc/services
    echo "# DX Spider Cluster" >> /etc/services
    echo "dxspider        $SPIDER_PORT/tcp                        # DX Spider Cluster" >> /etc/services
    echo "    Added dxspider to /etc/services (port $SPIDER_PORT)"
else
    echo "    dxspider already in /etc/services"
fi

# Add to /etc/inetd.conf if not present (for BPQ integration)
if ! grep -q "^dxspider" /etc/inetd.conf 2>/dev/null; then
    echo "" >> /etc/inetd.conf
    echo "# DX Spider Cluster for BPQ access" >> /etc/inetd.conf
    echo "dxspider        stream  tcp     nowait  sysop   /spider/perl/client.pl client.pl sysop localhost" >> /etc/inetd.conf
    echo "    Added dxspider to /etc/inetd.conf"
else
    echo "    dxspider already in /etc/inetd.conf"
fi

# Reload inetd
if pgrep -x inetd >/dev/null 2>&1; then
    killall -HUP inetd
    echo "    Reloaded inetd"
else
    echo "    WARNING: inetd not running - start manually if needed"
fi

#------------------------------------------------------------------------------
# Start DX Spider
#------------------------------------------------------------------------------
echo ""
echo "Starting DX Spider..."
systemctl start dxspider

# Wait for startup
sleep 3

if systemctl is-active --quiet dxspider; then
    echo "DX Spider is running!"
else
    echo "WARNING: DX Spider may not have started correctly."
    echo "Check: journalctl -u dxspider -f"
fi

#------------------------------------------------------------------------------
# Output BPQ32 configuration snippet
#------------------------------------------------------------------------------
echo ""
echo "========================================"
echo "INSTALLATION COMPLETE"
echo "========================================"
echo ""
echo "DX Spider $CLUSTER_CALL is now running on port $SPIDER_PORT"
echo ""
echo "Test locally:"
echo "  telnet localhost $SPIDER_PORT"
echo ""
echo "Connect to upstream clusters (from Spider console):"
echo "  connect $UPSTREAM_1"
echo "  connect $UPSTREAM_2"
echo ""
echo "----------------------------------------"
echo "BPQ32 CONFIGURATION REQUIRED"
echo "----------------------------------------"
echo "Add the following to your bpq32.cfg:"
echo ""
echo "1. Update CMDPORT line (add $SPIDER_PORT at position 16):"
echo ""
echo "   CMDPORT 63000 63010 63020 63030 63040 63050 63060 63070 63080 63090 63100 63110 63120 63130 63140 63160 $SPIDER_PORT"
echo ""
echo "2. Add APPLICATION line:"
echo ""
echo "   APPLICATION 20,DX,C 9 HOST 16 S,$CLUSTER_CALL,CCEDX,255"
echo ""
echo "3. Update INFOMSG to add DX to the Applications menu"
echo ""
echo "4. Restart linbpq:"
echo "   sudo systemctl restart linbpq"
echo ""
echo "----------------------------------------"
echo "USEFUL COMMANDS"
echo "----------------------------------------"
echo "Service control:"
echo "  sudo systemctl status dxspider"
echo "  sudo systemctl restart dxspider"
echo "  journalctl -u dxspider -f"
echo ""
echo "Spider console (as sysop):"
echo "  su - sysop -c '/spider/perl/console.pl'"
echo ""
echo "Common Spider commands:"
echo "  sh/dx          - Show recent DX spots"
echo "  sh/links       - Show upstream connections"
echo "  connect NODE   - Connect to upstream cluster"
echo "  set/filter     - Configure spot filters"
echo "  bye            - Disconnect"
echo ""
echo "73 de $SYSOP_CALL"
