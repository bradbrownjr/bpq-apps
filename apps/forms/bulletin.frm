{
  "id": "BULLETIN",
  "title": "Bulletin Message",
  "version": "1.0",
  "description": "General bulletin message for announcements, alerts, and information distribution to multiple recipients.",
  "fields": [
    {
      "name": "bulletin_number",
      "label": "Bulletin Number",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "Sequential bulletin number (e.g., BUL-001)"
    },
    {
      "name": "priority",
      "label": "Priority",
      "type": "choice",
      "required": true,
      "choices": [
        "Routine",
        "Priority",
        "Immediate",
        "Flash"
      ],
      "description": "Message priority level"
    },
    {
      "name": "subject",
      "label": "Subject",
      "type": "text",
      "required": true,
      "max_length": 200,
      "description": "Subject line for the bulletin"
    },
    {
      "name": "effective_time",
      "label": "Effective Date/Time",
      "type": "text",
      "required": false,
      "max_length": 50,
      "description": "When this bulletin becomes effective"
    },
    {
      "name": "expiration_time",
      "label": "Expiration Date/Time",
      "type": "text",
      "required": false,
      "max_length": 50,
      "description": "When this bulletin expires or should be superseded"
    },
    {
      "name": "category",
      "label": "Category",
      "type": "choice",
      "required": false,
      "choices": [
        "General Information",
        "Net Announcement",
        "Schedule Change",
        "Weather Alert",
        "Emergency Notice",
        "Training/Exercise",
        "Equipment/Technical",
        "Administrative"
      ],
      "description": "Category of bulletin"
    },
    {
      "name": "message_body",
      "label": "Message",
      "type": "textarea",
      "required": true,
      "description": "The bulletin message content"
    },
    {
      "name": "action_required",
      "label": "Action Required",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Does this bulletin require action from recipients?"
    },
    {
      "name": "action_description",
      "label": "Required Action",
      "type": "textarea",
      "required": false,
      "description": "Describe what action is required (if applicable)"
    },
    {
      "name": "contact_info",
      "label": "Contact Information",
      "type": "text",
      "required": false,
      "max_length": 100,
      "description": "Who to contact for questions or more information"
    }
  ]
}
