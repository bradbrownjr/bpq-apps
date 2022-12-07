#!/usr/bin/python3
# Original script acquired from https://github.com/hink/qrzpy/blob/master/qrz3.py
# Script will try to install necessary module: beautifulsoup4 for XML parsing
from getpass import getpass
import signal
import sys 
import os
import requests

try:
  from bs4 import BeautifulSoup as soup
except ImportError:
  print ("Trying to Install required module: BeautifulSoup4\n")
  os.system('python3 -m pip install BeautifulSoup4')
from bs4 import BeautifulSoup as soup


# Brad's additions
import urllib.parse # Allow special characters in password
import warnings # Suppress "it looks like you're trying to parse HTML
warnings.filterwarnings("ignore")

# User variables
# --------------
# If it is preferred to prompt the user for their
# creds, remark the next two lines and re-enable
# lines 107 and 108.
api_root = 'http://xmldata.qrz.com/xml/current/'
qrz_user = "" # Enter QRZ username in the quotes
qrz_pass = urllib.parse.quote_plus("") # Enter QRZ password in the quotes
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
    sys.exit(0)


def _error(msg, do_exit=False):
    print('{0}[ERROR]{1} {2}'.format(Colors.RED, Colors.END, msg))
    if do_exit:
        sys.exit(1)

def print_header():
    print("""  ____  _____   ______
 / __ \|  __ \ |___  /
| |  | | |__) |   / / 
| |  | |  _  /   / /  
| |__| | | \ \  / /__ 
 \___\_\_|  \_\/_____|
     Lookup Tool""")

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
    while True:
        callsign = input(Colors.BLUE + '\nCallsign: ' + Colors.END)
        if "?" in callsign or "h"in callsign.lower() or "help" in callsign.lower():
            print("Enter callsign or enter 'q' to quit")
        elif "q" in callsign.lower() or "quit" in callsign.lower() or "x" in callsign.lower():
            exit()
        else:
            lookup_callsign(callsign, session_key)

if __name__ == "__main__":
    exit (main())
