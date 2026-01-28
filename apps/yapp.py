#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YAPP Protocol Implementation for BPQ Packet Radio Apps

⚠️  STATUS: DEAD END - NOT VIABLE FOR PACKET RADIO

PROBLEM: Control characters (< 0x20) required by YAPP are ALWAYS stripped by
BPQ32's terminal emulation layer. Packet radio users have NO way to bypass
this filtering - they can only access services via APPLICATION commands which
go through the stdio/inetd pipeline.

ROOT CAUSES (per BPQ32 source code analysis Jan 2026):
    1. Terminal emulation filters < 0x20 (TelnetV6.c:861-897)
    2. Node explicitly rejects YAPP frames (Cmd.c:4972-5007)
    3. No telnet binary mode support (only echo/suppressgoahead)
    4. Packet radio users cannot make outbound TCP connections

This code is REFERENCE ONLY for the unlikely case G8BPQ adds binary mode
support to BPQ32. For current packet radio file serving, use text-based
approaches (forms.py, gopher.py text viewing).

See docs/YAPP-PROTOCOL.md for complete technical analysis and research.

A Python 3.5.3 compatible implementation of the YAPP (Yet Another Packet
Protocol) file transfer protocol for packet radio networks.

Usage:
    # As a sender
    yapp = YAPPProtocol(read_func, write_func)
    success, msg = yapp.send_file("test.txt", file_data)
    
    # As a receiver
    yapp = YAPPProtocol(read_func, write_func)
    filename, data, error = yapp.receive_file()

Author: Brad KC1JMH
Version: 1.4
Date: 2026-01-28
License: MIT

See also:
    docs/YAPP-PROTOCOL.md - Complete protocol documentation
