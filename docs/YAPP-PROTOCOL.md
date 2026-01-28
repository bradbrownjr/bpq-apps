# YAPP Protocol Technical Documentation

## Overview

**YAPP** (Yet Another Packet Protocol) is a file transfer protocol designed for amateur packet radio BBS systems. It was created by **Jeff Jacobsen, WA7MBL** (author of the original W0RLI/WA7MBL BBS software) as a simple, reliable method to transfer binary files over AX.25 packet radio links.

## Protocol Specification

### Control Characters

YAPP uses standard ASCII control characters for protocol framing:

| Character | Hex Value | Name | Description |
|-----------|-----------|------|-------------|
| SOH | 0x01 | Start of Header | Initiates file header transmission |
| STX | 0x02 | Start of Text | Indicates start of data block |
| ETX | 0x03 | End of Text | Marks end of data block |
| EOT | 0x04 | End of Transmission | Signals end of file transfer |
| ENQ | 0x05 | Enquiry | Initiates YAPP session (sent by sender) |
| ACK | 0x06 | Acknowledgment | Positive response |
| DLE | 0x10 | Data Link Escape | Escape character for binary transparency |
| NAK | 0x15 | Negative Acknowledgment | Error/rejection response |
| CAN | 0x18 | Cancel | Abort transfer |

### Frame Format

YAPP frames follow a simple structure:

```
+--------+--------+------------------+
| Control| Length | Data (optional)  |
| (1 byte)| (1 byte)|  (0-255 bytes)  |
+--------+--------+------------------+
```

#### Frame Types

**1. Session Initiation (ENQ)**
```
+-----+------+
| ENQ | 0x01 |
+-----+------+
  05    01
```
- Sent by the file sender to initiate a YAPP transfer
- The 0x01 byte indicates YAPP protocol version 1

**2. Session Accept (ACK)**
```
+-----+------+
| ACK | 0x01 |
+-----+------+
  06    01
```
- Sent by receiver to accept the YAPP session

**3. Session Reject (NAK)**
```
+-----+--------+-------------------+
| NAK | Length | Error Message     |
+-----+--------+-------------------+
  15    nn       ASCII text
```
- Sent by receiver to reject YAPP (e.g., "Node doesn't support YAPP Transfers")

**4. File Header (SOH)**
```
+-----+--------+----------+---------+---------+
| SOH | Length | Filename | 0x00    | Filesize|
+-----+--------+----------+---------+---------+
  01    nn       ASCII      null     ASCII digits
```
- Length: Total length of filename + null + filesize string
- Filename: ASCII filename (no path)
- Filesize: File size in bytes as ASCII decimal string

**5. Header Acknowledgment**
```
+-----+------+
| ACK | 0x01 |  (Accept file)
+-----+------+

+-----+------+
| ACK | 0x02 |  (Resume - if supported)
+-----+------+

+-----+--------+-------------------+
| NAK | Length | Reason            |
+-----+--------+-------------------+
```

**6. Data Block (STX)**
```
+-----+--------+------------------+
| STX | Length | Binary Data      |
+-----+--------+------------------+
  02    nn       (nn bytes of data)
```
- Length byte: 0x00 = 256 bytes, 0x01-0xFF = 1-255 bytes
- Maximum data per block: 256 bytes

**7. End of File (ETX)**
```
+-----+------+
| ETX | 0x01 |
+-----+------+
  03    01
```
- Indicates all file data has been sent

**8. End of Transmission (EOT)**
```
+-----+------+
| EOT | 0x01 |
+-----+------+
  04    01
```
- Closes the YAPP session

**9. Cancel Transfer (CAN)**
```
+-----+------+
| CAN | 0x01 |
+-----+------+
  18    01
```
- Either side can send to abort the transfer

### Handshaking Sequence

#### Normal File Transfer

```
Sender                          Receiver
  |                                |
  |--- ENQ 0x01 ------------------>|  Session initiation
  |                                |
  |<-- ACK 0x01 -------------------|  Session accepted
  |                                |
  |--- SOH len filename 0 size --->|  File header
  |                                |
  |<-- ACK 0x01 -------------------|  Ready to receive
  |                                |
  |--- STX len [data] ------------>|  Data block 1
  |--- STX len [data] ------------>|  Data block 2
  |    ...                         |  (streaming - no per-block ACK)
  |--- STX len [data] ------------>|  Data block n
  |                                |
  |--- ETX 0x01 ------------------>|  End of file
  |                                |
  |<-- ACK 0x01 -------------------|  File received OK
  |                                |
  |--- EOT 0x01 ------------------>|  End session
  |                                |
```

#### Rejected Transfer

```
Sender                          Receiver
  |                                |
  |--- ENQ 0x01 ------------------>|  Session initiation
  |                                |
  |<-- NAK len "error msg" --------|  Rejected
  |                                |
```

