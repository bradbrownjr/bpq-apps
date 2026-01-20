{
  "id": "GYX_WEATHER",
  "title": "GYX Weather Report",
  "version": "1.0",
  "description": "SKYWARN weather observation strip for the Gray, Maine (GYX) weather service. Report severe weather observations including precipitation, wind, hail, and storm damage. Data submitted via this form can be compiled into NWS-compatible databases.",
  "strip_mode": true,
  "template": "GYX WEATHER/DATE (MM-DD-YYYY)/TIME (HHMML OR HHMMZ)/CALL SIGN/SPOTTER ID (OR NA)/SOURCE (Amateur Radio, Trained Spotter, Media, Public Service Radio, Other 3rd Party, Direct Messaging)/LOCATION ROAD, TOWN)/STATE (AA)/CURRENT WEATHER (RELEVANT INFO, BE BRIEF)/SNOW, SLEET (INCHES OR NA, IF STORM TOTAL ADD * EG 2.6 or 3.5*)/ICE ACCRETION (INCHES OR NA)/RAINFALL (INCHES OR NA, IF STORM TOTAL ADD * EG 2.6 or 3.5*)/HAIL SIZE (INCHES OR NA)/WIND DIRECTION & SPEED (AAA@MPH)/STORM DAMAGE (WIND, FLOODING, ICE JAMS, OTHER DETAILS)/MODE (Personal Observation, FM Repeater, Winlink, DMR, Direct Messaging. For Others Leave Blank)/NET (NAME OF RADIO NET OR OTHER EG EMAIL, SLACK)//",
  "fields": [
    {
      "name": "gyx_weather_strip",
      "label": "GYX Weather Information Strip",
      "type": "strip",
      "required": true,
      "description": "Fill in your observations for each field."
    }
  ]
}