"""

from __future__ import print_function
import sys
import time
import os

__version__ = "1.4"

# YAPP Control Characters
SOH = 0x01  # Start of Header (file header frame)
STX = 0x02  # Start of Text (data block)
ETX = 0x03  # End of Text (end of file data)
EOT = 0x04  # End of Transmission (close session)
ENQ = 0x05  # Enquiry (initiate YAPP session)
ACK = 0x06  # Acknowledgment (positive response)
DLE = 0x10  # Data Link Escape (reserved)
NAK = 0x15  # Negative Acknowledgment (error/reject)
CAN = 0x18  # Cancel (abort transfer)

# YAPP States
YAPP_IDLE = 0
YAPP_WAIT_INIT_ACK = 1
YAPP_WAIT_HEADER_ACK = 2
YAPP_SENDING_DATA = 3
YAPP_WAIT_EOF_ACK = 4
YAPP_WAIT_HEADER = 5
YAPP_RECEIVING_DATA = 6
YAPP_WAIT_EOT = 7

# State names for debugging
STATE_NAMES = {
    YAPP_IDLE: "IDLE",
    YAPP_WAIT_INIT_ACK: "WAIT_INIT_ACK",
    YAPP_WAIT_HEADER_ACK: "WAIT_HEADER_ACK",
    YAPP_SENDING_DATA: "SENDING_DATA",
    YAPP_WAIT_EOF_ACK: "WAIT_EOF_ACK",
    YAPP_WAIT_HEADER: "WAIT_HEADER",
    YAPP_RECEIVING_DATA: "RECEIVING_DATA",
    YAPP_WAIT_EOT: "WAIT_EOT"
}

# Control character names for debugging
CTRL_NAMES = {
    SOH: "SOH", STX: "STX", ETX: "ETX", EOT: "EOT",
    ENQ: "ENQ", ACK: "ACK", DLE: "DLE", NAK: "NAK", CAN: "CAN"
}

# Protocol constants
MAX_DATA_LEN = 250  # Leave some room for framing
DEFAULT_TIMEOUT = 30  # seconds
EOF_TIMEOUT = 60  # longer timeout for final ACK


class YAPPError(Exception):
    """YAPP protocol error"""
    pass


class YAPPTimeout(YAPPError):
    """YAPP timeout error"""
    pass


class YAPPAborted(YAPPError):
    """YAPP transfer was cancelled"""
    pass


class YAPPProtocol(object):
    """
    YAPP file transfer protocol handler.
    
    This class implements both sender and receiver sides of the YAPP
    protocol for transferring binary files over packet radio.
    
    Example usage with stdin/stdout:
        def read_bytes(n, timeout):
            # Read n bytes with timeout
            return sys.stdin.buffer.read(n)
        
        def write_bytes(data):
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        
        yapp = YAPPProtocol(read_bytes, write_bytes)
    """
    
    def __init__(self, read_func, write_func, debug=False):
        """
        Initialize YAPP protocol handler.
        
        Args:
            read_func: Function(n, timeout) -> bytes to read n bytes
            write_func: Function(data) to write bytes
            debug: Enable debug output
        """
        self.read_func = read_func
        self.write_func = write_func
        self.debug = debug
        self.state = YAPP_IDLE
        self.yappc_supported = False  # YAPPC resume capability
        
    def _debug(self, msg):
        """Print debug message if debugging enabled"""
        if self.debug:
            state = STATE_NAMES.get(self.state, str(self.state))
            sys.stderr.write("[YAPP:{}] {}\n".format(state, msg))
            sys.stderr.flush()
    
    def _send_frame(self, control, data=None):
        """
        Send a YAPP frame.
        
        Args:
            control: Control byte (SOH, STX, ACK, etc.)
            data: Optional data payload (bytes)
        """
        if data is None:
            frame = bytes([control, 0x01])
        else:
            # Length encoding: 0 = 256 bytes, 1-255 = that many bytes
            length = len(data) if len(data) < 256 else 0
            frame = bytes([control, length]) + data
        
        ctrl_name = CTRL_NAMES.get(control, hex(control))
        self._debug("TX: {} len={}".format(ctrl_name, len(frame)))
        self.write_func(frame)
    
    def _receive_frame(self, timeout=DEFAULT_TIMEOUT):
        """
        Receive a YAPP frame.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (control_byte, data_bytes) or (None, None) on timeout
            
        Raises:
            YAPPTimeout: On timeout
            YAPPAborted: If CAN received
        """
        # Read 2-byte header
        header = self.read_func(2, timeout)
        if header is None or len(header) < 2:
            raise YAPPTimeout("Timeout waiting for frame header")
        
        control = header[0] if isinstance(header[0], int) else ord(header[0])
        length = header[1] if isinstance(header[1], int) else ord(header[1])
        
        ctrl_name = CTRL_NAMES.get(control, hex(control))
        self._debug("RX: {} raw_len={}".format(ctrl_name, length))
        
        # Check for cancel
        if control == CAN:
            raise YAPPAborted("Transfer cancelled by remote")
        
        # Simple control frames (ACK, NAK, ENQ, ETX, EOT) may have no data
        if control in (ACK, ENQ, ETX, EOT) and length <= 2:
            return (control, bytes([length]))
        
        # NAK may have error message
        if control == NAK:
            if length > 0:
                data = self.read_func(length, timeout)
                return (control, data if data else b'')
            return (control, b'')
        
        # SOH and STX frames have data payload
        if control in (SOH, STX):
            actual_length = length if length > 0 else 256
            data = self.read_func(actual_length, timeout)
            if data is None or len(data) < actual_length:
                raise YAPPTimeout("Timeout reading frame data")
            return (control, data)
        
        # Unknown control byte
        return (control, bytes([length]))
    
    def send_file(self, filename, filedata, timestamp=None):
        """
        Send a file using YAPP protocol.
        
        Args:
            filename: Name of file (will be sent to receiver)
            filedata: File contents as bytes
            timestamp: Optional file modification time (for YAPPC resume)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            return self._send_file_impl(filename, filedata, timestamp)
        except YAPPAborted as e:
            return (False, str(e))
        except YAPPTimeout as e:
            return (False, "Timeout: {}".format(e))
        except YAPPError as e:
            return (False, str(e))
        except Exception as e:
            return (False, "Error: {}".format(e))
        finally:
            self.state = YAPP_IDLE
    
    def _send_file_impl(self, filename, filedata, timestamp):
        """Internal implementation of send_file"""
        
        # Step 1: Send session initiation
        self._debug("Initiating YAPP session")
        self._send_frame(ENQ)
        self.state = YAPP_WAIT_INIT_ACK
        
        # Step 2: Wait for session ACK
        ctrl, data = self._receive_frame()
        
        if ctrl == NAK:
            error = data.decode('ascii', errors='replace') if data else "Unknown error"
            return (False, "Session rejected: {}".format(error))
        
        if ctrl != ACK:
            return (False, "Invalid response to session init: {}".format(ctrl))
        
        # Check for YAPPC support
        if data and len(data) > 0:
            flag = data[0] if isinstance(data[0], int) else ord(data[0])
            self.yappc_supported = (flag == 0x02)
            if self.yappc_supported:
                self._debug("Remote supports YAPPC (resume)")
        
        # Step 3: Send file header
        self._debug("Sending file header: {} ({} bytes)".format(filename, len(filedata)))
        
        # Header format: filename + null + filesize as ASCII
        header = filename.encode('ascii', errors='replace') + b'\x00'
        header += str(len(filedata)).encode('ascii')
        
        # Add timestamp for YAPPC if available
        if timestamp and self.yappc_supported:
            header += b'\x00' + str(int(timestamp)).encode('ascii')
        
        # YAPP frames limited to 256 bytes max - validate header fits
        if len(header) > 256:
            return (False, "Header too long ({} bytes, max 256). Use shorter filename.".format(len(header)))
        
        self._send_frame(SOH, header)
        self.state = YAPP_WAIT_HEADER_ACK
        
        # Step 4: Wait for header ACK
        ctrl, data = self._receive_frame()
        
        if ctrl == NAK:
            error = data.decode('ascii', errors='replace') if data else "File rejected"
            return (False, error)
        
        if ctrl != ACK:
            return (False, "Invalid response to header: {}".format(ctrl))
        
        # Check for YAPPC resume offset
        resume_offset = 0
        if data and len(data) >= 2:
            flag = data[0] if isinstance(data[0], int) else ord(data[0])
            if flag == 0x02 and len(data) >= 5:
                # YAPPC resume: 4-byte offset follows
                resume_offset = (
                    (data[1] if isinstance(data[1], int) else ord(data[1])) |
                    ((data[2] if isinstance(data[2], int) else ord(data[2])) << 8) |
                    ((data[3] if isinstance(data[3], int) else ord(data[3])) << 16) |
                    ((data[4] if isinstance(data[4], int) else ord(data[4])) << 24)
                )
                self._debug("YAPPC resume from offset: {}".format(resume_offset))
        
        # Step 5: Send data blocks
        self.state = YAPP_SENDING_DATA
        offset = resume_offset
        total = len(filedata)
        blocks = 0
        
        while offset < total:
            chunk = filedata[offset:offset + MAX_DATA_LEN]
            self._send_frame(STX, chunk)
            offset += len(chunk)
            blocks += 1
            
            # Progress indicator every 10 blocks
            if blocks % 10 == 0:
                self._debug("Sent {} bytes ({:.0%})".format(offset, float(offset)/total))
        
        self._debug("Sent {} blocks, {} bytes total".format(blocks, offset))
        
        # Step 6: Send end of file
        self._send_frame(ETX)
        self.state = YAPP_WAIT_EOF_ACK
        
        # Step 7: Wait for final ACK (longer timeout)
        ctrl, data = self._receive_frame(EOF_TIMEOUT)
        
        if ctrl != ACK:
            return (False, "File not acknowledged: {}".format(ctrl))
        
        # Step 8: Send end of transmission
        self._send_frame(EOT)
        self.state = YAPP_IDLE
        
        return (True, "Sent {} bytes in {} blocks".format(total, blocks))
    
    def receive_file(self, save_dir=None):
        """
        Receive a file using YAPP protocol.
        
        Args:
            save_dir: Optional directory to save file (if None, returns data)
            
        Returns:
            Tuple of (filename, filedata, error_message)
            - On success: (filename, data, None)
            - On failure: (None, None, error_message)
        """
        try:
            return self._receive_file_impl(save_dir)
        except YAPPAborted as e:
            return (None, None, str(e))
        except YAPPTimeout as e:
            return (None, None, "Timeout: {}".format(e))
        except YAPPError as e:
            return (None, None, str(e))
        except Exception as e:
            return (None, None, "Error: {}".format(e))
        finally:
            self.state = YAPP_IDLE
    
    def _receive_file_impl(self, save_dir):
        """Internal implementation of receive_file"""
        
        # Step 1: Wait for session initiation
        self._debug("Waiting for YAPP session")
        ctrl, data = self._receive_frame()
        
        if ctrl != ENQ:
            return (None, None, "Expected ENQ, got {}".format(ctrl))
        
        # Step 2: Send session accept (with YAPPC support)
        self._debug("Session accepted")
        self._send_frame(ACK, bytes([0x02]))  # 0x02 = YAPPC support
        self.state = YAPP_WAIT_HEADER
        
        # Step 3: Receive file header
        ctrl, header = self._receive_frame()
        
        if ctrl != SOH:
            return (None, None, "Expected SOH header, got {}".format(ctrl))
        
        # Parse header: filename\0filesize[\0timestamp]
        parts = header.split(b'\x00')
        if len(parts) < 2:
            return (None, None, "Invalid file header")
        
        filename = parts[0].decode('ascii', errors='replace')
        try:
            filesize = int(parts[1].decode('ascii'))
        except ValueError:
            return (None, None, "Invalid file size in header")
        
        timestamp = None
        if len(parts) >= 3:
            try:
                timestamp = int(parts[2].decode('ascii'))
            except ValueError:
                pass
        
        self._debug("Receiving: {} ({} bytes)".format(filename, filesize))
        
        # Check for existing partial file (YAPPC resume)
        resume_offset = 0
        if save_dir and timestamp:
            partial_path = os.path.join(save_dir, filename + ".partial")
            if os.path.exists(partial_path):
                partial_size = os.path.getsize(partial_path)
                # Only resume if partial file is smaller
                if partial_size < filesize:
                    resume_offset = partial_size
                    self._debug("Resume from offset: {}".format(resume_offset))
        
        # Step 4: Send header ACK
        if resume_offset > 0:
            # YAPPC resume: ACK 0x02 + 4-byte offset
            offset_bytes = bytes([
                0x02,
                resume_offset & 0xFF,
                (resume_offset >> 8) & 0xFF,
                (resume_offset >> 16) & 0xFF,
                (resume_offset >> 24) & 0xFF
            ])
            self._send_frame(ACK, offset_bytes)
        else:
            self._send_frame(ACK)
        
        self.state = YAPP_RECEIVING_DATA
        
        # Step 5: Receive data blocks
        filedata = bytearray()
        blocks = 0
        
        while True:
            ctrl, data = self._receive_frame()
            
            if ctrl == STX:
                filedata.extend(data)
                blocks += 1
                
                if blocks % 10 == 0:
                    self._debug("Received {} bytes".format(len(filedata)))
                    
            elif ctrl == ETX:
                self._debug("End of file received")
                break
            
            elif ctrl == CAN:
                return (None, None, "Transfer cancelled by sender")
            
            else:
                return (None, None, "Unexpected frame: {}".format(ctrl))
        
        # Step 6: Verify size and send ACK
        received_size = len(filedata) + resume_offset
        if received_size != filesize:
            self._debug("Size mismatch: expected {}, got {}".format(filesize, received_size))
        
        self._send_frame(ACK)
        self.state = YAPP_WAIT_EOT
        
        # Step 7: Wait for EOT
        ctrl, data = self._receive_frame()
        
        # EOT is expected but not critical
        if ctrl != EOT:
            self._debug("Expected EOT, got {}".format(ctrl))
        
        self.state = YAPP_IDLE
        
        # Save file if directory specified
        if save_dir:
            filepath = os.path.join(save_dir, filename)
            mode = 'ab' if resume_offset > 0 else 'wb'
            with open(filepath, mode) as f:
                f.write(bytes(filedata))
            
            # Remove partial file marker
            partial_path = os.path.join(save_dir, filename + ".partial")
            if os.path.exists(partial_path):
                os.remove(partial_path)
            
            self._debug("Saved to: {}".format(filepath))
            return (filename, None, None)
        
        return (filename, bytes(filedata), None)
    
    def cancel(self):
        """Send cancel frame to abort current transfer"""
        self._debug("Cancelling transfer")
        self._send_frame(CAN)
        self.state = YAPP_IDLE
    
    def detect_yapp_init(self, data):
        """
        Check if data contains YAPP session initiation.
        
        Args:
            data: Bytes to check
            
        Returns:
            True if this looks like a YAPP ENQ
        """
        if len(data) >= 2:
            b0 = data[0] if isinstance(data[0], int) else ord(data[0])
            b1 = data[1] if isinstance(data[1], int) else ord(data[1])
            return (b0 == ENQ and b1 == 0x01)
        return False


