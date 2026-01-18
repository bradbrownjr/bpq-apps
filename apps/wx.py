#!/usr/bin/env python3
# Switched to API from pulling text files, as the text files were removed from the NWS site
# Switching to API will allow us to pull reports from any NWS office

# Reference material:
# https://www.weather.gov/documentation/services-web-api

# Import necessary modules
import requests # Import requests module for making HTTP requests, for pulling data from the NWS API
import json # Import json module for parsing JSON data
import os # Import os module for file operations
import sys # Import sys module for command-line arguments
import re # Import re module for stripping HTML tags from text with regular expressions
from datetime import datetime # Import datetime module for parsing ISO 8601 date strings into human-readable format
try:
    import maidenhead as mh # Import what's needed to get lattitude and longitude from gridsquare location
except ImportError:
    os.system('python3 -m pip install maidenhead')
    import maidenhead as mh


# User variables
url="https://api.weather.gov"
state="ME" # State abbreviation

# Look for the LOCATOR variable in the BPQ32 config file ""../linbpq/bpq32.cfg", assuming the apps folder is adjacent
pwd=os.getcwd() # Get the current working directory
try:
    config_path = os.path.join(pwd, "linbpq", "bpq32.cfg") # Path to the BPQ32 config file
    with open(config_path, "r") as f:
        for line in f:
            if "LOCATOR" in line: # Look for the LOCATOR variable
                gridsquare = line.split("=")[1].strip()
except FileNotFoundError:
    print("File not found. Using default gridsquare.")
    gridsquare="FN43pp" # Default gridsquare is in Southern Maine, author's QTH

# Get the gridpoint for the NWS office from the lattitude and longitude of the maidenhead gridsquare
def get_gridpoint(latlon):
    lat, lon = latlon
    response = requests.get(f"{url}/points/{lat},{lon}")
    data = response.json()
    gridpoint = data['properties']['forecastGridData']
    wfo = data['properties']['cwa']
    return gridpoint, wfo

# Strip html and special characters from a value with the re module
def strip_html(text):
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Remove special characters like &nbsp;
    text = re.sub('&[a-zA-Z]+;', ' ', text)
    # Replace \r\n with a single carriage return
    text = text.replace('\r\n', '\r')
    return text

# Get the gridpoint and WFO values for the local NWS office
gridpoint, wfo = get_gridpoint(mh.to_location(gridsquare))
print(f"Gridpoint URL: {gridpoint}")
print(f"WFO: {wfo}")

# Get weather office headlines from "/offices/{officeId}/headlines"
def get_headlines():
    response = requests.get(f"{url}/offices/{wfo}/headlines")
    data = response.json()
    headlines = []
    for item in data["@graph"]:
        title = item["title"]
        # Parse the ISO 8601 date string and format the date into a more human-readable format
        issuance_time_human_str = datetime.fromisoformat(item["issuanceTime"]).strftime("%Y-%m-%d %H:%M:%S")
        content_html = item["content"]
        content_text = strip_html(content_html)
        headlines.append({
            "title": title,
            "issuanceTime": issuance_time_human_str,
            "content": content_text
        })
    return headlines

headlines = get_headlines()
for headline in headlines:
    print(f"Title: {headline['title']}")
    print(f"Issuance Time: {headline['issuanceTime']}")
    print(f"Content: {headline['content']}\n")
