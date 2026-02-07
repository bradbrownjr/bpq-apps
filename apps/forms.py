#!/usr/bin/env python3
"""
Fillable Forms Application for Packet Radio
--------------------------------------------
A text-based forms system for BPQ32 packet radio nodes.
Users can select and fill out forms which are then exported
as BPQ-importable messages.

Features:
- Auto-discovery and download of form templates from GitHub
- Multiple field types: text (single-line), textarea (/EX terminated), yes/no/na, numeric choice
- Required and optional field validation
- BPQ message format export for auto-import
- FLMSG-compatible plaintext output
- Press Q to quit at any time

Field Types:
- text: Single-line input (press Enter to finish)
- textarea: Multi-line input (type /EX on new line to finish)
- yesno: Yes/No/NA response
- choice: Numbered list of options
- strip: Slash-separated MARS/SHARES format

Author: Brad Brown KC1JMH
Version: 1.13
Date: January 2026
"""

import sys

# Check Python version
if sys.version_info < (3, 5):
    print("Error: This script requires Python 3.5 or later.")
    print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ))
    print("\nPlease run with: python3 forms.py")
    sys.exit(1)

VERSION = "1.13"
APP_NAME = "forms.py"

import os
import json
from datetime import datetime
import textwrap
import select
import urllib.request
import urllib.error

def extract_base_call(callsign):
    """Remove SSID from callsign (e.g., KC1JMH-8 -> KC1JMH)"""
    if not callsign:
        return ""
    return callsign.split('-')[0] if callsign else ""

# Configuration
# -------------
FORMS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forms")
EXPORT_FILE = "../linbpq/infile"  # Single file for all messages (BPQ import format)
GITHUB_FORMS_URL = "https://api.github.com/repos/bradbrownjr/bpq-apps/contents/apps/forms"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/forms"

def get_line_width():
    """Get terminal width from COLUMNS env var, default to 80"""
    try:
        if 'COLUMNS' in os.environ:
            width = int(os.environ['COLUMNS'])
            if width > 0:
                return width
    except (ValueError, KeyError, TypeError):
        pass
    return 80  # Default width for packet radio terminals

LINE_WIDTH = get_line_width()  # Dynamic terminal width

