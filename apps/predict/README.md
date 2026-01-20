# PREDICT - HF Propagation Estimator

Estimates best HF bands and times for contacts between two locations using a simplified ionospheric model with resilient solar data handling.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Accuracy & Limitations](#accuracy--limitations)
- [Usage](#usage)
- [Location Input Formats](#location-input-formats)
- [Solar Data Strategy](#solar-data-strategy)
- [Technical Details](#technical-details)
- [Files](#files)
- [Comparison with Full VOACAP](#comparison-with-full-voacap)

## Overview

PREDICT provides "which band should I try?" guidance for HF amateur radio operators. It calculates the Maximum Usable Frequency (MUF) and band reliability estimates using:

- Current solar conditions (SSN, SFI, K-index)
- Path distance and geometry
- Time of day and seasonal factors
- Simplified F2 layer ionospheric model

## Features

- **Resilient data strategy**: Works online, cached, or fully offline
- **Multiple location formats**: Gridsquare, GPS, DMS, state, country, callsign
- **Callsign lookup**: Automatic gridsquare lookup via HamDB API
- **BPQ integration**: Reads LOCATOR from bpq32.cfg
- **Terse output**: Optimized for 1200 baud packet radio
- **No external dependencies**: Pure Python 3.5+ stdlib

## Accuracy & Limitations

### Accuracy

| Model | Accuracy | Computation |
|-------|----------|-------------|
| Full VOACAP (ITU-R P.533) | ~90% | FORTRAN binaries, 50MB data |
| **PREDICT (simplified)** | **~70-80%** | **Pure Python, ~5KB data** |

PREDICT is suitable for:
- ✅ "Which band should I try?" guidance
- ✅ Quick path assessments
- ✅ Offline/low-bandwidth environments

PREDICT is NOT suitable for:
- ❌ Precise circuit planning
- ❌ Antenna pattern optimization
- ❌ Commercial broadcast coverage

### Limitations

| Feature | Full VOACAP | PREDICT |
|---------|-------------|---------|
| F2 layer model | Full ITU-R ray-tracing | Simplified correlation |
| Terrain effects | Yes | No |
| Antenna patterns | 100+ patterns | None (isotropic) |
| Sporadic-E | Predicted | Not modeled |
| Auroral effects | Modeled | Not modeled |
| Multi-hop optimization | Yes | Basic estimate |
| D-layer absorption | Calculated | Estimated |

## Usage

```
$ python3 predict.py

============================================================
PREDICT v1.0 - HF Propagation Estimator
============================================================

Loading solar data...
Solar data: 2 hours old (cached)

Prediction Options:
------------------------------------------------------------
  1) From my location to another ham (by callsign)
  2) From my location to a place
  3) Between two places
------------------------------------------------------------
  A) About this app
  Q) Quit

:> 1
```

### Example Output

```
============================================================
HF Propagation Estimate
============================================================
From: FN43hp
To:   W1ABC (FM18lw)

Distance: 680 km    Bearing: 225 (SW)
Solar data: SSN 145, SFI 178 (2 hrs old)

Band   MUF%   Reliability   Best Hours
----   ----   -----------   ----------
80m     92%   Good          02-08 UTC
40m    100%   Excellent     All day
20m    100%   Excellent     12-22 UTC
15m     78%   Fair          14-18 UTC
10m     45%   Poor          15-17 UTC

Recommended: 40m (Excellent, All day)

------------------------------------------------------------
NOTE: Simplified model (~70-80% accuracy).
For precise predictions: voacap.com
------------------------------------------------------------
```

## Location Input Formats

| Format | Example | Notes |
|--------|---------|-------|
| Gridsquare (4-char) | `FN43` | ~70x50 mi resolution |
| Gridsquare (6-char) | `FN43hp` | ~5x2.5 mi resolution |
| Decimal GPS | `43.65, -70.25` | Lat, Lon |
| DMS | `43d39m32sN 70d15m24sW` | Degrees/minutes/seconds |
| US State | `Maine` or `ME` | Uses state centroid |
| Country | `Germany` | Uses country centroid |
| Callsign | `W1ABC` | Looks up via HamDB API |

## Solar Data Strategy

PREDICT uses a resilient strategy to handle intermittent connectivity:

```
1. TRY ONLINE (hamqsl.com, 3-sec timeout)
   ├─ Success → Cache result, use fresh data
   └─ Fail → Continue to step 2

2. CHECK CACHE (solar_cache.json)
   ├─ Fresh (< 24 hours) → Use cached data
   ├─ Stale (1-7 days) → Prompt user for current SSN
   ├─ Very stale (> 7 days) → Warn, use anyway
   └─ No cache → Continue to step 3

3. USER INPUT / DEFAULTS
   ├─ Interactive → Prompt for SSN/SFI
   └─ Non-interactive → Use defaults (SSN=100)
```

### Solar Data Sources

- **Primary**: hamqsl.com (free, no API key)
- **Fallback**: User-supplied values
- **Check current conditions**: spaceweather.com, hamqsl.com

## Technical Details

### MUF Estimation

The Maximum Usable Frequency is estimated using:

```
MUF = foF2 × oblique_factor
```

Where:
- `foF2` = F2 critical frequency, correlated to SSN
- `oblique_factor` = Path geometry factor (1.0 - 3.5)

Critical frequency correlation:
```
foF2 ≈ 3.0 + 0.06 × √(SSN + 10)
```

Adjustments applied for:
- Latitude (mid-latitudes stronger)
- Time of day (peaks ~14:00 local)
- Season (winter enhancement)

### Reliability Estimation

Signal reliability is estimated from:
- Frequency vs MUF ratio (optimal at 80-90% of MUF)
- Path distance (multi-hop penalty)
- Geomagnetic K-index (disturbance penalty)

### Path Geometry

- Great-circle distance: Haversine formula
- Bearing: Initial true bearing
- Midpoint: Used for ionospheric calculations
- Hop estimation: 1 hop per ~2500 km

## Files

```
apps/
├── predict.py              # Main application
└── predict/
    ├── __init__.py         # Package init
    ├── geo.py              # Coordinate utilities
    ├── solar.py            # Solar data fetching/caching
    ├── ionosphere.py       # MUF estimation model
    ├── regions.json        # US state + country centroids
    ├── solar_cache.json    # Cached solar data (auto-generated)
    └── README.md           # This file
```

## Comparison with Full VOACAP

### Why Not Use Full VOACAP?

Full VOACAP (voacapl) requires:
- FORTRAN binaries compiled for target architecture
- ~50MB of ionospheric coefficient data files
- Complex installation process
- Significant disk space and memory

PREDICT provides:
- Pure Python, no compilation
- ~5KB total data files
- Works on resource-constrained systems (RPi)
- Suitable for packet radio BBS environment

### When to Use Full VOACAP

For precise propagation analysis, install full VOACAP:
- **voacap.com**: Online interface (no installation)
- **pythonprop**: Python GUI wrapper (requires voacapl)
- **voacapl**: Linux port of VOACAP engine

References:
- https://github.com/jawatson/voacapl
- https://github.com/jawatson/pythonprop
- https://www.voacap.com

## Author

Brad Brown KC1JMH

## License

MIT License - See repository LICENSE file
