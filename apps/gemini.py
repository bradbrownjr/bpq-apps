#!/usr/bin/env python3
"""
AI Chat Assistant for Amateur Radio Operators
Version: 1.0

Interactive AI chat using Google Gemini API.
Designed for BPQ32 packet radio with ham radio context and etiquette.

Usage:
    gemini.py                  # Interactive chat session
    gemini.py --help           # Show help

BPQ32 APPLICATION line:
    APPLICATION 7,GEMINI,C 9 HOST # K,CALLSIGN,FLAGS

Note: Requires callsign (no NOCALL flag) for personalized greetings.

Author: Brad Brown Jr (KC1JMH)
Date: January 29, 2026
"""

import sys
import os
import json
import socket
import re
from urllib.request import urlopen, Request, HTTPError, URLError
from urllib.parse import urlencode

VERSION = "1.0"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "gemini.conf")

# Ham Radio Ten Commandments for system prompt
HAM_COMMANDMENTS = """
1. Never knowingly operate in a manner contrary to FCC regulations.
2. Assist other operators when needed.
3. Conduct yourself with dignity and courtesy at all times.
4. Use the minimum power necessary for reliable communication.
5. Operate in such a way as to set a good example for others.
6. Promote the amateur service and encourage others to participate.
7. Use your station and skills in times of emergency.
8. Continuously improve your operating skills and station.
9. Respect the rights of others and their use of frequencies.
10. Share knowledge freely with other operators.
"""


def show_logo():
    """Display ASCII art logo"""
    logo = r"""
                     _       _ 
  __ _  ___ _ __ ___ (_)_ __ (_)
 / _` |/ _ \ '_ ` _ \| | '_ \| |
| (_| |  __/ | | | | | | | | | |
 \__,_|\___|_| |_| |_|_|_| |_|_|
"""
    print(logo)


def is_internet_available():
    """Check if internet is available via DNS lookup"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def check_for_app_update(current_version, script_name):
    """Check GitHub for newer version and auto-update if available"""
    try:
        url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        req = Request(url, headers={"User-Agent": "BPQ-Apps-Updater"})
        response = urlopen(req, timeout=3)
        remote_content = response.read().decode('utf-8')
        
        # Extract version from remote file
        version_match = re.search(r'Version:\s*([\d.]+)', remote_content)
        if version_match:
            remote_version = version_match.group(1)
            if compare_versions(remote_version, current_version) > 0:
                script_path = os.path.abspath(__file__)
                temp_path = script_path + ".tmp"
                try:
                    with open(temp_path, 'w') as f:
                        f.write(remote_content)
                    
                    # Preserve executable permission
                    if os.path.exists(script_path):
                        os.chmod(temp_path, os.stat(script_path).st_mode)
                    
                    os.replace(temp_path, script_path)
                    print("Updated to version {}".format(remote_version))
                    print("Please restart the app.")
                    sys.exit(0)
                except Exception:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
    except Exception:
        pass  # Silent failure on network issues


def compare_versions(v1, v2):
    """Compare version strings. Returns: 1 if v1>v2, -1 if v1<v2, 0 if equal"""
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    return 0


def extract_base_call(callsign):
    """Remove SSID from callsign"""
    return callsign.split('-')[0] if callsign else ""


def load_config():
    """Load API key from config file"""
    if not os.path.exists(CONFIG_FILE):
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data.get('gemini_api_key')
    except Exception:
        return None


def save_config(api_key):
    """Save API key to config file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'gemini_api_key': api_key}, f, indent=2)
        return True
    except Exception:
        return False


def prompt_for_api_key():
    """Prompt user to enter and save API key"""
    print("-" * 40)
    print("GEMINI API KEY SETUP")
    print("-" * 40)
    print("")
    print("To use this app, you need a free Google")
    print("Gemini API key.")
    print("")
    print("Get your API key at:")
    print("https://aistudio.google.com/apikey")
    print("")
    print("Steps:")
    print("1. Visit the URL above")
    print("2. Sign in with Google account")
    print("3. Click 'Create API key'")
    print("4. Copy the key")
    print("")
    print("-" * 40)
    print("")
    
    try:
        api_key = input("Paste your API key (or Q to quit): ").strip()
        
        if api_key.upper() == 'Q':
            print("\nExiting...")
            return None
        
        if not api_key or len(api_key) < 20:
            print("\nInvalid API key. Must be at least")
            print("20 characters.")
            return None
        
        if save_config(api_key):
            print("\nAPI key saved successfully!")
            return api_key
        else:
            print("\nError saving config file.")
            return None
            
    except (EOFError, KeyboardInterrupt):
        print("\n\nExiting...")
        return None


