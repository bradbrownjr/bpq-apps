#!/usr/bin/env python3
"""
PREDICT Ionospheric Propagation Model
--------------------------------------
Simplified MUF estimation using ITU-R correlations.

This is NOT a full VOACAP implementation. It provides approximate
predictions suitable for "which band should I try?" guidance.

Accuracy: ~70-80% vs full VOACAP (~90%)

Limitations:
- No terrain modeling
- No antenna pattern effects
- No sporadic-E prediction
- No auroral effects
- Simplified F2 layer model only
- No multi-hop optimization

Author: Brad Brown KC1JMH
Version: 1.3
Date: January 2026
"""

import math
from datetime import datetime

# HF Amateur bands (MHz)
BANDS = {
    '80m': {'freq': 3.8, 'low': 3.5, 'high': 4.0},
    '40m': {'freq': 7.2, 'low': 7.0, 'high': 7.3},
    '30m': {'freq': 10.1, 'low': 10.1, 'high': 10.15},
    '20m': {'freq': 14.2, 'low': 14.0, 'high': 14.35},
    '17m': {'freq': 18.1, 'low': 18.068, 'high': 18.168},
    '15m': {'freq': 21.2, 'low': 21.0, 'high': 21.45},
    '12m': {'freq': 24.9, 'low': 24.89, 'high': 24.99},
    '10m': {'freq': 28.5, 'low': 28.0, 'high': 29.7},
}

# All HF bands for prediction (comprehensive coverage)
DISPLAY_BANDS = ['80m', '40m', '30m', '20m', '17m', '15m', '12m', '10m']

# Earth radius for geometry calculations
EARTH_RADIUS_KM = 6371.0

# F2 layer height (km) - simplified constant
F2_HEIGHT_KM = 300.0


def estimate_muf(ssn, distance_km, lat_mid, hour_utc, month=None):
    """
    Estimate Maximum Usable Frequency (MUF) for a path.
    
    Uses simplified ITU-R correlation:
    - Critical frequency from SSN
    - Path geometry for oblique factor
    - Time/latitude adjustment for F2 layer
    
    Args:
        ssn: Sunspot number
        distance_km: Great circle distance
        lat_mid: Latitude of path midpoint
        hour_utc: UTC hour (0-23)
        month: Month (1-12), defaults to current
        
    Returns:
        Estimated MUF in MHz
    """
    if month is None:
        month = datetime.utcnow().month
    
    # Step 1: Estimate F2 critical frequency (foF2)
    # More realistic correlation: foF2 ranges from ~4 MHz (solar min) to ~14 MHz (solar max)
    # Using simplified CCIR formula approximation
    fo_f2_base = 4.0 + 0.067 * ssn
    fo_f2_base = min(fo_f2_base, 15.0)  # Cap at realistic maximum
    
    # Step 2: Latitude adjustment
    # F2 layer is stronger at mid-latitudes (around 30-50 degrees)
    # Reduced at equator (equatorial trough) and high latitudes
    lat_abs = abs(lat_mid)
    if lat_abs < 20:
        lat_factor = 0.85  # Equatorial reduction
    elif lat_abs < 60:
        lat_factor = 1.0 + 0.15 * math.cos(math.radians(2 * (lat_abs - 40)))
    else:
        lat_factor = 0.7  # High latitude reduction
    
    # Step 3: Time of day adjustment
    # F2 peaks in early afternoon local time (around 13:00-15:00 local)
    # Minimum at night but doesn't go to zero
    local_noon_offset = lat_mid / 15.0  # Rough longitude->time approximation
    local_hour = (hour_utc - local_noon_offset) % 24
    
    # Diurnal variation: peaks around 14:00 local, minimum ~0.4 at night
    if 6 <= local_hour <= 18:
        # Daytime: sinusoidal with peak at 14:00
        hour_factor = 0.6 + 0.4 * math.cos(math.radians((local_hour - 14) * 15))
    else:
        # Nighttime: reduced but not zero (F2 persists)
        hour_factor = 0.5
    
    # Step 4: Seasonal adjustment
    # F2 has complex seasonal behavior, simplified here
    # Generally higher in winter months for mid-latitudes
    if lat_mid > 0:  # Northern hemisphere
        winter_month = 1  # January
    else:
        winter_month = 7  # July
    months_from_winter = min(abs(month - winter_month), 12 - abs(month - winter_month))
    season_factor = 1.0 + 0.15 * math.cos(math.radians(months_from_winter * 30))
    
    # Combined critical frequency
    fo_f2 = fo_f2_base * lat_factor * hour_factor * season_factor
    
    # Step 5: Calculate MUF from path geometry
    # MUF = foF2 * sec(theta) where theta is elevation angle
    # For oblique incidence, MUF can be 2-4x the critical frequency
    
    num_hops = estimate_hops(distance_km)
    hop_distance = distance_km / num_hops
    
    # Oblique factor increases with hop distance
    # Short paths (NVIS): factor ~1.0
    # Medium paths: factor ~2.5-3.0
    # Long paths: factor ~3.0-3.5
    if hop_distance < 500:
        oblique_factor = 1.0 + (hop_distance / 1000.0)  # NVIS region
    else:
        oblique_factor = 1.5 + (hop_distance / 2000.0)
    oblique_factor = min(oblique_factor, 3.5)  # Cap at realistic value
    
    muf = fo_f2 * oblique_factor
    
    return max(muf, 3.0)  # Floor at 3 MHz (practical minimum)


