{
  "id": "ICS213",
  "title": "ICS-213 General Message Form",
  "version": "1.0",
  "description": "General message form for emergency and non-emergency communications. Based on the Incident Command System ICS-213 form used for tactical communications.",
  "fields": [
    {
      "name": "incident_name",
      "label": "Incident/Event Name",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Name of the incident or event (if applicable)"
    },
    {
      "name": "to_name",
      "label": "To (Name)",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Name of the primary recipient"
    },
    {
      "name": "to_position",
      "label": "To (Position/Title)",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Position or title of the recipient"
    },
    {
      "name": "from_name",
      "label": "From (Name)",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Your name"
    },
    {
      "name": "from_position",
      "label": "From (Position/Title)",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Your position or title"
    },
    {
      "name": "subject",
      "label": "Subject",
      "type": "text",
      "required": true,
      "max_length": 200,
      "description": "Brief subject line for the message"
    },
    {
      "name": "message",
      "label": "Message",
      "type": "textarea",
      "required": true,
      "description": "The message content"
    },
    {
      "name": "priority",
      "label": "Priority",
      "type": "choice",
      "required": true,
      "choices": [
        "Routine",
        "Urgent",
        "Emergency"
      ],
      "description": "Message priority level"
    },
    {
      "name": "reply_requested",
      "label": "Reply Requested",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Do you need a reply to this message?"
    }
  ]
}