def lookup_operator_name(callsign):
    """Try to get operator name from HamDB or QRZ"""
    base_call = extract_base_call(callsign)
    
    # Try HamDB first (no API key required)
    try:
        url = "https://api.hamdb.org/v1/{}/json/bpq-apps".format(base_call)
        req = Request(url, headers={"User-Agent": "BPQ-Gemini/1.0"})
        response = urlopen(req, timeout=3)
        data = json.loads(response.read().decode('utf-8'))
        
        if data.get('hamdb', {}).get('callsign', {}).get('call') == base_call:
            fname = data['hamdb']['callsign'].get('fname', '')
            if fname:
                return fname
    except Exception:
        pass
    
    # Try QRZ if config exists
    try:
        qrz_config_path = os.path.join(os.path.dirname(__file__), "config.py")
        if os.path.exists(qrz_config_path):
            # Import QRZ credentials
            sys.path.insert(0, os.path.dirname(__file__))
            import config as cfg
            
            if cfg.qrz_user and cfg.qrz_pass:
                # QRZ session login
                login_url = "http://xmldata.qrz.com/xml/current/?" + urlencode({
                    'username': cfg.qrz_user,
                    'password': cfg.qrz_pass
                })
                response = urlopen(login_url, timeout=3)
                xml_data = response.read().decode('utf-8')
                
                # Extract session key
                key_match = re.search(r'<Key>([^<]+)</Key>', xml_data)
                if key_match:
                    session_key = key_match.group(1)
                    
                    # Query callsign
                    query_url = "http://xmldata.qrz.com/xml/current/?" + urlencode({
                        's': session_key,
                        'callsign': base_call
                    })
                    response = urlopen(query_url, timeout=3)
                    xml_data = response.read().decode('utf-8')
                    
                    # Extract first name
                    fname_match = re.search(r'<fname>([^<]+)</fname>', xml_data)
                    if fname_match:
                        return fname_match.group(1)
    except Exception:
        pass
    
    return None


def call_gemini_api(api_key, prompt, conversation_history, operator_name=None, callsign=None):
    """Call Gemini API with ham radio context"""
    try:
        # Build system prompt with ham radio context
        system_context = """You are a helpful AI assistant for amateur radio operators. Keep responses brief (2-3 sentences max) due to 1200 baud packet radio bandwidth constraints. Use ASCII text only - no Unicode or special characters.

Ham Radio Ten Commandments (guide your tone and advice):
{}

Sign off friendly with amateur radio expressions like:
- 73 (best regards)
- 88 (love and kisses - for YLs/OMs)
- Good DX!
- See you down the log!
- Stay QRV! (stay active)
- Keep the shack warm!
""".format(HAM_COMMANDMENTS)

        if operator_name:
            system_context += "\nOperator's name: {}\n".format(operator_name)
        if callsign:
            system_context += "Operator's callsign: {}\n".format(callsign)
        
        # Build conversation payload
        contents = []
        
        # Add conversation history
        for msg in conversation_history:
            contents.append({
                "role": msg["role"],
                "parts": [{"text": msg["text"]}]
            })
        
        # Add current user prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        # Build request
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={}".format(api_key)
        
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_context}]
            },
            "generationConfig": {
                "maxOutputTokens": 256,  # Keep responses short
                "temperature": 0.7
            }
        }
        
        payload_json = json.dumps(payload).encode('utf-8')
        
        req = Request(
            url,
            data=payload_json,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "BPQ-Gemini/1.0"
            }
        )
        
        response = urlopen(req, timeout=10)
        result = json.loads(response.read().decode('utf-8'))
        
        # Extract response text
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                text = candidate['content']['parts'][0].get('text', '').strip()
                return text, None
        
        return None, "No response from AI"
        
    except HTTPError as e:
        if e.code == 400:
            return None, "Invalid API key or request"
        elif e.code == 429:
            return None, "Rate limit exceeded. Try again later."
        else:
            return None, "HTTP error: {}".format(e.code)
    except URLError:
        return None, "Network error. Check internet connection."
    except Exception as e:
        return None, "Error: {}".format(str(e))