def estimate_hops(distance_km):
    """
    Estimate number of ionospheric hops for distance.
    
    Single hop: ~0-2500 km
    Two hops: ~2500-5000 km
    Three hops: ~5000-7500 km
    
    Args:
        distance_km: Great circle distance
        
    Returns:
        Number of hops (1-4)
    """
    if distance_km < 500:
        return 1  # Ground wave or NVIS
    elif distance_km < 2500:
        return 1
    elif distance_km < 5000:
        return 2
    elif distance_km < 7500:
        return 3
    else:
        return 4


def estimate_reliability(freq_mhz, muf, distance_km, kindex=3):
    """
    Estimate signal reliability for a frequency.
    
    Args:
        freq_mhz: Operating frequency
        muf: Maximum Usable Frequency
        distance_km: Path distance
        kindex: Geomagnetic K-index (0-9)
        
    Returns:
        Reliability percentage (0-100)
    """
    # Frequency must be below MUF
    if freq_mhz > muf:
        return 0
    
    # Frequency ratio to MUF
    # Best results at 80-90% of MUF (FOT - Frequency of Optimum Traffic)
    # Too low: D-layer absorption increases, signal-to-noise decreases
    # Too high: approaching MUF, fading increases
    fot_ratio = freq_mhz / muf
    
    if fot_ratio > 0.95:
        # Very close to MUF - high fading, unreliable
        base_rel = 40
    elif fot_ratio > 0.85:
        # Near FOT - optimal operating range
        base_rel = 95
    elif fot_ratio > 0.70:
        # Good operating range
        base_rel = 90
    elif fot_ratio > 0.50:
        # Below optimum - still good but more absorption
        base_rel = 80
    elif fot_ratio > 0.30:
        # Well below FOT - increasing D-layer absorption
        base_rel = 70
    else:
        # Much lower than MUF - significant absorption on lower bands
        # But low bands (80m, 40m) work well at night
        base_rel = 60
    
    # Distance penalty for very long paths (more hops = more loss)
    if distance_km > 10000:
        base_rel -= 15
    elif distance_km > 5000:
        base_rel -= 10
    elif distance_km > 2500:
        base_rel -= 5
    
    # K-index penalty for disturbed conditions
    # K>=5 is storm level, seriously degrades HF
    if kindex >= 7:
        base_rel -= 40
    elif kindex >= 5:
        base_rel -= 25
    elif kindex >= 4:
        base_rel -= 10
    
    return max(0, min(100, base_rel))


def estimate_best_hours(freq_mhz, ssn, lat_mid, month=None):
    """
    Estimate best UTC hours for a frequency.
    
    Args:
        freq_mhz: Operating frequency
        ssn: Sunspot number
        lat_mid: Path midpoint latitude
        month: Month (1-12)
        
    Returns:
        Tuple (start_hour, end_hour) or None if band closed
    """
    if month is None:
        month = datetime.utcnow().month
    
    # Check MUF at various hours
    usable_hours = []
    for hour in range(24):
        muf = estimate_muf(ssn, 2000, lat_mid, hour, month)  # Use typical distance
        if freq_mhz <= muf * 0.95:
            usable_hours.append(hour)
    
    if not usable_hours:
        return None
    
    # Find contiguous ranges
    if len(usable_hours) == 24:
        return (0, 24)  # All day
    
    # Find the longest contiguous block
    # Simple approach: return first and last usable hour
    return (min(usable_hours), max(usable_hours))


def predict_bands(distance_km, lat_mid, ssn, kindex=3, hour_utc=None, month=None):
    """
    Predict propagation for all HF bands.
    
    Args:
        distance_km: Great circle distance
        lat_mid: Path midpoint latitude
        ssn: Sunspot number
        kindex: Geomagnetic K-index
        hour_utc: UTC hour (defaults to current)
        month: Month (defaults to current)
        
    Returns:
        List of dicts with band predictions
    """
    if hour_utc is None:
        hour_utc = datetime.utcnow().hour
    if month is None:
        month = datetime.utcnow().month
    
    # Calculate MUF for this path
    muf = estimate_muf(ssn, distance_km, lat_mid, hour_utc, month)
    
    predictions = []
    
    for band_name in DISPLAY_BANDS:
        band = BANDS[band_name]
        freq = band['freq']
        
        # Calculate MUF percentage
        muf_pct = min(100, int((freq / muf) * 100)) if muf > 0 else 0
        
        # Calculate reliability
        rel = estimate_reliability(freq, muf, distance_km, kindex)
        
        # Estimate best hours
        best_hours = estimate_best_hours(freq, ssn, lat_mid, month)
        
        # Format best hours string
        if best_hours is None:
            hours_str = "Closed"
            rel = 0
            muf_pct = 0
        elif best_hours[0] == 0 and best_hours[1] == 24:
            hours_str = "All day"
        else:
            hours_str = "{:02d}-{:02d} UTC".format(best_hours[0], best_hours[1])
        
        # Determine reliability label
        if rel >= 80:
            rel_label = "Excellent"
        elif rel >= 60:
            rel_label = "Good"
        elif rel >= 40:
            rel_label = "Fair"
        elif rel > 0:
            rel_label = "Poor"
        else:
            rel_label = "Closed"
        
        predictions.append({
            'band': band_name,
            'freq': freq,
            'muf_pct': muf_pct,
            'reliability': rel,
            'rel_label': rel_label,
            'best_hours': hours_str,
            'usable': rel > 0
        })
    
    return predictions