# Convenience functions for stdin/stdout usage

def create_stdio_yapp(debug=False):
    """
    Create a YAPP protocol handler using stdin/stdout.
    
    IMPORTANT: This forces stdin/stdout into binary unbuffered mode for YAPP frames.
    
    Returns:
        YAPPProtocol instance configured for stdio
    """
    import select
    import io
    
    # Force binary mode for stdin/stdout (required for YAPP control bytes)
    # Use unbuffered mode (buffering=0) to prevent control byte loss
    if hasattr(sys.stdin, 'buffer'):
        stdin_raw = sys.stdin.buffer
    else:
        stdin_raw = sys.stdin
    
    # For stdout, we MUST use unbuffered binary mode
    # sys.stdout.buffer may still have line buffering which can corrupt YAPP frames
    if hasattr(sys.stdout, 'fileno'):
        try:
            # Open stdout file descriptor in binary unbuffered mode
            stdout_raw = io.open(sys.stdout.fileno(), 'wb', buffering=0, closefd=False)
        except Exception:
            # Fallback to buffer if available
            if hasattr(sys.stdout, 'buffer'):
                stdout_raw = sys.stdout.buffer
            else:
                stdout_raw = sys.stdout
    elif hasattr(sys.stdout, 'buffer'):
        stdout_raw = sys.stdout.buffer
    else:
        stdout_raw = sys.stdout
    
    def read_bytes(n, timeout):
        """Read n bytes from stdin with timeout"""
        result = bytearray()
        deadline = time.time() + timeout
        
        while len(result) < n:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            
            # Check if data available
            if hasattr(select, 'select'):
                rlist, _, _ = select.select([stdin_raw], [], [], min(remaining, 1.0))
                if not rlist:
                    continue
            
            # Read available data from binary stream
            chunk = stdin_raw.read(n - len(result))
            if isinstance(chunk, str):
                chunk = chunk.encode('latin-1')
            
            if chunk:
                result.extend(chunk)
            else:
                break
        
        return bytes(result) if result else None
    
    def write_bytes(data):
        """Write bytes to stdout (binary mode)"""
        stdout_raw.write(data)
        stdout_raw.flush()
    
    return YAPPProtocol(read_bytes, write_bytes, debug=debug)


