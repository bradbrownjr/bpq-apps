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
Version: 1.23
Date: May 2026
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

VERSION = "1.23"
APP_NAME = "forms.py"

import os
import re
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

# US state name/shorthand -> 2-letter USPS abbreviation
_STATE_ABBR = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
    # common shorthands
    'mass': 'MA', 'conn': 'CT', 'penn': 'PA', 'penna': 'PA',
    'wash': 'WA', 'tenn': 'TN', 'mich': 'MI', 'minn': 'MN',
}
_VALID_STATE_ABBRS = set(_STATE_ABBR.values())

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

    def _continue_prompt(self):
        """Show continue prompt with Q)uit escape option."""
        resp = self.get_input("\n[Q)uit Enter=continue] :> ")
        # Q handled by get_input
    
    def check_for_app_update(self):
        """Check if forms.py has an update available on GitHub"""
        try:
            # Get the version from GitHub's forms.py (silent check)
            github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/forms.py"
            with urllib.request.urlopen(github_url, timeout=10) as response:
                content = response.read().decode('utf-8')
            
            # Extract version from VERSION = "x.y" assignment
            import re
            version_match = re.search(r'^\s*VERSION\s*=\s*[\'"](\S+)[\'"]', content, re.MULTILINE)
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
        # Fetch the manifest once — one small request covers all version checks
        github_versions = self.get_github_manifest()

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
        
        # Update existing local forms where the manifest shows a newer version
        for filename, local_version in list(local_form_versions.items()):
            github_version = github_versions.get(filename)
            if github_version and self.compare_versions(github_version, local_version) > 0:
                if self.download_form(filename):
                    filepath = os.path.join(FORMS_DIR, filename)
                    try:
                        with open(filepath, 'r') as f:
                            form_data = json.load(f)
                            form_data['filename'] = filename
                            form_data['_status'] = 'UPDATED'
                            for i, form in enumerate(self.forms):
                                if form['filename'] == filename:
                                    self.forms[i] = form_data
                                    break
                    except Exception:
                        pass

        # Sync .json data files already present locally
        for fname in os.listdir(FORMS_DIR):
            if not fname.endswith('.json'):
                continue
            local_path = os.path.join(FORMS_DIR, fname)
            try:
                url = "{}/{}".format(GITHUB_RAW_URL, fname)
                with urllib.request.urlopen(url, timeout=10) as resp:
                    remote = resp.read()
                with open(local_path, 'rb') as f:
                    local = f.read()
                if remote.strip() != local.strip():
                    with open(local_path, 'wb') as f:
                        f.write(remote)
            except Exception:
                pass

        # Use GitHub listing API to discover and download brand-new forms/data files
        # Use manifest to discover brand-new forms not yet installed
        existing_files = set(f['filename'] for f in self.forms)
        local_data_files = set(os.listdir(FORMS_DIR))
        for github_form in github_versions.keys():
            if github_form.endswith('.json'):
                continue  # data files handled below
            if github_form not in existing_files:
                if self.download_form(github_form):
                    filepath = os.path.join(FORMS_DIR, github_form)
                    try:
                        with open(filepath, 'r') as f:
                            form_data = json.load(f)
                            form_data['filename'] = github_form
                            form_data['_status'] = 'NEW'
                            self.forms.append(form_data)
                    except Exception as e:
                        print("Warning: Could not load downloaded {}: {}".format(github_form, str(e)))

        # Sync .json data files listed in the manifest (download if missing or changed)
        for fname in github_versions.keys():
            if not fname.endswith('.json'):
                continue
            local_path = os.path.join(FORMS_DIR, fname)
            if fname not in local_data_files:
                self.download_form(fname)
            else:
                try:
                    url = "{}/{}".format(GITHUB_RAW_URL, fname)
                    with urllib.request.urlopen(url, timeout=10) as resp:
                        remote = resp.read()
                    with open(local_path, 'rb') as f:
                        local = f.read()
                    if remote.strip() != local.strip():
                        with open(local_path, 'wb') as f:
                            f.write(remote)
                except Exception:
                    pass

        if not self.forms:
            print("Error: No form templates found.")
            print("Please check your internet connection or manually download forms from:")
            print("https://github.com/bradbrownjr/bpq-apps/tree/main/apps/forms")
            return False
        
        return True
    
    def get_github_manifest(self):
        """Fetch manifest.json — one request returns all form versions (and data file names)"""
        url = "{}/manifest.json".format(GITHUB_RAW_URL)
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception:
            return {}

    def get_github_forms(self):
        """Get list of available form templates from GitHub repository (silent operation)"""
        try:
            with urllib.request.urlopen(GITHUB_FORMS_URL, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Extract .frm and .json data files
            forms = []
            for item in data:
                if item['type'] == 'file' and (item['name'].endswith('.frm') or item['name'].endswith('.json')):
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
        print()
        self.print_separator()
        print("Form: {}".format(form.get('title', 'Untitled')))
        self.print_separator()
        print()
        desc = form.get('description', '')
        if desc:
            print(self.wrap_text(desc))
            print()
        print("(Press Q at any field to quit, except message text fields)")
        print()
        
        # Collect form data
        form_data = {
            'form_title': form.get('title', 'Untitled'),
            'form_id': form.get('id', 'UNKNOWN'),
            'form_version': form.get('version', '1.0'),
            'output_format': form.get('format', 'standard'),
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

            # Pre-compute default values for special auto-fill fields
            if field.get('default_now'):
                field = dict(field)
                field['default'] = datetime.now().strftime(field['default_now'])
            elif field.get('auto_fill') == 'callsign' and self.user_call:
                field = dict(field)
                field['default'] = self.user_call
            
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
                if field.get('arl_enabled'):
                    value = self.fill_arl_or_textarea_field(field, required)
                else:
                    value = self.fill_textarea_field(field, required)
                if value is None:
                    return None  # User pressed B to back
                # NTS normalization: convert periods/decimals before word count
                if value and field.get('nts_normalize'):
                    normalized = self.normalize_nts_text(value)
                    if normalized != value.upper().strip():
                        print("NTS text (normalized):")
                        print(normalized)
                    wc = len(normalized.split())
                    print("Check (word count): {}".format(wc))
                    value = normalized
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
        print()
        self.print_separator()
        print("Form: {}".format(form.get('title', 'Untitled')))
        self.print_separator()
        print()
        print(self.wrap_text(form.get('description', '')))
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
            
            choice = self.get_input("Q)uit B)ack 1)Template 2)Custom :> ").strip().upper()
            
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
            resp = self.get_input("[Q)uit Enter=menu] :> ").strip().upper()
            if resp == "Q":
                print("\nExiting...")
                sys.exit(0)
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
                resp = self.get_input("[Q)uit Enter=menu] :> ").strip().upper()
                if resp == "Q":
                    print("\nExiting...")
                    sys.exit(0)
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

    def validate_field_value(self, field, value):
        """Validate a non-empty field value against the field's 'validate' rule.
        Returns None if valid, or an error string to display.
        """
        rule = field.get('validate')
        if not rule:
            return None

        if rule == 'nts_number':
            if not re.match(r'^\d{1,4}$', value):
                return "Message number must be 1-4 digits (e.g. 42)"

        elif rule == 'callsign':
            if not re.match(r'^[A-Z]{1,2}[0-9][A-Z]{1,3}(/[A-Z0-9]+)?$', value.upper()):
                return "Must be a valid callsign (e.g. KC1JMH, W1AW, VK3XYZ)"

        elif rule == 'city_state':
            parts = value.strip().replace(',', ' ').split()
            if len(parts) < 2:
                return "Enter city and state (e.g. PORTLAND ME)"
            if parts[-1].upper() not in _VALID_STATE_ABBRS:
                return "Last word must be a 2-letter state abbreviation (e.g. ME, NH, TX)"

        elif rule == 'us_zip':
            if not re.match(r'^\d{5}(-\d{4})?$', value):
                return "ZIP code must be 5 digits (e.g. 04543)"

        elif rule == 'phone':
            digits = re.sub(r'[^\d]', '', value)
            if len(digits) not in (7, 10, 11):
                return "Enter a valid phone number (e.g. 207-555-0100)"

        elif rule == 'email':
            if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
                return "Enter a valid email address (e.g. name@example.com)"

        elif rule == 'hhmm':
            if not re.match(r'^\d{4}$', value):
                return "Time must be 4 digits HHMM (e.g. 1430)"
            h, m = int(value[:2]), int(value[2:])
            if h > 23 or m > 59:
                return "Invalid time. Hours 00-23, minutes 00-59."

        elif rule == 'hx_code':
            for code in value.upper().split():
                if not re.match(r'^HX[A-G]\d*$', code):
                    return "HX code must be HXA-HXG with optional number (e.g. HXA100, HXB24)"

        return None

    def fill_text_field(self, field, required):
        """Fill a single-line text field (press Enter to finish, B to back)"""
        max_length = field.get('max_length', 255)
        default = field.get('default', '')

        if default:
            print("(Press Enter to accept: {})".format(default))
        if field.get('help'):
            print("(Type ? for help)")

        while True:
            value = self.get_input("> ")

            if value == '__BACK__':
                return None
            elif value == '?':
                help_lines = field.get('help', [])
                if help_lines:
                    print()
                    for line in help_lines:
                        print(line)
                    print()
                else:
                    print("No help available for this field.")
                continue
            elif not value and default:
                return default
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
                err = self.validate_field_value(field, value)
                if err:
                    print("Invalid: {}".format(err))
                    continue
                return value
    
    # ------------------------------------------------------------------
    # ARL Numbered Message helpers
    # ------------------------------------------------------------------

    def _load_arl_messages(self):
        """Load ARL numbered messages from arl_messages.json (cached after first load)"""
        if not hasattr(self, '_arl_messages_cache'):
            forms_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forms')
            arl_path = os.path.join(forms_dir, 'arl_messages.json')
            try:
                with open(arl_path, 'r') as f:
                    self._arl_messages_cache = json.load(f)
            except (IOError, ValueError) as e:
                print("Warning: Could not load ARL messages: {}".format(e))
                self._arl_messages_cache = []
        return self._arl_messages_cache

    def _print_arl_group(self, messages, group):
        """Print all ARL messages for a group as a numbered list"""
        label = "Emergency/Welfare" if group == "emergency" else "Routine"
        print("")
        print("--- ARL {} Messages ---".format(label))
        print("")
        for msg in messages:
            if msg['group'] != group:
                continue
            snippet = msg['text']
            if len(snippet) > 52:
                snippet = snippet[:49] + "..."
            print("  {:2d}. {:13s} - {}".format(msg['num'], msg['word'], snippet))
        print("")

    def _fill_arl_blanks(self, msg):
        """Show selected ARL message, prompt for each blank, return assembled ARL text."""
        print("")
        print("Selected: ARL {} (#{}):".format(msg['word'], msg['num']))
        print(self.wrap_text(msg['text'], width=72))
        print("")
        filled = []
        for prompt_label in msg.get('blanks', []):
            val = self.get_input("  {}: ".format(prompt_label))
            if val == '__BACK__':
                return None
            filled.append(val.strip())
        parts = ["ARL", msg['word']] + [v for v in filled if v]
        result = " ".join(parts)
        print("")
        print("Message text: {}".format(result))
        return result

    def fill_arl_or_textarea_field(self, field, required):
        """Textarea field with optional ARL canned message picker."""
        print("Press A to browse ARL templates, enter ARL number if known,")
        print("or press Enter to type your own message:")

        while True:
            choice = self.get_input("> ")
            if choice == '__BACK__':
                return None

            choice_stripped = choice.strip()

            # Empty Enter -> normal textarea
            if choice_stripped == '':
                return self.fill_textarea_field(field, required)

            # 'A' -> show group menu, then group list
            if choice_stripped.upper() == 'A':
                arl_msgs = self._load_arl_messages()
                if not arl_msgs:
                    print("ARL messages unavailable. Please type your message.")
                    return self.fill_textarea_field(field, required)

                print("")
                print("Select message group:")
                print("  1. Emergency/Welfare  (ARL 1-40)")
                print("  2. Routine            (ARL 46-94)")
                print("")

                group = None
                while group is None:
                    grp = self.get_input("Enter 1 or 2 (B=back): ")
                    if grp == '__BACK__':
                        break
                    if grp.strip() == '1':
                        group = 'emergency'
                    elif grp.strip() == '2':
                        group = 'routine'
                    else:
                        print("Please enter 1 or 2.")

                if group is None:
                    # User pressed B at group menu; re-show top prompt
                    print("")
                    print("Press A to browse ARL templates, enter ARL number if known,")
                    print("or press Enter to type your own message:")
                    continue

                self._print_arl_group(arl_msgs, group)

                while True:
                    num_input = self.get_input("Enter ARL number (B=back to groups): ")
                    if num_input == '__BACK__':
                        break  # back to group menu
                    try:
                        num = int(num_input.strip())
                        msg = next((m for m in arl_msgs if m['num'] == num and m['group'] == group), None)
                        if msg:
                            result = self._fill_arl_blanks(msg)
                            if result is None:
                                # Backed out during blank-filling; re-show group list
                                self._print_arl_group(arl_msgs, group)
                                continue
                            return result
                        else:
                            print("ARL {} not found in this group. Try again.".format(num))
                    except ValueError:
                        print("Please enter a valid number.")

                # Fell through back to group menu; loop back to top
                print("")
                print("Press A to browse ARL templates, enter ARL number if known,")
                print("or press Enter to type your own message:")
                continue

            # Direct number entry
            try:
                num = int(choice_stripped)
                arl_msgs = self._load_arl_messages()
                msg = next((m for m in arl_msgs if m['num'] == num), None)
                if msg:
                    result = self._fill_arl_blanks(msg)
                    if result is None:
                        print("")
                        print("Press A to browse ARL templates, enter ARL number if known,")
                        print("or press Enter to type your own message:")
                        continue
                    return result
                else:
                    print("ARL {} not found. Press A to browse, a number to select, or Enter for custom.".format(num))
            except ValueError:
                print("Enter A, a number (1-94), or press Enter for custom message.")

    # ------------------------------------------------------------------

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
    
    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def _resolve_state_abbr(self, user_input):
        """Return 2-letter state abbreviation from a name or abbreviation."""
        s = user_input.strip()
        # Try exact 2-letter abbreviation
        if s.upper() in _VALID_STATE_ABBRS:
            return s.upper()
        # Try full name or shorthand (case-insensitive)
        lower = s.lower()
        if lower in _STATE_ABBR:
            return _STATE_ABBR[lower]
        # Try prefix match (e.g. "new h" -> NH)
        matches = [abbr for name, abbr in _STATE_ABBR.items() if name.startswith(lower)]
        if len(matches) == 1:
            return matches[0]
        return None

    def _prompt_nts_routing(self, fv):
        """Ask for destination state and ZIP, return ST [ZIP] @ NTS[STATE] string."""
        suggested_state = fv.get('to_state', '').strip().upper()
        if not suggested_state:
            # Extract trailing state abbreviation from "City, State" field (e.g. "DAMARISCOTTA ME" -> "ME")
            city_state = fv.get('to_city_state', '').strip()
            parts = city_state.replace(',', ' ').split()
            if parts:
                suggested_state = parts[-1].upper()
        suggested_zip   = fv.get('to_zip',   '').strip()

        # State
        state_abbr = None
        while state_abbr is None:
            hint = ' [{}]'.format(suggested_state) if suggested_state else ''
            raw = self.get_input('Destination state (name or abbr){}: '.format(hint)).strip()
            if not raw and suggested_state:
                raw = suggested_state
            state_abbr = self._resolve_state_abbr(raw)
            if state_abbr:
                print('  -> {}'.format(state_abbr))
            else:
                print('  Unrecognized: "{}". Try the full name or 2-letter abbreviation.'.format(raw))

        # ZIP
        zip_code = None
        while zip_code is None:
            hint = ' [{}]'.format(suggested_zip) if suggested_zip else ''
            raw = self.get_input('Destination ZIP code{}: '.format(hint)).strip()
            if not raw and suggested_zip:
                raw = suggested_zip
            if raw.isdigit() and len(raw) == 5:
                zip_code = raw
            else:
                print('  ZIP code must be 5 digits.')

        routing = 'ST {} @ NTS{}'.format(zip_code, state_abbr)
        print('  Routing: {}'.format(routing))
        return routing

    def _prompt_bulletin_routing(self, fv):
        """Ask for bulletin topic and distribution, return SB TOPIC@DIST string."""
        COMMON_DISTS = ['USA', 'WW', 'NA', 'SA', 'EU', 'AF', 'AS', 'OC', 'PAC', 'CAR', 'CAN', 'ALLUS']

        # Pre-suggest from the form's To field (e.g. "PKTNET@USA" -> topic=PKTNET, dist=USA)
        form_to = fv.get('to', '').strip().upper()
        if '@' in form_to:
            suggested_topic = form_to.split('@')[0]
            suggested_dist  = form_to.split('@')[1]
        else:
            suggested_topic = form_to
            suggested_dist  = 'USA'

        hint = ' [{}]'.format(suggested_topic) if suggested_topic else ''
        topic = self.get_input('Bulletin topic (e.g. PKTNET, ARRL, WX){}: '.format(hint)).strip().upper()
        if not topic and suggested_topic:
            topic = suggested_topic

        print('Common distributions: {}'.format(', '.join(COMMON_DISTS)))
        hint = ' [{}]'.format(suggested_dist) if suggested_dist else ''
        dist = self.get_input('Distribution{}: '.format(hint)).strip().upper()
        if not dist and suggested_dist:
            dist = suggested_dist

        routing = 'SB {}@{}'.format(topic, dist)
        print('  Address: {}'.format(routing))
        return routing

    def prompt_routing(self, form_data):
        """Interactively build the BPQ routing line (SP/ST/SB + address)."""
        fv = {f['name']: f['value'] for f in form_data['fields']}

        print('Message type:')
        print('  1. Personal    (SP - to a callsign or BBS address)')
        print('  2. NTS Traffic (ST - enters NTS routing system)')
        print('  3. Bulletin    (SB - broadcast to a distribution)')
        print()

        while True:
            choice = self.get_input('Select type [1/2/3]: ').strip()

            if choice == '1':
                suggested = fv.get('to', '').strip().upper()
                # Only use form's To as a hint if it looks like a callsign/personal address
                if '@' in suggested and suggested.split('@')[-1] in _VALID_STATE_ABBRS:
                    suggested = ''  # Looks like NTS, don't suggest for personal
                hint = ' [{}]'.format(suggested) if suggested else ''
                addr = self.get_input('Callsign or BBS address{}: '.format(hint)).strip().upper()
                if not addr and suggested:
                    addr = suggested
                if addr:
                    return 'SP {}'.format(addr)
                print('Address is required.')

            elif choice == '2':
                return self._prompt_nts_routing(fv)

            elif choice == '3':
                return self._prompt_bulletin_routing(fv)

            else:
                print('Please enter 1, 2, or 3.')

    # ------------------------------------------------------------------
    # Body formatters
    # ------------------------------------------------------------------

    def format_pktnet_checkin(self, form_data):
        """Format body as PACKET CHECK-IN matching vden.org check_in.html output exactly"""
        fv = {f['name']: f['value'] for f in form_data['fields']}

        lines = []
        lines.append("PACKET CHECK-IN")
        lines.append("")

        agency = fv.get('agency', '').strip()
        if agency:
            lines.append(agency)
            lines.append("")

        lines.append("1. STATION")
        lines.append("")
        lines.append("a. Date/Time: {}".format(fv.get('datetime', '')))
        lines.append("")
        lines.append("b. To: {}".format(fv.get('to', '')))
        lines.append("")
        lines.append("c. From: {}    d. Station Contact Name: {}    e. Initial Operator(s): {}".format(
            fv.get('from_call', form_data.get('submitted_by', '')),
            fv.get('contact', ''),
            fv.get('operator', '')
        ))
        lines.append("")
        lines.append("")
        lines.append("2. SESSION")
        lines.append("")
        lines.append("a. Type: {}    b. Service: {}    c. Band: {}".format(
            fv.get('session_type', ''),
            fv.get('service_type', 'AMATEUR'),
            fv.get('band', '')
        ))
        lines.append("")
        lines.append("d. Session: {}".format(fv.get('mode', '')))
        lines.append("")
        lines.append("")
        lines.append("3. LOCATION")
        lines.append("")
        lines.append("a. Location: {}".format(fv.get('location', '')))
        lines.append("")
        lines.append("b. GRID SQUARE: {}".format(fv.get('gridsquare', '')))
        lines.append("")
        lines.append("")
        lines.append("4. COMMENTS: {}".format(fv.get('comments', '')))

        return '\n'.join(lines)

    def normalize_nts_text(self, text):
        """Apply NTS radiogram encoding rules to message text.
        - Trailing periods are dropped (NTS: never end message with X)
        - Decimal point between digits: 146.52 -> 146R52
        - All other periods: . -> X (word group separator)
        - Uppercase, collapsed whitespace
        """
        t = text.upper().strip()
        # Drop trailing periods before any conversion
        t = t.rstrip('. ')
        # Decimal point between digits -> R (e.g. 146.52 -> 146R52)
        t = re.sub(r'(\d)\.(\d)', r'\1R\2', t)
        # Remaining periods -> X word group
        t = re.sub(r'\s*\.\s*', ' X ', t)
        # Collapse multiple spaces
        t = re.sub(r' {2,}', ' ', t).strip()
        # Safety: strip trailing standalone X word (never end on X)
        words = t.split()
        while words and words[-1] == 'X':
            words.pop()
        return ' '.join(words)

    def format_nts_radiogram(self, form_data):
        """Format body as standard ARRL NTS radiogram preamble"""
        fv = {f['name']: f['value'] for f in form_data['fields']}

        # Precedence: extract just the letter from e.g. "R - Routine"
        prec = fv.get('precedence', 'R - Routine').split(' ')[0].upper()
        handling = fv.get('handling', '').strip().upper()
        origin = fv.get('station_of_origin', form_data.get('submitted_by', '')).upper()
        # Auto-compute check (word count of normalized message text)
        raw_text = fv.get('text', '')
        text = self.normalize_nts_text(raw_text)
        check = str(len(text.split()))
        place = fv.get('place_of_origin', '').upper()

        filed_time = fv.get('filed_time', '').strip()
        if not filed_time:
            filed_time = datetime.now().strftime('%H%M')
        filed_date = datetime.now().strftime('%b %d').upper()  # e.g. MAY 20

        preamble_parts = ['NR', fv.get('number', ''), prec]
        if handling:
            preamble_parts.append(handling)
        preamble_parts.extend([origin, check, place, filed_time, filed_date])
        preamble = ' '.join(p for p in preamble_parts if p)

        lines = []
        lines.append(preamble)
        lines.append("")

        lines.append("TO: {}".format(fv.get('to_name', '').upper()))
        to_address = fv.get('to_address', '').upper()
        if to_address:
            lines.append(to_address)
        to_cs = fv.get('to_city_state', '').upper()
        to_zip = fv.get('to_zip', '').strip()
        lines.append("{} {}".format(to_cs, to_zip).strip())
        to_phone = fv.get('to_phone', '').strip()
        if to_phone:
            lines.append(to_phone)
        to_email = fv.get('to_email', '').strip()
        if to_email:
            lines.append(to_email)
        lines.append("")

        for line in text.split('\n'):
            lines.append(line)
        lines.append("")

        lines.append(fv.get('signature', ''))

        return '\n'.join(lines)

    def format_as_bpq_message(self, form_data, routing):
        """Format the filled form as a BPQ-importable message.

        routing -- the full BPQ command string from prompt_routing(), e.g.
                   'SP KC1JMH', 'ST 04543 @ NTSME', 'SB PKTNET@USA'
        """
        lines = []
        lines.append("{} < {}".format(routing, self.user_call))

        output_format = form_data.get('output_format', 'standard')

        if output_format == 'pktnet_checkin':
            fv = {f['name']: f['value'] for f in form_data['fields']}
            subject = "{}, {}, {}".format(
                fv.get('contact', form_data.get('submitted_by', '')),
                fv.get('from_call', form_data.get('submitted_by', '')),
                fv.get('location', '')
            )
            lines.append(subject)
            lines.append("")
            lines.append(self.format_pktnet_checkin(form_data))
            lines.append("")
            lines.append("/EX")
            return '\n'.join(lines)

        if output_format == 'nts_radiogram':
            fv = {f['name']: f['value'] for f in form_data['fields']}
            # Subject: destination city/state ZIP (what NTS operators see in LT listing)
            subject = "{} {}".format(
                fv.get('to_city_state', '').upper(),
                fv.get('to_zip', '').strip()
            ).strip()
            lines.append(subject)
            lines.append("")
            lines.append(self.format_nts_radiogram(form_data))
            lines.append("")
            lines.append("/EX")
            return '\n'.join(lines)

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
        lines.append("Submitted by: {}".format(form_data['submitted_by']))
        lines.append("Date: {}".format(form_data['submitted_date']))
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
            selection = self.get_input("Q)uit or select [1-N] :> ")
            
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
                        self._continue_prompt()
                        continue
                    
                    # Routing
                    print("\n")
                    self.print_separator()
                    print("\nPreparing to submit form...")
                    print()

                    routing = self.prompt_routing(form_data)

                    # Format as BPQ message
                    message = self.format_as_bpq_message(form_data, routing)

                    # Save to file
                    if self.save_message(message):
                        print("\nThe form has been submitted and will be imported")
                        print("into the BBS for delivery via: {}".format(routing))
                    
                    # Ask if they want to fill another form
                    print()
                    another = self.get_input("\nFill another form? (Y/N): ")
                    if another.upper() not in ['Y', 'YES']:
                        print("\nThank you for using the Forms System!")
                        print("73!")
                        break
                else:
                    print("\nInvalid selection. Please try again.")
                    self._continue_prompt()
                    
            except ValueError:
                print("\nInvalid input. Please enter a number.")
                self._continue_prompt()

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
