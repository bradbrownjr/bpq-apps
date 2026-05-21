{
  "id": "RADIOGRAM",
  "title": "ARRL Radiogram",
  "version": "2.4",
  "format": "nts_radiogram",
  "description": "Standard ARRL radiogram for the National Traffic System (NTS).",
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
      "description": "Optional handling instructions (HXA, HXB, etc.) or ? for list",
      "help": [
        "HXA(n) Collect delivery authorized within n miles",
        "HXB(n) Cancel if not delivered within n hours; notify origin",
        "HXC    Report delivery date/time to originating station",
        "HXD    Report relay and delivery chain to originating station",
        "HXE    Get reply from addressee; originate reply message back",
        "HXF(n) Hold delivery until date n",
        "HXG    No toll delivery; cancel and notify origin if cost required"
      ]
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
      "name": "to_zip",
      "label": "To (ZIP Code)",
      "type": "text",
      "required": true,
      "max_length": 10,
      "description": "Destination ZIP code — used for NTS routing (e.g. 04543)"
    },
    {
      "name": "to_state",
      "label": "To (2-letter state abbr)",
      "type": "text",
      "required": true,
      "max_length": 2,
      "description": "Destination state abbreviation — used for NTS routing (e.g. ME, MA, NH)"
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
      "name": "to_email",
      "label": "To (Email)",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Recipient email address (optional, e.g. KY2D@ARRL.NET)"
    },
    {
      "name": "text",
      "label": "Message Text",
      "type": "textarea",
      "required": true,
      "arl_enabled": true,
      "description": "The message text (word count is computed automatically for the check)"
    },
    {
      "name": "signature",
      "label": "Signature",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Sender's name or signature"
    },
    {
      "name": "filed_time",
      "label": "Time Filed (UTC, HHMM)",
      "type": "text",
      "required": false,
      "max_length": 6,
      "default_now": "%H%M",
      "description": "UTC time message is filed (auto-filled with current time)"
    }
  ]
}
