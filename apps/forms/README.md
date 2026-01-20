# Form Templates Directory

This directory contains form templates (`.frm` files) for the fillable forms system. This pairs with the forms.py application in the parent folder.

## Included Forms

### ICS-213 General Message Form (`ics213.frm`)
Standard Incident Command System form for general messages in emergency and non-emergency communications. Includes fields for incident name, sender/recipient information, message content, priority level, and reply request.

### Net Check-in Form (`netcheck.frm`)
Standard form for checking into amateur radio nets. Collects station information including operator name, location, grid square, operational status, and whether the station has traffic to pass.

### Equipment Status Report (`eqstat.frm`)
Report operational status of radio equipment and infrastructure. Useful for nets and emergency preparedness assessments. Covers power source, radio equipment status (HF/VHF/UHF), digital modes, antennas, and overall capability.

### ARRL Radiogram (`radiogram.frm`)
Standard ARRL radiogram format for formal message traffic used in the National Traffic System (NTS). Includes all standard radiogram fields: number, precedence, handling instructions, check, address information, and message text.

### Field Situation Report (`fsr.frm`)
Report field conditions, resource status, and operational situation during incidents or exercises. Used for tactical field updates. Includes situation summary, personnel status, resources needed, safety concerns, and communications status.

### Severe Weather Report (`severe_wx.frm`)
Report severe weather conditions including storms, flooding, high winds, and other hazardous weather. Compatible with SKYWARN reporting. Covers tornado sightings, wind damage, hail, rainfall, flooding, and damage observations.

### Bulletin Message (`bulletin.frm`)
General bulletin message for announcements, alerts, and information distribution to multiple recipients. Includes priority levels, effective/expiration times, categories, and action requirements.

### ICS-309 Communications Log (`ics309.frm`)
Communications log for documenting all radio traffic during an incident. Records operator, station, and message details per ICS standards. Includes time stamps, from/to stations, message content, frequencies, and actions taken.

### USGS Did You Feel It? (DYFI) Report (`dyfi.frm`)
Report earthquake experiences to the USGS Did You Feel It system. Helps create maps showing what people experienced and extent of damage. Data can be sent to USGS for earthquake intensity analysis. Includes location, GPS coordinates, situation, felt intensity, damage observations, and detailed effects.

### GYX Weather Report (`gyx-weather.frm`)
**Special Mode**: SKYWARN weather observation strip for the Gray, Maine (GYX) weather service. Report severe weather conditions including precipitation, wind, hail, and storm damage. Data submitted via this form can be compiled into NWS-compatible databases.

**Strip Format:**
```
GYX WEATHER/DATE (MM-DD-YYYY)/TIME (HHMML OR HHMMZ)/CALL SIGN/SPOTTER ID (OR NA)/SOURCE (Amateur Radio, Trained Spotter, Media, Public Service Radio, Other 3rd Party, Direct Messaging)/LOCATION ROAD, TOWN)/STATE (AA)/CURRENT WEATHER (RELEVANT INFO, BE BRIEF)/SNOW, SLEET (INCHES OR NA, IF STORM TOTAL ADD * EG 2.6 or 3.5*)/ICE ACCRETION (INCHES OR NA)/RAINFALL (INCHES OR NA, IF STORM TOTAL ADD * EG 2.6 or 3.5*)/HAIL SIZE (INCHES OR NA)/WIND DIRECTION & SPEED (AAA@MPH)/STORM DAMAGE (WIND, FLOODING, ICE JAMS, OTHER DETAILS)/MODE (Personal Observation, FM Repeater, Winlink, DMR, Direct Messaging. For Others Leave Blank)/NET (NAME OF RADIO NET OR OTHER EG EMAIL, SLACK)//
```

**Example Response:**
```
GYX WEATHER/01-02-2026/2220Z/WO1J/CU330/Amateur Radio/314 POPE RD, WINDHAM/ME/CLEAR & COLD/1.4*/NA/0.01*/NA/WNW @ 2/NONE/Personal Observation/REPEATER 147.045//
```

**How it works:**
1. The form displays the GYX WEATHER strip template
2. You paste the template and fill in your observations for each field
3. The form creates a response strip formatted for NWS database import

