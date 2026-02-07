#!/usr/bin/env python3
"""
QRZ Callsign Lookup for Packet Radio
------------------------------------
Query QRZ XML API for amateur radio operator information.

Version: 1.3
"""
VERSION = "1.3"
APP_NAME = "qrz3.py"

# Original script acquired from https://github.com/hink/qrzpy/blob/master/qrz3.py
# Script will try to install necessary module: beautifulsoup4 for XML parsing
from getpass import getpass
import signal
import sys 
import os
import requests
import config as cfg  # Enter variables into config.py!
import urllib.parse # Allow special characters in password
import warnings # Suppress "it looks like you're trying to parse HTML
warnings.filterwarnings("ignore")

# Install and load from pip: libxml and BeautifulSoup4
try:
  import lxml
except ImportError:
  print ("Trying to Install required module: lxml\n")
  os.system('python3 -m pip install lxml')
import lxml

try:
  from bs4 import BeautifulSoup as soup
except ImportError:
  print ("Trying to Install required module: BeautifulSoup4\n")
  os.system('python3 -m pip install BeautifulSoup4')
from bs4 import BeautifulSoup as soup

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
        import re
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

# Check for app updates
check_for_app_update(VERSION, APP_NAME)

# User variables
# --------------
# If it is preferred to prompt the user for their
# creds, remark the qrz_user and pass lines and 
# re-enable lines 207 and 208.
api_root = 'http://xmldata.qrz.com/xml/current/'
qrz_user = cfg.qrz_user
qrz_pass = urllib.parse.quote_plus(cfg.qrz_pass)
color_term = False # Set to false if using script on packet radio
if qrz_user == "":
    print("Please enter your QRZ API account credentials in config!")
    quit()
###


class Colors(object):
    if color_term == True:
        BLUE = '\033[1;36m'
        RED = '\033[1;31m'
        GREEN = '\033[1;32m'
        YELLOW = '\033[1;33m'
        END = '\033[0m'
    else:
        BLUE = '' 
        RED = ''
        GREEN = ''
        YELLOW = ''
        END = ''

def signal_handler(signal, frame):
    print('\n\nBye!\n')
    # Don't exit - let the app continue or the caller handle shutdown


def _error(msg, do_exit=False):
    print('{0}[ERROR]{1} {2}'.format(Colors.RED, Colors.END, msg))
    if do_exit:
        sys.exit(1)

def print_header():
    print("")
    print(r"  __ _ _ __ ____")
    print(r" / _` | '__|_  /")
    print(r"| (_| | |   / / ")
    print(r" \__, |_|  /___|")
    print(r"    |_|         ")
    print()
    print("QRZ v{} - Callsign Lookup Tool".format(VERSION))
    print("-" * 31)
    print("")

def login(username, password):
    # Login to QRZ - Must have access to XML API
    login_url = ('{0}?username={1};password={2};agent=qrzpy1.0'
        .format(api_root, username, password))

    # Send request
    try:
        res = requests.get(login_url)
    except requests.exceptions.Timeout:
        _error('Login request to QRZ.com timed out', True)

    # Check Response code
    if res.status_code != 200:
        _error('Invalid server response from QRZ.com', True)

    # Parse response and grab session key
    data = soup(res.content, 'lxml')
    if data.session.key:
        session_key = data.session.key.text
    else:
        if data.session.error:
            err = data.session.error.text
            _error('Could not login to QRZ.com - {0}'.format(err), True)
        else:
            _error('Unspecified error logging into QRZ.com', True)

    return session_key

def lookup_callsign(callsign, session_key):
    # Check for no callsign
    if not callsign:
        return

    search_url = ('{0}?s={1};callsign={2}'
        .format(api_root, session_key, callsign))

    # Send request
    try:
        res = requests.get(search_url)
    except requests.exceptions.Timeout:
        _error('Login request to QRZ.com timed out', True)

    # Check response code
    if res.status_code != 200:
        _error('Invalid server respnse from QRZ.com')
        return

    # Parse response and grab operator info
    data = soup(res.content, 'lxml')
    if not data.callsign:
        print('No data found on {0}'.format(callsign))
    else:
        display_callsign_info(data.callsign)

