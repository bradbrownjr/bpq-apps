#!/usr/bin/python3
import requests
menu = """
Space Weather Reports
-----------------------------------
1) Forecast Discussion
2) 3-Day Forecast
3) 3-Day Geomagnetic Forecast
4) 3-day Space Weather Predictions
5) Advisory Outlook
6) Weekly Highlights and Forecasts
7) Geophysical Alert Message
-----------------------------------"""

about = """
This is a Python3 script which pulls data from
https://services.swpc.noaa.gov/text/.
Developed by Brad Brown KC1JMH
"""

def pullthis(url):
        response = requests.get(url)
        data = response.text
        print("\n{}\n".format(data))

print(menu)
while True:
        selected = str(input("#1-7), R)elist, A)bout, Q)uit :> "))
        if "1" in selected:
                pullthis("https://services.swpc.noaa.gov/text/discussion.txt")
        elif "2" in selected:
                pullthis("https://services.swpc.noaa.gov/text/3-day-forecast.txt")
        elif "3" in selected:
                pullthis("https://services.swpc.noaa.gov/text/3-day-geomag-forecast.txt")
        elif "4" in selected:
                pullthis("https://services.swpc.noaa.gov/text/3-day-solar-geomag-predictions.txt")
        elif "5" in selected:
                pullthis("https://services.swpc.noaa.gov/text/advisory-outlook.txt")
        elif "6" in selected:
                pullthis("https://services.swpc.noaa.gov/text/weekly.txt")
        elif "7" in selected:
                pullthis("https://services.swpc.noaa.gov/text/wwv.txt")
        elif "a" in selected.lower():
                print (about)
        elif "r" in selected.lower():
                print (menu)
        elif "q" in selected.lower():
                print ("\nExiting...\n")
                exit()
