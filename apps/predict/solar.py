#!/usr/bin/env python3
"""
PREDICT Solar Data Utilities
-----------------------------
Resilient solar data fetching with caching and fallback.

Strategy:
1. Try online (hamqsl.com, 3-sec timeout)
2. Use cached data if fresh (< 24 hours)
3. Prompt user if cache is stale (1-7 days)
4. Fall back to stale cache with warning (> 7 days)
5. Last resort: prompt for manual entry or use defaults

Author: Brad Brown KC1JMH
Version: 1.0
Date: January 2026
"""

import os
import json
import time

# Try to import urllib for Python 3.5
try:
    import urllib.request
    import xml.etree.ElementTree as ET
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

# Cache settings
CACHE_FRESH_HOURS = 24      # Cache is "fresh" if under this age
CACHE_STALE_DAYS = 7        # Cache is "stale" but usable if under this
CACHE_FILENAME = 'solar_cache.json'
FETCH_TIMEOUT = 3           # Seconds to wait for online data

# hamqsl.com solar data URL
SOLAR_URL = "https://www.hamqsl.com/solarxml.php"

# Default solar values (conservative, mid-cycle)
DEFAULT_SSN = 100
DEFAULT_SFI = 130
DEFAULT_KINDEX = 3


def get_cache_path():
    """Get path to solar cache file."""
    return os.path.join(os.path.dirname(__file__), CACHE_FILENAME)


def load_cache():
    """
    Load cached solar data.
    
    Returns:
        Dict with solar data and timestamp, or None
    """
    cache_path = get_cache_path()
    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except (IOError, ValueError):
        return None


def save_cache(data):
    """
    Save solar data to cache.
    
    Args:
        data: Dict with ssn, sfi, kindex, timestamp
    """
    cache_path = get_cache_path()
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass  # Cache write failure is not critical


