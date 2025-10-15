# BBS Apps
These following applications should be able to be run stand-alone or by a BBS. See below for notes on the purpose, setup and usage of the individual applications.

gopher.py
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

![Terminal output](images/hamqsl.png)

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

![Terminal output](images/qrz3.png)

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
- Multiple field types: text, textarea, yes/no/na, multiple choice
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
APPLICATION 12,FORMS,C 9 HOST 8 S
```
Note: Does NOT use NOCALL flag, so callsign is passed to the application. The 'S' flag strips SSID.

**Setup**:
1. Create the BPQ import directory: `mkdir -p ../bpq/import`
2. Ensure the forms directory exists: `mkdir -p forms`
3. Add form templates (`.frm` files) to the `forms/` subdirectory
4. Configure BPQ32 to auto-import messages from the import directory

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
- `text` - Single line text input
- `textarea` - Multi-line text input (enter END to finish)
- `yesno` - Yes/No/NA response
- `choice` - Numbered list of options

**BPQ Import Setup**:
Configure BPQ32 to automatically import messages from the export directory. Add to your BPQ32 forwarding configuration:
```
IMPORT ../bpq/import/*.txt DELETE
```

space.py
--------
**Type**: Python  
**Purpose**: NOAA Space Weather reports  
**Information source**: Space Weather Prediction Center, National Oceanic and Atmospheric Administration  
**Developer**: Brad Brown KC1JMH

**Download or update**:  
```wget -O space.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/space.py && chmod +x space.py```

![Terminal output](images/space.png)

sysinfo.sh
----------
**Type**: Shell script  
**Purpose**: Get host information and confirm BBS services are running  
**Information source**: localhost  
**Developer**: Brad Brown KC1JMH  
**Notes**: Requires neofetch be installed  

**Download or update**:  
```wget -O sysinfo.sh https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/sysinfo.sh && chmod +x sysinfo.sh```

![Terminal output](images/sysinfo.png)

wx-me.py
--------
**Type**: Python  
**Purpose**: Local weather reports to Southern Maine and New Hampshire  
**Information source**: National Weather Service, Gray Office  
**Developer**: Brad Brown KC1JMH

**Download or update**:  
```wget -O wx.py https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/wx-me.py && chmod +x wx.py```

**Note**: The original wx.py is being retooled to leverage the NWS FTP API to make it easier to pull more reports, for all of their coverage area. It is not ready, yet. Please continue to use the original code in wx-me.py, and update the source text file locations. 

![Terminal output](images/wx.png)

# ToDos
[X] **All** - Update #! to call interpreter regardless of location using env  
[ ] **qrz3.py** - Add variable check so as to not require sysop to comment lines if used in the mode that requires user login  
[ ] **wx.py** - Expand to provide weather information for other areas, in the meantime the txt web requests may be updated to pull any URL.