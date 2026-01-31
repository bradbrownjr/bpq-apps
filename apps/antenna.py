#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
antenna.py - Antenna Calculator & Configuration Database

Calculators for common antenna types and a user-contributed database
of antenna configurations for portable/field antennas.

Version: 1.1

Author: Brad Brown Jr, KC1JMH
Date: 2026-01-31
"""

import json
import os
import sys
import math
import textwrap

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen, Request, URLError

VERSION = "1.1"
SCRIPT_NAME = "antenna.py"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps/"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antenna.json")

# Speed of light factor for antenna calculations (468 for feet, 143 for meters)
SPEED_FACTOR_FT = 468
SPEED_FACTOR_M = 142.65

# Common ham bands with typical frequencies (MHz)
HAM_BANDS = {
    "160m": 1.9,
    "80m": 3.75,
    "60m": 5.3545,
    "40m": 7.15,
    "30m": 10.125,
    "20m": 14.175,
    "17m": 18.118,
    "15m": 21.225,
    "12m": 24.94,
    "10m": 28.5,
    "6m": 52.0,
    "2m": 146.0,
    "70cm": 445.0
}


def compare_versions(v1, v2):
    """Compare two version strings."""
    def parse(v):
        return tuple(map(int, v.split('.')))
    try:
        return parse(v1) < parse(v2)
    except (ValueError, AttributeError):
        return False


def check_for_app_update(current_version, script_name):
    """Check GitHub for newer version and auto-update if available."""
    import tempfile
    try:
        url = GITHUB_RAW_URL + script_name
        req = Request(url)
        req.add_header('User-Agent', 'BPQ-Antenna/1.0')
        response = urlopen(req, timeout=3)
        new_code = response.read().decode('utf-8')
        
        for line in new_code.split('\n')[:50]:
            if line.strip().startswith('VERSION'):
                remote_version = line.split('=')[1].strip().strip('"\'')
                if compare_versions(current_version, remote_version):
                    script_path = os.path.abspath(__file__)
                    current_mode = os.stat(script_path).st_mode
                    
                    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(script_path))
                    try:
                        os.write(fd, new_code.encode('utf-8'))
                        os.close(fd)
                        os.rename(temp_path, script_path)
                        os.chmod(script_path, current_mode)
                    except Exception:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                break
    except Exception:
        pass


def get_terminal_width():
    """Get terminal width with fallback."""
    try:
        return os.get_terminal_size(fallback=(80, 24)).columns
    except (AttributeError, ValueError, OSError):
        return 80


def wrap_text(text, width=40):
    """Wrap text to specified width."""
    return '\n'.join(textwrap.wrap(text, width=width))


def print_header():
    """Print app header with ASCII logo."""
    logo = r"""
                _
  __ _ _ _  ___| |_ ___ _ _  _ _  __ _
 / _` | ' \|___   _/ -_| ' \| ' \/ _` |
 \__,_|_||_|   |_| \___|_||_|_||_\__,_|
    """
    print(logo)
    print("ANTENNA v{} - Calculator & Database".format(VERSION))
    print("-" * 40)


def get_frequency():
    """Prompt user for frequency in MHz."""
    print("\nEnter frequency in MHz")
    print("Or band name (e.g., 40m, 20m, 2m)")
    sys.stdout.flush()
    
    while True:
        try:
            inp = raw_input("Frequency/Band :> ").strip().lower()
        except NameError:
            inp = input("Frequency/Band :> ").strip().lower()
        
        if not inp:
            return None
        
        # Check if it's a band name
        if inp in HAM_BANDS:
            return HAM_BANDS[inp]
        
        # Try parsing as frequency
        try:
            freq = float(inp)
            if 0.1 < freq < 3000:
                return freq
            else:
                print("Enter 0.1-3000 MHz")
        except ValueError:
            print("Invalid. Try again or Enter to cancel")
    
    return None


def calc_half_wave(freq_mhz):
    """Calculate half-wave length."""
    return SPEED_FACTOR_FT / freq_mhz


def calc_quarter_wave(freq_mhz):
    """Calculate quarter-wave length."""
    return SPEED_FACTOR_FT / freq_mhz / 2


# =============================================================================
# ANTENNA CALCULATORS
# =============================================================================

def calc_dipole():
    """Calculate dipole antenna dimensions."""
    print("\n" + "-" * 40)
    print("DIPOLE CALCULATOR")
    print("-" * 40)
    print("A classic half-wave dipole antenna.")
    print("Fed at center with 50-ohm coax.")
    
    freq = get_frequency()
    if not freq:
        return
    
    total_len = calc_half_wave(freq)
    leg_len = total_len / 2
    
    print("\n" + "-" * 40)
    print("DIPOLE for {:.3f} MHz".format(freq))
    print("-" * 40)
    print("Total length: {:.1f} ft ({:.2f} m)".format(
        total_len, total_len * 0.3048))
    print("Each leg:     {:.1f} ft ({:.2f} m)".format(
        leg_len, leg_len * 0.3048))
    print("\nFeed: Center with balun recommended")
    print("Impedance: ~73 ohms at resonance")
    print("-" * 40)
    pause()


def calc_efhw():
    """Calculate end-fed half-wave antenna."""
    print("\n" + "-" * 40)
    print("END-FED HALF-WAVE (EFHW)")
    print("-" * 40)
    print("Select transformer ratio:")
    print("1) 49:1 (most common EFHW)")
    print("2) 64:1 (alternative ratio)")
    print("3) 9:1 (random wire/EFRW)")
    print("4) 4:1 (random wire)")
    
    try:
        choice = raw_input("\nSelect [1-4] :> ").strip()
    except NameError:
        choice = input("\nSelect [1-4] :> ").strip()
    
    ratios = {"1": "49:1", "2": "64:1", "3": "9:1", "4": "4:1"}
    if choice not in ratios:
        print("Cancelled")
        return
    
    ratio = ratios[choice]
    
    freq = get_frequency()
    if not freq:
        return
    
    half_wave = calc_half_wave(freq)
    
    print("\n" + "-" * 40)
    print("EFHW {} for {:.3f} MHz".format(ratio, freq))
    print("-" * 40)
    print("Wire length: {:.1f} ft ({:.2f} m)".format(
        half_wave, half_wave * 0.3048))
    
    if ratio in ["49:1", "64:1"]:
        print("\nThis is a resonant half-wave antenna.")
        print("Works on fundamental + harmonic bands.")
        print("Example: 40m EFHW works on 40/20/15/10m")
        # Show harmonic bands
        print("\nHarmonic bands from {:.3f} MHz:".format(freq))
        for mult in [1, 2, 3, 4]:
            harmonic = freq * mult
            if harmonic <= 30:
                print("  {:.3f} MHz ({}x)".format(harmonic, mult))
    else:
        print("\nRandom wire with {} unun.".format(ratio))
        print("Requires antenna tuner for most bands.")
        print("\nSuggested lengths (avoid 1/2 wave):")
        # Random wire lengths that avoid resonance
        lengths = [29, 35.5, 41, 58, 71, 84, 107, 119, 148]
        for l in lengths:
            if l < half_wave * 1.5:
                print("  {} ft ({:.1f} m)".format(l, l * 0.3048))
    
    print("-" * 40)
    pause()


def calc_ocf_dipole():
    """Calculate off-center fed dipole."""
    print("\n" + "-" * 40)
    print("OFF-CENTER FED DIPOLE (OCF/Windom)")
    print("-" * 40)
    print("Fed at ~1/3 point, multiband operation.")
    print("Typically uses 4:1 or 6:1 balun.")
    
    freq = get_frequency()
    if not freq:
        return
    
    total_len = calc_half_wave(freq)
    # OCF is typically fed at 33% point
    short_leg = total_len * 0.33
    long_leg = total_len * 0.67
    
    print("\n" + "-" * 40)
    print("OCF DIPOLE for {:.3f} MHz".format(freq))
    print("-" * 40)
    print("Total length: {:.1f} ft ({:.2f} m)".format(
        total_len, total_len * 0.3048))
    print("Short leg:    {:.1f} ft ({:.2f} m)".format(
        short_leg, short_leg * 0.3048))
    print("Long leg:     {:.1f} ft ({:.2f} m)".format(
        long_leg, long_leg * 0.3048))
    print("\nFeed: 4:1 balun at offset point")
    print("Impedance: ~200-300 ohms at feedpoint")
    print("\nMultiband on even harmonics:")
    for mult in [1, 2, 4]:
        harmonic = freq * mult
        if harmonic <= 54:
            print("  {:.3f} MHz ({}x)".format(harmonic, mult))
    print("-" * 40)
    pause()


def calc_folded_dipole():
    """Calculate folded dipole dimensions."""
    print("\n" + "-" * 40)
    print("FOLDED DIPOLE")
    print("-" * 40)
    print("Higher impedance (~300 ohms), broader")
    print("bandwidth than standard dipole.")
    
    freq = get_frequency()
    if not freq:
        return
    
    total_len = calc_half_wave(freq)
    spacing = total_len * 0.01  # Typical 1% of length
    
    print("\n" + "-" * 40)
    print("FOLDED DIPOLE for {:.3f} MHz".format(freq))
    print("-" * 40)
    print("Total length: {:.1f} ft ({:.2f} m)".format(
        total_len, total_len * 0.3048))
    print("Wire spacing:  {:.1f} in ({:.1f} cm)".format(
        spacing * 12, spacing * 30.48))
    print("\nFeed: 4:1 balun (300 to 75 ohm)")
    print("      or direct to 300 ohm line")
    print("Impedance: ~288 ohms at resonance")
    print("-" * 40)
    pause()


def calc_moxon():
    """Calculate Moxon rectangle antenna."""
    print("\n" + "-" * 40)
    print("MOXON RECTANGLE")
    print("-" * 40)
    print("Compact 2-element beam with good")
    print("front-to-back ratio. Single band.")
    
    freq = get_frequency()
    if not freq:
        return
    
    # Moxon formulas (empirical)
    wavelength = 984.0 / freq  # feet
    
    # Dimensions as percentage of wavelength
    A = wavelength * 0.4755  # Element length
    B = wavelength * 0.1260  # Tip spacing
    C = wavelength * 0.0175  # Tip length
    D = wavelength * 0.1520  # Element spacing
    
    print("\n" + "-" * 40)
    print("MOXON for {:.3f} MHz".format(freq))
    print("-" * 40)
    print("    A           A")
    print("  |---|       |---|")
    print("  +---+   D   +---+")
    print("  | C | <---> | C |")
    print("  +---+       +---+")
    print("    B           B")
    print("  <->           <->")
    print("  DRIVEN     REFLECTOR")
    print("-" * 40)
    print("A (element):  {:.1f} ft ({:.2f} m)".format(A, A * 0.3048))
    print("B (tip gap):  {:.1f} in ({:.1f} cm)".format(B * 12, B * 30.48))
    print("C (tip len):  {:.1f} in ({:.1f} cm)".format(C * 12, C * 30.48))
    print("D (spacing):  {:.1f} ft ({:.2f} m)".format(D, D * 0.3048))
    print("\nTotal width:  {:.1f} ft".format(A))
    print("Total depth:  {:.1f} ft".format(D + (C * 2 / 12)))
    print("\nGain: ~4 dBd, F/B: ~25-30 dB")
    print("Feed: Direct 50 ohm at driven elem")
    print("-" * 40)
    pause()


def calc_vertical():
    """Calculate vertical antenna dimensions."""
    print("\n" + "-" * 40)
    print("VERTICAL ANTENNA")
    print("-" * 40)
    print("1) 1/4 wave ground plane")
    print("2) 5/8 wave vertical")
    print("3) 1/2 wave vertical (J-pole)")
    
    try:
        choice = raw_input("\nSelect [1-3] :> ").strip()
    except NameError:
        choice = input("\nSelect [1-3] :> ").strip()
    
    if choice not in ["1", "2", "3"]:
        print("Cancelled")
        return
    
    freq = get_frequency()
    if not freq:
        return
    
    quarter = calc_quarter_wave(freq)
    half = calc_half_wave(freq)
    
    print("\n" + "-" * 40)
    
    if choice == "1":
        print("1/4 WAVE GROUND PLANE - {:.3f} MHz".format(freq))
        print("-" * 40)
        print("Vertical:   {:.1f} ft ({:.2f} m)".format(
            quarter, quarter * 0.3048))
        print("Radials:    {:.1f} ft ({:.2f} m) x4 min".format(
            quarter, quarter * 0.3048))
        print("\nRadials at 45 deg = ~50 ohm match")
        print("Radials horizontal = ~35 ohm")
        
    elif choice == "2":
        fiveeighth = half * 0.625 * 2
        print("5/8 WAVE VERTICAL - {:.3f} MHz".format(freq))
        print("-" * 40)
        print("Vertical:   {:.1f} ft ({:.2f} m)".format(
            fiveeighth, fiveeighth * 0.3048))
        print("Radials:    {:.1f} ft min".format(quarter))
        print("\nRequires matching network")
        print("~1.5 dB gain over 1/4 wave")
        
    elif choice == "3":
        # J-pole dimensions
        matching = quarter * 0.05  # ~5% for matching section
        print("J-POLE / SLIM JIM - {:.3f} MHz".format(freq))
        print("-" * 40)
        print("Total:      {:.1f} ft ({:.2f} m)".format(
            half * 1.25, half * 1.25 * 0.3048))
        print("Radiator:   {:.1f} ft (3/4 wave)".format(half * 0.75 * 2))
        print("Stub:       {:.1f} ft (1/4 wave)".format(quarter))
        print("Gap:        {:.1f} in".format(matching * 12))
        print("\nNo radials required")
        print("Feed: tap point ~5% up from gap")
    
    print("-" * 40)
    pause()


def calc_nvis():
    """Calculate NVIS antenna parameters."""
    print("\n" + "-" * 40)
    print("NVIS ANTENNA CALCULATOR")
    print("-" * 40)
    print("Near Vertical Incidence Skywave")
    print("For short-range HF (0-400 miles)")
    
    freq = get_frequency()
    if not freq:
        return
    
    if freq > 10:
        print("\nWarning: NVIS works best below 10 MHz")
        print("Typical bands: 80m, 60m, 40m")
    
    half_wave = calc_half_wave(freq)
    
    # NVIS height calculations
    # Optimal height is 0.1 to 0.25 wavelength
    wavelength_ft = 984.0 / freq
    min_height = wavelength_ft * 0.10
    opt_height = wavelength_ft * 0.15
    max_height = wavelength_ft * 0.25
    
    print("\n" + "-" * 40)
    print("NVIS for {:.3f} MHz".format(freq))
    print("-" * 40)
    print("Dipole length: {:.1f} ft ({:.2f} m)".format(
        half_wave, half_wave * 0.3048))
    print("\nHeight above ground:")
    print("  Minimum:  {:.1f} ft ({:.1f} m)".format(
        min_height, min_height * 0.3048))
    print("  Optimal:  {:.1f} ft ({:.1f} m)".format(
        opt_height, opt_height * 0.3048))
    print("  Maximum:  {:.1f} ft ({:.1f} m)".format(
        max_height, max_height * 0.3048))
    print("\nTakeoff angle: 70-90 degrees")
    print("\nTips:")
    print("- Lower height = higher angle")
    print("- Reflector wire below helps")
    print("- Works well with poor ground")
    print("-" * 40)
    pause()


def calc_loop():
    """Calculate loop antenna dimensions."""
    print("\n" + "-" * 40)
    print("LOOP ANTENNA")
    print("-" * 40)
    print("1) Full wave loop (horizontal)")
    print("2) Full wave loop (vertical)")
    print("3) Magnetic loop (small TX)")
    
    try:
        choice = raw_input("\nSelect [1-3] :> ").strip()
    except NameError:
        choice = input("\nSelect [1-3] :> ").strip()
    
    if choice not in ["1", "2", "3"]:
        print("Cancelled")
        return
    
    freq = get_frequency()
    if not freq:
        return
    
    # Full wave circumference
    circumference = 1005.0 / freq  # feet
    
    print("\n" + "-" * 40)
    
    if choice in ["1", "2"]:
        # Calculate shapes
        square_side = circumference / 4
        triangle_side = circumference / 3
        delta_base = circumference * 0.36
        delta_sides = circumference * 0.32
        
        if choice == "1":
            print("HORIZONTAL LOOP - {:.3f} MHz".format(freq))
        else:
            print("VERTICAL LOOP - {:.3f} MHz".format(freq))
        print("-" * 40)
        print("Total wire: {:.1f} ft ({:.1f} m)".format(
            circumference, circumference * 0.3048))
        print("\nSquare loop:")
        print("  Each side: {:.1f} ft".format(square_side))
        print("\nTriangle loop:")
        print("  Each side: {:.1f} ft".format(triangle_side))
        print("\nDelta loop:")
        print("  Base: {:.1f} ft".format(delta_base))
        print("  Sides: {:.1f} ft each".format(delta_sides))
        print("\nFeed impedance: ~100-120 ohms")
        print("Use 4:1 balun or 75-ohm match")
        
    elif choice == "3":
        # Small transmitting loop
        print("MAGNETIC LOOP (STL) - {:.3f} MHz".format(freq))
        print("-" * 40)
        print("Small loop for limited space.")
        print("Requires high-voltage tuning cap.")
        print("\nTypical circumference: 8-25 ft")
        print("Circumference < 0.25 wavelength")
        max_circ = circumference * 0.25
        min_circ = circumference * 0.08
        print("\nFor {:.1f} MHz:".format(freq))
        print("  Min circ: {:.1f} ft".format(min_circ))
        print("  Max circ: {:.1f} ft".format(max_circ))
        print("  Diameter: {:.1f}-{:.1f} ft".format(
            min_circ / 3.14, max_circ / 3.14))
        print("\nEfficiency improves with larger")
        print("diameter and thicker conductor.")
    
    print("-" * 40)
    pause()


def calc_longwire():
    """Calculate longwire/random wire lengths."""
    print("\n" + "-" * 40)
    print("RANDOM WIRE LENGTHS")
    print("-" * 40)
    print("Lengths that avoid resonance on")
    print("multiple bands (needs tuner).")
    print("\nThese lengths work well with")
    print("9:1 or 4:1 unun and tuner:")
    print("-" * 40)
    
    # Good random wire lengths (feet)
    lengths = [
        (29, "Good multiband starter"),
        (35.5, "Avoids 80/40m resonance"),
        (41, "Classic random length"),
        (58, "Popular EFRW length"),
        (71, "Extended multiband"),
        (84, "Good for 160-10m"),
        (107, "Very long wire"),
        (119, "Extended coverage"),
        (135, "160m capability"),
        (148, "Full 160m+")
    ]
    
    for length, desc in lengths:
        print("{:5.1f} ft ({:5.1f} m) - {}".format(
            length, length * 0.3048, desc))
    
    print("-" * 40)
    print("\nCounterpoise recommendations:")
    print("- 17 ft for 20m and up")
    print("- 25 ft for 40m and up")
    print("- 65 ft for 80m")
    print("-" * 40)
    pause()


def calculator_menu():
    """Display calculator submenu."""
    while True:
        print("\n" + "-" * 40)
        print("ANTENNA CALCULATORS")
        print("-" * 40)
        print("1) Dipole")
        print("2) End-Fed Half-Wave (EFHW)")
        print("3) Off-Center Fed Dipole (OCF)")
        print("4) Folded Dipole")
        print("5) Moxon Rectangle")
        print("6) Vertical / Ground Plane")
        print("7) NVIS Antenna")
        print("8) Loop Antennas")
        print("9) Random Wire Lengths")
        print("-" * 40)
        print("Q) Quit  M) Main Menu")
        
        try:
            choice = raw_input("\nSelect [1-9,Q,M] :> ").strip().upper()
        except NameError:
            choice = input("\nSelect [1-9,Q] :> ").strip().upper()
        
        if choice == "1":
            calc_dipole()
        elif choice == "2":
            calc_efhw()
        elif choice == "3":
            calc_ocf_dipole()
        elif choice == "4":
            calc_folded_dipole()
        elif choice == "5":
            calc_moxon()
        elif choice == "6":
            calc_vertical()
        elif choice == "7":
            calc_nvis()
        elif choice == "8":
            calc_loop()
        elif choice == "9":
            calc_longwire()
        elif choice == "M":
            return
        elif choice == "Q":
            print("\nExiting...")
            sys.exit(0)
        else:
            print("Invalid selection")


# =============================================================================
# ANTENNA DATABASE
# =============================================================================

def load_database():
    """Load antenna database from JSON file."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except (IOError, ValueError):
            pass
    return {"antennas": []}


