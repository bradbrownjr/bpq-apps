#!/usr/bin/env python3
"""
Community Bulletin Board for Packet Radio
------------------------------------------
Classic BBS-style one-liner bulletin board for packet radio networks.
Users can post short messages and view recent messages from the community.

Features:
- Post new one-liner messages (up to 80 characters)
- View recent messages with pagination
- Delete your own messages
- JSON storage with callsign, timestamp, and message text
- Automatic callsign detection from BPQ32
- Manual callsign entry if not provided by BBS

Usage in bpq32.cfg:
  APPLICATION X,BULLETIN,C 9 HOST X S

The 'S' flag strips SSID from callsign for cleaner display.
Remove 'S' to include SSID (e.g., KC1JMH-8).

Author: Brad Brown KC1JMH
Version: 1.2
Date: January 2026
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
        import stat
        
        # Get the version from GitHub (silent check with short timeout)
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read().decode('utf-8')
        
        # Extract version from docstring
        version_match = re.search(r'Version:\s*([0-9.]+)', content)
        if version_match:
            github_version = version_match.group(1)
            
            if compare_versions(github_version, current_version) > 0:
                print("\nUpdate available: v{} -> v{}".format(current_version, github_version))
                print("Downloading new version...")
                
                # Download the new version
                script_path = os.path.abspath(__file__)
                try:
                    # Write to temporary file first, then replace
                    temp_path = script_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    # Ensure file is executable
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    
                    # Replace old file with new one
                    os.replace(temp_path, script_path)
                    
                    print("\nUpdate installed successfully!")
                    print("Please re-run this command to use the updated version.")
                    print("\nQuitting...")
                    sys.exit(0)
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    # Clean up temp file if it exists
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
    except Exception:
        # Don't block startup if update check fails (no internet, etc.)
        pass

def compare_versions(version1, version2):
    """Compare two version strings"""
    try:
        parts1 = [int(x) for x in str(version1).split('.')]
        parts2 = [int(x) for x in str(version2).split('.')]
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0
    except (ValueError, AttributeError):
        return 0

def is_valid_callsign(callsign):
    """Validate amateur radio callsign format"""
    if not callsign:
        return False
    # Pattern: 1-2 prefix letters, digit, 1-3 suffix letters, optional -SSID
    pattern = r'^[A-Z]{1,2}\d[A-Z]{1,3}(?:-\d{1,2})?$'
    return bool(re.match(pattern, callsign.upper().strip()))

def get_callsign():
    """Get callsign from BPQ32 or prompt user"""
    try:
        # Try to read callsign from stdin (BPQ32 passes it)
        call = input().strip().upper()
        if is_valid_callsign(call):
            # Reopen stdin for interactive use after piped input
            try:
                sys.stdin = open('/dev/tty', 'r')
            except (OSError, IOError):
                pass  # Continue with current stdin if /dev/tty unavailable
            return call
    except (EOFError, KeyboardInterrupt):
        pass
    
    # No valid callsign from BPQ, prompt user
    while True:
        try:
            call = input("Enter your callsign: ").strip().upper()
            if call.upper() == 'Q':
                print("Exiting...")
                sys.exit(0)
            if is_valid_callsign(call):
                return call
            print("Invalid callsign format. Try again (Q to quit):")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            sys.exit(0)

def load_messages():
    """Load messages from JSON file"""
    data_file = os.path.join(os.path.dirname(__file__), 'bulletin_board.json')
    try:
        with open(data_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'messages': []}

def save_messages(data):
    """Save messages to JSON file"""
    data_file = os.path.join(os.path.dirname(__file__), 'bulletin_board.json')
    try:
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print("Error saving messages: {}".format(e))
        return False

def format_timestamp(iso_string):
    """Format ISO timestamp for display"""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%m/%d %H:%M')
    except:
        return 'unknown'

def display_messages(data, callsign, page=0, per_page=10):
    """Display paginated messages"""
    messages = data.get('messages', [])
    if not messages:
        print("No messages posted yet.")
        return
    
    # Sort by timestamp (newest first)
    messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    total_messages = len(messages)
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_messages)
    
    if start_idx >= total_messages:
        print("No more messages.")
        return
    
    print("\n--- Community Bulletin Board ---")
    print("Messages {}-{} of {}".format(start_idx + 1, end_idx, total_messages))
    print()
    
    for i in range(start_idx, end_idx):
        msg = messages[i]
        msg_num = i + 1
        timestamp = format_timestamp(msg.get('timestamp', ''))
        author = msg.get('callsign', 'Unknown')
        text = msg.get('message', '')
        
        # Mark messages you can delete (prefix for visibility)
        marker = '*' if author == callsign else ' '
        
        print("{}{}. [{}] {}: {}".format(marker, msg_num, timestamp, author, text))
    
    if callsign:
        print("\n* = Your messages (can delete)")
    
    total_pages = (total_messages + per_page - 1) // per_page
    if total_pages > 1:
        print("\nPage {} of {}".format(page + 1, total_pages))

def post_message(data, callsign):
    """Post a new message"""
    print("\nPost new message (80 chars max, Q to cancel):")
    try:
        message = input("> ").strip()
        if message.upper() == 'Q':
            return data
        
        if not message:
            print("Message cannot be empty.")
            return data
        
        if len(message) > 80:
            print("Message too long ({} chars). Max 80 characters.".format(len(message)))
            return data
        
        # Create new message entry
        new_msg = {
            'callsign': callsign,
            'message': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        if 'messages' not in data:
            data['messages'] = []
        
        data['messages'].append(new_msg)
        
        print("Message posted!")
        return data
        
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return data

def delete_message(data, callsign):
    """Delete a user's own message"""
    messages = data.get('messages', [])
    if not messages:
        print("No messages to delete.")
        return data
    
    # Find user's messages
    user_messages = []
    for i, msg in enumerate(messages):
        if msg.get('callsign') == callsign:
            user_messages.append((i + 1, msg))
    
    if not user_messages:
        print("You have no messages to delete.")
        return data
    
    print("\nYour messages:")
    for msg_num, msg in user_messages:
        timestamp = format_timestamp(msg.get('timestamp', ''))
        text = msg.get('message', '')
        print("{}. [{}] {}".format(msg_num, timestamp, text))
    
    try:
        choice = input("\nEnter message number to delete (Q to cancel): ").strip()
        if choice.upper() == 'Q':
            return data
        
        msg_num = int(choice)
        if msg_num < 1 or msg_num > len(messages):
            print("Invalid message number.")
            return data
        
        # Check if user owns this message
        target_msg = messages[msg_num - 1]
        if target_msg.get('callsign') != callsign:
            print("You can only delete your own messages.")
            return data
        
        # Confirm deletion
        confirm = input("Delete this message? (y/N): ").strip().lower()
        if confirm == 'y' or confirm == 'yes':
            del data['messages'][msg_num - 1]
            print("Message deleted.")
        else:
            print("Deletion cancelled.")
        
        return data
        
    except (ValueError, EOFError, KeyboardInterrupt):
        print("Invalid input or cancelled.")
        return data

