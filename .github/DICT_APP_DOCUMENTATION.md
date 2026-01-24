# Dictionary App (dict.py) - Complete Documentation

## Overview

The dictionary app (`dict.py`) is a BPQ32 packet radio application that provides dictionary word lookup functionality using the Linux `dict` command-line tool (dictd client). It's optimized for low-bandwidth operation on 1200 baud AX.25 packet radio networks.

## What It Is

A simple, interactive dictionary lookup utility for ham radio operators using packet radio. Users can:
- Enter any word at a prompt
- Get definitions from online/local dictionary servers via dictd
- Navigate through paginated results (20 lines per page)
- Quit with 'Q' or continue with Enter

## How It Works

```
User connects to BPQ DICT command
           ↓
inetd routes to port 63160 (dictionary service)
           ↓
dict.py starts, displays ASCII logo and prompt
           ↓
User enters word (e.g., "aircraft")
           ↓
dict.py calls: subprocess.Popen(['dict', 'aircraft'])
           ↓
dictd returns definitions from configured databases
           ↓
dict.py formats output with word wrapping at 80 chars
           ↓
Results paginated every 20 lines with "(press Enter, Q to quit)" prompt
           ↓
User navigates or quits
```

## Prerequisites

**System Requirements:**
- Linux `dict` package (dictd client) installed on the BPQ node
- Python 3.5.3+ (tested on Raspbian 9)
- Network connectivity to dictd server (typically online via internet)
- inetd or equivalent TCP socket service manager

**Installation:**
```bash
# On Raspbian/Debian systems
sudo apt-get install dictd dict

# Verify dict command works
dict aircraft
```

**Optional:** For offline operation, configure a local dictd database server (advanced setup).

## Critical Naming Constraint

### ⚠️ IMPORTANT: Service Name Collision Issue

**Problem:** The Linux `dict` package registers port 2628 in `/etc/services` with the name "dict".

**Issue:** If you name the BPQ app service "dict" in `/etc/services`, the system creates ambiguity:
- Port 2628: Standard dictd server (installed by `dict` package)
- Port 63160: Custom BPQ app

When inetd tries to resolve the service name, it may find the wrong port or fail.

**Solution:** Use a different service name in system configuration files. "dictionary" is recommended:

```
# DON'T DO THIS:
dict            63160/tcp

# DO THIS INSTEAD:
dictionary      63160/tcp
```

### Configuration Points

1. **Script filename**: Can be anything (`dict.py`, `dictionary.py`, etc.)
   - ✅ `/home/ect/apps/dict.py`

2. **BPQ APPLICATION name**: Can be "DICT"
   - ✅ `APPLICATION 6,DICT,C 9 HOST 15 NOCALL K`

3. **System service name**: Must NOT be "dict"
   - ❌ `dict            63160/tcp`
   - ✅ `dictionary      63160/tcp`

4. **inetd.conf service name**: Must match `/etc/services`
   - ✅ `dictionary      stream  tcp  nowait  ect  /home/ect/apps/dict.py`

## Configuration Files

### `/etc/services` Entry

Add this line to the "Local services" section:
```
dictionary      63160/tcp               # Dictionary lookup (HOST 15)
```

### `/etc/inetd.conf` Entry

Add this line in the "HAM-RADIO" section:
```
dictionary      stream  tcp     nowait  ect     /home/ect/apps/dict.py
```

After editing, restart inetd:
```bash
sudo killall -HUP inetd
```

### `bpq32.cfg` Configuration

**1. Add port to CMDPORT list:**
```
CMDPORT 63000 63010 63020 63030 63040 63050 63060 63070 63080 63090 63100 63110 63120 63130 63140 63160
                                                                                                      ↑
                                                                                         Position 15 (HOST 15)
```

**2. Add APPLICATION line:**
```
APPLICATION 6,DICT,C 9 HOST 15 NOCALL K
```

Where:
- `6` = Application number (unique)
- `DICT` = BPQ command name (visible in menu)
- `C 9` = Connect via port 9 (telnet)
- `HOST 15` = CMDPORT position 15 (maps to port 63160)
- `NOCALL` = No authentication required
- `K` = Keep session alive (inetd socket)

## Installation Steps

### On WS1EC Node

1. **Add to `/etc/services`:**
```bash
echo 'dictionary      63160/tcp               # Dictionary lookup' | sudo tee -a /etc/services
```

2. **Add to `/etc/inetd.conf`:**
```bash
echo 'dictionary      stream  tcp     nowait  ect     /home/ect/apps/dict.py' | sudo tee -a /etc/inetd.conf
```

3. **Restart inetd:**
```bash
sudo killall -HUP inetd
```

4. **Update `bpq32.cfg`:**
   - Edit `/home/ect/linbpq/bpq32.cfg`
   - Add/update CMDPORT line (see above)
   - Add APPLICATION line (see above)

