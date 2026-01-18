# Documentation

Complete setup guides, configuration examples, and reference materials for BPQ packet radio applications.

## Contents

### [INSTALLATION.md](INSTALLATION.md)
Complete installation and configuration guide covering:
- Installing and configuring inetd for BPQ applications
- Setting up TCP services and ports
- Configuring BPQ32 APPLICATION commands
- Utilities installation and directory layout
- Troubleshooting common issues

### [examples/](examples/)
Configuration file examples and templates:

#### [examples/etc/](examples/etc/)
- **inetd.conf** - Sample inetd service configurations
- **services** - Sample TCP port assignments for BPQ applications

#### [examples/linbpq/](examples/linbpq/)
- **bpq32.cfg** - Sample BPQ32 node configuration with APPLICATION commands

### [images/](images/)
Screenshots and example outputs demonstrating application functionality.

## Quick Start

1. Read [INSTALLATION.md](INSTALLATION.md) for complete setup instructions
2. Review [examples/](examples/) for configuration templates
3. Adapt examples to your node's username (pi, ect, etc.) and directory structure

## Node Layout Reference

```
/home/pi/               (or /home/ect/)
├── apps/               # User-facing BPQ applications
├── utilities/          # Sysop tools
├── linbpq/             # BPQ32 installation
│   └── bpq32.cfg       # Node configuration
└── ...
```

## Additional Resources

- [LinBPQ Applications Interface Documentation](https://www.cantab.net/users/john.wiseman/Documents/LinBPQ%20Applications%20Interface.html)
- [inetd - Wikipedia](https://en.wikipedia.org/wiki/Inetd)
- [Main Repository README](../README.md)
