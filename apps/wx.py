#!/usr/bin/env python3
import requests
menu = """
Weather reports from NWS Gray, ME
------------------------------------------
1) Maine/New Hampshire Weather Summary
2) Maine/New Hampshire Weather Roundup
3) Western Maine/New Hampshire Forecast
4) Northern and Eastern Maine Forecast
5) Maine/New Hampshire Max/Min Temperature
   and Precipitation Table
------------------------------------------"""

about = """
Get text products right from the
National Weather Service in Gray, ME.

This is a Python3 script which pulls data from
https://www.maine.gov/mema/weather/general-information

Script developed by Brad Brown KC1JMH
"""

def pullthis(url):
        response = requests.get(url)
        data = response.text
        print("\n{}\n".format(data))

print (menu)
while True:
        selected = str(input("#1-5), R)elist, A)bout, Q)uit :> "))
        if "1" in selected:
                pullthis("https://w1.weather.gov/data/GYX/RWSGYX")
        elif "2" in selected:
                pullthis("http://www.weather.gov/data/GYX/RWRGYX")
        elif "3" in selected:
                pullthis("http://www.weather.gov/data/GYX/SFTGYX")
        elif "4" in selected:
                pullthis("http://www.weather.gov/data/CAR/SFTCAR")
        elif "5" in selected:
                pullthis("http://www.weather.gov/data/GYX/RTPGYX")
        elif "a" in selected.lower():
                print (about)
        elif "r" in selected.lower():
                print (menu)
        elif "q" in selected.lower():
                print ("\nExiting...\n")
                exit()