def get_solar_context(ssn, sfi, kindex, aindex):
    """
    Generate human-readable solar conditions context.
    
    Args:
        ssn: Sunspot number
        sfi: Solar flux index
        kindex: Geomagnetic K-index (0-9)
        aindex: A-index
        
    Returns:
        Tuple (conditions_str, warnings)
    """
    # Solar activity level based on SSN
    if ssn >= 150:
        solar_level = "HIGH (Solar max active)"
    elif ssn >= 100:
        solar_level = "MODERATE-HIGH"
    elif ssn >= 50:
        solar_level = "MODERATE"
    elif ssn >= 25:
        solar_level = "LOW-MODERATE"
    else:
        solar_level = "LOW (Solar min)"
    
    # Geomagnetic disturbance level
    if kindex >= 7:
        geo_level = "SEVERE STORM (K={})".format(kindex)
        geo_warning = "MAJOR geomagnetic disturbance! HF severely degraded."
    elif kindex >= 5:
        geo_level = "STORM (K={})".format(kindex)
        geo_warning = "Geomagnetic storm in progress. HF conditions poor."
    elif kindex >= 4:
        geo_level = "UNSETTLED (K={})".format(kindex)
        geo_warning = "Unsettled conditions. HF degraded."
    elif kindex >= 2:
        geo_level = "QUIET (K={})".format(kindex)
        geo_warning = None
    else:
        geo_level = "VERY QUIET (K={})".format(kindex)
        geo_warning = None
    
    # Solar flux effect
    if sfi >= 200:
        sfi_note = "Very high solar activity"
    elif sfi >= 150:
        sfi_note = "High solar activity"
    elif sfi >= 100:
        sfi_note = "Moderate solar activity"
    elif sfi >= 80:
        sfi_note = "Low solar activity"
    else:
        sfi_note = "Very low solar activity"
    
    context = "Solar: {} (SSN {})\nGeomagnetic: {}\n{}".format(
        solar_level, ssn, geo_level, sfi_note
    )
    
    warnings = []
    if geo_warning:
        warnings.append(geo_warning)
    
    if ssn < 30:
        warnings.append("WARNING: Low solar activity. Only 80m/40m typically open.")
    
    return (context, warnings)


def format_prediction_table_with_context(predictions, distance_km, bearing_deg, 
                                         ssn, sfi, kindex, aindex, solar_status):
    """
    Format predictions with solar context.
    
    Args:
        predictions: List from predict_bands()
        distance_km: Path distance
        bearing_deg: Path bearing
        ssn, sfi, kindex, aindex: Solar parameters
        solar_status: Solar data status string
        
    Returns:
        Formatted string with full context
    """
    lines = []
    
    # Solar context
    context_str, warnings = get_solar_context(ssn, sfi, kindex, aindex)
    
    lines.append("")
    lines.append("SOLAR CONDITIONS:")
    lines.append("-" * 60)
    for line in context_str.split('\n'):
        lines.append(line)
    lines.append("")
    
    # Warnings
    if warnings:
        lines.append("[!] CONDITIONS ALERT:")
        for warning in warnings:
            lines.append("  - {}".format(warning))
        lines.append("")
    
    # Band predictions
    lines.append("Band   MUF%   Reliability   Best Hours")
    lines.append("----   ----   -----------   ----------")
    
    for pred in predictions:
        if pred['usable']:
            line = "{:<6} {:>3}%   {:<11}   {}".format(
                pred['band'],
                pred['muf_pct'],
                pred['rel_label'],
                pred['best_hours']
            )
        else:
            line = "{:<6}  --    Closed        --".format(pred['band'])
        lines.append(line)
    
    lines.append("")
    
    return "\n".join(lines)



def get_recommendation(predictions):
    """
    Get recommended band from predictions.
    
    Args:
        predictions: List from predict_bands()
        
    Returns:
        String with recommendation and current UTC time
    """
    # Find best band by reliability
    usable = [p for p in predictions if p['usable']]
    
    if not usable:
        return "No bands currently open for this path."
    
    # Sort by reliability, prefer higher frequencies if equal
    best = sorted(usable, key=lambda p: (-p['reliability'], -p['freq']))[0]
    
    # Get current UTC time
    utc_now = datetime.utcnow()
    utc_str = utc_now.strftime("%H%M UTC")
    
    return "Recommended: {} ({}, {})\n  UTC: {}".format(
        best['band'], 
        best['rel_label'],
        best['best_hours'],
        utc_str
    )
