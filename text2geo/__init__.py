"""
text2geo - Offline fuzzy geocoder for converting place names to coordinates.

Supports World, CIS, and Russia-only datasets powered by GeoNames.

Usage:
    >>> from text2geo import Geocoder
    >>> geo = Geocoder(dataset="cis")
    >>> geo.geocode("Москва")
    {'name': 'Moscow', 'lat': 55.75222, 'lon': 37.61556, ...}
"""

__version__ = "0.1.0"
__author__ = "text2geo contributors"

from text2geo.geocoder import Geocoder
from text2geo.data import download, available_datasets, is_downloaded

__all__ = ["Geocoder", "download", "available_datasets", "is_downloaded"]