def save_database(db):
    """Save antenna database to JSON file."""
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        return True
    except IOError:
        return False


def get_callsign():
    """Get user callsign from stdin or prompt."""
    # Check if callsign provided via stdin (BPQ mode)
    if not sys.stdin.isatty():
        try:
            first_line = sys.stdin.readline().strip()
            if first_line and len(first_line) < 15:
                return first_line.split('-')[0].upper()
        except Exception:
            pass
    return None


def add_antenna_entry(callsign):
    """Add a new antenna configuration to database."""
    print("\n" + "-" * 40)
    print("ADD ANTENNA CONFIGURATION")
    print("-" * 40)
    
    db = load_database()
    
    try:
        inp = raw_input
    except NameError:
        inp = input
    
    print("Antenna brand/model:")
    brand = inp(":> ").strip()
    if not brand:
        print("Cancelled")
        return
    
    print("\nAntenna type:")
    print("1) Portable/Field  2) Base")
    print("3) Mobile          4) QRP")
    atype = inp("[1-4] :> ").strip()
    types = {"1": "Portable", "2": "Base", "3": "Mobile", "4": "QRP"}
    atype = types.get(atype, "Other")
    
    print("\nBand (e.g., 40m, 20m, multi):")
    band = inp(":> ").strip().lower()
    if not band:
        band = "multi"
    
    print("\nRadiator length (include units):")
    print("Example: 16.5 ft, 5.1 m, 33 in")
    radiator = inp(":> ").strip()
    
    print("\nTap/coil position (if applicable):")
    print("Example: tap 3, 75%, full")
    tap = inp(":> ").strip()
    
    print("\nNotes (optional):")
    notes = inp(":> ").strip()
    
    entry = {
        "brand": brand,
        "type": atype,
        "band": band,
        "radiator": radiator,
        "tap": tap,
        "notes": notes,
        "submitter": callsign if callsign else "ANON",
        "id": len(db["antennas"]) + 1
    }
    
    db["antennas"].append(entry)
    
    if save_database(db):
        print("\n" + "-" * 40)
        print("Entry added! ID: {}".format(entry["id"]))
        print("-" * 40)
    else:
        print("Error saving entry")
    
    pause()


