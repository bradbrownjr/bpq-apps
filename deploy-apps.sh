#!/bin/bash
# Deploy apps.py to WS1EC node

set -e

echo "Deploying apps.py to WS1EC node..."

# Copy app to node
scp -i ~/.ssh/id_rsa -P 4722 apps/apps.py ect@ws1ec.mainepacketradio.org:/home/ect/apps/

# Make executable and copy apps.json if needed
ssh -i ~/.ssh/id_rsa -p 4722 ect@ws1ec.mainepacketradio.org "chmod +x /home/ect/apps/apps.py"

echo ""
echo "Deployed successfully!"
echo ""
echo "To add APPS to BPQ32, add this APPLICATION line (in alphabetical order):"
echo "  APPLICATION X,APPS,C 9 HOST YY S K            ; apps.py"
echo ""
echo "And add to /etc/services:"
echo "  apps            63YY0/tcp       # Application launcher"
echo ""
echo "And add to /etc/inetd.conf:"
echo "  apps  stream  tcp  nowait  ect  /home/ect/apps/apps.py  apps.py"
echo ""
echo "Then: sudo killall -HUP inetd && sudo systemctl restart linbpq"
