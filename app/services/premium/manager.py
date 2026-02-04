"""
Premium manager - central point for managing premium features.

Provides high-level API for accessing premium services without modifying core code.
"""

from typing import Optional, Any, Dict, Callable
from app.services.premium.registry import premium_registry
import logging

logger = logging.getLogger(__name__)


class PremiumManager:
    """
    Central manager for all premium features.

    Usage:
        PremiumManager.init()  # Call once at app startup

        if PremiumManager.is_enabled('bookcover_api'):
            cover = PremiumManager.call('bookcover_api', 'get_cover_from_bookcover_api', isbn='...')
    """

    _initialized = False

    @staticmethod
    def init() -> None:
        """
        Initialize premium manager and register all available premium features.

        Should be called once at application startup in create_app() or similar.
        """
        if PremiumManager._initialized:
            logger.debug("PremiumManager: Already initialized")
            return

        logger.info("PremiumManager: Initializing premium features...")

        # Register available premium features
        # Format: (feature_id, name, description, module_path, class_name, env_var)

        premium_registry.register(
            feature_id='bookcover_api',
            name='Bookcover API (Goodreads)',
            description='Premium covers from bookcover.longitood.com',
            module_path='app.services.premium.covers.bookcover_service',
            class_name='BookcoverService',
            enabled_env_var='PREMIUM_BOOKCOVER_ENABLED',
            requires_config={
                'API_URL': 'https://bookcover.longitood.com/bookcover',
            },
            license_path='app/services/premium/covers/license.json',
        )

        # TODO: Register more premium features as they're added
        # premium_registry.register(
        #     feature_id='metadata',
        #     name='Premium Metadata',
        #     ...
        # )

        PremiumManager._initialized = True
        logger.info("PremiumManager: Initialization complete")

    @staticmethod
    def is_enabled(feature_id: str) -> bool:
        """Check if a premium feature is enabled."""
        return premium_registry.is_enabled(feature_id)

    @staticmethod
    def get_service(feature_id: str) -> Optional[Any]:
        """Get a premium service class (not instance)."""
        return premium_registry.get_service(feature_id)

    @staticmethod
    def call(
        feature_id: str,
        method_name: str,
        **kwargs
    ) -> Optional[Any]:
        """
        Call a static method on a premium service.

        Args:
            feature_id: Premium feature ID
            method_name: Static method name to call
            **kwargs: Arguments to pass to the method

        Returns:
            Method result or None if feature is disabled/not found

        Example:
            cover = PremiumManager.call('bookcover_api', 'get_cover_from_bookcover_api',
                                       isbn='9780545003957', title='The Hobbit')
        """
        if not premium_registry.is_enabled(feature_id):
            logger.debug(f"PremiumManager: Feature '{feature_id}' is not enabled")
            return None

        method = premium_registry.get_service_method(feature_id, method_name)
        if method is None:
            logger.warning(f"PremiumManager: Method '{method_name}' not found in '{feature_id}'")
            return None

        try:
            result = method(**kwargs)
            logger.debug(f"PremiumManager: Called {feature_id}.{method_name}")
            return result
        except Exception as e:
            logger.error(f"PremiumManager: Error calling {feature_id}.{method_name}: {e}")
            return None

    @staticmethod
    def list_features() -> Dict[str, Dict[str, Any]]:
        """List all registered premium features and their status."""
        return premium_registry.list_features()

    @staticmethod
    def get_enabled_features() -> Dict[str, Any]:
        """Get all currently enabled premium features."""
        return premium_registry.get_all_enabled_features()

    @staticmethod
    def feature_info(feature_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a premium feature."""
        info = premium_registry.get_feature_info(feature_id)
        if info:
            # Remove service reference from returned info
            return {
                'feature_id': info['feature_id'],
                'name': info['name'],
                'description': info['description'],
                'enabled': premium_registry.is_enabled(feature_id),
                'enabled_env_var': info['enabled_env_var'],
                'requires_config': info['requires_config'],
                'dependencies': info['dependencies'],
            }
        return None
