{
  "id": "SEVERE_WX",
  "title": "Severe Weather Report",
  "version": "1.0",
  "description": "Report severe weather conditions including storms, flooding, high winds, and other hazardous weather. Compatible with SKYWARN reporting.",
  "fields": [
    {
      "name": "observer_name",
      "label": "Observer Name",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "Your name"
    },
    {
      "name": "observer_location",
      "label": "Observation Location",
      "type": "text",
      "required": true,
      "max_length": 100,
      "description": "City/town and nearest landmark"
    },
    {
      "name": "observation_time",
      "label": "Observation Date/Time",
      "type": "text",
      "required": true,
      "max_length": 50,
      "description": "When did you observe this? (e.g., 10/15 14:30)"
    },
    {
      "name": "weather_type",
      "label": "Weather Event Type",
      "type": "choice",
      "required": true,
      "choices": [
        "Tornado/Funnel Cloud",
        "Severe Thunderstorm",
        "Flash Flooding",
        "High Winds",
        "Heavy Rain",
        "Large Hail",
        "Snow/Ice Storm",
        "Other"
      ],
      "description": "Primary weather event being reported"
    },
    {
      "name": "tornado_sighted",
      "label": "Tornado or Funnel Cloud Sighted",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Did you see a tornado or funnel cloud?"
    },
    {
      "name": "wind_damage",
      "label": "Wind Damage Observed",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Did you observe damage from wind?"
    },
    {
      "name": "wind_speed",
      "label": "Estimated Wind Speed",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "Estimated wind speed in MPH (if known)"
    },
    {
      "name": "hail",
      "label": "Hail Observed",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Did you observe hail?"
    },
    {
      "name": "hail_size",
      "label": "Hail Size",
      "type": "choice",
      "required": false,
      "choices": [
        "Pea size (1/4 inch)",
        "Penny size (3/4 inch)",
        "Quarter size (1 inch)",
        "Golf ball (1.75 inches)",
        "Tennis ball (2.5 inches)",
        "Baseball or larger (2.75+ inches)"
      ],
      "description": "Size of hail observed"
    },
    {
      "name": "rainfall",
      "label": "Heavy Rainfall",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Heavy or excessive rainfall observed?"
    },
    {
      "name": "rainfall_amount",
      "label": "Estimated Rainfall",
      "type": "text",
      "required": false,
      "max_length": 20,
      "description": "Estimated amount in inches (if known)"
    },
    {
      "name": "flooding",
      "label": "Flooding Observed",
      "type": "yesno",
      "required": true,
      "allow_na": false,
      "description": "Flooding in streets, streams, or low areas?"
    },
    {
      "name": "flood_description",
      "label": "Flooding Description",
      "type": "textarea",
      "required": false,
      "description": "Describe extent and location of flooding"
    },
    {
      "name": "damage_description",
      "label": "Damage Description",
      "type": "textarea",
      "required": false,
      "description": "Describe any damage observed (trees, structures, etc.)"
    },
    {
      "name": "injuries",
      "label": "Injuries Reported",
      "type": "yesno",
      "required": true,
      "allow_na": true,
      "description": "Are there any injuries?"
    },
    {
      "name": "additional_info",
      "label": "Additional Information",
      "type": "textarea",
      "required": false,
      "description": "Any other relevant observations"
    }
  ]
}
