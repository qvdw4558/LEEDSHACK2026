from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

def city_to_coordinates(city_name: str):
    """
    Convert a city name to (latitude, longitude).

    Parameters:
        city_name (str): Name of the city (e.g. "Leeds, UK")

    Returns:
        tuple: (latitude, longitude) or None if not found
    """
    geolocator = Nominatim(user_agent="city_to_coords_app")

    try:
        location = geolocator.geocode(city_name)
        if location is None:
            return None
        return location.latitude, location.longitude

    except (GeocoderTimedOut, GeocoderServiceError):
        return None


