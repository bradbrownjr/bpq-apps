#!/usr/bin/env python3
"""
Fillable Forms Application for Packet Radio
--------------------------------------------
A text-based forms system for BPQ32 packet radio nodes.
Users can select and fill out forms which are then exported
as BPQ-importable messages.

Features:
- Auto-discovery of form templates from forms/ subdirectory
- Multiple field types: text, yes/no/na, numeric choice
- Required and optional field validation
- BPQ message format export for auto-import
- FLMSG-compatible plaintext output
- Press Q to quit at any time

Author: Brad Brown KC1JMH
Date: October 2025
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

import os
import json
from datetime import datetime
import textwrap
import select
import urllib.request
import urllib.error

# Configuration
# -------------
FORMS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forms")
EXPORT_FILE = "../linbpq/infile"  # Single file for all messages (BPQ import format)
LINE_WIDTH = 80  # Maximum line width for display
GITHUB_FORMS_URL = "https://api.github.com/repos/bradbrownjr/bpq-apps/contents/apps/forms"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/forms"

class FormsApp:
    """Main forms application class"""
    
    def __init__(self):
        self.forms = []
        self.user_call = ""
        self.version = "1.0"
        self.bpq_callsign = None  # Callsign passed from BPQ
        
    def clear_screen(self):
        """Clear screen for better readability (optional, works in most terminals)"""
        # For packet radio, we'll just print some newlines instead
        print("\n" * 2)
    
    def print_header(self):
        """Print application header"""
        print("=" * LINE_WIDTH)
        print("FILLABLE FORMS SYSTEM v{}".format(self.version).center(LINE_WIDTH))
        print("=" * LINE_WIDTH)
        print()
    
    def print_separator(self):
        """Print a separator line"""
        print("-" * LINE_WIDTH)
    
    def wrap_text(self, text, width=LINE_WIDTH):
        """Wrap text to specified width"""
        return textwrap.fill(text, width=width)
    
    def get_input(self, prompt):
        """Get user input with quit check"""
        try:
            user_input = input(prompt).strip()
            if user_input.upper() == 'Q':
                print("\nQuitting...")
                sys.exit(0)
            return user_input
        except (EOFError, KeyboardInterrupt):
            print("\n\nQuitting...")
            sys.exit(0)
    
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
        for filename in sorted(os.listdir(FORMS_DIR)):
            if filename.endswith('.frm'):
                filepath = os.path.join(FORMS_DIR, filename)
                try:
                    with open(filepath, 'r') as f:
                        form_data = json.load(f)
                        form_data['filename'] = filename
                        self.forms.append(form_data)
                except Exception as e:
                    print("Warning: Could not load {}: {}".format(filename, str(e)))
        
        # Download any missing forms from GitHub
        if github_forms:
            existing_files = set(f['filename'] for f in self.forms)
            for github_form in github_forms:
                if github_form not in existing_files:
                    print("Downloading new form: {}".format(github_form))
                    if self.download_form(github_form):
                        # Load the newly downloaded form
                        filepath = os.path.join(FORMS_DIR, github_form)
                        try:
                            with open(filepath, 'r') as f:
                                form_data = json.load(f)
                                form_data['filename'] = github_form
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
        """Get list of available form templates from GitHub repository"""
        try:
            print("Checking GitHub for available forms...")
            with urllib.request.urlopen(GITHUB_FORMS_URL, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Extract .frm files
            forms = []
            for item in data:
                if item['type'] == 'file' and item['name'].endswith('.frm'):
                    forms.append(item['name'])
            
            if forms:
                print("Found {} forms on GitHub".format(len(forms)))
            return forms
            
        except Exception as e:
            print("Note: Could not check GitHub repository: {}".format(e))
            print("Will use local forms only.")
            return []
    
    def download_form(self, filename):
        """Download a form template from GitHub"""
        url = "{}/{}".format(GITHUB_RAW_URL, filename)
        local_path = os.path.join(FORMS_DIR, filename)
        
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            print("Successfully downloaded {}".format(filename))
            return True
            
        except Exception as e:
            print("Error downloading {}: {}".format(filename, e))
            return False
    
    def display_menu(self):
        """Display the main menu of available forms"""
        self.clear_screen()
        self.print_header()
        print("Available Forms:")
        print()
        
        for idx, form in enumerate(self.forms, 1):
            print("{}. {}".format(idx, form.get('title', 'Untitled Form')))
            desc = form.get('description', '')
            if desc:
                print("   {}".format(self.wrap_text(desc, width=LINE_WIDTH-3)))
            print()
        
        self.print_separator()
        print("\nPress Q at any time to quit.")
        print()
    
    def get_user_callsign(self):
        """Get user's callsign from BPQ or prompt if not available"""
        # Check if BPQ passed a callsign via stdin
        if self.bpq_callsign:
            self.user_call = self.bpq_callsign
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
            'submitted_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
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
            elif field_type == 'yesno':
                value = self.fill_yesno_field(field, required)
            elif field_type == 'choice':
                value = self.fill_choice_field(field, required)
            elif field_type == 'textarea':
                value = self.fill_textarea_field(field, required)
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
        
        # Get the strip input
        print("\nPaste the Information Request Strip below:")
        print("(Type END on a new line when finished)\n")
        
        strip_lines = []
        while True:
            line = self.get_input("")
            if line.upper() == 'END':
                break
            strip_lines.append(line)
        
        strip_input = ' '.join(strip_lines).strip()
        
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
        print("(Leave blank if not applicable)")
        print()
        self.print_separator()
        
        # Collect responses
        responses = []
        for idx, field_label in enumerate(strip_fields, 1):
            print("\n[{}/{}] {}".format(idx, len(strip_fields), field_label))
            response = self.get_input("> ").strip()
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
            'submitted_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
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
        """Fill a text field"""
        max_length = field.get('max_length', 255)
        
        while True:
            value = self.get_input("> ")
            
            if not value and not required:
                return ""
            elif not value and required:
                print("This field is required. Please enter a value.")
                continue
            elif len(value) > max_length:
                print("Input too long. Maximum {} characters.".format(max_length))
                continue
            else:
                return value
    
    def fill_textarea_field(self, field, required):
        """Fill a multi-line text field"""
        print("(Enter text. Type END on a new line when finished)")
        lines = []
        
        while True:
            line = self.get_input("")
            if line.upper() == 'END':
                break
            lines.append(line)
        
        value = '\n'.join(lines)
        
        if not value.strip() and required:
            print("This field is required.")
            return self.fill_textarea_field(field, required)
        
        return value
    
    def fill_yesno_field(self, field, required):
        """Fill a yes/no/na field"""
        allow_na = field.get('allow_na', True)
        
        if allow_na:
            print("Enter Y (Yes), N (No), or NA (Not Applicable/Unknown)")
        else:
            print("Enter Y (Yes) or N (No)")
        
        while True:
            value = self.get_input("> ").upper()
            
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
        """Fill a numeric choice field"""
        choices = field.get('choices', [])
        
        if not choices:
            print("Error: No choices defined for this field.")
            return ""
        
        print("Available choices:")
        for idx, choice in enumerate(choices, 1):
            print("  {}. {}".format(idx, choice))
        
        while True:
            value = self.get_input("Enter number (1-{}): ".format(len(choices)))
            
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
        
        try:
            # Append to the import file (BPQ will process and delete it)
            with open(export_filepath, 'a') as f:
                f.write(message_text)
                f.write('\n')  # Extra newline between messages
            print("\nForm queued successfully!")
            print("Message appended to: {}".format(export_filepath))
            print("BPQ will automatically import and deliver this message.")
            return True
        except Exception as e:
            print("\nError saving form: {}".format(str(e)))
            return False
    
    def run(self):
        """Main application loop"""
        self.clear_screen()
        self.print_header()
        
        print("Welcome to the Fillable Forms System!")
        print()
        print("This application allows you to fill out forms that will be")
        print("automatically imported into the BPQ BBS for delivery.")
        print()
        print("Press Q at any time to quit.")
        print()
        self.print_separator()
        
        # Load form templates
        print("\nLoading form templates...")
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
                if 1 <= form_num <= len(self.forms):
                    selected_form = self.forms[form_num - 1]
                    
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
    
    # Try to capture callsign from BPQ (passed via stdin)
    # BPQ sends the callsign on first line when connecting
    try:
        # Check if stdin has data available (non-blocking check)
        if not sys.stdin.isatty():
            # Read first line which should contain the callsign
            first_line = sys.stdin.readline().strip()
            if first_line:
                app.bpq_callsign = first_line.upper()
    except Exception:
        # If we can't read from stdin, that's okay - we'll prompt later
        pass
    
    app.run()

if __name__ == "__main__":
    main()