def main():
    """Command-line interface for YAPP testing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YAPP file transfer protocol for packet radio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Send a file
    yapp.py --send myfile.txt
    
    # Receive a file
    yapp.py --receive --save-dir /tmp
    
    # Debug mode
    yapp.py --send myfile.txt --debug
"""
    )
    
    parser.add_argument('--send', '-s', metavar='FILE',
                        help='Send file via YAPP')
    parser.add_argument('--receive', '-r', action='store_true',
                        help='Receive file via YAPP')
    parser.add_argument('--save-dir', '-o', metavar='DIR',
                        help='Directory to save received files')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug output')
    parser.add_argument('--version', '-v', action='version',
                        version='YAPP Protocol 1.0')
    
    args = parser.parse_args()
    
    if not args.send and not args.receive:
        parser.print_help()
        return 1
    
    yapp = create_stdio_yapp(debug=args.debug)
    
    if args.send:
        # Read and send file
        try:
            with open(args.send, 'rb') as f:
                filedata = f.read()
            
            filename = os.path.basename(args.send)
            success, msg = yapp.send_file(filename, filedata)
            
            if success:
                sys.stderr.write("Success: {}\n".format(msg))
                return 0
            else:
                sys.stderr.write("Failed: {}\n".format(msg))
                return 1
                
        except IOError as e:
            sys.stderr.write("Error reading file: {}\n".format(e))
            return 1
    
    if args.receive:
        filename, data, error = yapp.receive_file(save_dir=args.save_dir)
        
        if error:
            sys.stderr.write("Failed: {}\n".format(error))
            return 1
        
        if args.save_dir:
            sys.stderr.write("Received: {} (saved)\n".format(filename))
        else:
            sys.stderr.write("Received: {} ({} bytes)\n".format(filename, len(data)))
            # Output file data to stdout
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout.buffer.write(data)
            else:
                sys.stdout.write(data.decode('latin-1'))
        
        return 0
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
