{
  "id": "ICS309",
  "title": "ICS-309 Communications Log",
  "version": "1.0",
  "description": "Communications log for documenting all radio traffic during an incident. Records operator, station, and message details per ICS standards.",
  "fields": [
    {
      "name": "incident_name",
      "label": "Incident Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Name of the incident"
    },
    {
      "name": "operational_period",
      "label": "Operational Period",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Date/Time range of this log (e.g., 10/15 0800-1600)"
    },
    {
      "name": "operator_name",
      "label": "Radio Operator Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Name of radio operator"
    },
    {
      "name": "operator_callsign",
      "label": "Operator Callsign",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "Amateur radio callsign"
    },
    {
      "name": "station_id",
      "label": "Station ID/Location",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Station identifier or location"
    },
    {
      "name": "log_entry_time",
      "label": "Entry Time",
      "type": "text",
      "required": true,
      "max_length": 20,
      "description": "Time of this log entry (HHMM format)"
    },
    {
      "name": "from_station",
      "label": "From (Station/Unit)",
      "type": "text",
      "required": true,
      "max_length": 50,
      "description": "Originating station or unit"
    },
    {
      "name": "to_station",
      "label": "To (Station/Unit)",
      "type": "text",
      "required": true,
      "max_length": 50,
      "description": "Destination station or unit"
    },
    {
      "name": "message_number",
      "label": "Message Number",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "Message number if applicable"
    },
    {
      "name": "message_content",
      "label": "Message Content/Summary",
      "type": "textarea",
      "required": true,
      "description": "Content or summary of communication"
    },
    {
      "name": "frequency_channel",
      "label": "Frequency/Channel",
      "type": "text",
      "required": false,
      "max_length": 50,
      "description": "Radio frequency or channel used"
    },
    {
      "name": "mode",
      "label": "Mode",
      "type": "choice",
      "required": false,
      "choices": [
        "Voice",
        "Packet/Digital",
        "Phone/Telephone",
        "Face-to-Face",
        "Other"
      ],
      "description": "Communication mode"
    },
    {
      "name": "action_taken",
      "label": "Action Taken",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Action taken or forwarded to whom"
    },
    {
      "name": "remarks",
      "label": "Remarks",
      "type": "textarea",
      "required": false,
      "description": "Additional remarks or notes"
    }
  ]
}
