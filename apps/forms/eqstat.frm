{
  "id": "EQSTAT",
  "title": "Equipment Status Report",
  "version": "1.0",
  "description": "Report the operational status of radio equipment and infrastructure. Useful for nets and emergency preparedness assessments.",
  "fields": [
    {
      "name": "station_call",
      "label": "Station Callsign",
      "type": "text",
      "required": true,
      "max_length": 20,
      "description": "The callsign of the station being reported"
    },
    {
      "name": "location",
      "label": "Location",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Physical location of the equipment"
    },
    {
      "name": "power_source",
      "label": "Power Source",
      "type": "choice",
      "required": true,
      "choices": [
        "Commercial AC",
        "Generator",
        "Battery",
        "Solar",
        "Multiple sources",
        "No power"
      ],
      "description": "Current power source"
    },
    {
      "name": "hf_radio",
      "label": "HF Radio Operational",
      "type": "yesno",
      "required": true,
      "allow_na": true,
      "description": "Is HF radio equipment operational?"
    },
    {
      "name": "vhf_radio",
      "label": "VHF Radio Operational",
      "type": "yesno",
      "required": true,
      "allow_na": true,
      "description": "Is VHF radio equipment operational?"
    },
    {
      "name": "uhf_radio",
      "label": "UHF Radio Operational",
      "type": "yesno",
      "required": true,
      "allow_na": true,
      "description": "Is UHF radio equipment operational?"
    },
    {
      "name": "digital_modes",
      "label": "Digital Modes Operational",
      "type": "yesno",
      "required": true,
      "allow_na": true,
      "description": "Are digital modes (packet, PSK31, FT8, etc.) operational?"
    },
    {
      "name": "internet",
      "label": "Internet Connectivity",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Do you have internet connectivity?"
    },
    {
      "name": "antenna_status",
      "label": "Antenna Status",
      "type": "choice",
      "required": true,
      "choices": [
        "All antennas operational",
        "Partial - some antennas down",
        "Emergency antenna only",
        "No antennas operational"
      ],
      "description": "Status of antenna systems"
    },
    {
      "name": "overall_status",
      "label": "Overall Operational Status",
      "type": "choice",
      "required": true,
      "choices": [
        "Fully operational",
        "Operational with limitations",
        "Minimal capability",
        "Not operational"
      ],
      "description": "Overall assessment of station capability"
    },
    {
      "name": "issues",
      "label": "Issues or Needed Repairs",
      "type": "textarea",
      "required": false,
      "description": "Describe any issues or needed repairs"
    },
    {
      "name": "notes",
      "label": "Additional Notes",
      "type": "textarea",
      "required": false,
      "description": "Any additional information"
    }
  ]
}