def fetch_online():
    """
    Fetch solar data from hamqsl.com.
    
    Returns:
        Dict with ssn, sfi, kindex or None on failure
    """
    if not HAS_URLLIB:
        return None
    
    try:
        req = urllib.request.Request(
            SOLAR_URL,
            headers={'User-Agent': 'PREDICT-BPQ/1.0'}
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as response:
            xml_data = response.read().decode('utf-8')
        
        root = ET.fromstring(xml_data)
        
        # Parse solar data from XML
        solar = root.find('solardata')
        if solar is None:
            return None
        
        data = {
            'ssn': parse_int(solar.findtext('sunspots'), DEFAULT_SSN),
            'sfi': parse_int(solar.findtext('solarflux'), DEFAULT_SFI),
            'kindex': parse_int(solar.findtext('kindex'), DEFAULT_KINDEX),
            'aindex': parse_int(solar.findtext('aindex'), 10),
            'updated': solar.findtext('updated', ''),
            'timestamp': int(time.time()),
            'source': 'online'
        }
        
        return data
    except Exception:
        return None


def parse_int(value, default):
    """Parse integer with default fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def cache_age_hours(cache):
    """
    Get cache age in hours.
    
    Args:
        cache: Cache dict with timestamp
        
    Returns:
        Age in hours, or float('inf') if invalid
    """
    if not cache or 'timestamp' not in cache:
        return float('inf')
    
    age_seconds = time.time() - cache.get('timestamp', 0)
    return age_seconds / 3600


def cache_age_description(hours):
    """
    Human-readable cache age.
    
    Args:
        hours: Age in hours
        
    Returns:
        String like "2 hours", "3 days", etc.
    """
    if hours < 1:
        return "< 1 hour"
    elif hours < 24:
        return "{:.0f} hour{}".format(hours, 's' if hours >= 2 else '')
    else:
        days = hours / 24
        return "{:.0f} day{}".format(days, 's' if days >= 2 else '')


def get_solar_data(interactive=True):
    """
    Get solar data using resilient strategy.
    
    Strategy:
    1. Try online fetch (3-sec timeout)
    2. Use fresh cache (< 24 hours)
    3. Prompt user if cache is stale
    4. Fall back to stale cache with warning
    5. Use defaults as last resort
    
    Args:
        interactive: If True, prompt user for stale data
        
    Returns:
        Tuple (data_dict, status_message, warning_message)
        - data_dict: {ssn, sfi, kindex, aindex}
        - status_message: Brief status for display
        - warning_message: Warning if data is stale (or None)
    """
    cache = load_cache()
    cache_hours = cache_age_hours(cache)
    
    # Try online first
    online_data = fetch_online()
    
    if online_data:
        # Fresh online data - cache it and return
        save_cache(online_data)
        status = "Solar data: {} (live)".format(online_data.get('updated', 'current'))
        return (online_data, status, None)
    
    # Online failed - check cache
    if cache:
        age_desc = cache_age_description(cache_hours)
        
        if cache_hours < CACHE_FRESH_HOURS:
            # Cache is fresh enough
            status = "Solar data: {} old (cached)".format(age_desc)
            return (cache, status, None)
        
        elif cache_hours < CACHE_STALE_DAYS * 24:
            # Cache is stale but usable - prompt if interactive
            if interactive:
                print("\nSolar data is {} old.".format(age_desc))
                print("Cached: SSN={}, SFI={}".format(
                    cache.get('ssn', '?'), cache.get('sfi', '?')))
                
                user_ssn = prompt_solar_value(
                    "Enter current SSN (or Enter for {}): ".format(cache.get('ssn', DEFAULT_SSN)),
                    cache.get('ssn', DEFAULT_SSN)
                )
                
                if user_ssn != cache.get('ssn'):
                    # User provided new value
                    cache['ssn'] = user_ssn
                    cache['source'] = 'user'
                    save_cache(cache)
                    status = "Solar data: SSN {} (user)".format(user_ssn)
                    return (cache, status, None)
            
            # Use stale cache with warning
            status = "Solar data: {} old".format(age_desc)
            warning = "WARNING: Solar data is {} old. Predictions may vary.".format(age_desc)
            return (cache, status, warning)
        
        else:
            # Cache is very stale (> 7 days)
            if interactive:
                print("\nSolar data is {} old (very stale).".format(age_desc))
                print("Predictions may be inaccurate.")
                
                user_ssn = prompt_solar_value(
                    "Enter current SSN (or Enter for {}): ".format(cache.get('ssn', DEFAULT_SSN)),
                    cache.get('ssn', DEFAULT_SSN)
                )
                
                cache['ssn'] = user_ssn
                cache['source'] = 'user'
                save_cache(cache)
            
            status = "Solar data: {} old".format(age_desc)
            warning = ("WARNING: Solar data is very old ({}). "
                       "Predictions may be significantly inaccurate.").format(age_desc)
            return (cache, status, warning)
    
    # No cache at all - need user input or defaults
    if interactive:
        print("\nNo solar data available (offline, no cache).")
        print("Current SSN can be found at spaceweather.com")
        
        user_ssn = prompt_solar_value(
            "Enter current SSN (or Enter for {}): ".format(DEFAULT_SSN),
            DEFAULT_SSN
        )
        user_sfi = prompt_solar_value(
            "Enter solar flux index (or Enter for {}): ".format(DEFAULT_SFI),
            DEFAULT_SFI
        )
        
        data = {
            'ssn': user_ssn,
            'sfi': user_sfi,
            'kindex': DEFAULT_KINDEX,
            'aindex': 10,
            'timestamp': int(time.time()),
            'source': 'user'
        }
        save_cache(data)
        status = "Solar data: SSN {} (user)".format(user_ssn)
        return (data, status, None)
    
    # Non-interactive fallback to defaults
    data = {
        'ssn': DEFAULT_SSN,
        'sfi': DEFAULT_SFI,
        'kindex': DEFAULT_KINDEX,
        'aindex': 10,
        'timestamp': 0,
        'source': 'default'
    }
    status = "Solar data: defaults (no data)"
    warning = ("WARNING: Using default solar values (SSN={}). "
               "Predictions may be inaccurate.").format(DEFAULT_SSN)
    return (data, status, warning)


def prompt_solar_value(prompt, default):
    """
    Prompt user for solar value with default.
    
    Args:
        prompt: Prompt string
        default: Default value if user presses Enter
        
    Returns:
        Integer value
    """
    try:
        response = input(prompt).strip()
        if not response:
            return default
        return int(response)
    except (ValueError, EOFError):
        return default


def format_solar_summary(data):
    """
    Format solar data for display.
    
    Args:
        data: Solar data dict
        
    Returns:
        Formatted string
    """
    parts = []
    
    if 'ssn' in data:
        parts.append("SSN {}".format(data['ssn']))
    if 'sfi' in data:
        parts.append("SFI {}".format(data['sfi']))
    if 'kindex' in data:
        parts.append("K={}".format(data['kindex']))
    
    return ", ".join(parts)


def get_band_conditions(data):
    """
    Estimate general band conditions from solar data.
    
    Args:
        data: Solar data dict
        
    Returns:
        Dict mapping band to condition string
    """
    ssn = data.get('ssn', DEFAULT_SSN)
    kindex = data.get('kindex', DEFAULT_KINDEX)
    
    # High K-index = disturbed conditions
    if kindex >= 5:
        return {
            '80m': 'Disturbed',
            '40m': 'Disturbed', 
            '20m': 'Poor',
            '15m': 'Poor',
            '10m': 'Closed'
        }
    
    # Estimate based on SSN
    conditions = {}
    
    # 80m - less affected by solar activity
    conditions['80m'] = 'Good' if kindex < 4 else 'Fair'
    
    # 40m - reliable workhorse
    conditions['40m'] = 'Excellent' if ssn > 50 else 'Good'
    
    # 20m - needs moderate activity
    if ssn > 100:
        conditions['20m'] = 'Excellent'
    elif ssn > 50:
        conditions['20m'] = 'Good'
    else:
        conditions['20m'] = 'Fair'
    
    # 15m - needs higher activity
    if ssn > 120:
        conditions['15m'] = 'Good'
    elif ssn > 80:
        conditions['15m'] = 'Fair'
    else:
        conditions['15m'] = 'Poor'
    
    # 10m - needs high activity
    if ssn > 150:
        conditions['10m'] = 'Good'
    elif ssn > 100:
        conditions['10m'] = 'Fair'
    else:
        conditions['10m'] = 'Poor'
    
    return conditions
