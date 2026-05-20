{
  "id": "NETCHECK",
  "title": "Net Check-in Form",
  "version": "2.0",
  "format": "pktnet_checkin",
  "description": "Packet Radio Net Check-in Form. Output matches vden.org PACKET CHECK-IN format. Send as bulletin SB PKTNET@USA with subject: Name, Call, Town, State.",
  "fields": [
    {
      "name": "agency",
      "label": "Agency/Group Name",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Optional: agency or group affiliation (leave blank if none)"
    },
    {
      "name": "datetime",
      "label": "Date/Time",
      "type": "text",
      "required": true,
      "max_length": 20,
      "default_now": "%Y-%m-%d %H:%M",
      "description": "Check-in date and time UTC (YYYY-MM-DD HH:MM)"
    },
    {
      "name": "to",
      "label": "To (destination address)",
      "type": "text",
      "required": true,
      "max_length": 50,
      "default": "PKTNET@USA",
      "description": "Bulletin address (e.g. PKTNET@USA)"
    },
    {
      "name": "from_call",
      "label": "From (your callsign)",
      "type": "text",
      "required": true,
      "max_length": 20,
      "auto_fill": "callsign",
      "description": "Your callsign"
    },
    {
      "name": "contact",
      "label": "Station Contact Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Your name"
    },
    {
      "name": "operator",
      "label": "Initial Operator(s)",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Callsign(s) of operator(s) at this station (leave blank if same as From)"
    },
    {
      "name": "session_type",
      "label": "Session Type",
      "type": "choice",
      "required": true,
      "choices": [
        "EXERCISE",
        "REAL EVENT"
      ],
      "description": "Type of session"
    },
    {
      "name": "service_type",
      "label": "Service",
      "type": "text",
      "required": false,
      "max_length": 50,
      "default": "AMATEUR",
      "description": "Service type (default: AMATEUR)"
    },
    {
      "name": "band",
      "label": "Band",
      "type": "choice",
      "required": true,
      "choices": [
        "AXIP",
        "HF",
        "VHF",
        "UHF",
        "SHF"
      ],
      "description": "Frequency band or link type used"
    },
    {
      "name": "mode",
      "label": "Session/Mode",
      "type": "choice",
      "required": true,
      "choices": [
        "AXIP",
        "AX25 Packet",
        "Pactor",
        "Robust Packet",
        "Ardop",
        "VARA HF",
        "VARA FM",
        "Mesh"
      ],
      "description": "Digital mode used for this session"
    },
    {
      "name": "location",
      "label": "Location",
      "type": "text",
      "required": true,
      "max_length": 200,
      "description": "Your location - city, state (or specific site/address)"
    },
    {
      "name": "gridsquare",
      "label": "Grid Square",
      "type": "text",
      "required": false,
      "max_length": 10,
      "description": "Maidenhead grid square (e.g., FN42sr)"
    },
    {
      "name": "comments",
      "label": "Comments",
      "type": "textarea",
      "required": false,
      "max_length": 500,
      "description": "Hub station and band used, BBS used, notes (max 500 chars)"
    }
  ]
}
