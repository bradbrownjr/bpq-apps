{
  "id": "MCF720_PRICE_SURVEY",
  "title": "Local Price Survey Report (MCF720)",
  "version": "1.0",
  "description": "Price Survey Report for SitRepNet. Submit local commodity price observations including milk, eggs, coffee, beef, beer, bread, gasoline, and diesel. Helps track inflation and supply chain issues.",
  "strip_mode": true,
  "template": "MCF720 PRICE SURVEY/STATE (ST) or Region:/GRID (GR) Maidenhead Grid or NA:/MILK 1gal (ML):/EGGS 1doz (EG):/COFFEE Ground (CF):/BEEF Ground 1lb (BF):/BEER 24 pack (BR):/BREAD Loaf (BD):/GASOLINE 1gal (GA):/DIESEL 1gal (DS):/SOURCE (@0=Local/Regional Chain, @1=Walmart, @2=Other):/POWER RELIABILITY (@0=No Outages, @1=One+ Outages in 7 days):/ADDITIONAL INFO (AI)://",
  "fields": [
    {
      "name": "mcf720_survey_strip",
      "label": "MCF720 Price Survey Strip",
      "type": "strip",
      "required": true,
      "description": "Enter commodity prices as reported in local area. Use decimal notation (e.g., 3.49). Leave blank for NA."
    }
  ]
}
