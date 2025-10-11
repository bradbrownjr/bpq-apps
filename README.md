# bpq-apps
Custom applications for a BPQ32 packet radio node

Here are some custom applications I am working on for my
local packet radio node, which runs on a Raspberry Pi B+
running John Wiseman's linbpq32 downloadable from:
https://www.cantab.net/users/john.wiseman/Documents/Downloads.html

APPLICATIONS
============
These applications are custom-built for low bandwidth terminal access over packet radio:

* **gopher.py** - Gopher protocol client for accessing gopherspace with text-based navigation. It's like the Internet, but for terminals!  
* **hamqsl.py** - HF propagation reports from www.hamqsl.com.  
* **hamtest.py** - Ham radio license test practice with automatic question pool updates.  
* **qrz3.py** - Look up name, city, state, country of an amateur radio operator with QRZ.com.  
* **rss-news.py** - News feed reader with categorized feeds: News, Science, Technology, Weather, and of course, ham radio topics.  
* **space.py** - NOAA Space Weather reports and solar activity data.  
* **sysinfo.sh** - Node system information and BBS service status checker.  
* **wx-me.py** - Local weather reports for Southern Maine and New Hampshire.  

For detailed documentation, installation commands, and configuration instructions, see [apps/README.md](apps/README.md).

DIRECTORIES
===========
**/apps** contains Applications written for Python 3.5+ and BASH.

**/etc** contains excerpts of the Linux service files required for the running of these applications with linbpq. Content may be added to the end of the respective file on your own  node host.

**/linbpq** contains excerpts of the bpq32.cfg node configuration file required for the execution of external applications by the user.

INSTALLATION INSTRUCTIONS
============
Applications or scripts on a Linux system are typically piped to stdout: the screen. In order to get the output redirected to the users connected to the BPQ node over AX.25 (radio) or telnet (IP), they need to be redirected to a tcp socket. This is done by making them into a service run with inetd.

![](Screenshot-2022-09-26%20094854.png)

These steps assume that you have already installed the applications or downloaded the scripts which you wish to run on your node.

Step 1
------
The Raspberry Pi Raspian OS is using systemd to run its services, so we need to install the legacy inetd software:

```sudo apt-get install openbsd-inetd```

Step 2
------
Now we add the applications to the services list. These may be native Linux applications or scripts built with a language that is installed to the host: Python, Perl, Go, BASH, etc.

```sudo nano /etc/inetd.conf```

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

See more examples in /etc/

Note: 
* Applications should be run under the same user account whose /home directory contains linbpq.
* Exact paths to the app or script should be used. 
* In the case of my node, the username is 'ect' for emergency communications team; not to be confused with 'etc' the system configuration directory.
* More info can be found at https://en.wikipedia.org/wiki/Inetd

Step 3
------
Next, we will assign the service application a tcp port. In the examples I've found, sysops are using ports in the 63,000 range. Take note of these port numbers, you will need them for the next step.

```sudo nano /etc/services```

Step 5
------
Now that the services are defined, start inetd:

```sudo service inetd start```

Or, if you are making edits to these files later, restart:

```sudo service inetd restart```

Step 7
------
Test your application by telnetting into it:

```telnet localhost 63010```

If it executes as expected, it *should* work via AX.25.

Step 8
------
Finally, we add the commands to the BPQ node to call the external applications running as services. Again, my linbpq directory is under the 'ect' user, yours likely differs:

```nano /home/ect/linbpq/bpq32.cfg```

See my example linbpq/bpq32.cfg configuration file for the more complete uncommented version. The full file, with passwords redacted, is available in that file's revision history.

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

Step 9
------
Restart your linbpq node.
1) If you run it as a service:

```sudo systemctl restart linbpq```

2) If you run it detached, from the linbpq directory:
```
ps -A | grep linbpq
kill -1 (process number of prior command's output)
nohup ./linbpq &
```

Step 10
-------
Test locally. This will be the node's telnet port defined by TCPPORT=8010 in bpq32.cfg:

```telnet localhost 8010```

Log into your node and run the new command. If it works, it *should* work over radio.

Caveats
=======
There seems to be some sort of timeout for which a command run by the BPQ node software waits before it terminates the process. 
* If the application returns to the node prompt without output, try the command again
* If the application runs fine but output is truncated, you may need to add the 'K' to your bpq32.cfg APPLICATION line

If scripts are not executing locally
* Ensure the script is executable  
```chmod +x script.py```
* Ensure the interpreter is installed. These scripts require Python3 or a shell. The first lines of a script will indicate what interpreter and modules are needed.
e.g.: ```#!/bin/env sh``` or ```#!/bin/env python3```

Scripts run locally, and via their inetd telnet port, but won't produce output when accessed from the node, check for and remove the following lines from your TELNET port configuration:
* FALLBACKTORELAY=1
* RELAYAPPL=BBS
* RELAYHOST=127.0.0.1

References
==========
https://www.cantab.net/users/john.wiseman/Documents/LinBPQ%20Applications%20Interface.html
