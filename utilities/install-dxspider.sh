#!/bin/bash
# install-dxspider.sh - DX Spider Cluster Installation for LinBPQ
# Version: 1.1
# Author: KC1JMH
# Date: 2026-01-24
#
# Installs DX Spider as an isolated Perl service with dedicated user (sysop),
# integrating with linbpq via telnet port 7300.
#
# Usage: sudo ./install-dxspider.sh
#
# IMPORTANT: After installation, you must contact an upstream DX Spider node
# sysop to request node peering. Without peering approval, your cluster can
# receive spots but cannot relay local spots to the network.
#
# Find peering partners at:
#   https://www.dxcluster.info/telnet/index.php
#   Filter by "DX Spider" software and contact sysops in your region.
#
# References:
#   https://github.com/glaukos78/dxspider_installation_v2
#   https://www.cantab.net/users/john.wiseman/Documents/LinBPQtoSpider.html

set -e

#------------------------------------------------------------------------------
# Configuration - Defaults (will be auto-detected if possible)
#------------------------------------------------------------------------------
CLUSTER_CALL=""                 # Cluster callsign (auto-detected)
SYSOP_CALL=""                   # Primary sysop callsign (auto-detected)
SYSOP_NAME=""                   # Sysop first name
SYSOP_EMAIL=""                  # Sysop email
LOCATOR=""                      # Maidenhead grid square (auto-detected)
QTH=""                          # QTH description

# Local ports
SPIDER_PORT="7300"              # DX Spider telnet port
BPQ_USER=""                     # Existing BPQ user (auto-detected)
BPQ_CFG=""                      # Path to bpq32.cfg (auto-detected)

