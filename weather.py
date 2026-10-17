import urllib.request
import re

def get_live_density(icao):
    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            metar = response.read().decode('utf-8').strip()
            
        temp_match = re.search(r"\b(M?\d{2})/(M?\d{2})?\b", metar)
        if not temp_match:
            return 1.225
            
        temp_str = temp_match.group(1)
        if temp_str.startswith('M'):
            temp_c = -float(temp_str[1:])
        else:
            temp_c = float(temp_str)
            
        press_pascals = 101325.0
        alt_match = re.search(r"\bA(\d{4})\b", metar)
        qnh_match = re.search(r"\bQ(\d{4})\b", metar)
        
        if alt_match:
            inhg = float(alt_match.group(1)) / 100.0
            press_pascals = inhg * 3386.39
        elif qnh_match:
            hpa = float(qnh_match.group(1))
            press_pascals = hpa * 100.0
            
        t_kelvin = temp_c + 273.15
        r_specific = 287.05
        rho = press_pascals / (r_specific * t_kelvin)
        return rho
    except:
        return 1.225