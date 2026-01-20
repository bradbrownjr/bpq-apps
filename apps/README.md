# BBS Apps
Applications designed to run via BPQ BBS APPLICATION commands or standalone.

## Table of Contents
- [Features](#features)
- [Applications](#applications)
  - [bulletin.py](#bulletinpy)
  - [callout.py](#calloutpy)
  - [forms.py](#formspy)
  - [gopher.py](#gopherpy)
  - [hamqsl.py](#hamqslpy)
  - [hamtest.py](#hamtestpy)
  - [predict.py](#predictpy)
  - [qrz3.py](#qrz3py)
  - [rss-news.py](#rss-newspy)
  - [space.py](#spacepy)
  - [wx.py](#wxpy)
  - [wx-me.py](#wx-mepy)
  - [wxnws-ftp.py](#wxnws-ftppy)
- [Installation](#installation)
- [BPQ Configuration](#bpq-configuration)

## Features

**🔄 Automatic Updates**: All applications automatically check for updates on startup. When a newer version is available on GitHub, it will be downloaded and installed automatically. The check has a 3-second timeout to ensure fast startup even without internet connectivity.

**📻 Packet Radio Optimized**: Designed for low-bandwidth AX.25 packet radio with:
- Plain ASCII text output (no ANSI codes or Unicode)
- Minimal data usage
- 80-column terminal compatibility
- Simple command-based navigation
- Fast startup and response times

## Applications

bulletin.py
-----------
**Type**: Python  
**Purpose**: Community bulletin board for posting and viewing one-liner messages  
**Information source**: User submissions stored locally  
**Developer**: Brad Brown KC1JMH  
**Notes**: Classic BBS-style one-liner door application. Messages stored in JSON format with callsign, timestamp, and message text. Automatically captures user callsign from BPQ32.

**Download or update**:  
```wget -O bulletin.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/bulletin.py && chmod +x bulletin.py```

**Features**:
- Post one-liner messages (up to 80 characters)
- View recent messages with pagination (10 messages per page)
- Delete your own messages
- Message statistics and top contributors
- Automatic callsign detection from BPQ32 or manual entry
- JSON storage with callsign, timestamp, and message text
- Chronological display (newest first)
- Messages marked with '*' can be deleted by author

**BPQ32 Configuration**:
```
APPLICATION 8,BULLETIN,C 9 HOST 8 S
```
The 'S' flag strips SSID from callsign for cleaner display. Remove 'S' to include SSID.

**Usage**:
- Menu-driven interface with numeric choices
- Option 1: View messages (shows 10 per page)
- Option 2: Post new message
- Option 3: Delete your own messages
- Option 4/5: Navigate pages (next/previous)
- Option 6: View statistics
- Q: Quit

**Data Storage**:
Messages are stored in `bulletin_board.json` in the same directory as the script:
```json
{
  "messages": [
    {
      "callsign": "KC1JMH",
      "message": "73 to everyone on the network!",
      "timestamp": "2026-01-20T15:30:00Z"
    }
  ]
}
```

callout.py
----------
---------
**Type**: Python  
**Purpose**: Gopher protocol client for accessing gopherspace  
**Information source**: Gopher servers worldwide  
**Developer**: Brad Brown KC1JMH

**Download or update**:  
```wget -O gopher.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/gopher.py && chmod +x gopher.py```

hamqsl.py
---------
**Type**: Python  
**Purpose**: HF Propagation  
**Information source**: www.hamqsl.com, used by permission of author Paul N0NBH  
**Developer**: Brad Brown KC1JMH

**Download or update**:  
```wget -O hamqsl.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/hamqsl.py && chmod +x hamqsl.py```

![Terminal output](../docs/images/hamqsl.png)

hamtest.py
----------
**Type**: Python  
**Purpose**: Ham radio license test practice application  
**Information source**: russolsen/ham_radio_question_pool GitHub repository  
**Developer**: Brad Brown KC1JMH  
**Notes**: Automatically downloads current question pools from GitHub. Python 3.5+ required.

**Download or update**:  
```wget -O hamtest.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/hamtest.py && chmod +x hamtest.py```

**Features**:
- Practice tests for Technician, General, and Extra class licenses
- Realistic exam simulation with proper question distribution
- Automatic question pool updates from GitHub
- ASCII art interface optimized for packet radio terminals
- Pass/fail scoring with 74% threshold
- Quit functionality during exams
- Credit attribution to original question pool author

**Usage**:
- Select license class from main menu
- Answer multiple choice questions (A, B, C, D)
- Press 'Q' during exam to quit back to menu

predict.py
----------
**Type**: Python  
**Purpose**: HF propagation estimator - best bands/times for contacts  
**Information source**: hamqsl.com solar data, simplified ITU-R ionospheric model  
**Developer**: Brad Brown KC1JMH  
**Notes**: Simplified model (~70-80% accuracy). For precise predictions, use voacap.com.

**Download or update** (from ~/apps directory):  
```cd ~/apps && wget -O predict.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict.py && chmod +x predict.py```  
```mkdir -p predict && wget -O predict/__init__.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict/__init__.py```  
```wget -O predict/geo.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict/geo.py```  
```wget -O predict/solar.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict/solar.py```  
```wget -O predict/ionosphere.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict/ionosphere.py```  
```wget -O predict/regions.json https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/predict/regions.json```

**Features**:
- Estimates best HF bands (80m-10m) and times for contacts
- Resilient solar data: online → cached → user input → defaults
- Location input: gridsquare, GPS, DMS, US state, country, callsign
- Callsign gridsquare lookup via HamDB API
- BPQ LOCATOR config integration
- Works offline with cached or user-supplied solar data

**Solar Data & Geomagnetic Conditions**:
Real-time solar indices from hamqsl.com determine band reliability:
- **K-Index (Geomagnetic)**: 0-9 scale measuring magnetosphere disturbance
  - K >= 7: SEVERE STORM (major HF degradation)
  - K >= 5: STORM (poor HF conditions)
  - K >= 4: UNSETTLED (degraded)
  - K < 2: QUIET (excellent conditions)
- **SSN (Sunspot Number)**: 0-300 scale, higher = better HF propagation
- **SFI (Solar Flux Index)**: Radiation intensity; affects band openings

**Usage**:
- Select prediction type from menu (me to ham, me to place, place to place)
- Enter locations as gridsquare, coordinates, state, country, or callsign
- View band reliability estimates and recommended frequencies

qrz3.py
- Use option 5 to manually update question pools

qrz3.py
-------
**Type**: Python  
**Purpose**: QRZ lookup  
**Information source**: qrz.com   
**Developer**: Modified code from github.com/hink/qrzpy  
**Notes**: Requires XML subscription and API key to download all available information, unless you are prompting visitors for their QRZ creds (in plaintext over the air or local)

**Download or update**:  
```wget -O qrz3.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/qrz3.py && chmod +x qrz3.py```

![Terminal output](../docs/images/qrz3.png)

rss-news.py
-----------
**Type**: Python  
**Purpose**: RSS feed reader with categorized feeds  
**Information source**: Configurable RSS feeds  
**Developer**: Brad Brown KC1JMH  
**Notes**: Requires rss-news.conf configuration file. Optionally uses w3m for better text extraction from web articles.

**Download or update**:  
```
wget -O rss-news.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/rss-news.py && chmod +x rss-news.py
wget -O rss-news.conf https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/rss-news.conf
```

**Features**:
- Categorized RSS feeds from configuration file
- Browse feeds by category and view article lists
- Article size warnings for bandwidth management
- Pagination support for large articles
- Clean text extraction from web pages
- Optional full article fetching from source URLs

**Configuration**:
Edit `rss-news.conf` to add your own RSS feeds in CSV format:
```
Category,Feed Name,Feed URL
```

callout.py
----------
**Type**: Python  
**Purpose**: Test application demonstrating BPQ callsign capture  
**Information source**: BPQ32 connection data  
**Developer**: Brad Brown KC1JMH  
**Notes**: Simple example showing how to capture the connecting user's callsign from BPQ32. Used as a reference for other applications.

**Download or update**:  
```wget -O callout.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/callout.py && chmod +x callout.py```

**Features**:
- Captures callsign passed from BPQ32 via stdin
- Demonstrates configuration without NOCALL flag
- Shows how to use 'S' flag to strip SSID
- Reference implementation for other applications

**BPQ32 Configuration**:
```
APPLICATION 7,CALLOUT,C 9 HOST 3 S
```
The 'S' flag strips the SSID (e.g., KC1JMH-8 becomes KC1JMH). Remove 'S' to include SSID.

forms.py
--------
**Type**: Python  
**Purpose**: Fillable forms system for packet radio  
**Information source**: User input, form templates  
**Developer**: Brad Brown KC1JMH  
**Notes**: Generates BPQ-importable messages from completed forms. Automatically captures user callsign from BPQ32. Form templates are automatically downloaded from GitHub on first run.

**Download or update**:  
```
wget -O forms.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/forms.py && chmod +x forms.py
```

**Features**:
- **Auto-downloads form templates from GitHub** - no manual wget needed for forms!
- Auto-discovery of form templates from `forms/` subdirectory
- Captures user callsign automatically from BPQ32 (or prompts if not available)
- User always specifies recipient for each form submission
- Optional form review before submission (saves bandwidth)
- **Strip Mode**: Parse and respond to slash-separated information request strips (MARS/SHARES format)
- Multiple field types: text (single-line), textarea (/EX terminated), yes/no/na, multiple choice
- Required and optional field validation
- Press Q to quit at any time during form filling
- Exports to BPQ message format for automatic import

**Included Forms**:
- ICS-213 General Message
- Net Check-in
- Equipment Status Report
- ARRL Radiogram
- Field Situation Report (FSR)
- Severe Weather Report (SKYWARN compatible)
- Bulletin Message
- ICS-309 Communications Log
- USGS Did You Feel It? (DYFI) Earthquake Report
- Information Strip Response (MARS/SHARES format)

**BPQ32 Configuration**:
```
APPLICATION 14,FORMS,C 9 HOST 10 S
```
Note: Does NOT use NOCALL flag, so callsign is passed to the application. The 'S' flag strips SSID.

**BPQ Import Setup**:
The forms application appends completed forms to a single file (`../linbpq/infile` relative to the forms.py script) in BPQ message format. To automatically import these messages into your BPQ BBS:

1. The export file will be: `linbpq/infile` (same directory as your bpq32.cfg)
2. In the BPQ32 web UI, configure a forwarding record to import from this file
3. Use the forwarding script command: `IMPORT infile DELETE`
4. The DELETE option removes the file after successful import

For manual import via web UI: **Actions → Import Messages** and select the infile.

**Creating Custom Forms**:
Form templates use JSON format with the following structure:
```json
{
  "id": "FORMID",
  "title": "Form Title",
  "version": "1.0",
  "description": "Form description",
  "fields": [
    {
      "name": "field_name",
      "label": "Field Label",
      "type": "text|textarea|yesno|choice",
      "required": true|false,
      "description": "Field description",
      "max_length": 100,
      "allow_na": true|false,
      "choices": ["Option 1", "Option 2"]
    }
  ]
}
```
Note: Recipient is always prompted from user after form completion.

**Field Types**:
- `text` - Single-line text input (press Enter to finish, can be left blank if not required)
- `textarea` - Multi-line text input (type `/EX` on new line to finish)
- `yesno` - Yes/No/NA response
- `choice` - Numbered list of options
- `strip` - Slash-separated MARS/SHARES format for information request/response

space.py
--------
**Type**: Python  
**Purpose**: NOAA Space Weather reports  
**Information source**: Space Weather Prediction Center, National Oceanic and Atmospheric Administration  
**Developer**: Brad Brown KC1JMH

**Download or update**:  
```wget -O space.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/space.py && chmod +x space.py```

![Terminal output](../docs/images/space.png)

sysinfo.sh
----------
**Type**: Shell script  
**Purpose**: Get host information and confirm BBS services are running  
**Information source**: localhost  
**Developer**: Brad Brown KC1JMH  
**Notes**: Requires neofetch be installed  

**Download or update**:  
```wget -O sysinfo.sh https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/sysinfo.sh && chmod +x sysinfo.sh```

![Terminal output](../docs/images/sysinfo.png)

wx.py
-----
**Type**: Python  
**Purpose**: Weather reports via NWS API  
**Information source**: National Weather Service API  
**Developer**: Brad Brown KC1JMH  
**Notes**: Work in progress. Uses NWS API to pull weather for any location. Requires `maidenhead` module for grid square conversions. Not yet production-ready.

**Download or update**:  
```wget -O wx.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/wx.py && chmod +x wx.py```

**Status**: Under development. For production use, see `wx-me.py` below.

wx-me.py
--------
**Type**: Python  
**Purpose**: Local weather reports for Southern Maine and New Hampshire  
**Information source**: National Weather Service, Gray Office  
**Developer**: Brad Brown KC1JMH  
**Notes**: Production version of weather app. Direct text file retrieval from NWS.

**Download or update**:  
```wget -O wx-me.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/wx-me.py && chmod +x wx-me.py```

![Terminal output](../docs/images/wx.png)

wxnws-ftp.py
------------
**Type**: Python  
**Purpose**: Retrieve NWS products via FTP  
**Information source**: NWS TGFTP server  
**Developer**: Brad Brown KC1JMH  
**Notes**: Experimental. Downloads and displays NWS text products from FTP server. Configurable region code.

**Download or update**:  
```wget -O wxnws-ftp.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/wxnws-ftp.py && chmod +x wxnws-ftp.py```

**Features**:
- Downloads AFD (Area Forecast Discussion) files from NWS FTP
- Pauses at section breaks (&&) for user pacing
- Configurable regional NWS office

**Status**: Experimental, not production-ready.

## Subdirectories

### forms/
Contains form templates (.frm files) used by forms.py. Templates are automatically downloaded from GitHub on first run. See forms/ subdirectory README for form template format and available forms.

### question_pools/
Contains ham radio license exam question pools in JSON format. Automatically downloaded and updated by hamtest.py from russolsen/ham_radio_question_pool repository.

### images/
Screenshots and example output images for documentation.

**Note**: Sysop utilities for managing the BBS are located in `/utilities` at repository root.

# ToDos
[X] **All** - Update #! to call interpreter regardless of location using env  
[ ] **qrz3.py** - Add variable check so as to not require sysop to comment lines if used in the mode that requires user login  
[ ] **wx.py** - Expand to provide weather information for other areas, in the meantime the txt web requests may be updated to pull any URL.

## Configuration

See [../docs/examples/](../docs/examples/) for inetd and bpq32.cfg configuration examples.