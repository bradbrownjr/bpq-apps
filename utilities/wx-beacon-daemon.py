#!/usr/bin/env python3
"""
BPQ Weather Alert Beacon Daemon

Sends weather alert beacons via BPQ HOST interface.
Reads beacon text from ~/linbpq/beacontext.txt and transmits
as UI frames on VHF port every 15 minutes.

Version: 1.0
Author: KC1JMH
Date: 2026-01-22

Usage:
    wx-beacon-daemon.py [OPTIONS]

Options:
    -p, --port PORT        BPQ HOST port (default: 8010)
    -i, --interval MINS    Beacon interval in minutes (default: 15)
    -c, --callsign CALL    Beacon callsign (default: WS1EC-15)
    -r, --radio-port NUM   BPQ radio port number (default: 2)
    -f, --file PATH        Beacon text file (default: ~/linbpq/beacontext.txt)
    -d, --daemon           Run as daemon (background)
    -v, --verbose          Verbose logging
    -h, --help             Show this help
"""

import socket
import time
import sys
import os
import signal
import argparse
from datetime import datetime


VERSION = "1.0"


def read_beacon_text(filepath):
    """Read beacon text from file."""
    try:
        with open(os.path.expanduser(filepath), 'r') as f:
            text = f.read().strip()
        return text if text else None
    except IOError:
        return None


def send_ui_frame(host, port, callsign, radio_port, text, verbose=False):
    """
    Send UI frame via BPQ HOST interface.
    
    BPQ HOST protocol for UI frames:
    1. Connect to HOST port
    2. Send: "CALLSIGN" (authenticate as callsign)
    3. Send: "U <port> <dest> <text>" for unproto/UI frame
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        # Authenticate with callsign
        sock.sendall("{}\r".format(callsign).encode('ascii'))
        time.sleep(0.5)
        
        # Send UI frame command
        # Format: U <port> <destination> <text>
        # Destination is typically "BEACON" or "CQ"
        ui_cmd = "U {} BEACON {}\r".format(radio_port, text)
        sock.sendall(ui_cmd.encode('ascii'))
        
        if verbose:
            print("{} - Sent beacon: {}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                text[:50] + "..." if len(text) > 50 else text
            ))
        
        sock.close()
        return True
        
    except socket.error as e:
        if verbose:
            print("{} - Socket error: {}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                str(e)
            ))
        return False
    except Exception as e:
        if verbose:
            print("{} - Error sending beacon: {}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                str(e)
            ))
        return False


def daemonize():
    """Fork process to run as daemon."""
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # Exit parent
    except OSError as e:
        sys.stderr.write("Fork failed: {}\n".format(e))
        sys.exit(1)
    
    # Decouple from parent environment
    os.chdir('/')
    os.setsid()
    os.umask(0)
    
    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("Fork #2 failed: {}\n".format(e))
        sys.exit(1)
    
    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def beacon_loop(args):
    """Main beacon loop."""
    interval_seconds = args.interval * 60
    
    if args.verbose:
        print("WX Beacon Daemon v{} starting".format(VERSION))
        print("BPQ HOST: {}:{}".format(args.host, args.port))
        print("Callsign: {}".format(args.callsign))
        print("Radio Port: {}".format(args.radio_port))
        print("Beacon file: {}".format(args.file))
        print("Interval: {} minutes".format(args.interval))
        print("-" * 40)
    
    while True:
        # Read beacon text
        text = read_beacon_text(args.file)
        
        if text:
            # Split multi-line beacons into separate UI frames
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    send_ui_frame(
                        args.host, 
                        args.port, 
                        args.callsign, 
                        args.radio_port, 
                        line.strip(),
                        args.verbose
                    )
                    time.sleep(1)  # Delay between lines
        elif args.verbose:
            print("{} - No beacon text found in {}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                args.file
            ))
        
        # Wait for next interval
        time.sleep(interval_seconds)


def signal_handler(signum, frame):
    """Handle termination signals."""
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='BPQ Weather Alert Beacon Daemon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wx-beacon-daemon.py
      Run with defaults (port 8010, 15 min interval)
  
  wx-beacon-daemon.py -v
      Run with verbose logging
  
  wx-beacon-daemon.py -d
      Run as background daemon
  
  wx-beacon-daemon.py -i 30 -c WS1EC-4
      30 minute interval, different callsign
        """
    )
    
    parser.add_argument('-p', '--port', type=int, default=8010,
                        help='BPQ HOST port (default: 8010)')
    parser.add_argument('--host', default='127.0.0.1',
                        help='BPQ HOST address (default: 127.0.0.1)')
    parser.add_argument('-i', '--interval', type=int, default=15,
                        help='Beacon interval in minutes (default: 15)')
    parser.add_argument('-c', '--callsign', default='WS1EC-15',
                        help='Beacon callsign (default: WS1EC-15)')
    parser.add_argument('-r', '--radio-port', type=int, default=2,
                        help='BPQ radio port number (default: 2)')
    parser.add_argument('-f', '--file', 
                        default='~/linbpq/beacontext.txt',
                        help='Beacon text file (default: ~/linbpq/beacontext.txt)')
    parser.add_argument('-d', '--daemon', action='store_true',
                        help='Run as daemon (background)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose logging')
    parser.add_argument('--version', action='version', 
                        version='wx-beacon-daemon {}'.format(VERSION))
    
    args = parser.parse_args()
    
    # Daemonize if requested
    if args.daemon:
        if args.verbose:
            print("Daemonizing...")
        daemonize()
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run beacon loop
    try:
        beacon_loop(args)
    except KeyboardInterrupt:
        if args.verbose:
            print("\nShutting down...")
        sys.exit(0)


if __name__ == '__main__':
    main()