**Field Descriptions:**
- **DATE**: Report date in MM-DD-YYYY format
- **TIME**: Report time in HHMML (local) or HHMMZ (UTC) format
- **CALL SIGN**: Your amateur radio callsign
- **SPOTTER ID**: Optional spotter identification (use NA if none)
- **SOURCE**: How the observation was made (Amateur Radio, Trained Spotter, Media, Public Service Radio, Other 3rd Party, Direct Messaging)
- **LOCATION**: Road/landmark and town name
- **STATE**: Two-letter state abbreviation (e.g., ME, MA)
- **CURRENT WEATHER**: Brief description of current conditions
- **PRECIPITATION**: Snow, sleet, rainfall (in inches; use * for storm totals, e.g., 2.6* means 2.6" storm total)
- **WIND**: Wind direction (AAA) and speed in MPH (e.g., WNW @ 2)
- **DAMAGE**: Description of any storm damage observed
- **MODE**: How the report was sent (Personal Observation, FM Repeater, Winlink, DMR, Direct Messaging)
- **NET**: Name of radio net or other delivery method (email, Slack, etc.)

### Information Strip Response Form (`strip.frm`)
**Special Mode**: Parse and respond to slash-separated information request strips. Common in MARS and SHARES operations.

**How it works:**
1. You paste an information request strip like: `ROSTER/CALL SIGN/NAME/LOCATION//`
2. The form parses each field (separated by `/`)
3. You enter responses for each field
4. The form creates a response strip: `ROSTER/KC1JMH/BRAD/MAINE//`

**Example Request Strip:**
```
ROSTER/HAM CALL SIGN/FIRST NAME/TOWN/COUNTY/STATE (2 LETTERS)/LAT (e.g. 44.123N)/LON (e.g. 069.123W)/MGRS (9 CHARACTERS)/WINLINK (Y,N)/HF NBEMS (Y,N)/VHF NBEMS (Y,N)/BRIEF COMMENTS//
```

**Example Response Strip:**
```
ROSTER/KC1JMH/BRAD/PORTLAND/CUMBERLAND/ME/43.661N/070.255W/19TCG8494/Y/Y/N/AVAILABLE FOR EXERCISES//
```

**Strip Format Rules:**
- Fields separated by forward slash (`/`)
- First field is the strip title/name
- Empty fields should contain three spaces: `   `
- Strip ends with double slash (`//`)
- No line breaks in the strip

This format is compact, ideal for low-bandwidth operations, and can be easily compiled into spreadsheets for data analysis.

## Creating Custom Forms

Form templates use JSON format. Here's the structure:

```json
{
  "id": "FORMID",
  "title": "Form Title",
  "version": "1.0",
  "description": "Brief description of the form's purpose",
  "fields": [
    {
      "name": "field_identifier",
      "label": "Human-readable Field Label",
      "type": "text|textarea|yesno|choice|strip",
      "required": true,
      "description": "Help text for the user",
      "max_length": 100,
      "allow_na": true,
      "choices": ["Option 1", "Option 2", "Option 3"]
    }
  ]
}
```

**Note**: The recipient is always prompted from the user after form completion, allowing flexibility for different scenarios and incidents.

## Field Types

### text
Single-line text input. User presses Enter to finish. Can be left blank if not required. Supports optional `max_length` parameter.

```json
{
  "name": "callsign",
  "label": "Your Callsign",
  "type": "text",
  "required": true,
  "max_length": 10,
  "description": "Enter your amateur radio callsign"
}
```

### textarea
Multi-line text input. User types `/EX` on a new line to finish. This is the standard packet radio message terminator, preventing conflicts with message content that might include "END".

```json
{
  "name": "message",
  "label": "Message Text",
  "type": "textarea",
  "required": true,
  "description": "Enter your message. Type /EX when finished."
}
```

### yesno
Yes/No/NA response. Supports optional `allow_na` parameter (default: true).

```json
{
  "name": "emergency",
  "label": "Is this an emergency",
  "type": "yesno",
  "required": true,
  "allow_na": false,
  "description": "Y for Yes, N for No"
}
```

### choice
Numbered list of options. User enters the number of their selection.

```json
{
  "name": "priority",
  "label": "Message Priority",
  "type": "choice",
  "required": true,
  "choices": [
    "Routine",
    "Priority",
    "Emergency"
  ],
  "description": "Select priority level"
}
```

## Required vs Optional Fields

Set `"required": true` to make a field mandatory. The user will be prompted until they provide a value. Optional fields can be left blank by pressing Enter.

## Tips for Creating Forms

1. **Keep it simple**: Packet radio is slow. Don't make forms too long.
2. **Clear labels**: Make field labels and descriptions concise but clear.
3. **Logical order**: Arrange fields in a logical sequence.
4. **Required fields**: Only mark fields as required if they're truly necessary.
5. **Choices over text**: Use choice fields instead of text when there are a limited number of valid responses.
6. **Test your forms**: Fill out the form yourself to check for issues.

## File Naming

Form template files should:
- Use the `.frm` extension
- Have descriptive filenames (lowercase, no spaces)
- Examples: `netcheck.frm`, `ics213.frm`, `weather-report.frm`

## Validation

The forms.py application will automatically:
- Validate required fields are not empty
- Check text length against max_length
- Ensure numeric choices are valid
- Allow users to press Q to quit at any time

## Output Format

Completed forms are appended to a single import file (`../linbpq/infile`) in BPQ message format. Multiple messages can be queued in this file, and BPQ will process them automatically. The format is compatible with FLMSG plaintext output and includes:
- BPQ message header (SP for private, SB for bulletin)
- Form title and metadata
- All field values
- /EX terminator for BPQ import

Each message is appended to the file, allowing multiple users to submit forms concurrently. BPQ's import system will process all messages in the file and then delete it (when configured with the DELETE option).

Example output:
```
SP SYSOP < KC1JMH
ICS213 - ICS-213 General Message Form

======================================================================
ICS-213 General Message Form
Form ID: ICS213
Version: 1.0
======================================================================

Submitted by: KC1JMH
Submitted on: 2025-10-15 14:30 UTC

----------------------------------------------------------------------

Incident/Event Name: Test Event
To (Name): John Smith
Subject: Test Message
Message:
  This is a test message.
  It has multiple lines.
Priority: Routine
Reply Requested: YES

----------------------------------------------------------------------
End of form

/EX
```
