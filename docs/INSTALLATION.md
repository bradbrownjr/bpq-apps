# Installation Instructions

Applications or scripts on a Linux system are typically piped to stdout: the screen. In order to get the output redirected to the users connected to the BPQ node over AX.25 (radio) or telnet (IP), they need to be redirected to a tcp socket. This is done by making them into a service run with inetd.

![Installation Diagram](images/Screenshot-2022-09-26%20094854.png)

These steps assume that you have already installed the applications or downloaded the scripts which you wish to run on your node.

## Step 1: Install inetd

The Raspberry Pi Raspbian OS is using systemd to run its services, so we need to install the legacy inetd software:

```bash
sudo apt-get install openbsd-inetd
```

## Step 2: Configure inetd Services

Now we add the applications to the services list. These may be native Linux applications or scripts built with a language that is installed to the host: Python, Perl, Go, BASH, etc.

```bash
sudo nano /etc/inetd.conf
```

Example entry:
```
wx                      stream  tcp     nowait  ect     /home/ect/apps/wx.py
|                       |       |       |       |      |
|                       |       |       |       |      Full path to *executable*
|                       |       |       |       User to run executable as, your node may use 'pi'
|                       |       |       Run new, concurrent processes for new requests
|                       |       Socket type to use for stream
|                       inetd hooks the network stream directly to stdin and stdout of the executable 
Application/service name to be executed from node
```

See more examples in [examples/etc/](examples/etc/)

**Notes:**
* Applications should be run under the same user account whose /home directory contains linbpq.
* Exact paths to the app or script should be used. 
* In the case of my node, the username is 'ect' for emergency communications team; not to be confused with 'etc' the system configuration directory.
* More info can be found at https://en.wikipedia.org/wiki/Inetd

## Step 3: Assign TCP Ports

Next, we will assign the service application a tcp port. In the examples I've found, sysops are using ports in the 63,000 range. Take note of these port numbers, you will need them for the next step.

```bash
sudo nano /etc/services
```

## Step 4: Add Service Entries

Add entries for each application service to the services file:

```
wx              63010/tcp
hamqsl          63020/tcp
space           63030/tcp
```

See more examples in [examples/etc/services](examples/etc/services)

## Step 5: Start inetd

Now that the services are defined, start inetd:

```bash
sudo service inetd start
```

Or, if you are making edits to these files later, restart:

```bash
sudo service inetd restart
```

## Step 6: Test Service via Telnet

Test your application by telnetting into it:

```bash
telnet localhost 63010
```

If it executes as expected, it *should* work via AX.25.

## Step 7: Configure BPQ32

Finally, we add the commands to the BPQ node to call the external applications running as services. Again, my linbpq directory is under the 'ect' user, yours likely differs:

```bash
nano /home/ect/linbpq/bpq32.cfg
```

See example [examples/linbpq/bpq32.cfg](examples/linbpq/bpq32.cfg) configuration file for the more complete uncommented version. The full file, with passwords redacted, is available in that file's revision history.

### Configuration Details

Note your telnet port number:
```
PORT
 PORTNUM=9
 ID=Telnet Server
```

Note the CMDPORT numbers need to match the port numbers defined in /etc/services.
Each port number is referred to by linbpq by its position number in the list.
```
    CMDPORT 63000 63010 63020 63030
            ^ #0  ^ #1  ^ #2  ^ #3
```

Internal and external applications are called with the following commands:
```
    APPLICATION 6,SYSINFO,C 9 HOST 2 NOCALL K S
                  ^       ^    ^   ^ ^      ^ ^
                  |       |    |   | |      | |
                  |       |    |   | |      | Return to node upon exit (omit if giving app its own NODECALL-#)
	              |       |    |   | |      Keep-alive to prevent premature exit of application
	        	  |       |    |   | Do not pass call sign to app (omit if you want it via stdin)
                  |       |    |   CMDPORT position number (see above)
         		  |       |    Localhost
           		  |       Connect to Telnet PORT #
	           	  App name entered at user prompt
```

## Step 8: Restart LinBPQ

Restart your linbpq node.

**If you run it as a service:**

```bash
sudo systemctl restart linbpq
```

**If you run it detached, from the linbpq directory:**
```bash
ps -A | grep linbpq
kill -1 (process number of prior command's output)
nohup ./linbpq &
```

## Step 9: Test from Node

Test locally. This will be the node's telnet port defined by TCPPORT=8010 in bpq32.cfg:

```bash
telnet localhost 8010
```

Log into your node and run the new command. If it works, it *should* work over radio.

---

## Troubleshooting

### Timeout Issues

There seems to be some sort of timeout for which a command run by the BPQ node software waits before it terminates the process.

* If the application returns to the node prompt without output, try the command again
* If the application runs fine but output is truncated, you may need to add the 'K' to your bpq32.cfg APPLICATION line

### Scripts Not Executing Locally

* Ensure the script is executable:
  ```bash
  chmod +x script.py
  ```
* Ensure the interpreter is installed. These scripts require Python3 or a shell. The first lines of a script will indicate what interpreter and modules are needed.
  
  e.g.: `#!/bin/env sh` or `#!/bin/env python3`

### Scripts Run Locally But Not From Node

If scripts run locally and via their inetd telnet port, but won't produce output when accessed from the node, check for and remove the following lines from your TELNET port configuration:

* FALLBACKTORELAY=1
* RELAYAPPL=BBS
* RELAYHOST=127.0.0.1

---

## Offline Support: Cache Updates via Cron

Several BPQ applications support offline operation using cached data. To enable this feature, configure cron jobs to periodically update the cache files when internet is available.