def browse_database():
    """Browse antenna configurations."""
    db = load_database()
    
    if not db["antennas"]:
        print("\nNo antenna configurations yet.")
        print("Be the first to add one!")
        pause()
        return
    
    # Get unique brands
    brands = sorted(set(e["brand"] for e in db["antennas"]))
    
    print("\n" + "-" * 40)
    print("BROWSE BY BRAND ({} entries)".format(len(db["antennas"])))
    print("-" * 40)
    
    for i, brand in enumerate(brands, 1):
        count = sum(1 for e in db["antennas"] if e["brand"] == brand)
        print("{:2}) {} ({})".format(i, brand[:30], count))
    
    print("-" * 40)
    print("A) Show all  Q) Back")
    
    try:
        choice = raw_input("\nSelect :> ").strip().upper()
    except NameError:
        choice = input("\nSelect :> ").strip().upper()
    
    if choice == "Q":
        return
    elif choice == "A":
        entries = db["antennas"]
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(brands):
                brand = brands[idx]
                entries = [e for e in db["antennas"] if e["brand"] == brand]
            else:
                print("Invalid selection")
                return
        except ValueError:
            print("Invalid selection")
            return
    
    display_entries(entries)


def search_database():
    """Search antenna configurations."""
    print("\n" + "-" * 40)
    print("SEARCH DATABASE")
    print("-" * 40)
    print("1) Search by band")
    print("2) Search by brand")
    print("3) Search by type")
    
    try:
        choice = raw_input("\nSelect [1-3] :> ").strip()
    except NameError:
        choice = input("\nSelect [1-3] :> ").strip()
    
    db = load_database()
    
    if choice == "1":
        try:
            band = raw_input("Band (e.g., 40m): ").strip().lower()
        except NameError:
            band = input("Band (e.g., 40m): ").strip().lower()
        entries = [e for e in db["antennas"] 
                   if band in e.get("band", "").lower()]
    elif choice == "2":
        try:
            brand = raw_input("Brand: ").strip().lower()
        except NameError:
            brand = input("Brand: ").strip().lower()
        entries = [e for e in db["antennas"] 
                   if brand in e.get("brand", "").lower()]
    elif choice == "3":
        print("Types: Portable, Base, Mobile, QRP")
        try:
            atype = raw_input("Type: ").strip().lower()
        except NameError:
            atype = input("Type: ").strip().lower()
        entries = [e for e in db["antennas"] 
                   if atype in e.get("type", "").lower()]
    else:
        print("Cancelled")
        return
    
    if entries:
        display_entries(entries)
    else:
        print("\nNo matching entries found.")
        pause()


