"""
Premium manager - central point for managing premium features.

Provides high-level API for accessing premium services loaded dynamically.
"""

from typing import Optional, Any, Dict
from app.services.premium.loader import PremiumModuleLoader
import logging

logger = logging.getLogger(__name__)


class PremiumManager:
    """
    Central manager for all premium features.

    Usage:
        if PremiumManager.is_enabled('biblioteka_narodowa'):
            cover = PremiumManager.call('biblioteka_narodowa', 'BibliotekaNarodowaService', 'search_by_isbn', isbn='...')
    """

    _initialized = False

    @staticmethod
    def init() -> None:
        """
        Initialize premium manager and discover available modules.

        Should be called once at application startup in create_app() or similar.
        """
        if PremiumManager._initialized:
            logger.debug("PremiumManager: Already initialized")
            return

        logger.info("PremiumManager: Initializing premium features...")
        
        # Discover and validate all premium modules
        modules = PremiumModuleLoader.discover_modules()
        
        for module_id in modules:
            if PremiumModuleLoader.validate_license(module_id):
                logger.info(f"✅ PremiumManager: Premium module '{module_id}' available")
            else:
                logger.warning(f"❌ PremiumManager: Premium module '{module_id}' not available (no valid license)")

        PremiumManager._initialized = True
        logger.info("PremiumManager: Initialization complete")


    @staticmethod
    def is_enabled(feature_id: str) -> bool:
        """Check if a premium feature is enabled and licensed."""
        return PremiumModuleLoader.is_enabled(feature_id)

    @staticmethod
    def get_service_class(feature_id: str, class_name: str) -> Optional[Any]:
        """Get a premium service class."""
        return PremiumModuleLoader.get_service_class(feature_id, class_name)

    @staticmethod
    def call(
        feature_id: str,
        class_name: str,
        method_name: str,
        **kwargs
    ) -> Optional[Any]:
        """
        Call a static method on a premium service.

        Args:
            feature_id: Premium feature ID (module identifier)
            class_name: Service class name
            method_name: Static method name to call
            **kwargs: Arguments to pass to the method

        Returns:
            Method result or None if feature is disabled/not found

        Example:
            book_data = PremiumManager.call(
                'biblioteka_narodowa',
                'BibliotekaNarodowaService',
                'search_by_isbn',
                isbn='9780545003957'
            )
        """
        if not PremiumModuleLoader.is_enabled(feature_id):
            logger.debug(f"PremiumManager: Feature '{feature_id}' is not enabled")
            return None

        service_class = PremiumModuleLoader.get_service_class(feature_id, class_name)
        if service_class is None:
            logger.warning(f"PremiumManager: Class '{class_name}' not found in '{feature_id}'")
            return None

        try:
            method = getattr(service_class, method_name, None)
            if method is None:
                logger.warning(f"PremiumManager: Method '{method_name}' not found in '{class_name}'")
                return None
            
            result = method(**kwargs)
            logger.debug(f"PremiumManager: Called {feature_id}.{class_name}.{method_name}")
            return result
        except Exception as e:
            logger.error(f"PremiumManager: Error calling {feature_id}.{class_name}.{method_name}: {e}")
            return None

    @staticmethod
    def list_modules() -> Dict[str, Dict[str, Any]]:
        """List all available premium modules and their status."""
        return PremiumModuleLoader.list_available_modules()

    @staticmethod
    def list_features() -> Dict[str, Dict[str, Any]]:
        """
        List all available premium features (alias for list_modules for compatibility).
        
        Returns:
            Dict with format expected by admin panel
        """
        modules = PremiumModuleLoader.list_available_modules()
        
        # Map modules to feature format for admin panel compatibility
        features = {}
        module_names = {
            'metadata': {'name': 'Biblioteka Narodowa Metadata', 'description': 'Premium metadata from Polish National Library API'},
            'covers': {'name': 'Bookcover API (Goodreads)', 'description': 'Premium covers from bookcover.longitood.com'},
        }
        
        for module_id, info in modules.items():
            meta = module_names.get(module_id, {})
            features[module_id] = {
                'feature_id': module_id,
                'name': meta.get('name', module_id.title()),
                'description': meta.get('description', ''),
                'enabled': info.get('enabled', False),
                'expiry_date': info.get('expiry_date'),
                'requires_config': {},
            }
        
        return features

    @staticmethod
    def reload() -> None:
        """
        Reload all premium modules and their licenses.
        
        Useful after uploading new modules or updating licenses.
        """
        logger.info("PremiumManager: Reloading premium modules...")
        PremiumModuleLoader.reload_all()
        logger.info("PremiumManager: Premium modules reloaded successfully")
