#!/bin/bash
# Deploy apps to WS1EC node

set -e

NODE="ect@ws1ec.mainepacketradio.org"
PORT=4722

echo "Deploying apps to WS1EC node..."

# Copy main app launchers
scp -P $PORT apps/apps.py $NODE:/home/ect/apps/

# Copy forms app and data files
scp -P $PORT apps/forms.py $NODE:/home/ect/apps/
scp -P $PORT apps/forms/*.frm apps/forms/arl_messages.json $NODE:/home/ect/apps/forms/

# Make executables
ssh -p $PORT $NODE "chmod +x /home/ect/apps/apps.py /home/ect/apps/forms.py"

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
