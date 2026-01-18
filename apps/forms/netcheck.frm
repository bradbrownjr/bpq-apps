{
  "id": "NETCHECK",
  "title": "Net Check-in Form",
  "version": "1.0",
  "description": "Standard form for checking into an amateur radio net. Collects station information and operational status.",
  "fields": [
    {
      "name": "net_name",
      "label": "Net Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Name of the net you are checking into"
    },
    {
      "name": "operator_name",
      "label": "Operator Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Your name"
    },
    {
      "name": "location",
      "label": "Location (City/County)",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Your current location"
    },
    {
      "name": "grid_square",
      "label": "Grid Square",
      "type": "text",
      "required": false,
      "max_length": 10,
      "description": "Maidenhead grid square (e.g., FN43sr)"
    },
    {
      "name": "status",
      "label": "Station Status",
      "type": "choice",
      "required": true,
      "choices": [
        "Active - Available for traffic",
        "Active - Monitoring only",
        "Mobile",
        "Portable",
        "Emergency Power"
      ],
      "description": "Your current operating status"
    },
    {
      "name": "traffic",
      "label": "Traffic to Pass",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Do you have traffic (messages) to pass?"
    },
    {
      "name": "emergency",
      "label": "Emergency or Priority Traffic",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Do you have emergency or priority traffic?"
    },
    {
      "name": "comments",
      "label": "Comments",
      "type": "textarea",
      "required": false,
      "description": "Additional comments or information (optional)"
    }
  ]
}
