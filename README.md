# bpq-apps
Custom applications for a BPQ32 packet radio node

Here are some custom applications I am working on for my
local packet radio node, which runs on a Raspberry Pi B+
running John Wiseman's linbpq32 downloadable from:
https://www.cantab.net/users/john.wiseman/Documents/Downloads.html

DIRECTORIES
===========
**/apps** contains Applications either written for Python 3,
where the input() command works as expected, and BASH.

**/etc** contains the Linux service files required for the
running of these applications with linbpq. Content may
be added to the end of the respective file on your own 
node host.

**/linbpq** contains excerpts of the bpq32.cfg node required
for the execution of external applications by the user.

INSTRUCTIONS
============
Applications or scripts on a Linux system are typically
piped to stdout: the screen. In order to get the output
redirected to the users connected to the BPQ node over
AX.25 (radio) or telnet (IP), they need to be redirected
to a tcp socket. This is done by making them into a 
service run by inetd.

These steps assume that you have already installed the
applications or downloaded the scripts which you wish
to run on your node.

Step 1
------
The Raspberry Pi Raspian OS is using systemd to run its
services, so we need to install the legacy inetd software:

```sudo apt-get install inetd```

Step 2
------
Now we add the applications to the services list. These
may be native Linux applications or scripts built with
a language that is installed to the host: Python, Perl,
Go, BASH, etc. See my examples in /etc/.

```sudo nano /etc/inetd.conf```

Note: 
* Applications should be run under the same user account whose /home directory contains linbpq.
* Exact paths to the app or script should be used. 
* In the case of my node, the username is 'ect' for emergency communications team; not to be confused with 'etc' the system configuration directory.

Step 3
------
Next, we will assign the service application a tcp port.
In the examples I've found, sysops are using ports in
the 63,000 range. Take note of these port numbers, you
will need them for the next step.

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
Finally, we add the commands to the BPQ node to call the 
external applications running as services. Again, my linbpq
directory is under the 'ect' user, yours likely differs:

```nano /home/ect/linbpq/bpq32.cfg```

See my example linbpq/bpq32.cfg configuration file for the
more complete uncommented version. The full file, with
passwords redacted, is available in that file's revision
history.

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
    APPLICATION 6,SYSINFO,C 9 HOST 2 NOCALL S
                  ^       ^    ^   ^ ^      ^
                  |       |    |   | |      |
	          |       |    |   | |      Return to node upon exit
		  |       |    |   | Do not pass call sign to app
                  |       |    |   CMDPORT #
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

Log into your node and run the new command. If it works, it /should/ work over radio.

Caveats
=======
There seems to be some sort of timeout for which a command run by the BPQ node software waits before it terminates the process. 
* If the application returns to the node prompt without output, try the command again
* If the application runs fine but output is truncated, you may need to curb your expectations and reduce the actions performed by the script
* I'll continue to research a way around this

If you are using script
* Ensure the script is executable

```chmod +x script.py```
* Ensure the first line is either #!/bin/sh or #!/bin/python3 and that the interpreter is installed there. Run 'whereis python3' to get the correct path.