def display_entries(entries):
    """Display a list of antenna entries with pagination."""
    page_size = 5
    page = 0
    total_pages = (len(entries) + page_size - 1) // page_size
    
    while True:
        start = page * page_size
        end = min(start + page_size, len(entries))
        
        print("\n" + "-" * 40)
        print("RESULTS ({}/{})".format(page + 1, total_pages))
        print("-" * 40)
        
        for i, entry in enumerate(entries[start:end], start + 1):
            print("#{} {} - {}".format(
                entry.get("id", i),
                entry.get("brand", "Unknown"),
                entry.get("band", "?")
            ))
            print("   Type: {}".format(entry.get("type", "?")))
            if entry.get("radiator"):
                print("   Radiator: {}".format(entry["radiator"]))
            if entry.get("tap"):
                print("   Tap: {}".format(entry["tap"]))
            if entry.get("notes"):
                print("   Notes: {}".format(entry["notes"][:35]))
            print("   By: {}".format(entry.get("submitter", "?")))
            print("")
        
        print("-" * 40)
        
        nav = ["Q)uit"]
        if page > 0:
            nav.append("P)rev")
        if page < total_pages - 1:
            nav.append("N)ext")
        
        try:
            choice = raw_input("[{}] :> ".format(" ".join(nav))).strip().upper()
        except NameError:
            choice = input("[{}] :> ".format(" ".join(nav))).strip().upper()
        
        if choice == "P" and page > 0:
            page -= 1
        elif choice == "N" and page < total_pages - 1:
            page += 1
        elif choice == "Q":
            return


