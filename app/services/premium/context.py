"""
Premium context manager - stores current tenant's premium feature settings.

This allows premium features to be enabled/disabled per-tenant instead of globally.
"""

from typing import Optional, Set
from flask import g
import logging

logger = logging.getLogger(__name__)


class PremiumContext:
    """
    Context manager for tenant-specific premium features.
    
    Stores enabled premium features for the current tenant in Flask's g object.
    This is populated when a user logs in or a request context is established.
    """
    
    _CONTEXT_KEY = '_premium_enabled_features'
    _TENANT_KEY = '_current_tenant_id'
    
    @classmethod
    def set_for_tenant(cls, tenant_id: Optional[int], enabled_features: Set[str]) -> None:
        """Set enabled premium features for current tenant."""
        g._premium_enabled_features = enabled_features or set()
        g._current_tenant_id = tenant_id
        logger.debug(f"PremiumContext: Set features for tenant {tenant_id}: {enabled_features}")
    
    @classmethod
    def get_enabled_features(cls) -> Set[str]:
        """Get set of enabled premium features for current tenant."""
        return getattr(g, cls._CONTEXT_KEY, set())
    
    @classmethod
    def get_current_tenant_id(cls) -> Optional[int]:
        """Get current tenant ID."""
        return getattr(g, cls._TENANT_KEY, None)
    
    @classmethod
    def is_enabled(cls, feature_id: str) -> bool:
        """Check if a specific premium feature is enabled for current tenant."""
        enabled = cls.get_enabled_features()
        return feature_id in enabled
    
    @classmethod
    def enable_feature(cls, feature_id: str) -> None:
        """Dynamically enable a feature for current request."""
        enabled = cls.get_enabled_features()
        enabled.add(feature_id)
        g._premium_enabled_features = enabled
    
    @classmethod
    def disable_feature(cls, feature_id: str) -> None:
        """Dynamically disable a feature for current request."""
        enabled = cls.get_enabled_features()
        enabled.discard(feature_id)
        g._premium_enabled_features = enabled
    
    @classmethod
    def clear(cls) -> None:
        """Clear context."""
        g._premium_enabled_features = set()
        g._current_tenant_id = None