5. **Restart BPQ32:**
```bash
sudo systemctl restart linbpq
```

6. **Test connectivity:**
```bash
telnet localhost 63160
# Should show ASCII logo and "Enter word (Q to quit):" prompt
```

## Technical Details

### Version Information
- **Current Version:** 1.6
- **Compatible Python:** 3.5.3+
- **Target System:** RPi 3B, Raspbian 9
- **Baud Rate:** 1200 (AX.25 packet radio)

### Auto-Update Mechanism
- Checks GitHub for newer version on startup (3-second timeout)
- If update available, downloads to temp file atomically
- Renames temp file to replace current version
- Preserves executable permissions
- Cleans up temp files on failure

### Terminal Handling
- Detects terminal width dynamically
- Fallback: 80 characters (inetd default)
- Wraps long definitions at terminal width
- Paginates output every 20 lines
- User can press Enter to continue or 'Q' to quit

### Output Format
```
 ___  _   _  ___  _      
|  _ \| | | |/ _ \| |     
| | | | |_| | (_) | |     
|_| |_|\___/ \___/|_|     

DICT v1.6 - Dictionary Lookup

Enter word (Q to quit): aircraft
aircraft
    n (noun)
       1: a plane powered by an engine or engines and able to fly
       2: a vehicle designed for travel through air or space
       3: military aircraft; warplanes collectively

(press Enter, Q to quit): 
```

### Subprocess Handling
Uses `subprocess.Popen()` for Python 3.5.3 compatibility (no timeout parameter available). Properly handles:
- Missing `dict` command (graceful error message)
- Network unavailability (dictd server unreachable)
- Malformed queries (dictd returns error message)

### Stdout Buffering
- Adds `sys.stdout.flush()` after all output to inetd
- Necessary because inetd uses full buffering for TCP sockets (not TTY)
- Without flush, output doesn't appear until app exits

## Usage Examples

### User Experience
```
[User connects via: telnet ws1ec.mainepacketradio.org from BBS]

WS1EC de WS1EC-15>
Enter I for node info and menu
Enter ? for commands

de WS1EC-15>DICT

 ___  _   _  ___  _      
|  _ \| | | |/ _ \| |     
| | | | |_| | (_) | |     
|_| |_|\___/ \___/|_|     

DICT v1.6 - Dictionary Lookup

Enter word (Q to quit): qrz

QRZ
    Proper noun
    n (noun)
       1: callsign lookup database; www.qrz.com

(press Enter, Q to quit): Q

WS1EC de WS1EC-15>
```

## Troubleshooting

### Symptoms & Solutions

**"Dict lookup failed" error:**
- Cause: dictd server unreachable or no network
- Solution: Check network connectivity, restart dictd service

**"dict: command not found" error:**
- Cause: `dict` package not installed
- Solution: `sudo apt-get install dict`

**App doesn't display in BPQ menu:**
- Cause: CMDPORT not updated or APPLICATION line incorrect
- Solution: Check bpq32.cfg syntax, restart BPQ32

**Telnet connects but no prompt appears:**
- Cause: stdout buffering issue or inetd permission problem
- Solution: Check inetd.conf user matches ect, restart inetd

**Service name conflicts:**
- Cause: Trying to name service "dict" instead of "dictionary"
- Solution: Rename to "dictionary" in `/etc/services` and `/etc/inetd.conf`

## Performance Characteristics

- **Startup Time:** ~0.5 seconds (includes auto-update check)
- **First Lookup:** ~1-2 seconds (network latency)
- **Subsequent Lookups:** ~0.5-1 second
- **Bandwidth Usage:** Depends on definition length (typically 1-5 KB per lookup)
- **Memory Footprint:** ~5-10 MB (Python interpreter)

## Future Enhancements

Potential improvements (not yet implemented):
- Local dictionary caching for offline operation
- Multiple dictionary database selection (currently uses default)
- Definition count indicator
- Search history navigation
- ANSI color highlighting (if terminal supports)

## Related Documentation

- [dict.py Source Code](../apps/dict.py)
- [BPQ32 Configuration Guide](../INSTALLATION.md)
- [Service Name Resolution & Port Mapping](./BPQ_INTEGRATION_GUIDE.md)
- [Auto-Update Protocol](../INSTALLATION.md#Auto-Update-Mechanism)

## References

- Linux `dict` command: `man dict`
- dictd protocol: RFC 2229
- inetd.conf format: `man 5 inetd.conf`
- BPQ32 docs: www.cantab.net/users/john.wiseman/Documents/

## Contact & Support

For issues or questions:
- GitHub Issues: https://github.com/bradbrownjr/bpq-apps/issues
- Author: Brad Brown, KC1JMH
- WS1EC Node: ws1ec.mainepacketradio.org

---
*Last Updated: January 24, 2026*
*Configuration Reference: WS1EC-15 (Windham, ME)*
