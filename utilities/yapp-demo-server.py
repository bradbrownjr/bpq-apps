#!/usr/bin/env python3
"""
YAPP Demo Server - Proof of Concept
Author: Brad Browning KC1JMH
Date: January 28, 2026
Version: 1.0

Simple standalone YAPP server demonstrating direct socket I/O (no stdio).
Bypasses BPQ32/inetd control character filtering by using raw TCP sockets.

USAGE:
    ./yapp-demo-server.py [--port PORT] [--host HOST]

INSTALLATION:
    1. Copy to /home/ect/utilities/
    2. Make executable: chmod +x yapp-demo-server.py
    3. Test standalone: ./yapp-demo-server.py
    4. (Optional) Add to /etc/services:
       yapp-demo  stream tcp nowait ect /usr/bin/python3 python3 /home/ect/utilities/yapp-demo-server.py

TESTING:
    telnet localhost 63020
    # Send YAPP ENQ: hex 05 01
    # Should receive YAPP ACK: hex 06

This demonstrates that YAPP protocol works fine when using direct sockets
instead of stdio pipes with terminal emulation.
"""

import socket
import threading
import argparse
import sys
import os
import time

VERSION = "1.0"

# YAPP Control Bytes
SOH = 0x01  # Start of header
STX = 0x02  # Start of text
ETX = 0x03  # End of text
EOT = 0x04  # End of transmission
ENQ = 0x05  # Enquiry (connection request)
ACK = 0x06  # Acknowledge
NAK = 0x15  # Negative acknowledge
CAN = 0x18  # Cancel


def handle_connection(conn, addr):
    """
    Handle single YAPP connection.
    
    Args:
        conn: socket connection object
        addr: (host, port) tuple
    """
    print("[{}] Connection from {}:{}".format(
        time.strftime("%H:%M:%S"), addr[0], addr[1]))
    
    try:
        # Send greeting (plain text, not YAPP protocol yet)
        greeting = b"YAPP Demo Server v{}\r\n".format(VERSION).encode('ascii')
        greeting += b"Send YAPP ENQ (0x05 0x01) to initiate transfer\r\n"
        greeting += b"Or send any text to test echo mode\r\n"
        greeting += b"Type 'quit' to disconnect\r\n\r\n"
        conn.send(greeting)
        
        # Simple echo/YAPP test loop
        while True:
            data = conn.recv(256)
            
            if not data:
                print("[{}] Client disconnected".format(time.strftime("%H:%M:%S")))
                break
                
            # Check for YAPP ENQ frame (connection request)
            if len(data) >= 2 and data[0] == ENQ and data[1] == 0x01:
                print("[{}] Received YAPP ENQ - sending ACK".format(
                    time.strftime("%H:%M:%S")))
                # Send YAPP ACK (acknowledging connection)
                conn.send(bytes([ACK]))
                continue
            
            # Check for quit command
            if b'quit' in data.lower():
                conn.send(b"73!\r\n")
                print("[{}] Client quit".format(time.strftime("%H:%M:%S")))
                break
            
            # Echo mode - show hex dump of received data
            hex_dump = ' '.join('{:02x}'.format(b) for b in data)
            response = "Received {} bytes: {}\r\n".format(len(data), hex_dump)
            conn.send(response.encode('ascii'))
            
            # Special handling for control characters
            if any(b < 0x20 for b in data):
                conn.send(b"INFO: Received control characters < 0x20\r\n")
                conn.send(b"      (This proves they're NOT filtered via direct socket!)\r\n")
    
    except Exception as e:
        print("[{}] Error: {}".format(time.strftime("%H:%M:%S"), str(e)))
    
    finally:
        conn.close()
        print("[{}] Connection closed".format(time.strftime("%H:%M:%S")))


def run_server(host, port):
    """
    Start YAPP demo server.
    
    Args:
        host: interface to bind to (0.0.0.0 for all)
        port: TCP port number
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((host, port))
        server.listen(5)
        
        print("=" * 60)
        print("YAPP Demo Server v{}".format(VERSION))
        print("=" * 60)
        print("Listening on {}:{}".format(host, port))
        print("Press Ctrl+C to stop")
        print("")
        print("TESTING:")
        print("  telnet localhost {}".format(port))
        print("  # Type any text to test echo")
        print("  # Send hex 05 01 to test YAPP ENQ")
        print("")
        
        while True:
            conn, addr = server.accept()
            # Spawn thread for each connection
            thread = threading.Thread(target=handle_connection, args=(conn, addr))
            thread.daemon = True
            thread.start()
    
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print("Server error: {}".format(str(e)))
        sys.exit(1)
    finally:
        server.close()
        print("Server stopped")


def main():
    parser = argparse.ArgumentParser(
        description='YAPP Demo Server - Proof of concept for direct socket I/O')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host interface to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=63020,
                        help='TCP port number (default: 63020)')
    parser.add_argument('--version', action='version',
                        version='YAPP Demo Server v{}'.format(VERSION))
    
    args = parser.parse_args()
    
    # Check if port is privileged (< 1024) and we're not root
    if args.port < 1024 and os.geteuid() != 0:
        print("ERROR: Port {} requires root privileges".format(args.port))
        print("       Use --port with value >= 1024, or run as root")
        sys.exit(1)
    
    run_server(args.host, args.port)


if __name__ == '__main__':
    main()