#### Cancelled Transfer

```
Sender                          Receiver
  |                                |
  |--- ENQ 0x01 ------------------>|
  |<-- ACK 0x01 -------------------|
  |--- SOH len filename 0 size --->|
  |<-- ACK 0x01 -------------------|
  |--- STX len [data] ------------>|
  |    ...                         |
  |                                |
  |<-- CAN 0x01 -------------------|  Receiver cancels
  |         or                     |
  |--- CAN 0x01 ------------------>|  Sender cancels
  |                                |
```

### State Machine

```
                    +-------------+
                    |    IDLE     |
                    +-------------+
                          |
                    ENQ received/sent
                          v
                    +-------------+
                    |  INIT_WAIT  |
                    +-------------+
                          |
                    ACK received
                          v
                    +-------------+
                    | HEADER_WAIT |
                    +-------------+
                          |
                    SOH received, ACK sent
                          v
                    +-------------+
                    |   RECEIVE   |<--+
                    +-------------+   |
                          |           |
                    STX received------+
                          |
                    ETX received
                          v
                    +-------------+
                    |   FINISH    |
                    +-------------+
                          |
                    EOT sent/received
                          v
                    +-------------+
                    |    IDLE     |
                    +-------------+
```

### Error Handling

1. **Timeout**: If no response within timeout period (typically 30-60 seconds), abort transfer
2. **NAK Response**: Abort and report error message to user
3. **CAN Received**: Immediately terminate transfer, cleanup partial file
4. **Invalid Control**: Send NAK with error message, abort session
5. **Length Mismatch**: If received bytes don't match declared filesize, report error after ETX

### Flow Control

YAPP relies on the underlying AX.25 link layer for flow control:

- **No per-block acknowledgment** during data transfer (streaming)
- AX.25 RNR (Receive Not Ready) provides backpressure
- Sender transmits blocks continuously until ETX
- Receiver only ACKs at session start, header, and end-of-file

This design minimizes round-trip delays over high-latency packet radio links.

### Binary Transparency

YAPP achieves binary transparency through the length-prefixed frame format:

- The length byte explicitly declares how many data bytes follow
- No escape sequences needed within data blocks
- All 256 byte values (0x00-0xFF) can be transmitted in data

### Comparison with Other Protocols

| Feature | YAPP | XMODEM | B2 (Winlink) | FBB Compressed |
|---------|------|--------|--------------|----------------|
| Block size | 1-256 | 128/1024 | Variable | Variable |
| Per-block ACK | No | Yes | No | No |
| Resume support | Limited | No | Yes | No |
| Compression | No | No | Yes | Yes (LZH) |
| CRC/Checksum | No (uses AX.25) | Yes | Yes | Yes |
| Header info | Filename, size | None | Full metadata | Full metadata |
| Typical use | BBS file transfer | Serial/modem | Winlink email | BBS forwarding |

**Advantages of YAPP:**
- Simple implementation (minimal code)
- Low overhead (no per-block ACK)
- Relies on AX.25 error correction
- Fast on reliable links

**Disadvantages:**
- No built-in error detection (trusts AX.25)
- Limited metadata (just filename and size)
- No compression
- No partial file resume in basic version

## Implementation Notes

### BPQ32 Implementation

From the BPQ32 source code (bpqmail.h, Cmd.c):

```c
// Control character definitions
#define SOH 1
#define STX 2
#define ETX 3
#define EOT 4
#define ENQ 5
#define ACK 6
#define DLE 0x10
#define NAK 0x15
#define CAN 0x18

// Session flag
#define YAPPTX 0x008000  // Sending YAPP file
```

Detection of YAPP initiation:
```c
// Check for YAPP session start (ENQ 0x01)
if (len == 2 && ptr1[0] == 5 && ptr1[1] == 1)
{
    // YAPP transfer request detected
    ptr1[0] = 0x15;  // NAK
    ptr1[1] = sprintf(&ptr1[2], "Node doesn't support YAPP Transfers");
    // ... send response
}
```

### Typical Implementation Flow

**Sender side:**
1. Send ENQ 0x01
2. Wait for ACK 0x01 (or NAK with error)
3. Build and send SOH header with filename and size
4. Wait for ACK 0x01
5. Loop: Send STX blocks until file complete
6. Send ETX 0x01
7. Wait for ACK 0x01
8. Send EOT 0x01

**Receiver side:**
1. Receive ENQ 0x01, send ACK 0x01
2. Receive SOH header, parse filename/size, send ACK 0x01
3. Loop: Receive STX blocks, write to file
4. Receive ETX 0x01, verify file size, send ACK 0x01
5. Receive EOT 0x01, close file

## Historical Context

