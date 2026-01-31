#!/bin/bash
# Deploy antenna.py to WS1EC node

set -e

SSH_KEY="$HOME/.ssh/id_rsa"
SSH_PORT="4722"
SSH_HOST="ect@ws1ec.mainepacketradio.org"
APP_NAME="antenna.py"
SERVICE_PORT="63015"

echo "=== Deploying antenna.py to WS1EC ==="
echo ""

# Step 1: Copy file
echo "[1/5] Copying antenna.py to remote host..."
scp -i "$SSH_KEY" -P "$SSH_PORT" "apps/$APP_NAME" "$SSH_HOST:/home/ect/apps/"

# Step 2: Make executable
echo "[2/5] Making antenna.py executable..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_HOST" "chmod +x /home/ect/apps/$APP_NAME"

# Step 3: Add to /etc/services and /etc/inetd.conf (requires sudo)
echo "[3/5] Adding to /etc/services and /etc/inetd.conf (sudo required)..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" -t "$SSH_HOST" "sudo bash -c '
echo \"antenna        $SERVICE_PORT/tcp       # Antenna Calculator\" >> /etc/services &&
echo \"antenna  stream  tcp  nowait  ect  /home/ect/apps/antenna.py  antenna.py\" >> /etc/inetd.conf &&
killall -HUP inetd &&
echo \"Services configured successfully\"
'"

# Step 4: Add to bpq32.cfg
echo "[4/5] Adding APPLICATION line to bpq32.cfg..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_HOST" "sed -i '/^APPLICATION.*YAPP/a APPLICATION 17,ANTENNA,C 9 HOST 17 NOCALL S K,WS1EC-6,CCEDX,255' ~/linbpq/bpq32.cfg"

# Step 5: Verify
echo "[5/5] Verifying deployment..."
ssh -i "$SSH_KEY" -p "$SSH_PORT" "$SSH_HOST" "
echo 'File permissions:' &&
ls -lh /home/ect/apps/antenna.py &&
echo '' &&
echo 'Service entry:' &&
grep antenna /etc/services &&
echo '' &&
echo 'inetd entry:' &&
grep antenna /etc/inetd.conf &&
echo '' &&
echo 'BPQ APPLICATION entry:' &&
grep 'APPLICATION.*ANTENNA' ~/linbpq/bpq32.cfg
"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Restart linbpq: ssh -i $SSH_KEY -p $SSH_PORT -t $SSH_HOST 'sudo systemctl restart linbpq'"
echo "2. Test via telnet: telnet ws1ec.mainepacketradio.org $SERVICE_PORT"
echo "3. Test via RF: Connect to WS1EC and type: ANTENNA"
