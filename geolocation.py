import requests
from typing import Optional, Dict
import time


def get_ip_location(ip: str, max_retries: int = 3, timeout: float = 5.0) -> Optional[Dict[str, str]]:
    """
    Get geolocation information for an IP address.
    
    Uses free geolocation APIs with fallback options.
    
    Args:
        ip: IP address string
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with location info or None if unable to get location
    """
    apis = [
        lambda ip_addr: _query_ipinfo_io(ip_addr, timeout),
        lambda ip_addr: _query_geoip_db(ip_addr, timeout),
        lambda ip_addr: _query_ip_api(ip_addr, timeout),
    ]
    
    for attempt in range(max_retries):
        for api_func in apis:
            try:
                result = api_func(ip)
                if result:
                    return result
            except Exception:
                continue
        
        if attempt < max_retries - 1:
            time.sleep(0.5)
    
    return {"location": "Unknown", "country": "Unknown"}


def _query_ipinfo_io(ip: str, timeout: float) -> Optional[Dict[str, str]]:
    """Query ipinfo.io API"""
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            city = data.get("city", "")
            country = data.get("country", "")
            location = f"{city} {country}".strip() if city else country
            return {
                "location": location or "Unknown",
                "country": country or "Unknown"
            }
    except Exception:
        pass
    return None


def _query_geoip_db(ip: str, timeout: float) -> Optional[Dict[str, str]]:
    """Query geoip-db API"""
    try:
        response = requests.get(f"https://geoip-db.com/json/{ip}", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            city = data.get("city", "")
            country_name = data.get("country_name", "")
            location = f"{city} {country_name}".strip() if city else country_name
            return {
                "location": location or "Unknown",
                "country": country_name or "Unknown"
            }
    except Exception:
        pass
    return None


def _query_ip_api(ip: str, timeout: float) -> Optional[Dict[str, str]]:
    """Query ip-api.com API (free tier)"""
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip}",
            timeout=timeout,
            params={"fields": "city,country,status"}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                country = data.get("country", "")
                location = f"{city} {country}".strip() if city else country
                return {
                    "location": location or "Unknown",
                    "country": country or "Unknown"
                }
    except Exception:
        pass
    return None
