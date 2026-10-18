import urllib.request
import json

AIRPORT_COORDS = {
    "CYYZ": (43.6777, -79.6248),
    "KORD": (41.9742, -87.9073),
    "EGLL": (51.4700, -0.4543),
}

FALLBACKS = {
    "CYYZ": 1.208,
    "KORD": 1.205,
    "EGLL": 1.259,
}

def get_live_density(icao):
    if icao not in AIRPORT_COORDS:
        return 1.225

    try:
        import platform
        if hasattr(platform, "window") and hasattr(platform.window, "eval"):
            val = float(platform.window.eval(f"window.live_densities ? window.live_densities['{icao}'] || 0 : 0"))
            if val > 0:
                return val
    except Exception:
        pass

    try:
        lat, lon = AIRPORT_COORDS[icao]
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,surface_pressure"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            temp_c = data['current']['temperature_2m']
            press_pa = data['current']['surface_pressure'] * 100.0
            t_kelvin = temp_c + 273.15
            r_specific = 287.05
            return press_pa / (r_specific * t_kelvin)
    except Exception:
        return FALLBACKS.get(icao, 1.225)