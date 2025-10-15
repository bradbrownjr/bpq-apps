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
      "type": "text|textarea|yesno|choice",
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
Single-line text input. Supports optional `max_length` parameter.

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
Multi-line text input. User types END on a new line to finish.

```json
{
  "name": "message",
  "label": "Message Text",
  "type": "textarea",
  "required": true,
  "description": "Enter your message. Type END when finished."
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

Completed forms are exported in BPQ message format and saved to the import directory. The format is compatible with FLMSG plaintext output and includes:
- BPQ message header (SP for private, SB for bulletin)
- Form title and metadata
- All field values
- /EX terminator for BPQ import

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
