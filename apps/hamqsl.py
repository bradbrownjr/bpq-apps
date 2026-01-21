#!/usr/bin/env python3
"""
Ham QSL Solar Data for Packet Radio
-----------------------------------
Retrieves solar data from hamqsl.com for propagation prediction.

Author: Brad Brown KC1JMH
Version: 1.1
Date: October 2025
"""

import requests
import xml.etree.ElementTree as ET
import sys
import os

def check_for_app_update(current_version, script_name):
    """Check if app has an update available on GitHub"""
    try:
        import urllib.request
        import re
        import stat
        
        # Get the version from GitHub (silent check with short timeout)
        github_url = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/{}".format(script_name)
        with urllib.request.urlopen(github_url, timeout=3) as response:
            content = response.read().decode('utf-8')
        
        # Extract version from docstring
        version_match = re.search(r'Version:\s*([0-9.]+)', content)
        if version_match:
            github_version = version_match.group(1)
            
            if compare_versions(github_version, current_version) > 0:
                print("\nUpdate available: v{} -> v{}".format(current_version, github_version))
                print("Downloading new version...")
                
                # Download the new version
                script_path = os.path.abspath(__file__)
                try:
                    # Write to temporary file first, then replace
                    temp_path = script_path + '.tmp'
                    with open(temp_path, 'wb') as f:
                        f.write(content.encode('utf-8'))
                    
                    # Ensure file is executable (Python script should be executable)
                    os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    
                    # Replace old file with new one
                    os.replace(temp_path, script_path)
                    
                    print("\nUpdate installed successfully!")
                    print("Please re-run this command to use the updated version.")
                    print("\nQuitting...")
                    sys.exit(0)
                except Exception as e:
                    print("\nError installing update: {}".format(e))
                    # Clean up temp file if it exists
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            pass
    except Exception as e:
        # Don't block startup if update check fails (no internet, etc.)
        pass

def compare_versions(version1, version2):
    """Compare two version strings"""
    try:
        parts1 = [int(x) for x in str(version1).split('.')]
        parts2 = [int(x) for x in str(version2).split('.')]
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0
    except (ValueError, AttributeError):
        return 0

# Check for app updates
check_for_app_update("1.1", "hamqsl.py")

# Get XML file from web server
url = "https://www.hamqsl.com/solarxml.php?nwra=north&muf=grnlnd"
webxml = (requests.get(url)).content
#print(webxml)

root = ET.fromstring(webxml)

# Declare variables from XML fields
for solardata in root.findall('solardata'):
    source = solardata.find('source').attrib['url']
    updated = solardata.find('updated').text

    solarflux = solardata.find('solarflux').text
    sunspots = solardata.find('sunspots').text
    aindex = solardata.find('aindex').text
    kindex = solardata.find('kindex').text
    kindexnt = solardata.find('kindexnt').text
    xray = solardata.find('xray').text
    heliumline = solardata.find('heliumline').text
    protonflux = solardata.find('protonflux').text
    electronflux = solardata.find('electonflux').text # misspelled in XML source
    aurora = solardata.find('aurora').text
    normalization = solardata.find('normalization').text
    solarwind = solardata.find('solarwind').text
    magneticfield = solardata.find('magneticfield').text

    b8040d = solardata.findall(".//band[@name='80m-40m'][@time='day']")[0].text
    b3020d = solardata.findall(".//band[@name='30m-20m'][@time='day']")[0].text
    b1715d = solardata.findall(".//band[@name='17m-15m'][@time='day']")[0].text
    b1210d = solardata.findall(".//band[@name='12m-10m'][@time='day']")[0].text

    b8040n = solardata.findall(".//band[@name='80m-40m'][@time='night']")[0].text
    b3020n = solardata.findall(".//band[@name='30m-20m'][@time='night']")[0].text
    b1715n = solardata.findall(".//band[@name='17m-15m'][@time='night']")[0].text
    b1210n = solardata.findall(".//band[@name='12m-10m'][@time='night']")[0].text

    auroralat = solardata.find('latdegree').text
    esaura = solardata.findall(".//phenomenon[@name='vhf-aurora'][@location='northern_hemi']")[0].text
    e6meseu = solardata.findall(".//phenomenon[@name='E-Skip'][@location='europe_6m']")[0].text
    e4meseu = solardata.findall(".//phenomenon[@name='E-Skip'][@location='europe_4m']")[0].text
    e2meseu = solardata.findall(".//phenomenon[@name='E-Skip'][@location='europe']")[0].text
    e2mesna = solardata.findall(".//phenomenon[@name='E-Skip'][@location='north_america']")[0].text

    geomagfield = solardata.find('geomagfield').text
    snr = solardata.find('signalnoise').text
    muf = solardata.find('muf').text
    muffactor = solardata.find('muffactor').text
    fof2 = solardata.find('fof2').text

logo = r"""
 _                               _ 
| |__   __ _ _ __ ___   __ _ ___| |
| '_ \ / _` | '_ ` _ \ / _` / __| |
| | | | (_| | | | | | | (_| \__ \ |
|_| |_|\__,_|_| |_| |_|\__, |___/_|
                          |_|      
"""

print(logo)
print("HAMQSL - Solar and Band Conditions")
print("-" * 40)
lr = "-" * 40
print()
print('From: ', source)
print('Updated: ', updated)

print(lr)
print("            Solar-Terrestrial Data")
print('Solar Flux: ', solarflux, end ="\t")
print('Sunspots: ', sunspots)

if kindexnt != "No Report":
        knt = "nt"
else:
        knt = ""
print('A-Index:', aindex, end ="\t\t")
print('K-Index:', kindex, '/', kindexnt, knt)

print('X-Ray:', xray, end ="\t\t")
print('Helium:', heliumline)

print('Proton Flux: ', protonflux, end ="\t")
print('Electron Flux: ', electronflux)

print('Solar Wind: ', solarwind, end ="\t")
print('Aurora: ', aurora, '/', normalization)

print('Magnetic Field: ', magneticfield)

print(lr)
print("    HF Conditions           VHF Conditions")
print("Band\t Day\tNight")
print('80m-40m\t', b8040d, '\t', b8040n, '\t6m ESkip EU: ', e6meseu)
print('30m-20m\t', b3020d, '\t', b3020n, '\t4m ESkip EU: ', e4meseu)
print('17m-15m\t', b1715d, '\t', b1715n, '\t2m ESkip EU: ', e2meseu)
print('12m-10m\t', b1210d, '\t', b1210n, '\t2m ESkip NA: ', e2mesna)
print('Auorora Latitude: ', auroralat, 'Aurora Skip: ', esaura)

print(lr)
print('Geomagnetic Field: ', geomagfield, end ="\t")
print('SNR: ', snr)

print('Max Usable Freq: ', muf, end ="\t\t")
print('MUF Factor: ', muffactor)
print('Crit foF2 Freq: ', fof2)

print(lr)
