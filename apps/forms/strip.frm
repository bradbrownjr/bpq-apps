{
  "id": "STRIP",
  "title": "Information Strip Response Form",
  "version": "1.0",
  "description": "Parse and respond to slash-separated information request strips. Common in MARS and SHARES operations. Example: ROSTER/CALL/NAME/LOCATION//",
  "fields": [
    {
      "name": "strip_input",
      "label": "Information Request Strip",
      "type": "textarea",
      "required": true,
      "description": "Paste the request strip here (slash-separated format ending with //)"
    }
  ],
  "strip_mode": true
}