### Why Cache Updates?

Packet radio nodes may have intermittent or unreliable internet connectivity. Cache updates allow apps to continue functioning with previously-fetched data when the network is unavailable.

### Cache-Enabled Apps

| App | Cache File | Recommended Interval | What's Cached |
|-----|-----------|---------------------|---------------|
| `wx.py` | `wx_cache.json` | 2 hours | Local weather, alerts, SKYWARN |
| `rss-news.py` | `rss_cache.json` | 2 hours | RSS feed articles |
| `hamqsl.py` | `hamqsl_cache.json` | 4 hours | HF propagation data |
| `space.py` | `space_cache.json` | 4 hours | Space weather reports |
| `eventcal.py` | `eventcal_cache.json` | 6 hours | Calendar events |
| `predict.py` | `solar_cache.json` | (auto) | Solar data (already cached) |

### Configure Cron Jobs

Edit the crontab for the user that runs BPQ (e.g., `ect` or `pi`):

```bash
crontab -e
```

Add the following entries (adjust paths for your system):

```cron
# BPQ App Cache Updates
# ----------------------
# wx.py - Local weather cache (every 2 hours)
0 */2 * * * /home/ect/apps/wx.py -c >/dev/null 2>&1

# rss-news.py - RSS feed cache (every 2 hours)
30 */2 * * * /home/ect/apps/rss-news.py -c >/dev/null 2>&1

# hamqsl.py - HF propagation cache (every 4 hours)
15 */4 * * * /home/ect/apps/hamqsl.py -c >/dev/null 2>&1

# space.py - Space weather cache (every 4 hours)
45 */4 * * * /home/ect/apps/space.py -c >/dev/null 2>&1

# eventcal.py - Calendar cache (every 6 hours)
0 */6 * * * /home/ect/apps/eventcal.py -c >/dev/null 2>&1
```

**Notes:**
- The `-c` or `--update-cache` flag runs the app in "cache update" mode
- Output is suppressed with `>/dev/null 2>&1` to avoid cron mail
- Stagger job times (0, 15, 30, 45 minutes) to avoid simultaneous network requests
- Adjust paths to match your installation (`/home/pi/apps/` vs `/home/ect/apps/`)

### Verify Cache Files

After cron jobs have run, verify cache files exist:

```bash
ls -la ~/apps/*.json
```

You should see recently-modified cache files:
```
-rw-r--r-- 1 ect ect 2048 Jan 15 10:00 eventcal_cache.json
-rw-r--r-- 1 ect ect 1024 Jan 15 10:15 hamqsl_cache.json
-rw-r--r-- 1 ect ect 8192 Jan 15 10:00 rss_cache.json
-rw-r--r-- 1 ect ect 4096 Jan 15 10:45 space_cache.json
-rw-r--r-- 1 ect ect 3072 Jan 15 10:00 wx_cache.json
```

### Test Offline Mode

To test offline operation:

1. Run an app normally (should show live data)
2. Temporarily block internet:
   ```bash
   sudo iptables -I OUTPUT -d 8.8.8.8 -j DROP
   ```
3. Run the app again (should show cached data with timestamp)
4. Restore internet:
   ```bash
   sudo iptables -D OUTPUT -d 8.8.8.8 -j DROP
   ```

### Cache Freshness Indicators

When using cached data, apps display:
- **Cache timestamp**: When the data was last fetched
- **Warning** (if >24 hours old): Data may be inaccurate

Example output when offline:
```
** OFFLINE: Using cached data **
Cached: 01/15/2026 at 10:00 EST
WARNING: Data over 24 hours old may be
         inaccurate.
```

---

## References

* [LinBPQ Applications Interface Documentation](https://www.cantab.net/users/john.wiseman/Documents/LinBPQ%20Applications%20Interface.html)
* [inetd - Wikipedia](https://en.wikipedia.org/wiki/Inetd)

---

## Utilities Installation

Utilities are sysop tools that typically run from command line or cron jobs, not as BPQ APPLICATION commands.

### Recommended Layout

Place scripts in `~/utilities/` or `~/apps/` adjacent to `~/linbpq/`:

```
/home/pi/               (or /home/ect/)
├── apps/               # User-facing BPQ applications
├── utilities/          # Sysop tools (nodemap.py, etc.)
├── linbpq/
│   └── bpq32.cfg       # Auto-detected by scripts
└── ...
```

### Setup

**Option 1: Download individual utilities (Recommended)**
```bash
# Create utilities directory
mkdir -p ~/utilities
cd ~/utilities

# Download specific utility (example: nodemap.py)
wget https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/nodemap.py
chmod +x nodemap.py

# Test help
./nodemap.py --help
```

**Option 2: Update existing utility**
```bash
cd ~/utilities

# Update to latest version
wget -O nodemap.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/utilities/nodemap.py
chmod +x nodemap.py
```

**Option 3: Clone entire repository (requires git)**
```bash
# Install git if needed
sudo apt-get install git

# Create utilities directory
mkdir -p ~/utilities
cd ~/utilities

# Clone repo
git clone https://github.com/bradbrownjr/bpq-apps.git
cd bpq-apps/utilities

# Make scripts executable
chmod +x *.py
```

### Configuration Detection

Utilities auto-detect `bpq32.cfg` from:
1. `../linbpq/bpq32.cfg` (script in utilities/ or apps/, config in linbpq/)
2. `/home/pi/linbpq/bpq32.cfg`
3. `/home/ect/linbpq/bpq32.cfg`
4. Same directory as script
5. `linbpq/bpq32.cfg` (script in parent)

See [utilities/README.md](../utilities/README.md) for individual utility documentation.
