#!/usr/bin/env python3
"""
AI Chat Assistant for Amateur Radio Operators
Version: 1.16

Interactive AI chat using Google Gemini API.
Designed for BPQ32 packet radio with ham radio context and etiquette.

Usage:
    ai.py                      # Interactive chat session
    ai.py --help               # Show help

BPQ32 APPLICATION line:
    APPLICATION 7,AI,C 9 HOST # K,CALLSIGN,FLAGS

Note: Requires callsign (no NOCALL flag) for personalized greetings.

Author: Brad Brown Jr (KC1JMH)
Date: January 29, 2026
"""

import sys
import os
import json
import shutil
import socket
import re
import readline
from urllib.request import urlopen, Request, HTTPError, URLError
from urllib.parse import urlencode

VERSION = "1.16"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "ai.conf")

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
11. Never discuss politics or religion on the air.
"""


def show_logo():
    """Display ASCII art logo"""
    logo = r"""
       _ 
  __ _(_)
 / _` | |
| (_| | |
 \__,_|_|
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
                print("\nUpdate available: v{} -> v{}".format(current_version, remote_version))
                print("Downloading new version...")
                sys.stdout.flush()
                
                script_path = os.path.abspath(__file__)
                temp_path = script_path + ".tmp"
                try:
                    with open(temp_path, 'w') as f:
                        f.write(remote_content)
                    
                    # Preserve executable permission
                    if os.path.exists(script_path):
                        os.chmod(temp_path, os.stat(script_path).st_mode)
                    
                    os.replace(temp_path, script_path)
                    print("\nUpdate installed successfully!")
                    print("Please re-run this command to use the updated version.")
                    print("\nQuitting...")
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
    """Load config file with API keys and user preferences"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config_data):
    """Save config data to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception:
        return False


def prompt_for_api_key(provider, config):
    """Prompt user to enter and save API key for a provider"""
    print("-" * 40)
    if provider == 'gemini':
        print("GEMINI API KEY SETUP")
    else:
        print("OPENAI API KEY SETUP")
    print("-" * 40)
    print("")
    
    if provider == 'gemini':
        print("Get Google Gemini API key:")
        print("1. Create project:")
        print("   https://aistudio.google.com/projects")
        print("2. Create API key:")
        print("   https://aistudio.google.com/api-keys")
        print("3. Enable Generative Language API")
        print("4. Add billing (required for usage):")
        print("   https://console.cloud.google.com/")
        print("   billing/linkedaccount")
        print("   - Link card to your project")
    else:
        print("Get OpenAI API key:")
        print("1. Sign up at:")
        print("   https://platform.openai.com/signup")
        print("2. Create API key:")
        print("   https://platform.openai.com/api-keys")
        print("   - Choose 'Service account' (not You)")
        print("   - Name it (e.g., bpq-api)")
        print("3. Add credits (pay-as-you-go)")
        print("4. Set budget limit (recommended $10):")
        print("   https://platform.openai.com/")
        print("   settings/organization/limits")
    
    print("")
    print("-" * 40)
    print("")
    
    try:
        api_key = input("Paste API key (or Q to quit): ").strip()
        
        if api_key.upper() == 'Q':
            print("\nExiting...")
            return None
        
        if not api_key or len(api_key) < 20:
            print("\nInvalid API key.")
            return None
        
        key_field = 'gemini_api_key' if provider == 'gemini' else 'openai_api_key'
        config[key_field] = api_key
        
        if save_config(config):
            print("\nAPI key saved!")
            return api_key
        else:
            print("\nError saving config.")
            return None
            
    except (EOFError, KeyboardInterrupt):
        print("\n\nExiting...")
        return None


def get_ai_name(config):
    """Get AI name from config, default to Elmer"""
    return config.get('ai_name', 'Elmer')


def get_available_providers(config):
    """Return list of configured AI providers"""
    providers = []
    if config.get('gemini_api_key'):
        providers.append('gemini')
    if config.get('openai_api_key'):
        providers.append('openai')
    return providers


def get_user_preference(config, callsign):
    """Get user's last used provider"""
    if not callsign:
        return None
    prefs = config.get('user_preferences', {})
    user_pref = prefs.get(callsign, {})
    return user_pref.get('provider')


def save_user_preference(config, callsign, provider):
    """Save user's provider preference"""
    if not callsign:
        return
    
    if 'user_preferences' not in config:
        config['user_preferences'] = {}
    
    config['user_preferences'][callsign] = {
        'provider': provider,
        'last_used': '2026-01-29'
    }
    save_config(config)


def offer_provider_switch(config, current_provider, callsign):
    """Offer to switch providers on API error. Returns new provider or None to exit."""
    providers = get_available_providers(config)
    other_providers = [p for p in providers if p != current_provider]
    
    if not other_providers:
        return None
    
    print("")
    print("Switch to another provider?")
    for i, p in enumerate(other_providers, 1):
        model = "Gemini 2.5 Flash" if p == 'gemini' else "GPT-4o Mini"
        print("{}. {} ({})".format(i, p.upper(), model))
    print("Q. Quit")
    print("")
    
    try:
        choice = input("Select: ").strip().upper()
        if choice == 'Q' or not choice:
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(other_providers):
            new_provider = other_providers[idx]
            save_user_preference(config, callsign, new_provider)
            print("")
            print("Switching to {}...".format(new_provider.upper()))
            return new_provider
    except (ValueError, EOFError):
        pass
    return None


def select_provider(config, callsign, force_menu=False):
    """Let user select AI provider or use sysop default/user preference"""
    providers = get_available_providers(config)
    
    if not providers:
        return None
    
    if len(providers) == 1:
        return providers[0]
    
    # Don't show menu if forced (e.g., user typed 'switch')
    if not force_menu:
        # Check sysop default first
        default = config.get('default_provider')
        if default and default in providers:
            return default
        
        # Check user preference
        pref = get_user_preference(config, callsign)
        if pref and pref in providers:
            return pref
    
    # Show menu
    print("SELECT AI PROVIDER")
    for i, provider in enumerate(providers, 1):
        model = "Gemini 2.5 Flash" if provider == 'gemini' else "GPT-4o Mini"
        print("{}. {} ({})".format(i, provider.upper(), model))
    print("")
    
    try:
        choice = input("Select [1-{}]: ".format(len(providers))).strip()
        idx = int(choice) - 1
        if 0 <= idx < len(providers):
            selected = providers[idx]
            save_user_preference(config, callsign, selected)
            print("")
            return selected
    except (ValueError, EOFError, KeyboardInterrupt):
        # If input fails (EOF from piped stdin), default to first provider
        print("(defaulting to {})".format(providers[0].upper()))
        print("")
        pass
    
    # Default to first provider
    return providers[0]


def lookup_operator_name(callsign):
    """Try to get operator name from HamDB or QRZ"""
    base_call = extract_base_call(callsign)
    
    # Try HamDB first (no API key required)
    try:
        url = "https://api.hamdb.org/v1/{}/json/bpq-apps".format(base_call)
        req = Request(url, headers={"User-Agent": "BPQ-AI/1.2"})
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


def call_openai_api(api_key, prompt, conversation_history, operator_name=None, callsign=None):
    """Call OpenAI API with conversation context"""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        
        # Build system message
        system_msg = """You are Elmer, a knowledgeable AI assistant. Keep responses brief (2-3 sentences max) for 1200 baud packet radio. ASCII text only - no Unicode, emoji, or special chars.

When the user says goodbye or asks you to say goodbye, respond with ONLY ONE brief ham radio sign-off like: 73! or Good DX! or See you down the log! Nothing else.

You can answer general questions, but avoid politics, religion, and sexual content. Focus on being helpful and friendly."""
        
        # Build messages array
        messages = [{"role": "system", "content": system_msg}]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": "assistant" if msg["role"] == "model" else msg["role"],
                "content": msg["text"]
            })
        
        # Add current prompt (no prepending needed - system message is separate)
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.7
        }
        
        payload_json = json.dumps(payload).encode('utf-8')
        
        req = Request(
            url,
            data=payload_json,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(api_key),
                "User-Agent": "BPQ-AI/1.2"
            }
        )
        
        response = urlopen(req, timeout=30)
        result = json.loads(response.read().decode('utf-8'))
        
        # Extract response text
        if 'choices' in result and len(result['choices']) > 0:
            text = result['choices'][0]['message']['content'].strip()
            return text, None
        
        return None, "No response from AI"
        
    except HTTPError as e:
        if e.code == 401:
            return None, "Invalid API key"
        elif e.code == 429:
            return None, "Rate limit exceeded. Try again later."
        else:
            return None, "HTTP error: {}".format(e.code)
    except URLError:
        return None, "Network error. Check internet connection."
    except Exception as e:
        return None, "Error: {}".format(str(e))


def call_gemini_api(api_key, prompt, conversation_history, operator_name=None, callsign=None):
    """Call Gemini API with ham radio context"""
    try:
        # Build system prompt with ham radio context
        system_context = """You are Elmer, a knowledgeable AI assistant. Keep responses brief (2-3 sentences max) for 1200 baud packet radio. ASCII text only - no Unicode, emoji, or special chars.

When the user says goodbye or asks you to say goodbye, respond with ONLY ONE brief ham radio sign-off like: 73! or Good DX! or See you down the log! Nothing else.

You can answer general questions, but avoid politics, religion, and sexual content. Focus on being helpful and friendly."""

        if operator_name:
            system_context += " User: {}".format(operator_name)
        if callsign:
            system_context += " ({})".format(callsign)
        
        # Build conversation payload
        contents = []
        
        # Add conversation history
        for msg in conversation_history:
            contents.append({
                "role": msg["role"],
                "parts": [{"text": msg["text"]}]
            })
        
        # Add current user prompt (only prepend system context if no history)
        if len(conversation_history) == 0:
            full_prompt = system_context + "\n\n" + prompt
        else:
            full_prompt = prompt
        
        contents.append({
            "role": "user",
            "parts": [{"text": full_prompt}]
        })
        
        # Build request
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={}".format(api_key)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7
            }
        }
        
        payload_json = json.dumps(payload).encode('utf-8')
        
        req = Request(
            url,
            data=payload_json,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "BPQ-AI/1.2"
            }
        )
        
        response = urlopen(req, timeout=30)
        result = json.loads(response.read().decode('utf-8'))
        
        # Extract response text (handle multiple parts)
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                # Concatenate all text parts
                text_parts = []
                for part in candidate['content']['parts']:
                    if 'text' in part:
                        text_parts.append(part['text'])
                text = ''.join(text_parts).strip()
                if text:
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


def wrap_text(text, width=None):
    """Wrap text to fit terminal width"""
    if width is None:
        try:
            width = shutil.get_terminal_size(fallback=(80, 24)).columns
        except Exception:
            width = 80  # Fallback for piped/non-TTY
    
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


def run_chat_session(config, provider, callsign=None, operator_name=None):
    """Run interactive chat session"""
    ai_name = get_ai_name(config)
    conversation_history = []
    last_user_input = None
    
    # Main session loop - allows provider switching
    while True:
        api_key = config.get('gemini_api_key' if provider == 'gemini' else 'openai_api_key')
        call_api = call_gemini_api if provider == 'gemini' else call_openai_api
        model_name = "Gemini 2.5 Flash" if provider == 'gemini' else "GPT-4o Mini"
        is_first_message = len(conversation_history) == 0  # Only true if no history yet
        
        # Send initial greeting request to AI
        sys.stdout.write("Connecting...\r")
        sys.stdout.flush()
        
        # Build system context for first message
        system_context = """You are {}, an AI ham radio mentor. Brief responses (2-3 sentences) for 1200 baud packet radio. ASCII only - no Unicode/emoji/special chars.

Ham principles: Assist others, be courteous, use minimum power, operate legally, promote amateur radio, help in emergencies, improve skills, respect frequencies, share knowledge.

Greeting: Hi!/Hello!/Howdy! Introduce yourself as {}.
Goodbye: Use ham sign-offs (73!, Good DX!, See you down the log!, Keep the shack warm!). Never "bye"/"goodbye".
""".format(ai_name, ai_name)
        
        if operator_name:
            system_context += "Operator: {} {}".format(operator_name, callsign if callsign else "")
        elif callsign:
            system_context += "Callsign: {}".format(callsign)
        
        greeting_prompt = system_context + "\n\nGreet the operator. Keep it brief and friendly."
        
        greeting, error = call_api(api_key, greeting_prompt, [], operator_name=operator_name, callsign=callsign)
        
        sys.stdout.write(" " * 40 + "\r")
        sys.stdout.flush()
        
        if error:
            print("AI: {}".format(error))
            if "API key" in error or "Rate limit" in error:
                new_provider = offer_provider_switch(config, provider, callsign)
                if new_provider:
                    provider = new_provider
                    continue  # Restart outer loop with new provider
                print("\nExiting...")
                return
            print("")
        elif greeting:
            print("AI: {}".format(greeting))
            print("")
            # Don't add greeting to history - let conversation start fresh
        
        # Inner chat loop
        provider_switched = False
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                print("")
                
                # Handle special commands without calling AI
                if user_input.lower() == 'switch':
                    print("")
                    # Show provider menu
                    providers = get_available_providers(config)
                    if len(providers) < 2:
                        print("Only one provider configured.")
                        print("")
                        continue
                    
                    print("SELECT AI PROVIDER")
                    for i, p in enumerate(providers, 1):
                        model = "Gemini 2.5 Flash" if p == 'gemini' else "GPT-4o Mini"
                        current = " (current)" if p == provider else ""
                        print("{}. {} ({}){}".format(i, p.upper(), model, current))
                    print("")
                    
                    try:
                        choice = input("Select [1-{}]: ".format(len(providers))).strip()
                        idx = int(choice) - 1
                        if 0 <= idx < len(providers):
                            new_provider = providers[idx]
                            if new_provider != provider:
                                save_user_preference(config, callsign, new_provider)
                                print("")
                                print("Switched to {}".format(new_provider.upper()))
                                print("(Conversation history preserved)")
                                print("")
                                provider = new_provider
                                provider_switched = True
                                break  # Break inner loop to restart with new provider
                            else:
                                print("")
                                print("Already using {}".format(provider.upper()))
                                print("")
                        else:
                            print("")
                            print("Invalid selection")
                            print("")
                    except (ValueError, EOFError):
                        print("")
                        print("Cancelled")
                        print("")
                    continue
                
                # Repeat last prompt with new/same provider
                if user_input.lower() in ['repeat', 'again', 'retry']:
                    if not last_user_input:
                        print("")
                        print("No previous message to repeat")
                        print("")
                        continue
                    user_input = last_user_input
                    print("Repeating: {}".format(user_input))
                    print("")
                
                # Check for quit commands first
                if user_input.upper() in ['Q', 'QUIT', 'EXIT', 'BYE']:
                    # Send goodbye with minimal context (empty conversation to avoid confusion)
                    sys.stdout.write("AI: [thinking...]\r")
                    sys.stdout.flush()
                    response, error = call_api(api_key, "Respond with ONLY ONE ham radio sign-off phrase like '73!' or 'Good DX!' - nothing else.", [], operator_name=operator_name, callsign=callsign)
                    sys.stdout.write(" " * 40 + "\r")
                    sys.stdout.flush()
                    
                    if response:
                        print("AI: {}".format(response))
                    print("")
                    return  # Exit completely
                
                # Prepend system context to first message only
                message_to_send = user_input
                if is_first_message:
                    message_to_send = "Remember: Brief responses, ASCII only, ham-friendly tone.\n\nUser: " + user_input
                    is_first_message = False
                
                # Save for repeat command
                last_user_input = user_input
                
                # Show thinking indicator
                sys.stdout.write("AI: [thinking...]\r")
                sys.stdout.flush()
                
                # Call API
                response, error = call_api(
                    api_key, 
                    message_to_send, 
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
                        new_provider = offer_provider_switch(config, provider, callsign)
                        if new_provider:
                            provider = new_provider
                            provider_switched = True
                            break  # Restart outer loop with new provider
                        print("\nExiting...")
                        return
                elif response:
                    conversation_history.append({"role": "user", "text": user_input})
                    conversation_history.append({"role": "model", "text": response})
                    
                    if len(conversation_history) > 20:
                        conversation_history = conversation_history[-20:]
                    
                    print("AI: {}".format(response))
                
                print("")
                
            except (EOFError, KeyboardInterrupt):
                print("\n\nExiting...")
                return
        
        # If we get here via break (provider switch), continue outer loop
        if not provider_switched:
            return  # User quit normally


def show_help():
    """Display help information"""
    help_text = """NAME
    ai.py - AI chat assistant for ham radio

SYNOPSIS
    ai.py [OPTIONS]

VERSION
    {}

DESCRIPTION
    Interactive AI chat powered by Google Gemini
    or OpenAI. Designed for packet radio with
    ham-focused context and bandwidth-efficient
    responses.

OPTIONS
    -h, --help, /?
        Display this help message

    --config [gemini|openai]
        Configure API key for provider
        Default: gemini
    
    --set-name NAME
        Set AI assistant name (default: Elmer)
    
    --set-default [gemini|openai]
        Set default AI provider for all users

FEATURES
    - Multiple AI providers (Gemini, OpenAI)
    - Per-callsign provider preferences
    - Personalized greetings using callsign
    - Ham radio context and etiquette
    - Brief responses for 1200 baud
    - Conversational memory within session
    - Offline detection with graceful errors

API KEYS
    Gemini (free):
      https://aistudio.google.com/projects
    
    OpenAI (paid):
      https://platform.openai.com/api-keys

    Config stored in: {}
    
    Sysop can set default provider:
      "default_provider": "gemini" or "openai"
    Users can override with 'switch' command.

EXAMPLES
    ai.py
        Start chat session
    
    ai.py --config gemini
        Configure Gemini API key
    
    ai.py --config openai
        Configure OpenAI API key
    
    ai.py --set-name Hal
        Change AI name to Hal
    
    ai.py --set-default gemini
        Set Gemini as default for all users

SEE ALSO
    qrz3.py - Callsign lookup
    hamtest.py - License exam practice
""".format(VERSION, CONFIG_FILE)
    print(help_text)


def main():
    """Main application entry point"""
    # Check for updates
    check_for_app_update(VERSION, "ai.py")
    
    # Handle command line arguments FIRST, before reading stdin
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['-h', '--help', '/?']:
            show_help()
            return
        elif arg == '--config':
            provider = sys.argv[2].lower() if len(sys.argv) > 2 else 'gemini'
            if provider not in ['gemini', 'openai']:
                print("Invalid provider. Use: gemini or openai")
                return
            config = load_config()
            api_key = prompt_for_api_key(provider, config)
            if api_key:
                print("\nConfig saved. Run app again to chat.")
            return
        elif arg == '--set-name':
            if len(sys.argv) < 3:
                print("Usage: ai.py --set-name NAME")
                return
            name = sys.argv[2]
            config = load_config()
            config['ai_name'] = name
            if save_config(config):
                print("AI name set to: {}".format(name))
            else:
                print("Error saving config.")
            return
        elif arg == '--set-default':
            if len(sys.argv) < 3:
                print("Usage: ai.py --set-default [gemini|openai]")
                return
            provider = sys.argv[2].lower()
            if provider not in ['gemini', 'openai']:
                print("Invalid provider. Use: gemini or openai")
                return
            config = load_config()
            config['default_provider'] = provider
            if save_config(config):
                print("Default provider set to: {}".format(provider.upper()))
            else:
                print("Error saving config.")
            return
    
    # Load config first (needed for header display)
    config = load_config()
    
    # Show logo
    show_logo()
    print("")
    print("AI CHAT v{}" .format(VERSION))
    print("Powered by {}".format("Gemini/OpenAI" if len(get_available_providers(config)) > 1 else ("Gemini 2.5 Flash" if 'gemini_api_key' in config and config['gemini_api_key'] else "GPT-4o Mini")))
    print("AI Assistant for Ham Radio Operators")
    print("-" * 40)
    print("Say 'bye' or enter Q to quit")
    if len(get_available_providers(config)) > 1:
        print('Enter "switch" to change AI provider')
    print("-" * 40)
    print("")
    
    # Check internet connectivity
    if not is_internet_available():
        print("Internet appears to be unavailable.")
        print("This app requires internet to function.")
        print("Try again later.")
        print("\nExiting...")
        return
    
    # Check available providers
    providers = get_available_providers(config)
    if not providers:
        print("No AI providers configured.")
        print("")
        print("Configure at least one:")
        print("1. Gemini (free): --config gemini")
        print("2. OpenAI (paid): --config openai")
        print("")
        return
    
    # Try to get callsign - env var first (apps.py), then stdin (BPQ direct)
    callsign = None
    operator_name = None
    force_menu = False
    
    env_call = os.environ.get("BPQ_CALLSIGN", "").strip()
    if env_call and re.match(r'^[A-Z]{1,2}\d[A-Z]{1,3}(-\d{1,2})?$', env_call):
        callsign = env_call
        print("Callsign: {}".format(callsign))
        operator_name = lookup_operator_name(callsign)
    else:
        try:
            import select
            if select.select([sys.stdin], [], [], 0.1)[0]:
                first_line = input().strip()
                if first_line.lower() == 'switch':
                    force_menu = True
                elif first_line and re.match(r'^[A-Z]{1,2}\d[A-Z]{1,3}(-\d{1,2})?$', first_line):
                    callsign = first_line
                    print("Callsign: {}".format(callsign))
                    operator_name = lookup_operator_name(callsign)
        except Exception:
            pass
    
    # Select provider
    provider = select_provider(config, callsign, force_menu=force_menu)
    if not provider:
        return
    
    # Show which model is being used
    model_name = "Gemini 2.5 Flash" if provider == 'gemini' else "GPT-4o Mini"
    print("Using: {}".format(model_name))
    print("")
    
    # Run chat session
    run_chat_session(config, provider, callsign=callsign, operator_name=operator_name)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