#------------------------------------------------------------------------------
# Auto-detect configuration from bpq32.cfg
#------------------------------------------------------------------------------
detect_bpq_config() {
    # Find bpq32.cfg
    for cfg in ~/linbpq/bpq32.cfg /home/*/linbpq/bpq32.cfg /etc/bpq32.cfg; do
        if [ -f "$cfg" ]; then
            BPQ_CFG="$cfg"
            break
        fi
    done

    if [ -z "$BPQ_CFG" ]; then
        echo "    WARNING: Could not find bpq32.cfg"
        return 1
    fi

    echo "    Found: $BPQ_CFG"

    # Extract NODECALL (e.g., WS1EC-15 -> WS1EC)
    local nodecall=$(grep -i "^NODECALL=" "$BPQ_CFG" 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' \r')
    local basecall=$(echo "$nodecall" | cut -d- -f1)

    if [ -n "$basecall" ]; then
        echo "    Detected base callsign: $basecall"
        SYSOP_CALL="$basecall"

        # Find used SSIDs from APPLICATION lines
        local used_ssids=$(grep -oE "$basecall-[0-9]+" "$BPQ_CFG" 2>/dev/null | cut -d- -f2 | sort -n | uniq)
        echo "    SSIDs in use: $(echo $used_ssids | tr '\n' ' ')"

        # Find first available SSID (skip 0, prefer 6 for cluster, then 1-15)
        local available_ssid=""
        for ssid in 6 7 8 9 11 12 13 14 1; do
            if ! echo "$used_ssids" | grep -qw "$ssid"; then
                available_ssid="$ssid"
                break
            fi
        done

        if [ -n "$available_ssid" ]; then
            CLUSTER_CALL="$basecall-$available_ssid"
            echo "    Suggested cluster call: $CLUSTER_CALL"
        fi
    fi

    # Extract LOCATOR
    local locator=$(grep -i "^LOCATOR=" "$BPQ_CFG" 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' \r')
    if [ -n "$locator" ]; then
        LOCATOR="$locator"
        echo "    Detected grid square: $LOCATOR"
    fi

    # Detect BPQ user from config file ownership
    local cfg_owner=$(stat -c '%U' "$BPQ_CFG" 2>/dev/null)
    if [ -n "$cfg_owner" ] && [ "$cfg_owner" != "root" ]; then
        BPQ_USER="$cfg_owner"
        echo "    Detected BPQ user: $BPQ_USER"
    fi

    return 0
}

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
echo "========================================"
echo ""

#------------------------------------------------------------------------------
# Auto-detect and confirm configuration
#------------------------------------------------------------------------------
echo "Detecting configuration from bpq32.cfg..."
detect_bpq_config

# Prompt for cluster callsign
echo ""
if [ -n "$CLUSTER_CALL" ]; then
    read -p "Cluster callsign [$CLUSTER_CALL]: " input
    [ -n "$input" ] && CLUSTER_CALL="$input"
else
    read -p "Cluster callsign (e.g., WS1EC-6): " CLUSTER_CALL
    if [ -z "$CLUSTER_CALL" ]; then
        echo "ERROR: Cluster callsign is required."
        exit 1
    fi
fi

# Prompt for grid square
if [ -n "$LOCATOR" ]; then
    read -p "Grid square [$LOCATOR]: " input
    [ -n "$input" ] && LOCATOR="$input"
else
    read -p "Grid square (e.g., FN43SR): " LOCATOR
    if [ -z "$LOCATOR" ]; then
        echo "ERROR: Grid square is required."
        exit 1
    fi
fi

# Prompt for QTH
read -p "QTH/Location (e.g., Windham, ME) [$QTH]: " input
[ -n "$input" ] && QTH="$input"
if [ -z "$QTH" ]; then
    read -p "QTH/Location (e.g., Windham, ME): " QTH
fi

# Prompt for sysop callsign
if [ -n "$SYSOP_CALL" ]; then
    read -p "Sysop callsign [$SYSOP_CALL]: " input
    [ -n "$input" ] && SYSOP_CALL="$input"
else
    read -p "Sysop callsign: " SYSOP_CALL
    if [ -z "$SYSOP_CALL" ]; then
        echo "ERROR: Sysop callsign is required."
        exit 1
    fi
fi

# Prompt for sysop name
read -p "Sysop first name: " SYSOP_NAME
if [ -z "$SYSOP_NAME" ]; then
    SYSOP_NAME="Sysop"
fi

# Prompt for sysop email
read -p "Sysop email (optional): " SYSOP_EMAIL

echo ""
echo "========================================"
echo "Configuration:"
echo "  Cluster:  $CLUSTER_CALL"
echo "  Grid:     $LOCATOR"
echo "  Location: $QTH"
echo "  Sysop:    $SYSOP_CALL ($SYSOP_NAME)"
echo "========================================"
echo ""
read -p "Continue with installation? (Y/n): " confirm
if [ "$confirm" = "n" ] || [ "$confirm" = "N" ]; then
    echo "Aborted."
    exit 0
fi
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
    # Only match uncommented lines pointing to EOL repos
    if grep -v "^#" /etc/apt/sources.list 2>/dev/null | grep -qE "raspbian\.raspberrypi\.org|archive\.raspbian\.org"; then
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
SPIDER_REPO_ALT="https://github.com/latchdevel/DXspider.git"

echo "    Trying GitHub mirror (dad98253)..."
if sudo -u sysop git clone --quiet "$SPIDER_REPO" spider 2>&1; then
    echo "    Download successful."
    # Switch to master branch (avoid MOJO branch which requires Mojolicious)
    cd spider
    sudo -u sysop git checkout master 2>/dev/null || sudo -u sysop git checkout main 2>/dev/null || true
    cd ..
else
    echo "    First mirror failed, trying alternate (latchdevel)..."
    if sudo -u sysop git clone --quiet "$SPIDER_REPO_ALT" spider 2>&1; then
        echo "    Download successful."
        cd spider
        sudo -u sysop git checkout master 2>/dev/null || sudo -u sysop git checkout main 2>/dev/null || true
        cd ..
    else
        echo ""
        echo "ERROR: Could not clone DX Spider from any source."
        echo "Manual install required:"
        echo "  sudo -u sysop git clone $SPIDER_REPO /home/sysop/spider"
        echo ""
        echo "Or download manually from: https://github.com/dad98253/spider"
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
sudo -u sysop mkdir -p /spider/data /spider/data/debug

# Ensure data directory is writable
chown -R sysop:spider /spider/data
chmod -R 2775 /spider/data

echo "    Permissions configured."

#------------------------------------------------------------------------------
# Configure DX Spider
#------------------------------------------------------------------------------
echo "[5/8] Configuring DX Spider..."

# Create DXVars.pm configuration
# Escape @ in email for Perl
ESCAPED_EMAIL=$(echo "$SYSOP_EMAIL" | sed 's/@/\\@/g')

cat > /spider/local/DXVars.pm << DXVARS_EOF
# DXVars.pm - Local configuration for $CLUSTER_CALL
# Generated by install-dxspider.sh on $(date)

package main;

# Cluster identification (CAPITAL LETTERS)
\$mycall = "$CLUSTER_CALL";
\$myalias = "$SYSOP_CALL";
\$myname = "$SYSOP_NAME";
\$myemail = "$ESCAPED_EMAIL";
\$mylocator = "$LOCATOR";
\$myqth = "$QTH";
\$mybbsaddr = "$SYSOP_CALL\@$CLUSTER_CALL.#$(echo $QTH | cut -d, -f2 | tr -d ' ' | cut -c1-2 | tr 'a-z' 'A-Z').USA.NOAM";

# Coordinates (approximate - derived from grid square)
\$mylatitude = 0;
\$mylongitude = 0;

# Language
\$lang = 'en';

# System paths (required)
\$data = "\$root/data";
\$system = "\$root/sys";
\$cmd = "\$root/cmd";
\$localcmd = "\$root/local_cmd";
\$userfn = "\$data/users";
\$motd = "\$data/motd";

# Network
\$clusteraddr = "localhost";
\$clusterport = 27754;

# User interface
\$yes = 'Yes';
\$no = 'No';
\$user_interval = 11*60;

# Debug (comment out for production)
@debug = qw(chan);

# Sysop privileges
@main::sysop = qw($SYSOP_CALL);

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

chown -R sysop:spider /spider/local /spider/connect
chmod 644 /spider/local/*.pm

echo "    Configuration files created:"
echo "      /spider/local/DXVars.pm"
echo "      /spider/local/Listeners.pm"

#------------------------------------------------------------------------------
# Initialize sysop user in Spider
#------------------------------------------------------------------------------
echo "[6/8] Initializing sysop user database..."

cd /spider/perl

# Create sysop user - requires interactive responses:
# "Want to add a user? (n/y)" -> y
# Then it creates the user from DXVars.pm settings
echo "y" | sudo -u sysop perl create_sysop.pl 2>/dev/null || true

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
# Add to /etc/services (informational only)
#------------------------------------------------------------------------------
echo "[8/8] Configuring network services..."

# Add to /etc/services if not present (informational only, systemd handles the port)
if ! grep -q "^dxspider" /etc/services 2>/dev/null; then
    echo "" >> /etc/services
    echo "# DX Spider Cluster" >> /etc/services
    echo "dxspider        $SPIDER_PORT/tcp                        # DX Spider Cluster" >> /etc/services
    echo "    Added dxspider to /etc/services (port $SPIDER_PORT)"
else
    echo "    dxspider already in /etc/services"
fi

# NOTE: We do NOT add to inetd.conf - systemd runs the daemon directly
# inetd would conflict with the systemd service on the same port

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
echo "----------------------------------------"
echo "IMPORTANT: UPSTREAM NODE PEERING"
echo "----------------------------------------"
echo "Your cluster is running but NOT connected to the DX network."
echo "To relay spots bidirectionally, you need peering approval."
echo ""
echo "1. Find DX Spider nodes at:"
echo "   https://www.dxcluster.info/telnet/index.php"
echo "   Filter by 'DX Spider' and choose nodes in your region."
echo ""
echo "2. Contact the sysop and request node peering:"
echo "   'Hi, I'm $SYSOP_CALL running $CLUSTER_CALL in $QTH ($LOCATOR)."
echo "   Would you add us as a peering node? Running DX Spider on packet radio.'"
echo ""
echo "3. Once approved, create connect script:"
echo "   /spider/connect/<nodecall>"
echo ""
echo "Example connect script for AE3N-2:"
echo "   timeout 60"
echo "   abort (Busy|Sorry|Fail)"
echo "   connect telnet dxc.ae3n.us 7300"
echo "   'ogin:' '$CLUSTER_CALL'"
echo "   client ae3n-2 spider"
echo ""
echo "4. Define and connect from Spider console:"
echo "   set/node <nodecall>"
echo "   connect <nodecall>"
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
echo "  sh/c           - Show connected nodes/users"
echo "  set/node CALL  - Define remote node"
echo "  connect NODE   - Connect to upstream cluster"
echo "  dx FREQ CALL   - Announce a DX spot"
echo "  bye            - Disconnect"
echo ""
echo "73 de $SYSOP_CALL"
