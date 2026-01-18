#!/usr/bin/env python3
# battleship_bbs.py (Version 1.3 - Production Ready)
# A simple, text-based Battleship server for Packet Radio BBS systems.
# Author: Brad Brown Jr, KC1JMH
# With help from Gemini 2.5 and GPT 4.1
# Date: 2025-09-19

import socket
import threading
import time
import random
import json
import os

# --- Configuration ---
HOST = '0.0.0.0'
PORT = 23000  # Updated to match user's telnet command
FORMAT = 'utf-8'
LEADERBOARD_FILE = 'leaderboard.json'

# --- Logging Configuration ---
# Set to a filename to enable logging to file, or None to disable
LOG_FILENAME = None  # Example: 'battleship.log'

# --- Display Configuration ---
# Set to True to send clear screen (ESC[2J) at game start and each round
CLEAR_SCREEN_ENABLED = True

# --- Game Constants ---
BOARD_SIZE = 10
SHIPS = {"Carrier": 5, "Battleship": 4, "Cruiser": 3, "Submarine": 3, "Destroyer": 2}
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# --- Logging Function ---
def log_info(message):
    """Log info message to console and optionally to file"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [INFO] {message}"
    print(log_msg, flush=True)
    
    if LOG_FILENAME:
        try:
            with open(LOG_FILENAME, 'a', encoding='utf-8') as f:
                f.write(log_msg + '\n')
        except Exception as e:
            print(f"[ERROR] Failed to write to log file: {e}", flush=True)

# --- Global State (managed with locks) ---
clients_lock = threading.Lock()
clients = {}

games_lock = threading.Lock()
games = {}

waiting_players_lock = threading.Lock()
waiting_players = {}

leaderboard_lock = threading.Lock()

# --- Game state tracking for efficient updates ---
game_state_lock = threading.Lock()
game_state_updates = {}  # game_id -> set of players needing updates

# --- Lobby state tracking ---
lobby_state_lock = threading.Lock()
lobby_needs_refresh = set()  # Set of players who need lobby refresh

# --- Leaderboard Management ---
def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return {}
    try:
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_leaderboard(board):
    with leaderboard_lock:
        with open(LEADERBOARD_FILE, 'w') as f:
            json.dump(board, f, indent=4)

def record_win(call_sign):
    board = load_leaderboard()
    board[call_sign] = board.get(call_sign, 0) + 1
    save_leaderboard(board)

# --- Game Logic ---
class Game:
    def __init__(self, player1_call, player2_call):
        self.players = {player1_call: None, player2_call: None}
        self.boards = {player1_call: self.create_board(), player2_call: self.create_board()}
        self.current_turn = random.choice([player1_call, player2_call])
        self.game_over = False
        self.winner = None
        self.id = f"{player1_call}_vs_{player2_call}_{int(time.time())}"
        self.last_move = None  # Store last move information for display
        # Track individual ships and their positions for each player
        self.ship_positions = {player1_call: {}, player2_call: {}}
        self.place_ships_for_player(player1_call)
        self.place_ships_for_player(player2_call)

    def create_board(self):
        return [['~' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

    def place_ships_for_player(self, call_sign):
        board = self.boards[call_sign]
        self.ship_positions[call_sign] = {}
        
        for ship_name, length in SHIPS.items():
            placed = False
            attempts = 0
            max_attempts = 1000  # Prevent infinite loops
            while not placed and attempts < max_attempts:
                attempts += 1
                orientation = random.choice(['h', 'v'])
                if orientation == 'h':
                    row = random.randint(0, BOARD_SIZE - 1)
                    col = random.randint(0, BOARD_SIZE - length)
                    if all(board[row][c] == '~' for c in range(col, col + length)):
                        ship_coords = []
                        for c in range(col, col + length):
                            board[row][c] = 'S'
                            ship_coords.append((row, c))
                        self.ship_positions[call_sign][ship_name] = ship_coords
                        placed = True
                else: # 'v'
                    row = random.randint(0, BOARD_SIZE - length)
                    col = random.randint(0, BOARD_SIZE - 1)
                    if all(board[r][col] == '~' for r in range(row, row + length)):
                        ship_coords = []
                        for r in range(row, row + length):
                            board[r][col] = 'S'
                            ship_coords.append((r, col))
                        self.ship_positions[call_sign][ship_name] = ship_coords
                        placed = True
            if not placed:
                print(f"[ERROR] Could not place ship {ship_name} for {call_sign} after {max_attempts} attempts", flush=True)
                raise Exception(f"Ship placement failed for {ship_name}")

    def check_ship_sunk(self, player_call, target_row, target_col):
        """Check if hitting this coordinate sunk a ship. Returns ship name if sunk, None otherwise."""
        board = self.boards[player_call]
        
        # Find which ship this coordinate belongs to
        for ship_name, coords in self.ship_positions[player_call].items():
            if (target_row, target_col) in coords:
                # Check if all coordinates of this ship are hit (marked as 'X')
                if all(board[r][c] == 'X' for r, c in coords):
                    return ship_name
                break
        return None

    def fire(self, firing_player, target_coord):
        if self.game_over or firing_player != self.current_turn:
            return "Error: Not your turn or game is over.", False
        opponent = [p for p in self.players if p != firing_player][0]
        opponent_board = self.boards[opponent]
        try:
            row_char = target_coord[0].upper()
            col_str = target_coord[1:]
            row = ALPHABET.index(row_char)
            col = int(col_str) - 1
            if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
                return "Invalid coordinate. Must be A-J and 1-10 (e.g., B5).", False
        except (ValueError, IndexError):
            return "Invalid coordinate format. Use format like B5.", False
        target_cell = opponent_board[row][col]
        result_msg = ""
        if target_cell in ['X', 'O']:
            result_msg = f"You already fired at {target_coord}."
        elif target_cell == 'S':
            opponent_board[row][col] = 'X'
            result_msg = f"HIT! You struck an enemy ship at {target_coord}!"
            
            # Check if this hit sunk a ship
            sunk_ship = self.check_ship_sunk(opponent, row, col)
            if sunk_ship:
                result_msg += f"\r\nYou sunk their {sunk_ship}!"
            
            if self.check_win(opponent):
                self.game_over = True
                self.winner = firing_player
                record_win(firing_player)
                result_msg += f"\r\nYOU SUNK ALL ENEMY BATTLESHIPS! YOU ARE THE WINNER!"
        else:
            opponent_board[row][col] = 'O'
            result_msg = f"MISS! Your shot at {target_coord} was a miss."
        if target_cell not in ['X', 'O']:
            self.current_turn = opponent
        
        # Store last move information for display (removed "Result:" text)
        self.last_move = f"{firing_player} fired at {target_coord}. {result_msg}"
        
        # Mark both players for game state updates
        with game_state_lock:
            if self.id not in game_state_updates:
                game_state_updates[self.id] = set()
            game_state_updates[self.id].add(firing_player)
            game_state_updates[self.id].add(opponent)
        
        return result_msg, True

    def check_win(self, opponent):
        return not any('S' in row for row in self.boards[opponent])

# --- Update Management ---
def needs_game_update(game_id, player_call):
    """Check if a player needs a game state update"""
    with game_state_lock:
        return game_id in game_state_updates and player_call in game_state_updates[game_id]

def mark_game_updated(game_id, player_call):
    """Mark that a player has received their game state update"""
    with game_state_lock:
        if game_id in game_state_updates:
            game_state_updates[game_id].discard(player_call)
            if not game_state_updates[game_id]:  # Remove empty sets
                del game_state_updates[game_id]

# --- Lobby Management ---
def notify_lobby_change():
    """Notify all waiting players that the lobby has changed"""
    with lobby_state_lock:
        with waiting_players_lock:
            lobby_needs_refresh.update(waiting_players.keys())

def needs_lobby_refresh(player_call):
    """Check if a player needs a lobby refresh"""
    with lobby_state_lock:
        return player_call in lobby_needs_refresh

def mark_lobby_refreshed(player_call):
    """Mark that a player has received their lobby refresh"""
    with lobby_state_lock:
        lobby_needs_refresh.discard(player_call)

# --- Challenge Management ---
challenge_lock = threading.Lock()
pending_challenges = {}  # target_call -> challenger_call

def handle_challenge(challenger_call, target_call):
    with waiting_players_lock:
        if target_call not in waiting_players:
            send_message(clients[challenger_call], f"Error: Player '{target_call}' is not available.")
            return
        if challenger_call == target_call:
            send_message(clients[challenger_call], "You can't challenge yourself!")
            return
        target_socket = waiting_players.get(target_call)
        challenger_socket = waiting_players.get(challenger_call)
        if not target_socket or not challenger_socket:
             send_message(clients[challenger_call], "An error occurred finding players.")
             return
    
    # Set up the challenge
    with challenge_lock:
        pending_challenges[target_call] = challenger_call
    
    send_message(target_socket, f"\r\n*** You have been challenged by {challenger_call}! ***\r\nType 'accept' to play, or 'decline' to refuse.")
    send_message(challenger_socket, f"Challenge sent to {target_call}. Waiting for a response...")
    log_info(f"Challenge issued: {challenger_call} challenged {target_call}")

def process_challenge_response(target_call, response):
    """Process a challenge response in the target player's main loop"""
    with challenge_lock:
        if target_call not in pending_challenges:
            return False  # No pending challenge
        
        challenger_call = pending_challenges[target_call]
        del pending_challenges[target_call]
    
    if response == 'accept' or response == 'yes' or response == 'y':
        # Remove players from waiting list first
        with waiting_players_lock:
            if challenger_call in waiting_players: 
                del waiting_players[challenger_call]
            if target_call in waiting_players: 
                del waiting_players[target_call]
        
        # Notify remaining lobby players that two players left
        notify_lobby_change()
        
        try:
            new_game = Game(challenger_call, target_call)
        except Exception as e:
            print(f"[ERROR] Failed to create game: {e}", flush=True)
            return False
        
        with games_lock:
            games[new_game.id] = new_game
        
        # Mark both players for initial game state update
        with game_state_lock:
            game_state_updates[new_game.id] = {challenger_call, target_call}
        
        challenger_socket = clients.get(challenger_call)
        target_socket = clients.get(target_call)
        if challenger_socket:
            send_clear_screen(challenger_socket)
            send_message(challenger_socket, f"{target_call} accepted! Starting game...")
        if target_socket:
            send_clear_screen(target_socket)
            send_message(target_socket, "You accepted the challenge! Starting game...")
        log_info(f"Challenge accepted: {target_call} accepted challenge from {challenger_call}, starting game {new_game.id}")
        return True
    else:
        challenger_socket = clients.get(challenger_call)
        target_socket = clients.get(target_call)
        if challenger_socket:
            send_message(challenger_socket, f"{target_call} declined your challenge.")
        if target_socket:
            send_message(target_socket, "You have declined the challenge.")
        log_info(f"Challenge declined: {target_call} declined challenge from {challenger_call}")
        return False