YAPP was developed in the late 1980s when packet radio BBS systems needed a reliable way to transfer binary files. At that time:

- **XMODEM** required per-block acknowledgments, causing significant delays on half-duplex packet links
- **ASCII transfers** couldn't handle binary files without encoding (uuencode/Base64)
- **Kermit** was too complex for small BBS systems

Jeff Jacobsen (WA7MBL) designed YAPP to be:
- Simple enough for 8-bit microcontrollers
- Efficient over high-latency links (streaming, no per-block ACK)
- Binary-transparent (length-prefixed frames)
- Interoperable with AX.25 error handling

The protocol became widely adopted in WA7MBL-derived BBS software and was later implemented in BPQ32 and other packet radio systems.

## References

- BPQ32 Source Code: https://github.com/g8bpq/BPQ32
- LinBPQ Source Code: https://github.com/g8bpq/linbpq
- WA7MBL BBS Documentation (historical)
- AX.25 Link Access Protocol: ARRL publications

## Version History

| Version | Features |
|---------|----------|
| YAPP (original) | Basic file transfer |
| YAPP-C | Added CRC checking (some implementations) |
| YAPP-R | Added resume capability (some implementations) |

---

## Application Ideas for bpq-apps

### Custom FILES Repository

BPQ32's built-in FILES command uses a flat directory structure. A custom FILES app could provide:

- **Hierarchical directories**: Navigate folders like a filesystem
- **File metadata**: Description, upload date, download count
- **Search**: Find files by name or description
- **Categories**: Software, documentation, forms, images
- **Access control**: Public vs. registered users

**Implementation approach:**
```
files.py - BPQ APPLICATION for file browsing/download
files/
    index.json - File catalog with metadata
    software/
    docs/
    forms/
```

### Gopher File Downloads

The existing gopher.py could be extended to support file downloads:

1. User browses Gopher menu, finds binary file (type 9)
2. User selects "Download" option
3. App switches to YAPP sender mode
4. File streamed to user's terminal
5. User's YAPP-capable terminal (Winpack, etc.) saves file

**Challenge:** Terminal must support YAPP. Need to detect capability.

### FTP Browser

An FTP client app that bridges FTP servers to packet radio users:

1. User connects to FTP app via BPQ
2. App connects to configured FTP server(s) via internet
3. User browses directories with text menu
4. Download triggers: App fetches file, sends via YAPP

**Considerations:**
- Pre-configured FTP servers (no arbitrary connections)
- File size limits (packet radio is slow)
- Caching frequently accessed files
- Internet connectivity detection

---

## YAPP Over BPQ32 stdio - Technical Limitations

### The Core Problem

BPQ32 APPLICATIONs invoked via `C 9 HOST #` connect to inetd, which pipes stdin/stdout to TCP sockets. This pipeline includes **terminal emulation layers that filter ASCII control characters < 0x20**, breaking YAPP protocol frames.

**Evidence from BPQ32 source code** (Cmd.c:4972-5007):
```c
// Check for sending YAPP to Node
if (len == 2 && ptr1[0] == 5 && ptr1[1] == 1)
{
    ptr1[0] = 0x15;  // NAK
    ptr1[1] = sprintf(&ptr1[2], "Node doesn't support YAPP Transfers");
    // ... send response
}
```

BPQ32 explicitly rejects YAPP at the node command level. Even if this check were bypassed, the stdio pipeline strips control bytes:

- **SOH (0x01)**, **STX (0x02)**, **ETX (0x03)** - frame delimiters
- **EOT (0x04)**, **ENQ (0x05)**, **ACK (0x06)** - handshaking
- **DLE (0x10)**, **NAK (0x15)**, **CAN (0x18)** - control flow
- **Length bytes 0x00-0x1F** - critical for frame parsing

### Why Control Bytes Are Stripped

From LinBPQ source analysis (TelnetV6.c, telnetserver.h):

1. **Telnet protocol handling**: IAC (0xFF), control character negotiation
2. **Terminal emulation**: VT100/ANSI escape sequence processing
3. **Flow control**: XON/XOFF (0x11/0x13) for serial compatibility
4. **Line discipline**: CR/LF normalization, backspace handling

The stdio pipeline was designed for **text-mode terminal emulation**, not raw binary transfer protocols.

### Alternative Approaches Research

#### 1. Dedicated TCP Socket Server (RECOMMENDED)

**Concept**: Run YAPP as a standalone TCP server, bypassing stdio entirely.

**Implementation**:
```python
# yapp_server.py - standalone daemon
import socket
import threading
from yapp import YAPPProtocol

def handle_yapp_session(conn, addr):
    yapp = YAPPProtocol(conn)  # Direct socket I/O
    yapp.receive_file()  # No stdio filtering

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 63020))  # Dedicated YAPP port
server.listen(5)

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_yapp_session, args=(conn, addr)).start()
```

