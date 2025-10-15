{
  "id": "RADIOGRAM",
  "title": "ARRL Radiogram",
  "version": "1.0",
  "description": "Standard ARRL radiogram format for formal message traffic. Used for passing messages through the National Traffic System (NTS).",
  "fields": [
    {
      "name": "number",
      "label": "Message Number",
      "type": "text",
      "required": true,
      "max_length": 10,
      "description": "Sequential message number from your station"
    },
    {
      "name": "precedence",
      "label": "Precedence",
      "type": "choice",
      "required": true,
      "choices": [
        "R - Routine",
        "W - Welfare",
        "P - Priority",
        "E - Emergency"
      ],
      "description": "Message precedence level"
    },
    {
      "name": "handling",
      "label": "HX (Handling Instructions)",
      "type": "text",
      "required": false,
      "max_length": 50,
      "description": "Optional handling instructions (HXA, HXB, etc.)"
    },
    {
      "name": "station_of_origin",
      "label": "Station of Origin",
      "type": "text",
      "required": true,
      "max_length": 20,
      "description": "Callsign of originating station"
    },
    {
      "name": "check",
      "label": "Check (Word Count)",
      "type": "text",
      "required": true,
      "max_length": 5,
      "description": "Number of words in message text"
    },
    {
      "name": "place_of_origin",
      "label": "Place of Origin",
      "type": "text",
      "required": true,
      "max_length": 50,
      "description": "City and state of origin"
    },
    {
      "name": "to_name",
      "label": "To (Name)",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Recipient's name"
    },
    {
      "name": "to_address",
      "label": "To (Address)",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Street address"
    },
    {
      "name": "to_city_state",
      "label": "To (City, State)",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "City and state"
    },
    {
      "name": "to_phone",
      "label": "To (Phone)",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "Phone number (optional)"
    },
    {
      "name": "text",
      "label": "Message Text",
      "type": "textarea",
      "required": true,
      "description": "The message text (count words for check)"
    },
    {
      "name": "signature",
      "label": "Signature",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Sender's name or signature"
    }
  ]
}
