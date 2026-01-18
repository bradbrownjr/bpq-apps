{
  "id": "FSR",
  "title": "Field Situation Report",
  "version": "1.0",
  "description": "Report field conditions, resource status, and operational situation during incidents or exercises. Used for tactical field updates.",
  "fields": [
    {
      "name": "incident_name",
      "label": "Incident/Exercise Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Name of the incident or exercise"
    },
    {
      "name": "report_number",
      "label": "Report Number",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "Sequential report number (e.g., FSR-001)"
    },
    {
      "name": "report_time",
      "label": "Report Date/Time",
      "type": "text",
      "required": true,
      "max_length": 50,
      "description": "Date and time of this report (e.g., 2025-10-15 14:30)"
    },
    {
      "name": "reporting_party",
      "label": "Reporting Party Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Name of person making report"
    },
    {
      "name": "location",
      "label": "Location",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Current location or area of operations"
    },
    {
      "name": "situation_summary",
      "label": "Situation Summary",
      "type": "textarea",
      "required": true,
      "description": "Brief summary of current situation"
    },
    {
      "name": "personnel_status",
      "label": "Personnel Status",
      "type": "choice",
      "required": true,
      "choices": [
        "All personnel accounted for",
        "Personnel en route",
        "Personnel missing/unaccounted",
        "Casualties reported",
        "Unknown"
      ],
      "description": "Status of personnel in area"
    },
    {
      "name": "resources_needed",
      "label": "Resources Needed",
      "type": "textarea",
      "required": false,
      "description": "List any resources or assistance needed"
    },
    {
      "name": "safety_concerns",
      "label": "Safety Concerns",
      "type": "textarea",
      "required": false,
      "description": "Any immediate safety or hazard concerns"
    },
    {
      "name": "communications_status",
      "label": "Communications Status",
      "type": "choice",
      "required": true,
      "choices": [
        "All systems operational",
        "Degraded - partial capability",
        "Limited - backup systems only",
        "Communications down"
      ],
      "description": "Status of communications capabilities"
    },
    {
      "name": "next_report",
      "label": "Next Report Expected",
      "type": "text",
      "required": false,
      "max_length": 50,
      "description": "When to expect next update (time or 'as needed')"
    },
    {
      "name": "additional_info",
      "label": "Additional Information",
      "type": "textarea",
      "required": false,
      "description": "Any other relevant information"
    }
  ]
}