def display_callsign_info(data):
    # Put data in a dictionary for easy retrieval
    d = {}
    for v in data.find_all():
        d[v.name] = v.text

    print('--------------------')

    # Display Operator Info
    #  Call/Aliases
    aliases = d.get('aliases', '')
    # print(aliases) # Redundant, prints again below
    if aliases:
        aliases = ' ({0})'.format(aliases)
    print('{0}{1}{2}{3}'.format(Colors.GREEN, d['call'], Colors.END, aliases))

    #  Name
    name = '{0} {1}'.format(d.get('fname', ''), d.get('name', ''))
    dob = d.get('born', '')
    if dob:
        dob = ' ({0})'.format(dob)
    print('{0}{1}'.format(name, dob))

    #  Contact and License
    if d.get('email'):
        print(d.get('email'))
    if d.get('url'):
        print(d.get('url'))
    if d.get('class'):
        codes = d.get('codes', '')
        if codes:
            codes = ' ({0})'.format(codes)
        print('Class: {0}{1}'.format(d.get('class'), codes))

    # Address Info
    print('-----')
    if d.get('addr1'):
        print(d.get('addr1'))

    addr2 = d.get('addr2', '')
    state = d.get('state', '')
    zipcode = d.get('zip', '')
    county = d.get('county', '')
    if state and addr2:
        state = ', {0}'.format(state)
    if county:
        county = ' ({0} county)'.format(county)
    print('{0}{1} {2}{3}'.format(addr2, state, zipcode, county))
    print(d.get('country', 'Unknown country'))

    # Location and Zone Info
    print('-----')
    print('Grid Square: {0}'.format(d.get('grid', 'Unknown')))
    print(('DXCC: {0}  CQ Zone: {1}  ITU Zone: {2}'
        .format(d.get('dxcc', 'Unknown'), d.get('cqzone', 'Unknown'),
                d.get('ituzone', 'Unknown'))))
    print('Location Source: {0}'.format(d.get('geoloc')))

    # QSL Info
    print('-----')
    lotw = 'Yes' if d.get('lotw', 'N') == 'Y' else 'No'
    eqsl = 'Yes' if d.get('eqsl', 'N') == 'Y' else 'No'
    mail = 'Yes' if d.get('mqsl', 'N') == 'Y' else 'No'
    info = d.get('qslmgr')
    print('LoTW: {0}  eQSL: {1}  Mail: {2}'.format(lotw, eqsl, mail))
    if info and info != 'NONE':
        print('QSL Manager/Info: {0}'.format(info))

def main():
    signal.signal(signal.SIGINT, signal_handler)
    print_header()

    # Login
    #qrz_user = input('Username: ')
    #qrz_pass = urllib.parse.quote_plus(getpass('Password: ')) # urllib allows special characters in QRZ password
    session_key = login(qrz_user, qrz_pass)

    # Lookup Callsigns
    ## Command Line Input
    if sys.argv:
        try:lookup_callsign(sys.argv[1], session_key)
        except:pass

    ## User Input
    while True:
        callsign = input(Colors.BLUE + '\nCallsign (Q to quit): ' + Colors.END).strip()
        if "" == callsign or "?" == callsign or "h" == callsign.lower() or "help" == callsign.lower():
            print("Enter callsign or enter 'q' to quit")
        elif "q" == callsign.lower() or "quit" == callsign.lower() or "x" == callsign.lower():
            print("\nBye!\n")
            break
        else:
            lookup_callsign(callsign, session_key)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print("\nError: {}".format(str(e)))
        print("Please report this issue if it persists.")