def popular_antennas():
    """Show info about popular portable antennas."""
    print("\n" + "-" * 40)
    print("POPULAR PORTABLE ANTENNAS")
    print("-" * 40)
    
    antennas = [
        ("Buddipole", "Modular dipole system with tapped coils"),
        ("Wolf River Coil", "Silver Bullet series loading coils"),
        ("Chameleon", "EMCOMM series, hybrid micro, etc"),
        ("MFJ-1899T", "Telescoping whip antenna"),
        ("EFHW-4010", "End-fed half-wave, 40-10m"),
        ("PAC-12", "Linked dipole/vertical system"),
        ("Elecraft AX1", "Ultra-compact 40/30/20m"),
        ("Super Antenna", "MP1 series portable"),
        ("AlexLoop", "Magnetic loop for QRP"),
        ("Ventenna", "HFp series portable")
    ]
    
    for name, desc in antennas:
        print("\n{}".format(name))
        print("  {}".format(desc))
    
    print("\n" + "-" * 40)
    print("Share your configurations to help")
    print("other operators!")
    print("-" * 40)
    pause()


def database_menu(callsign):
    """Display database submenu."""
    while True:
        db = load_database()
        count = len(db["antennas"])
        
        print("\n" + "-" * 40)
        print("ANTENNA DATABASE ({} entries)".format(count))
        print("-" * 40)
        print("1) Browse configurations")
        print("2) Search database")
        print("3) Add your configuration")
        print("4) Popular portable antennas")
        print("-" * 40)
        print("Q) Quit  M) Main Menu")
        
        try:
            choice = raw_input("\nSelect [1-4,Q,M] :> ").strip().upper()
        except NameError:
            choice = input("\nSelect [1-4,Q] :> ").strip().upper()
        
        if choice == "1":
            browse_database()
        elif choice == "2":
            search_database()
        elif choice == "3":
            add_antenna_entry(callsign)
        elif choice == "4":
            popular_antennas()
        elif choice == "M":
            return
        elif choice == "Q":
            print("\nExiting...")
            sys.exit(0)
        else:
            print("Invalid selection")


