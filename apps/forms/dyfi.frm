{
  "id": "DYFI",
  "title": "USGS Did You Feel It? (DYFI) Earthquake Report",
  "version": "1.0",
  "description": "Report earthquake experiences to the USGS Did You Feel It system. Helps create maps showing what people experienced and extent of damage. Data sent to USGS for earthquake intensity analysis.",
  "fields": [
    {
      "name": "event_type",
      "label": "Event Type",
      "type": "choice",
      "required": true,
      "choices": [
        "Real Event",
        "Exercise"
      ],
      "description": "Is this a real earthquake or an exercise?"
    },
    {
      "name": "event_id",
      "label": "USGS Event ID",
      "type": "text",
      "required": false,
      "max_length": 50,
      "description": "USGS Event ID from earthquake.usgs.gov (e.g., ci40063464)"
    },
    {
      "name": "exercise_id",
      "label": "Exercise ID",
      "type": "text",
      "required": false,
      "max_length": 50,
      "description": "Exercise identifier if applicable (e.g., ShakeOut2025)"
    },
    {
      "name": "report_location",
      "label": "Your Location (City, State)",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "City and state where you felt the earthquake"
    },
    {
      "name": "zip_code",
      "label": "ZIP Code",
      "type": "text",
      "required": false,
      "max_length": 10,
      "description": "ZIP or postal code"
    },
    {
      "name": "latitude",
      "label": "Latitude (Decimal Degrees)",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "e.g., 34.1341 (North is positive)"
    },
    {
      "name": "longitude",
      "label": "Longitude (Decimal Degrees)",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "e.g., -118.3215 (West is negative)"
    },
    {
      "name": "situation",
      "label": "Your Situation When Earthquake Occurred",
      "type": "choice",
      "required": true,
      "choices": [
        "Inside building",
        "Outside",
        "In stopped vehicle",
        "In moving vehicle",
        "Asleep"
      ],
      "description": "Where were you when the earthquake occurred?"
    },
    {
      "name": "felt_earthquake",
      "label": "Did You Feel the Earthquake?",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Did you feel the earthquake?"
    },
    {
      "name": "others_felt",
      "label": "Did Others Near You Feel It?",
      "type": "choice",
      "required": false,
      "choices": [
        "No one else",
        "Some",
        "Most",
        "Everyone"
      ],
      "description": "How many others near you felt it?"
    },
    {
      "name": "awakened",
      "label": "Were You Awakened?",
      "type": "yesno",
      "required": false,
      "allow_na": true,
      "description": "If asleep, were you awakened?"
    },
    {
      "name": "frightened",
      "label": "Were You Frightened?",
      "type": "choice",
      "required": false,
      "choices": [
        "Not at all",
        "A little",
        "Somewhat",
        "Very much"
      ],
      "description": "How frightened were you?"
    },
    {
      "name": "difficulty_standing",
      "label": "Difficulty Standing/Walking?",
      "type": "yesno",
      "required": false,
      "allow_na": true,
      "description": "Did you have trouble standing or walking?"
    },
    {
      "name": "furniture_moved",
      "label": "Furniture Moved",
      "type": "choice",
      "required": false,
      "choices": [
        "None",
        "Light furniture",
        "Heavy furniture",
        "Most/all furniture"
      ],
      "description": "Did furniture move or overturn?"
    },
    {
      "name": "objects_fell",
      "label": "Objects Fell or Broke",
      "type": "choice",
      "required": false,
      "choices": [
        "None",
        "A few",
        "Many",
        "Most/all"
      ],
      "description": "Did objects fall from shelves or walls?"
    },
    {
      "name": "walls_cracked",
      "label": "Walls Cracked",
      "type": "yesno",
      "required": false,
      "allow_na": true,
      "description": "Did walls crack or have damage?"
    },
    {
      "name": "building_damage",
      "label": "Building Damage Level",
      "type": "choice",
      "required": false,
      "choices": [
        "None",
        "Slight - hairline cracks",
        "Moderate - large cracks",
        "Severe - partial collapse",
        "Complete collapse"
      ],
      "description": "Damage to building you were in"
    },
    {
      "name": "damage_description",
      "label": "Damage Description",
      "type": "textarea",
      "required": false,
      "description": "Describe any damage you observed"
    },
    {
      "name": "additional_comments",
      "label": "Additional Comments",
      "type": "textarea",
      "required": false,
      "description": "Any other observations or information"
    }
  ]
}
