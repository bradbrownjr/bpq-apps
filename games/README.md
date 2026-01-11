# BPQ Games

Interactive games for packet radio BBS systems. Games run as standalone TCP servers and can be accessed via telnet.

## battleship.py

**Type**: Python  
**Purpose**: Multiplayer Battleship game server  
**Developer**: Brad Brown KC1JMH  
**Port**: 23000 (configurable in script)

**Download or update**:  
```wget -O battleship.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/games/battleship.py && chmod +x battleship.py```

**Features**:
- Classic Battleship gameplay over ASCII terminal
- Multiplayer support via TCP socket connections
- Leaderboard tracking with JSON persistence
- Configurable board size and ships
- Optional screen clearing for better display
- Designed for low-bandwidth packet radio connections

**Running**:
```python3 battleship.py```

Server listens on port 23000 by default. Players connect via telnet.

**Note**: This runs as an independent TCP server, not via BPQ APPLICATION command. Start it as a background service or via screen/tmux session.

**Configuration**:
Edit variables in the script:
- `PORT` - TCP port to listen on (default: 23000)
- `BOARD_SIZE` - Grid size (default: 10)
- `CLEAR_SCREEN_ENABLED` - Send clear screen codes (default: True)
- `LOG_FILENAME` - Log file path (default: None/disabled)
- `LEADERBOARD_FILE` - Leaderboard storage (default: leaderboard.json)