# --- Client Handling ---
def render_board(board, show_ships=False):
    s = "   1  2  3  4  5  6  7  8  9  10\r\n"
    for i, row in enumerate(board):
        row_char = ALPHABET[i]
        s += f"{row_char} "
        for cell in row:
            s += f" {cell if show_ships or cell != 'S' else '~'} "
        s += "\r\n"
    return s

def recv_line(client_socket, timeout=None):
    """Receive a complete line from the client, handling character-by-character input"""
    if timeout:
        client_socket.settimeout(timeout)
    
    line = ""
    while True:
        try:
            char = client_socket.recv(1).decode(FORMAT)
            if not char:  # Connection closed
                break
            if char == '\r':  # Carriage return - ignore
                continue
            if char == '\n':  # Line feed - end of line
                break
            if ord(char) == 8 or ord(char) == 127:  # Backspace or DEL
                if line:
                    line = line[:-1]
                continue
            line += char
        except socket.timeout:
            raise
        except (ConnectionResetError, OSError):
            break
    
    if timeout:
        client_socket.settimeout(None)
    
    return line.strip()

def send_message(client_socket, message):
    try:
        client_socket.sendall((message + "\r\n").encode(FORMAT))
    except (ConnectionResetError, BrokenPipeError, OSError):
        # Re-raise the exception so calling code can handle the disconnection
        raise