def wrap_text(text, width=40):
    """Wrap text to fit terminal width"""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_len = len(word)
        if current_length + word_len + len(current_line) <= width:
            current_line.append(word)
            current_length += word_len
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_len
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)


def run_chat_session(api_key, operator_name=None, callsign=None):
    """Run interactive chat session"""
    conversation_history = []
    
    # Initial greeting
    if operator_name:
        greeting = "Hello, {}! I'm your AI assistant for amateur radio. Ask me anything about ham radio, operating practices, equipment, or propagation. Type Q to quit.".format(operator_name)
    else:
        greeting = "Hello! I'm your AI assistant for amateur radio. Ask me anything about ham radio, operating practices, equipment, or propagation. Type Q to quit."
    
    print("-" * 40)
    print(wrap_text(greeting))
    print("-" * 40)
    print("")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.upper() in ['Q', 'QUIT', 'EXIT', 'BYE']:
                print("\n73! See you down the log!")
                break
            
            # Show thinking indicator (stays on one line)
            sys.stdout.write("AI: [thinking...]\r")
            sys.stdout.flush()
            
            # Call API
            response, error = call_gemini_api(
                api_key, 
                user_input, 
                conversation_history,
                operator_name=operator_name,
                callsign=callsign
            )
            
            # Clear thinking indicator
            sys.stdout.write(" " * 40 + "\r")
            sys.stdout.flush()
            
            if error:
                print("AI: {}".format(error))
                if "API key" in error or "Rate limit" in error:
                    print("\nExiting due to API error...")
                    break
            elif response:
                # Add to conversation history
                conversation_history.append({
                    "role": "user",
                    "text": user_input
                })
                conversation_history.append({
                    "role": "model",
                    "text": response
                })
                
                # Keep conversation history manageable (last 10 exchanges)
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                
                # Display response
                print("AI: {}".format(wrap_text(response)))
            
            print("")
            
        except (EOFError, KeyboardInterrupt):
            print("\n\n73! See you down the log!")
            break


def show_help():
    """Display help information"""
    help_text = """NAME
    gemini.py - AI chat assistant for ham radio

SYNOPSIS
    gemini.py [OPTIONS]

VERSION
    {}

DESCRIPTION
    Interactive AI chat powered by Google Gemini.
    Designed for packet radio with ham-focused
    context and bandwidth-efficient responses.

OPTIONS
    -h, --help, /?
        Display this help message

    --config
        Force config setup (API key)

FEATURES
    - Personalized greetings using callsign lookup
    - Ham radio context and etiquette awareness
    - Brief responses for 1200 baud efficiency
    - Conversational memory within session
    - Offline detection with graceful errors

API KEY
    Get free API key at:
    https://aistudio.google.com/apikey

    Stored in: {}

EXAMPLES
    gemini.py
        Start interactive chat session

SEE ALSO
    qrz3.py - Callsign lookup
    hamtest.py - License exam practice
""".format(VERSION, CONFIG_FILE)
    print(help_text)


def main():
    """Main application entry point"""
    # Check for updates
    check_for_app_update(VERSION, "gemini.py")
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['-h', '--help', '/?']:
            show_help()
            return
        elif arg == '--config':
            api_key = prompt_for_api_key()
            if api_key:
                print("\nConfig saved. Run app again to chat.")
            return
    
    # Show logo
    show_logo()
    print("")
    print("GEMINI AI CHAT v{}".format(VERSION))
    print("AI Assistant for Ham Radio Operators")
    print("")
    print("-" * 40)
    print("")
    
    # Check internet connectivity
    if not is_internet_available():
        print("Internet appears to be unavailable.")
        print("This app requires internet to function.")
        print("Try again later.")
        print("\nExiting...")
        return
    
    # Load or prompt for API key
    api_key = load_config()
    if not api_key:
        api_key = prompt_for_api_key()
        if not api_key:
            return
        print("")
    
    # Try to get callsign from stdin (BPQ sends it if no NOCALL flag)
    callsign = None
    operator_name = None
    
    # Check if stdin has data (non-interactive mode from BPQ)
    if not sys.stdin.isatty():
        try:
            first_line = sys.stdin.readline().strip()
            if first_line and re.match(r'^[A-Z]{1,2}\d[A-Z]{1,3}(-\d{1,2})?$', first_line):
                callsign = first_line
                # Lookup operator name
                operator_name = lookup_operator_name(callsign)
        except Exception:
            pass
    
    # Run chat session
    run_chat_session(api_key, operator_name=operator_name, callsign=callsign)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