# =============================================================================
# REFERENCE SECTION
# =============================================================================

def show_formulas():
    """Display antenna formulas."""
    print("\n" + "-" * 40)
    print("ANTENNA FORMULAS")
    print("-" * 40)
    print("Half wave (ft) = 468 / freq(MHz)")
    print("Half wave (m)  = 142.65 / freq(MHz)")
    print("")
    print("Quarter wave   = Half wave / 2")
    print("Full wave      = 468 * 2 / freq")
    print("")
    print("Loop circum    = 1005 / freq(MHz)")
    print("")
    print("Velocity factor affects length:")
    print("  Bare wire: 0.95")
    print("  Insulated: 0.93-0.97")
    print("  Coax:      0.66-0.82")
    print("-" * 40)
    pause()


def show_band_chart():
    """Display ham band frequencies."""
    print("\n" + "-" * 40)
    print("HAM BAND FREQUENCIES")
    print("-" * 40)
    print("Band   Freq(MHz)  Half-Wave(ft)")
    print("-" * 40)
    
    for band, freq in sorted(HAM_BANDS.items(), 
                             key=lambda x: x[1]):
        hw = calc_half_wave(freq)
        print("{:6} {:9.3f}  {:7.1f}".format(band, freq, hw))
    
    print("-" * 40)
    pause()


