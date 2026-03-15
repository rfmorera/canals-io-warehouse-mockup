from abc import ABC, abstractmethod

from app.exceptions import GeocodingError


class GeocoderInterface(ABC):
    @abstractmethod
    def geocode(self, address: str) -> tuple[float, float]:
        """Returns (latitude, longitude) or raises GeocodingError."""


class MockGeocoder(GeocoderInterface):
    """Deterministic geocoder for testing and local development.

    Derives lat/lng from hash(address) using modulo arithmetic to keep
    values within valid ranges: latitude [-90, 90], longitude [-180, 180].
    """

    def geocode(self, address: str) -> tuple[float, float]:
        if not address:
            raise GeocodingError(f"could not geocode address: {address!r}")
        h = hash(address)
        # Use two independent hash-derived values via bit manipulation
        lat = (h % 18001) / 100.0 - 90.0   # range [-90.0, 90.0]
        lng = ((h >> 16) % 36001) / 100.0- 180.0  # range [-180.0, 180.0]
        return (lat, lng)
