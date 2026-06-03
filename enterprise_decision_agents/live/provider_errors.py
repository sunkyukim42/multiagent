from __future__ import annotations


class LiveProviderError(ValueError):
    """Base error for Task 11 provider and collection failures."""


class ProviderConfigError(LiveProviderError):
    """Raised when provider configuration is invalid."""


class ProviderDisabledError(LiveProviderError):
    """Raised when a configured provider is disabled."""


class ProviderMissingKeyError(LiveProviderError):
    """Raised when a live provider call lacks a required API key."""


class ProviderRateLimitError(LiveProviderError):
    """Raised when provider limits would be exceeded or a 429 is returned."""


class ProviderFetchError(LiveProviderError):
    """Raised when a live provider request fails."""