def show_about():
    """Display about information."""
    print("\n" + "-" * 40)
    print("ABOUT ANTENNA CALCULATOR")
    print("-" * 40)
    print("Version: {}".format(VERSION))
    print("")
    print("Antenna calculators provide")
    print("starting dimensions. Always trim")
    print("and tune for your installation.")
    print("")
    print("Height, surrounding objects, and")
    print("ground conductivity all affect")
    print("resonant frequency.")
    print("")
    print("The configuration database lets")
    print("operators share settings for")
    print("portable antennas like Buddipole,")
    print("Wolf River Coil, and others.")
    print("-" * 40)
    pause()


def pause():
    """Pause for user input."""
    try:
        raw_input("\n[Press Enter to continue]")
    except NameError:
        input("\n[Press Enter to continue]")


def main_menu(callsign=None):
    """Main menu loop."""
    while True:
        print_header()
        print("\nMain Menu:")
        print("1) Antenna Calculators")
        print("2) Configuration Database")
        print("3) Band Frequency Chart")
        print("4) Antenna Formulas")
        print("")
        print("Q) Quit  A) About")
        
        try:
            choice = raw_input("\nMenu: [1-4,Q,A] :> ").strip().upper()
        except NameError:
            choice = input("\nMenu: [1-4,A,Q] :> ").strip().upper()
        
        if choice == "1":
            calculator_menu()
        elif choice == "2":
            database_menu(callsign)
        elif choice == "3":
            show_band_chart()
        elif choice == "4":
            show_formulas()
        elif choice == "A":
            show_about()
        elif choice == "Q":
            print("\nExiting...")
            break
        else:
            print("Invalid selection")


def show_help():
    """Display help text."""
    help_text = """
NAME
       antenna.py - Antenna Calculator & Database

SYNOPSIS
       antenna.py [OPTIONS]

VERSION
       {}

DESCRIPTION
       Calculators for common antenna types and a
       user-contributed database of antenna settings
       for portable/field antennas.

OPTIONS
       -h, --help, /?
              Show this help message.

       -v, --version
              Show version number.

CALCULATORS
       Dipole, End-Fed Half-Wave (EFHW), Off-Center
       Fed (OCF), Folded Dipole, Moxon Rectangle,
       Vertical/Ground Plane, NVIS, Loop, Random Wire

DATABASE
       User-contributed configurations for:
       Buddipole, Wolf River Coil, Chameleon, etc.
""".format(VERSION)
    print(help_text)


def main():
    """Main entry point."""
    # Check for help args
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['-h', '--help', '/?']:
            show_help()
            return
        if arg in ['-v', '--version']:
            print("antenna.py version {}".format(VERSION))
            return
    
    # Auto-update check
    check_for_app_update(VERSION, SCRIPT_NAME)
    
    # Get callsign if provided via BPQ
    callsign = get_callsign()
    
    # Run main menu
    main_menu(callsign)


if __name__ == "__main__":
    main()
