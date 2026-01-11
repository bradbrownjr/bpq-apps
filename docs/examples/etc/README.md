# BPQ Node Configuration Files

This directory contains example configuration snippets for integrating packet radio applications with linbpq BBS software.

## Files

### inetd.conf
Example service definitions for running applications via inetd. Each entry maps an application name to its executable path and specifies how inetd should handle connections.

Format:
```
service_name  stream  tcp  nowait  username  /full/path/to/executable
```

Copy relevant entries to `/etc/inetd.conf` on your node, adjusting paths and usernames as needed.

### services
Example TCP port assignments for packet radio applications. Standard practice uses ports in the 63000+ range to avoid conflicts.

Format:
```
service_name    63010/tcp
```

Copy relevant entries to `/etc/services` on your node, ensuring port numbers don't conflict with existing services.

## Integration Steps

1. Copy desired entries from these example files to the corresponding system files on your node
2. Adjust file paths to match your installation directory
3. Change username to match your linbpq user (commonly `pi` or `ect`)
4. Restart inetd: `sudo service inetd restart`
5. Configure corresponding entries in `bpq32.cfg` APPLICATION section
6. Test via telnet before radio deployment

See main [../../INSTALLATION.md](../../INSTALLATION.md) for complete installation instructions.