class FormsApp:
    """Main forms application class"""
    
    def __init__(self):
        self.forms = []
        self.user_call = ""
        self.version = VERSION
        self.bpq_callsign = None  # Callsign passed from BPQ
        
    def clear_screen(self):
        """Clear screen for better readability (optional, works in most terminals)"""
        # For packet radio, we'll just print a newline instead
        print()
    
    def print_header(self):
        """Print application header"""
        print(r"  __                          ")
        print(r" / _| ___  _ __ _ __ ___  ___ ")
        print(r"| |_ / _ \| '__| '_ ` _ \/ __|")
        print("|  _| (_) | |  | | | | | \\__ \\")
        print(r"|_|  \___/|_|  |_| |_| |_|___/")
        print()
        print("FORMS v{} - Fillable Forms System".format(self.version))
        print()
    
    def print_separator(self):
        """Print a separator line"""
        print("-" * 40)
    
    def wrap_text(self, text, width=LINE_WIDTH):
        """Wrap text to specified width"""
        return textwrap.fill(text, width=width)
    
    def get_input(self, prompt):
        """Get user input with quit/back check"""
        try:
            user_input = input(prompt).strip()
            if user_input.upper() == 'Q':
                print("\nQuitting...")
                sys.exit(0)
            elif user_input.upper() == 'B':
                # Return special marker for back-to-menu
                return '__BACK__'
            return user_input
        except (EOFError, KeyboardInterrupt):
            print("\n\nQuitting...")
            sys.exit(0)
    
    def check_for_app_update(self):
        """Check if forms.py has an update available on GitHub"""
        try:
            # Get the version from GitHub's forms.py (silent check)
            github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/forms.py"
            with urllib.request.urlopen(github_url, timeout=10) as response:
                content = response.read().decode('utf-8')
            
            # Extract version from docstring
            import re
            version_match = re.search(r'Version:\s*([0-9.]+)', content)
            if version_match:
                github_version = version_match.group(1)
                local_version = self.version
                
                if self.compare_versions(github_version, local_version) > 0:
                    print("\nUpdate available: v{} -> v{}".format(local_version, github_version))
                    print("Downloading new version...")
                    
                    # Download the new version
                    script_path = os.path.abspath(__file__)
                    try:
                        # Get current file permissions
                        import stat
                        current_stat = os.stat(script_path)
                        current_mode = current_stat.st_mode
                        
                        # Write to temporary file first, then replace
                        temp_path = script_path + '.tmp'
                        with open(temp_path, 'wb') as f:
                            f.write(content.encode('utf-8'))
                        
                        # Ensure file is executable (Python script should be executable)
                        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                        
                        # Replace old file with new one
                        os.replace(temp_path, script_path)
                        
                        print("Updated to v{}. Restarting...".format(github_version))
                        print()
                        sys.stdout.flush()
                        restart_args = [script_path] + sys.argv[1:]
                        os.execv(script_path, restart_args)
                    except Exception as e:
                        print("\nError installing update: {}".format(e))
                        # Clean up temp file if it exists
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except:
                                pass
        except Exception as e:
            # Don't block startup if update check fails
            pass
    
    def load_forms(self):
        """Load form templates from forms directory, downloading from GitHub if needed"""
        # Create forms directory if it doesn't exist
        if not os.path.exists(FORMS_DIR):
            print("Forms directory not found. Creating: {}".format(FORMS_DIR))
            try:
                os.makedirs(FORMS_DIR)
            except Exception as e:
                print("Error creating forms directory: {}".format(e))
                return False
        
        # Check GitHub for available forms
        github_forms = self.get_github_forms()
        
        # Load existing forms and check for updates
        self.forms = []
        local_form_versions = {}  # Track local versions for update checking
        
        for filename in sorted(os.listdir(FORMS_DIR)):
            if filename.endswith('.frm'):
                filepath = os.path.join(FORMS_DIR, filename)
                try:
                    with open(filepath, 'r') as f:
                        form_data = json.load(f)
                        form_data['filename'] = filename
                        self.forms.append(form_data)
                        local_form_versions[filename] = form_data.get('version', '0.0')
                except Exception as e:
                    print("Warning: Could not load {}: {}".format(filename, str(e)))
        
        # Download any missing forms from GitHub, or update existing ones if version is newer
        if github_forms:
            existing_files = set(f['filename'] for f in self.forms)
            for github_form in github_forms:
                should_download = False
                is_new_form = False
                
                if github_form not in existing_files:
                    # New form - download it silently
                    should_download = True
                    is_new_form = True
                else:
                    # Existing form - check if GitHub version is newer
                    github_version = self.get_github_form_version(github_form)
                    if github_version:
                        local_version = local_form_versions.get(github_form, '0.0')
                        if self.compare_versions(github_version, local_version) > 0:
                            should_download = True
                
                if should_download:
                    if self.download_form(github_form):
                        # Load the newly downloaded form
                        filepath = os.path.join(FORMS_DIR, github_form)
                        try:
                            with open(filepath, 'r') as f:
                                form_data = json.load(f)
                                form_data['filename'] = github_form
                                # Mark as new or updated (in-memory only, not persisted)
                                if is_new_form:
                                    form_data['_status'] = 'NEW'
                                else:
                                    form_data['_status'] = 'UPDATED'
                                # Update or add to forms list
                                if github_form in existing_files:
                                    # Replace existing form in list
                                    for i, form in enumerate(self.forms):
                                        if form['filename'] == github_form:
                                            self.forms[i] = form_data
                                            break
                                else:
                                    # Add new form to list
                                    self.forms.append(form_data)
                        except Exception as e:
                            print("Warning: Could not load downloaded {}: {}".format(github_form, str(e)))
        
        if not self.forms:
            print("Error: No form templates found.")
            print("Please check your internet connection or manually download forms from:")
            print("https://github.com/bradbrownjr/bpq-apps/tree/main/apps/forms")
            return False
        
        return True
    
    def get_github_forms(self):
        """Get list of available form templates from GitHub repository (silent operation)"""
        try:
            with urllib.request.urlopen(GITHUB_FORMS_URL, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Extract .frm files
            forms = []
            for item in data:
                if item['type'] == 'file' and item['name'].endswith('.frm'):
                    forms.append(item['name'])
            
            return forms
            
        except Exception:
            # Silent on network errors - use local forms only
            return []
    
    def download_form(self, filename):
        """Download a form template from GitHub (silent on success)"""
        url = "{}/{}".format(GITHUB_RAW_URL, filename)
        local_path = os.path.join(FORMS_DIR, filename)
        
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            return True
            
        except Exception:
            # Silent on errors - form updates are not critical
            return False
    
    def get_github_form_version(self, filename):
        """Get the version number of a form from GitHub"""
        url = "{}/{}".format(GITHUB_RAW_URL, filename)
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            return data.get('version', '0.0')
            
        except Exception as e:
            print("Warning: Could not check version for {}: {}".format(filename, e))
            return None
    
    def compare_versions(self, version1, version2):
        """
        Compare two version strings (e.g., '1.0', '1.2', '2.0')
        Returns: 
            1 if version1 > version2
            0 if version1 == version2
           -1 if version1 < version2
        """
        try:
            # Split versions into parts and convert to integers
            parts1 = [int(x) for x in str(version1).split('.')]
            parts2 = [int(x) for x in str(version2).split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            # Compare each part
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            
            return 0
            
        except (ValueError, AttributeError):
            # If version comparison fails, assume they're equal
            return 0
    
    def display_menu(self):
        """Display the main menu of available forms"""
        self.clear_screen()
        self.print_header()
        print("Available Forms:")
        print()
        
        # Sort forms alphabetically by title for consistent menu ordering
        sorted_forms = sorted(self.forms, key=lambda f: f.get('title', 'Untitled Form').lower())
        
        for idx, form in enumerate(sorted_forms, 1):
            title = form.get('title', 'Untitled Form')
            # Add status indicator if form is new or just updated
            status = form.get('_status', '')
            if status:
                title = "{} - {}".format(title, status)
            # Show title only - descriptions visible when form is opened
            print("{}. {}".format(idx, title))
        
        self.print_separator()
        print("\nPress Q at any time to quit.")
        print()
    
    def get_user_callsign(self):
        """Get user's callsign from BPQ or prompt if not available"""
        # Check if BPQ passed a callsign via stdin
        if self.bpq_callsign:
            # BPQ may pass callsign with SSID, strip it for cleaner display
            self.user_call = extract_base_call(self.bpq_callsign)
            print("\nCallsign from BPQ: {}".format(self.user_call))
            return self.user_call
        
        # Otherwise, prompt for callsign
        print("\nPlease enter your callsign:")
        while True:
            callsign = self.get_input("Callsign: ").upper()
            if callsign:
                # Basic validation - just check it's not empty and reasonable length
                if len(callsign) >= 3 and len(callsign) <= 10:
                    self.user_call = callsign
                    return callsign
                else:
                    print("Invalid callsign. Please try again.")
            else:
                print("Callsign is required.")
    
    def fill_form(self, form):
        """Interactive form filling"""
        # Check if this is a strip-mode form
        if form.get('strip_mode', False):
            return self.fill_strip_form(form)
        
        self.clear_screen()
        self.print_header()
        print("Form: {}".format(form.get('title', 'Untitled')))
        print()
        desc = form.get('description', '')
        if desc:
            print(self.wrap_text(desc))
            print()
        self.print_separator()
        print()
        
        # Collect form data
        form_data = {
            'form_title': form.get('title', 'Untitled'),
            'form_id': form.get('id', 'UNKNOWN'),
            'form_version': form.get('version', '1.0'),
            'submitted_by': self.user_call,
            'submitted_date': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            'fields': []
        }
        
        fields = form.get('fields', [])
        for field in fields:
            field_name = field.get('name', 'Unnamed Field')
            field_type = field.get('type', 'text')
            field_label = field.get('label', field_name)
            required = field.get('required', False)
            description = field.get('description', '')
            
            print("\n{}{}".format(field_label, ' (REQUIRED)' if required else ''))
            if description:
                print(self.wrap_text(description, width=LINE_WIDTH-2))
            
            value = None
            
            if field_type == 'text':
                value = self.fill_text_field(field, required)
                if value is None:
                    return None  # User pressed B to back
            elif field_type == 'yesno':
                value = self.fill_yesno_field(field, required)
                if value is None:
                    return None  # User pressed B to back
            elif field_type == 'choice':
                value = self.fill_choice_field(field, required)
                if value is None:
                    return None  # User pressed B to back
                if value is None:
                    return None  # User pressed B to back
            elif field_type == 'textarea':
                value = self.fill_textarea_field(field, required)
                if value is None:
                    return None  # User pressed B to back
            else:
                print("Unknown field type: {}".format(field_type))
                value = ""
            
            form_data['fields'].append({
                'name': field_name,
                'label': field_label,
                'type': field_type,
                'value': value
            })
        
        return form_data
    
    def get_strip_input_from_user(self, form):
        """Get strip input from user (pasted text or multi-line entry)"""
        fields = form.get('fields', [])
        strip_field_type = 'textarea'  # default to textarea for backwards compatibility
        if fields and len(fields) > 0:
            strip_field_type = fields[0].get('type', 'textarea')
        
        if strip_field_type == 'text':
            # Single-line input
            print("\nPaste the Information Request Strip below:")
            strip_input = self.get_input("> ").strip()
        else:
            # Multi-line input (textarea)
            print("\nPaste the Information Request Strip below:")
            print("(Type END on a new line when finished)\n")
            
            strip_lines = []
            while True:
                line = self.get_input("")
                if line.upper() == 'END':
                    break
                strip_lines.append(line)
            
            strip_input = ' '.join(strip_lines).strip()
        
        return strip_input
    
    def fill_strip_form(self, form):
        """Handle strip-mode forms (slash-separated request/response)"""
        self.clear_screen()
        self.print_header()
        print("Form: {}".format(form.get('title', 'Untitled')))
        print()
        print(self.wrap_text(form.get('description', '')))
        print()
        self.print_separator()
        print()
        
        # Check if form has a built-in template
        template = form.get('template', None)
        strip_input = None
        
        if template:
            # Offer choice between template and custom strip
            print("This form has a standard template. Choose an option:")
            print("  1. Use standard template")
            print("  2. Paste custom strip")
            print()
            
            choice = self.get_input("Enter choice (1 or 2, B)ack, Q)uit): ").strip().upper()
            
            if choice == '1':
                # Use the template
                strip_input = template
            elif choice == '2':
                # Get custom strip from user
                strip_input = self.get_strip_input_from_user(form)
            elif choice == 'B':
                # Back to menu
                return None
            else:
                print("Invalid choice. Please enter 1, 2, B, or Q.")
                return self.fill_strip_form(form)
        else:
            # No template, just get input from user
            strip_input = self.get_strip_input_from_user(form)
        
        if not strip_input:
            return None
        
        # Remove trailing // if present
        if strip_input.endswith('//'):
            strip_input = strip_input[:-2]
        
        # Parse the strip
        fields = strip_input.split('/')
        
        if len(fields) < 2:
            print("\nError: Strip must have at least 2 fields (title and one data field)")
            print("Press Enter to return to menu...")
            self.get_input("")
            return None
        
        # First field is the strip title/name
        strip_title = fields[0].strip()
        strip_fields = [f.strip() for f in fields[1:] if f.strip()]
        
        print("\n")
        self.print_separator()
        print("\nParsed {} fields from strip: {}".format(len(strip_fields), strip_title))
        print()
        print("Now enter your response for each field:")
        print("(Leave blank if not applicable, type EXIT to cancel form)")
        print()
        self.print_separator()
        
        # Collect responses
        responses = []
        for idx, field_label in enumerate(strip_fields, 1):
            print("\n[{}/{}] {}".format(idx, len(strip_fields), field_label))
            response = self.get_input("> ").strip()
            # Check for EXIT command
            if response.upper() == 'EXIT':
                print("\nForm cancelled.")
                print("Press Enter to return to menu...")
                self.get_input("")
                return None
            # If empty, use three spaces as placeholder (MARS convention)
            if not response:
                response = "   "
            responses.append(response)
        
        # Build the response strip
        response_strip = strip_title + '/' + '/'.join(responses) + '//'
        
        # Create form data structure
        form_data = {
            'form_title': form.get('title', 'Untitled'),
            'form_id': form.get('id', 'UNKNOWN'),
            'form_version': form.get('version', '1.0'),
            'submitted_by': self.user_call,
            'submitted_date': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            'strip_title': strip_title,
            'strip_request': strip_input + '//',
            'strip_response': response_strip,
            'fields': []
        }
        
        # Store field/response pairs for display
        for field_label, response in zip(strip_fields, responses):
            form_data['fields'].append({
                'name': field_label,
                'label': field_label,
                'type': 'strip',
                'value': response
            })
        
        return form_data
    
    def fill_text_field(self, field, required):
        """Fill a single-line text field (press Enter to finish, B to back)"""
        max_length = field.get('max_length', 255)
        
        while True:
            value = self.get_input("> ")
            
            if value == '__BACK__':
                return None
            elif not value and not required:
                return ""
            elif not value and required:
                print("This field is required. Please enter a value.")
                print("(Or press B to go back, Q to quit)")
                continue
            elif len(value) > max_length:
                print("Input too long. Maximum {} characters.".format(max_length))
                continue
            else:
                return value
    
    def fill_textarea_field(self, field, required):
        """Fill a multi-line text field (terminated with /EX, B to back)"""
        print("(Enter text. Type /EX on a new line when finished, B on empty line to go back)")
        lines = []
        
        while True:
            line = self.get_input("")
            if line == '__BACK__':
                return None
            elif line.upper() == '/EX':
                break
            lines.append(line)
        
        text = '\n'.join(lines)
        
        if not text and required:
            print("This field is required.")
            return self.fill_textarea_field(field, required)
        
        return text
    
    def fill_yesno_field(self, field, required):
        """Fill a yes/no/na field (B to back)"""
        allow_na = field.get('allow_na', True)
        
        if allow_na:
            print("Enter Y (Yes), N (No), or NA (Not Applicable/Unknown)")
        else:
            print("Enter Y (Yes) or N (No)")
        
        while True:
            value = self.get_input("> ")
            
            if value == '__BACK__':
                return None
            
            value = value.upper()
            
            if not value and not required:
                return "NA" if allow_na else ""
            elif value in ['Y', 'YES']:
                return "YES"
            elif value in ['N', 'NO']:
                return "NO"
            elif value in ['NA', 'N/A', 'UNKNOWN'] and allow_na:
                return "NA"
            else:
                if allow_na:
                    print("Please enter Y, N, or NA.")
                else:
                    print("Please enter Y or N.")
    
    def fill_choice_field(self, field, required):
        """Fill a numeric choice field (B to back)"""
        choices = field.get('choices', [])
        
        if not choices:
            print("Error: No choices defined for this field.")
            return ""
        
        print("Available choices:")
        for idx, choice in enumerate(choices, 1):
            print("  {}. {}".format(idx, choice))
        
        while True:
            value = self.get_input("Enter number (1-{}): ".format(len(choices)))
            
            if value == '__BACK__':
                return None
            
            if not value and not required:
                return ""
            
            try:
                choice_num = int(value)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                else:
                    print("Please enter a number between 1 and {}.".format(len(choices)))
            except ValueError:
                print("Please enter a valid number.")
    
    def display_form_review(self, form_data):
        """Display a review/preview of the filled form"""
        self.clear_screen()
        self.print_header()
        print("FORM REVIEW")
        print()
        self.print_separator()
        print()
        
        # Check if this is a strip form
        if 'strip_response' in form_data:
            print("Strip Type: {}".format(form_data.get('strip_title', 'Unknown')))
            print()
            print("Request Strip:")
            print("  {}".format(form_data['strip_request']))
            print()
            print("Your Response Strip:")
            print("  {}".format(form_data['strip_response']))
            print()
            self.print_separator()
            print()
            print("Field-by-Field Review:")
            print()
            for field in form_data['fields']:
                label = field['label']
                value = field['value']
                # Highlight empty fields
                if value.strip() == '':
                    value = '(empty)'
                print("  {}: {}".format(label, value))
        else:
            # Standard form review
            print("Form: {}".format(form_data['form_title']))
            print("Form ID: {}".format(form_data['form_id']))
            print()
            self.print_separator()
            print()
            
            for field in form_data['fields']:
                label = field['label']
                value = field['value']
                field_type = field['type']
                
                if field_type == 'textarea':
                    print("{}:".format(label))
                    if value.strip():
                        for line in value.split('\n'):
                            print("  {}".format(line))
                    else:
                        print("  (empty)")
                    print()
                else:
                    if not value or value.strip() == '':
                        value = '(empty)'
                    print("{}: {}".format(label, value))
        
        print()
        self.print_separator()
        print("\nSubmitted by: {}".format(form_data['submitted_by']))
        print("Date: {}".format(form_data['submitted_date']))
        print()
        self.print_separator()
    
    def format_as_bpq_message(self, form_data, recipient):
        """Format the filled form as a BPQ-importable message"""
        lines = []
        
        # BPQ message header
        # SP for Private (default for callsigns), SB for Bulletin (ALL, WW, etc.)
        # Use SB only if recipient is a bulletin address
        bulletin_addresses = ['ALL', 'WW', 'ALLUS', 'INFO', 'SALE', 'WANTED', 'TECH', 'TEST']
        msg_type = "SB" if recipient.upper() in bulletin_addresses or '@WW' in recipient.upper() else "SP"
        lines.append("{} {} < {}".format(msg_type, recipient, self.user_call))
        
        # Check if this is a strip form
        if 'strip_response' in form_data:
            # Subject line for strip forms
            subject = "{} - {}".format(
                form_data.get('strip_title', 'Strip Response'),
                form_data['form_id']
            )
            lines.append(subject)
            lines.append("")
            
            # For strip forms, include both request and response
            lines.append("Request Strip:")
            lines.append(form_data['strip_request'])
            lines.append("")
            lines.append("Response Strip:")
            lines.append(form_data['strip_response'])
            lines.append("")
            lines.append("-" * 70)
            lines.append("")
            lines.append("Field Details:")
            lines.append("")
            
            # Show field by field breakdown
            for field in form_data['fields']:
                lines.append("{}: {}".format(field['label'], field['value']))
            
            lines.append("")
            lines.append("-" * 70)
            lines.append("Submitted by: {}".format(form_data['submitted_by']))
            lines.append("Submitted on: {}".format(form_data['submitted_date']))
            lines.append("")
            lines.append("/EX")
            
            return '\n'.join(lines)
        
        # Standard form format
        # Subject line
        subject = "{} - {}".format(
            form_data['form_id'],
            form_data['form_title']
        )
        lines.append(subject)
        
        # Message body
        lines.append("")
        lines.append("=" * 70)
        lines.append(form_data['form_title'])
        lines.append("Form ID: {}".format(form_data['form_id']))
        lines.append("Version: {}".format(form_data['form_version']))
        lines.append("=" * 70)
        lines.append("")
        lines.append("Submitted by: {}".format(form_data['submitted_by']))
        lines.append("Submitted on: {}".format(form_data['submitted_date']))
        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        
        # Form fields
        for field in form_data['fields']:
            label = field['label']
            value = field['value']
            field_type = field['type']
            
            if field_type == 'textarea':
                lines.append("{}:".format(label))
                for line in value.split('\n'):
                    lines.append("  {}".format(line))
                lines.append("")
            else:
                lines.append("{}: {}".format(label, value))
        
        lines.append("")
        lines.append("-" * 70)
        lines.append("End of form")
        lines.append("")
        
        # BPQ message terminator
        lines.append("/EX")
        
        return '\n'.join(lines)
    
    def save_message(self, message_text):
        """Append the message to the BPQ import file"""
        # Determine export file path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        export_filepath = os.path.join(script_dir, EXPORT_FILE)
        
        # Create directory if it doesn't exist
        export_dir = os.path.dirname(export_filepath)
        try:
            if export_dir and not os.path.exists(export_dir):
                os.makedirs(export_dir, exist_ok=True)
        except Exception as e:
            print("\nError: Could not create export directory: {}".format(str(e)))
            print("Attempting to save to current directory instead...")
            export_filepath = os.path.join(script_dir, "infile")
        
        # Check if file exists before appending (for debug info)
        file_existed = os.path.exists(export_filepath)
        file_size_before = os.path.getsize(export_filepath) if file_existed else 0
        
        try:
            # Append to the import file (BPQ will process and delete it)
            with open(export_filepath, 'a') as f:
                f.write(message_text)
                f.write('\n')  # Extra newline between messages
            
            file_size_after = os.path.getsize(export_filepath)
            
            print("\nForm queued successfully!")
            print("Message appended to: {}".format(export_filepath))
            if file_existed:
                print("File already contained {} bytes, now {} bytes".format(
                    file_size_before, file_size_after))
            else:
                print("New file created with {} bytes".format(file_size_after))
            print("BPQ will automatically import and deliver this message.")
            return True
        except Exception as e:
            print("\nError saving form: {}".format(str(e)))
            return False
    
    def run(self):
        """Main application loop"""
        self.clear_screen()
        
        # Check for application updates BEFORE loading templates
        # This prevents users from seeing "Loading..." then update prompt
        self.check_for_app_update()
        
        # Show loading message after update check
        print("Loading form templates...")
        sys.stdout.flush()
        
        # Load form templates
        if not self.load_forms():
            print("\nNo forms available. Exiting.")
            return
        
        print("Loaded {} form(s).".format(len(self.forms)))
        
        # Get user callsign
        self.get_user_callsign()
        
        # Main loop
        while True:
            # Display menu
            self.display_menu()
            
            # Get form selection
            selection = self.get_input("Select form number (or Q to quit): ")
            
            try:
                form_num = int(selection)
                # Sort forms alphabetically for consistent menu ordering
                sorted_forms = sorted(self.forms, key=lambda f: f.get('title', 'Untitled Form').lower())
                if 1 <= form_num <= len(sorted_forms):
                    selected_form = sorted_forms[form_num - 1]
                    
                    # Fill out the form
                    form_data = self.fill_form(selected_form)
                    
                    if form_data is None:
                        # Error during form fill, return to menu
                        continue
                    
                    # Ask if they want to review before submitting
                    print("\n")
                    self.print_separator()
                    print("\nForm completed!")
                    print()
                    review_choice = self.get_input("Review form before submitting? (Y/N): ")
                    
                    if review_choice.upper() in ['Y', 'YES']:
                        # Display form review/preview
                        self.display_form_review(form_data)
                    
                    # Ask if they want to submit or cancel
                    print()
                    submit_choice = self.get_input("Submit this form? (Y/N): ")
                    
                    if submit_choice.upper() not in ['Y', 'YES']:
                        print("\nForm cancelled. Returning to menu.")
                        self.get_input("\nPress Enter to continue...")
                        continue
                    
                    # Get recipient - always prompt user
                    print("\n")
                    self.print_separator()
                    print("\nPreparing to submit form...")
                    print()
                    print("Who should receive this form?")
                    print("(Enter a callsign or address)")
                    print()
                    
                    recipient = ""
                    while not recipient:
                        recipient = self.get_input("Send to: ").strip()
                        if not recipient:
                            print("Recipient is required.")
                    
                    # Format as BPQ message
                    message = self.format_as_bpq_message(form_data, recipient.upper())
                    
                    # Save to file
                    if self.save_message(message):
                        print("\nThe form has been submitted and will be imported")
                        print("into the BBS for delivery to {}.".format(recipient.upper()))
                    
                    # Ask if they want to fill another form
                    print()
                    another = self.get_input("\nFill another form? (Y/N): ")
                    if another.upper() not in ['Y', 'YES']:
                        print("\nThank you for using the Forms System!")
                        print("73!")
                        break
                else:
                    print("\nInvalid selection. Please try again.")
                    self.get_input("\nPress Enter to continue...")
                    
            except ValueError:
                print("\nInvalid input. Please enter a number.")
                self.get_input("\nPress Enter to continue...")

def main():
    """Main entry point"""
    app = FormsApp()
    
    # Try to capture callsign: CLI arg first, then env var, then stdin
    arg_call = ""
    for i in range(len(sys.argv) - 1):
        if sys.argv[i] == "--callsign":
            arg_call = sys.argv[i + 1].strip().upper()
            break
    
    if arg_call:
        app.bpq_callsign = arg_call
    else:
        env_call = os.environ.get("BPQ_CALLSIGN", "").strip()
        if env_call:
            app.bpq_callsign = env_call.upper()
        else:
            # Fall back to stdin pipe (direct BPQ launch)
            try:
                if not sys.stdin.isatty():
                    first_line = sys.stdin.readline().strip()
                    if first_line:
                        app.bpq_callsign = first_line.upper()
            except Exception:
                pass
    
    app.run()

if __name__ == "__main__":
    main()