def show_stats(data):
    """Show bulletin board statistics"""
    messages = data.get('messages', [])
    if not messages:
        print("No messages posted yet.")
        return
    
    print("\n--- Bulletin Board Stats ---")
    print("Total messages: {}".format(len(messages)))
    
    # Count messages by author
    authors = {}
    recent_count = 0
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    for msg in messages:
        author = msg.get('callsign', 'Unknown')
        authors[author] = authors.get(author, 0) + 1
        
        # Count recent messages (last 7 days)
        try:
            msg_time = datetime.fromisoformat(msg.get('timestamp', '').replace('Z', '+00:00'))
            if msg_time > week_ago:
                recent_count += 1
        except:
            pass
    
    print("Messages last 7 days: {}".format(recent_count))
    print("Active contributors: {}".format(len(authors)))
    
    # Top contributors
    if authors:
        sorted_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)
        print("\nTop contributors:")
        for i, (author, count) in enumerate(sorted_authors[:5]):
            print("  {}. {} ({} messages)".format(i + 1, author, count))

def main_loop(callsign):
    """Main program loop with standardized interface"""
    current_page = 0
    
    # Standardized header with proper spacing
    print()
    print("BULLETIN v1.2 - Community Messages")
    print("-" * 40)
    
    data = load_messages()
    display_messages(data, callsign, current_page)
    
    while True:
        try:
            # Compressed prompt for bandwidth efficiency
            choice = input("\nMenu: P)ost D)el N)ext Pr)ev S)tat Q :> ").strip().upper()
            
            if choice.startswith('Q'):
                print("\nExiting...")
                break
            elif choice.startswith('P'):
                data = load_messages()
                updated_data = post_message(data, callsign)
                if save_messages(updated_data):
                    current_page = 0  # Reset to first page to see new message
                    data = load_messages()
                    display_messages(data, callsign, current_page)
            elif choice.startswith('D'):
                data = load_messages()
                updated_data = delete_message(data, callsign)
                if save_messages(updated_data):
                    # Refresh display after deletion
                    data = load_messages()
                    display_messages(data, callsign, current_page)
            elif choice.startswith('N'):
                current_page += 1
                data = load_messages()
                display_messages(data, callsign, current_page)
            elif choice.startswith('PR'):
                if current_page > 0:
                    current_page -= 1
                data = load_messages()
                display_messages(data, callsign, current_page)
            elif choice.startswith('S'):
                data = load_messages()
                show_stats(data)
            else:
                print("Invalid choice. P)ost, D)elete, N)ext, Pr)evious, S)tats, Q)uit")
                
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

def main():
    """Main application entry point"""
    # Check for app updates
    check_for_app_update("1.2", "bulletin.py")
    


    
    # Get callsign from BPQ or user input
    callsign = get_callsign()
    

    
    # Enter main program loop
    main_loop(callsign)

if __name__ == '__main__':
    main()