def send_clear_screen(client_socket):
    """Send clear screen command if enabled"""
    if CLEAR_SCREEN_ENABLED:
        try:
            # Send ANSI escape sequence for clear screen and cursor to home
            client_socket.sendall(b"\x1b[2J\x1b[H")
        except (ConnectionResetError, BrokenPipeError, OSError):
            # Ignore errors for clear screen - not critical
            pass

def handle_client(client_socket, addr):
    print(f"[NEW CONNECTION] {addr} connected.", flush=True)
    log_info(f"New connection from {addr}")
    send_message(client_socket, "Welcome to Battleship BBS!\r\nPlease enter your call sign:")
    call_sign = ""
    try:
        call_sign_raw = recv_line(client_socket, timeout=60.0).upper()
        if not call_sign_raw or not call_sign_raw.replace('-', '').isalnum() or len(call_sign_raw) > 10:
            send_message(client_socket, "Invalid call sign. Disconnecting.")
            return
        call_sign = call_sign_raw
    except (ConnectionResetError, OSError, socket.timeout):
        print(f"[DISCONNECTED] {addr} disconnected before login.", flush=True)
        log_info(f"Connection from {addr} disconnected before login")
        return
    finally:
        if not call_sign:
            client_socket.close()

    with clients_lock:
        if call_sign in clients:
            send_message(client_socket, f"Call sign '{call_sign}' is already in use. Disconnecting.")
            client_socket.close()
            return
        clients[call_sign] = client_socket
    with waiting_players_lock:
        waiting_players[call_sign] = client_socket
    log_info(f"Player {call_sign} logged in from {addr}")
    send_message(client_socket, f"Welcome, {call_sign}! You are now in the lobby.")
    
    # Notify other players that someone new has joined
    notify_lobby_change()
    
    current_game = None
    lobby_shown = False
    try:
        while True:
            if not current_game:
                # Check if this is a response to a pending challenge first
                with challenge_lock:
                    has_pending = call_sign in pending_challenges

                # Check if lobby needs refresh due to player changes
                if needs_lobby_refresh(call_sign):
                    lobby_shown = False
                    mark_lobby_refreshed(call_sign)
                
                # Only show lobby info once or when player count changes, and no pending challenge
                if not lobby_shown and not has_pending:
                    try:
                        send_message(client_socket, "\r\n--- LOBBY ---\r\nCommands: [list], [challenge <callsign>], [leaderboard], [quit]")
                        with waiting_players_lock:
                            other_players = [p for p in waiting_players if p != call_sign]
                        if not other_players:
                            send_message(client_socket, "Waiting for an opponent...")
                        else:
                            send_message(client_socket, f"Players waiting: {', '.join(other_players)}")
                        lobby_shown = True
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        break
                
                client_socket.settimeout(5.0)  # Shorter timeout for faster lobby updates
                try:
                    command_raw = recv_line(client_socket, timeout=5.0)
                    command = command_raw.lower()
                    parts = command.split()
                    cmd = parts[0] if parts else ""
                    
                    # Check if this is a response to a pending challenge
                    with challenge_lock:
                        has_pending = call_sign in pending_challenges
                    
                    # Process challenge response without holding the lock
                    if has_pending:
                        if process_challenge_response(call_sign, command_raw.lower().strip()):
                            # Challenge accepted, will transition to game
                            continue
                        else:
                            # Challenge declined, continue in lobby
                            lobby_shown = False  # Reset lobby display
                            continue
                    
                    if cmd == "list": 
                        lobby_shown = False  # Force refresh
                        continue
                    elif cmd == "leaderboard":
                        board = load_leaderboard()
                        if not board: 
                            try:
                                send_message(client_socket, "Leaderboard is empty.")
                            except (ConnectionResetError, BrokenPipeError, OSError):
                                break
                        else:
                            sorted_board = sorted(board.items(), key=lambda item: item[1], reverse=True)
                            try:
                                send_message(client_socket, "\r\n--- TOP 10 WINS ---")
                                for i, (cs, wins) in enumerate(sorted_board[:10]):
                                    send_message(client_socket, f"{i+1}. {cs}: {wins} wins")
                            except (ConnectionResetError, BrokenPipeError, OSError):
                                break
                    elif cmd == "challenge" and len(parts) > 1:
                        handle_challenge(call_sign, parts[1].upper())
                        lobby_shown = False  # May need refresh after challenge
                    elif cmd in ["quit"]: 
                        try:
                            send_message(client_socket, "Goodbye! Thanks for playing Battleship BBS!")
                        except (ConnectionResetError, BrokenPipeError, OSError):
                            pass  # Client already disconnected
                        break
                    elif cmd: 
                        try:
                            send_message(client_socket, f"Unknown command: '{cmd}'")
                        except (ConnectionResetError, BrokenPipeError, OSError):
                            break
                except socket.timeout:
                    # Check for game assignment without sending messages
                    with games_lock:
                        for game in games.values():
                            if call_sign in game.players and not game.game_over:
                                current_game = game
                                break
                    continue
                except (ConnectionResetError, OSError): break
            if current_game:
                client_socket.settimeout(None)
                opponent = [p for p in current_game.players if p != call_sign][0]
                
                # Only send board updates when there's an actual update
                if needs_game_update(current_game.id, call_sign):
                    try:
                        # Clear screen first for clean display
                        send_clear_screen(client_socket)
                        send_message(client_socket, f"\r\n{'='*20}\r\nGame against {opponent}\r\n\r\nYOUR BOARD (Your Ships)")
                        send_message(client_socket, render_board(current_game.boards[call_sign], show_ships=True))
                        send_message(client_socket, "\r\nOPPONENT'S BOARD (Your Shots)")
                        send_message(client_socket, render_board(current_game.boards[opponent]))
                        
                        # Show last move if there was one
                        if current_game.last_move:
                            # Parse the last move to show correct perspective
                            parts = current_game.last_move.split(" fired at ")
                            if len(parts) == 2:
                                firing_player = parts[0]
                                coord_and_result = parts[1].split(". ")
                                if len(coord_and_result) >= 2:
                                    coordinate = coord_and_result[0]
                                    result = ". ".join(coord_and_result[1:])  # Join in case there are multiple periods
                                    
                                    if firing_player == call_sign:
                                        # This player made the move
                                        send_message(client_socket, f"\r\nYou shot at {coordinate}")
                                        send_message(client_socket, result)
                                    else:
                                        # Opponent made the move, adjust perspective
                                        if "You struck" in result:
                                            result = result.replace("You struck", f"{firing_player} struck")
                                        if "Your shot" in result:
                                            result = result.replace("Your shot", f"{firing_player}'s shot")
                                        if "You sunk their" in result:
                                            result = result.replace("You sunk their", "They sunk your")
                                        send_message(client_socket, f"\r\n{firing_player} fired at {coordinate}")
                                        send_message(client_socket, result)
                                else:
                                    send_message(client_socket, f"\r\n{current_game.last_move}")
                            else:
                                send_message(client_socket, f"\r\n{current_game.last_move}")
                        
                        mark_game_updated(current_game.id, call_sign)
                        
                        # Show waiting message once after board display if it's not their turn
                        if current_game.current_turn != call_sign:
                            send_message(client_socket, "Waiting for opponent. Type 'quit' to forfeit.")
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        break
                
                if current_game.game_over:
                    victory_msg = "** YOU ARE VICTORIOUS! **" if current_game.winner == call_sign else "** YOU HAVE BEEN DEFEATED. **"
                    try:
                        send_message(client_socket, victory_msg)
                        send_message(client_socket, "Returning to lobby...")
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        break
                    log_info(f"Game completed: {current_game.winner} defeated {opponent} in game {current_game.id}")
                    time.sleep(5)
                    with games_lock:
                        if current_game.id in games: del games[current_game.id]
                    current_game = None
                    lobby_shown = False  # Reset lobby display flag
                    with waiting_players_lock:
                        waiting_players[call_sign] = client_socket
                    
                    # Notify other players that someone returned to lobby
                    notify_lobby_change()
                    
                    continue
                
                if current_game.current_turn == call_sign:
                    try:
                        send_message(client_socket, "Your turn. Enter coordinate to fire (e.g., A1, or 'quit' to forfeit):")
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        break
                    try:
                        target_coord = recv_line(client_socket, timeout=300.0)  # 5 minute timeout for moves
                        if not target_coord: continue
                        if target_coord.lower() in ['quit', 'forfeit']:
                            current_game.game_over = True
                            current_game.winner = opponent
                            record_win(opponent)
                            opponent_socket = clients.get(opponent)
                            if opponent_socket:
                                send_message(opponent_socket, f"\r\n{call_sign} has forfeited the game! You win!")
                            send_message(client_socket, "You have forfeited the game. Returning to lobby...")
                            log_info(f"Game forfeited: {call_sign} forfeited to {opponent} in game {current_game.id}")
                            # Clean up and return to lobby
                            with games_lock:
                                if current_game.id in games: del games[current_game.id]
                            current_game = None
                            lobby_shown = False
                            with waiting_players_lock:
                                waiting_players[call_sign] = client_socket
                            notify_lobby_change()
                            continue
                        result_msg, _ = current_game.fire(call_sign, target_coord)
                        send_message(client_socket, result_msg)
                        # Note: Opponent will see the move in their next board update via last_move
                    except (ConnectionResetError, socket.timeout, OSError): break
                else:
                    # Wait for opponent's turn - no repeated messages since it's shown after board
                    try:
                        # Check for any input (forfeit command) with shorter timeout
                        data = recv_line(client_socket, timeout=10.0)
                        if data.lower() in ['quit', 'forfeit']:
                            current_game.game_over = True
                            current_game.winner = opponent
                            record_win(opponent)
                            opponent_socket = clients.get(opponent)
                            if opponent_socket:
                                send_message(opponent_socket, f"\r\n{call_sign} has forfeited the game! You win!")
                            send_message(client_socket, "You have forfeited the game. Returning to lobby...")
                            log_info(f"Game forfeited: {call_sign} forfeited to {opponent} in game {current_game.id}")
                            # Clean up and return to lobby
                            with games_lock:
                                if current_game.id in games: del games[current_game.id]
                            current_game = None
                            lobby_shown = False
                            with waiting_players_lock:
                                waiting_players[call_sign] = client_socket
                            notify_lobby_change()
                    except socket.timeout:
                        pass  # Continue waiting silently
                    except (ConnectionResetError, OSError): 
                        break
    except Exception as e:
        print(f"[ERROR] An error occurred with client {call_sign}: {e}", flush=True)
    finally:
        print(f"[DISCONNECTED] {call_sign} has disconnected.", flush=True)
        log_info(f"Player {call_sign} disconnected")
        with clients_lock:
            if call_sign in clients: del clients[call_sign]
        with waiting_players_lock:
            if call_sign in waiting_players: del waiting_players[call_sign]
        
        # Notify remaining players that someone left
        notify_lobby_change()
        
        if current_game and not current_game.game_over:
            opponent = [p for p in current_game.players if p != call_sign][0]
            current_game.winner = opponent
            current_game.game_over = True
            record_win(opponent)
            opponent_socket = clients.get(opponent)
            if opponent_socket:
                send_message(opponent_socket, f"\r\n{call_sign} disconnected. You win by default!")
            log_info(f"Player disconnected during game: {call_sign} disconnected, {opponent} wins by default in game {current_game.id}")
            # Clean up game state updates
            with game_state_lock:
                if current_game.id in game_state_updates:
                    del game_state_updates[current_game.id]
        
        # Clean up lobby notifications
        with lobby_state_lock:
            lobby_needs_refresh.discard(call_sign)
        
        # Clean up pending challenges
        with challenge_lock:
            if call_sign in pending_challenges:
                challenger_call = pending_challenges[call_sign]
                del pending_challenges[call_sign]
                challenger_socket = clients.get(challenger_call)
                if challenger_socket:
                    send_message(challenger_socket, f"{call_sign} disconnected before responding to challenge.")
            # Also remove if this player was the challenger
            to_remove = [target for target, challenger in pending_challenges.items() if challenger == call_sign]
            for target in to_remove:
                del pending_challenges[target]
        
        client_socket.close()

# --- Server Main Loop ---
def main():
    """The main function to start the server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
    except OSError as e:
        print(f"[FATAL ERROR] Could not start server: {e}", flush=True)
        return

    log_info(f"Battleship BBS Server started - listening on {HOST}:{PORT}")

    try:
        while True:
            client_socket, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        print("\n[SHUTTING DOWN] Server is shutting down.", flush=True)
    finally:
        server.close()

if __name__ == "__main__":
    main()