**BPQ32 Configuration**:
```
; /etc/services
yapp-files    63020/tcp    # YAPP File Transfer Server

; /etc/inetd.conf  
yapp-files stream tcp nowait ect /usr/bin/python3 python3 /home/ect/apps/yapp_server.py

; bpq32.cfg
APPLICATION 7,YAPP,C 9 HOST 7 NOCALL S K,NOCALL,SK
```

**Advantages**:
- No stdio filtering - raw binary I/O via socket
- Full YAPP protocol compatibility
- Multi-user support with threading
- Can implement YAPPC (resume) easily

**Disadvantages**:
- Requires additional port configuration
- User must explicitly connect to YAPP port (not transparent)
- Cannot integrate seamlessly into existing apps (e.g., gopher.py)

#### 2. ASCII-Safe Encoding Wrapper

**Concept**: Encode YAPP frames to avoid control characters < 0x20.

**Base64 Approach**:
```python
import base64

def send_yapp_frame_safe(sock, control, data):
    # Build YAPP frame
    frame = bytes([control, len(data)]) + data
    
    # Encode to ASCII-safe Base64
    encoded = base64.b64encode(frame)
    
    # Wrap in printable delimiters
    sock.send(b"<YAPP>" + encoded + b"</YAPP>\r\n")
```

**Advantages**:
- Works over stdio without modification
- Can be integrated into existing APPLICATIONs
- No additional ports required

**Disadvantages**:
- **Not YAPP-compatible** - breaks protocol standard
- 33% size overhead (Base64 encoding)
- Requires both ends to implement custom encoding
- Defeats the purpose of using YAPP (existing terminal software won't work)

#### 3. BPQ32 DLL Integration (Windows Only)

**Concept**: Use BPQ32's DLL interface to bypass stdio and write directly to AX.25 frames.

**Research from BPQ32 documentation**:
- `BPQDLLInterface.h` provides `SendRaw()` function
- Direct access to L2 (AX.25) layer
- No terminal emulation filtering

**Advantages**:
- True binary transparency
- Full YAPP compatibility
- Can implement within BPQ32 as native feature

**Disadvantages**:
- **Windows-only** (DLL not available on Linux/Raspberry Pi)
- Requires C/C++ development (not Python)
- Tight coupling to BPQ32 internals
- Not portable to LinBPQ installations

#### 4. Custom Telnet Binary Mode

**Concept**: Negotiate Telnet BINARY mode (RFC856) to disable control character processing.

**Telnet Option Negotiation**:
```python
# IAC WILL BINARY (0xFF 0xFB 0x00)
# IAC DO BINARY (0xFF 0xFD 0x00)
sock.send(b"\xFF\xFB\x00")  # Request binary send
sock.send(b"\xFF\xFD\x00")  # Request binary receive
```

**Research findings** (TelnetV6.c:5424-5453):
```c
BOOL ProcessTelnetCommand(struct ConnectionInfo * sockptr, byte * Msg, int * Len)
{
    // Telnet IAC processing
    if (cmd == DOx || cmd == DONT || cmd == WILL || cmd == WONT)
    {
        // Option negotiation
    }
}
```

**Advantages**:
- Standard Telnet protocol extension
- Should disable control character filtering
- No code changes to BPQ32 needed

**Disadvantages**:
- **Requires terminal/client support** for binary mode
- May not work with all BPQ32 versions (depends on telnet implementation)
- Still goes through terminal emulation layer (may not fully disable filtering)
- Untested - no evidence this works in practice

### Conclusion

**YAPP over stdio is fundamentally broken** in BPQ32/inetd architecture. The recommended approach is:

1. **Short-term**: Disable YAPP in gopher.py (already done in v1.17)
2. **Long-term**: Implement dedicated YAPP socket server (yapp_server.py) as standalone daemon
3. **Future**: Investigate Telnet binary mode as potential transparent solution

### Implementation Notes

Since BPQ32 node rejects YAPP at the command level, all YAPP transfers
must occur within applications that:

1. Run as BPQ APPLICATIONs connected to HOST port (if using stdio)
2. **OR** run as standalone TCP servers (recommended for YAPP)
3. Handle raw binary I/O via sockets (not stdio)
4. Implement full YAPP state machine

The apps/yapp.py module provides the protocol implementation, but is currently
marked as **EXPERIMENTAL** due to stdio limitations. See yapp.py header for details.

---

*Document compiled from BPQ32/LinBPQ source code analysis and packet radio protocol documentation.*
*Last updated: 2026-01-28*
*Research contributors: BPQ32 source code (Cmd.c, TelnetV6.c, telnetserver.h), RFC856 (Telnet Binary Transmission)*
