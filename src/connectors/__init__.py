"""Data connectors for marketing platforms."""

from .base import (
    AuthenticationError,
    BaseConnector,
    ConnectorError,
    RateLimitError,
    TemporaryError,
)
from .google_ads import GoogleAdsConnector
from .meta_ads import MetaAdsConnector
from .mock_data import MockDataGenerator

__all__ = [
    "AuthenticationError",
    "BaseConnector",
    "ConnectorError",
    "GoogleAdsConnector",
    "MetaAdsConnector",
    "MockDataGenerator",
    "RateLimitError",
    "TemporaryError",
]
