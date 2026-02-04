"""
Premium features registry.

Central registry for all premium modules and their metadata.
Handles license validation for each feature.
"""

from typing import Dict, Any, Optional, Callable
import logging
import os

logger = logging.getLogger(__name__)


class PremiumRegistry:
    """Registry for premium features and their metadata."""

    def __init__(self):
        self._features: Dict[str, Dict[str, Any]] = {}
        self._services: Dict[str, Any] = {}

    def register(
        self,
        feature_id: str,
        name: str,
        description: str,
        module_path: str,
        class_name: str,
        enabled_env_var: Optional[str] = None,
        requires_config: Optional[Dict[str, str]] = None,
        dependencies: Optional[list] = None,
        license_path: Optional[str] = None,
    ) -> None:
        """
        Register a premium feature.

        Args:
            feature_id: Unique identifier (e.g., 'bookcover_api')
            name: User-friendly name
            description: Feature description
            module_path: Python module path (e.g., 'app.services.premium.covers')
            class_name: Service class name (e.g., 'BookcoverService')
            enabled_env_var: Environment variable to enable/disable (default: PREMIUM_{feature_id}_ENABLED)
            requires_config: Dict of required config keys
            dependencies: List of feature IDs this feature depends on
            license_path: Path to license.json file for license validation
        """
        if feature_id in self._features:
            logger.warning(f"PremiumRegistry: Feature '{feature_id}' already registered, overwriting")

        if enabled_env_var is None:
            enabled_env_var = f"PREMIUM_{feature_id.upper()}_ENABLED"

        self._features[feature_id] = {
            'feature_id': feature_id,
            'name': name,
            'description': description,
            'module_path': module_path,
            'class_name': class_name,
            'enabled_env_var': enabled_env_var,
            'requires_config': requires_config or {},
            'dependencies': dependencies or [],
            'license_path': license_path,
            'has_valid_license': False,  # Will be set during license check
            'service': None,  # Lazy-loaded
        }

        logger.info(f"PremiumRegistry: Registered premium feature '{feature_id}'")

    def get_feature_info(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """Get feature metadata."""
        return self._features.get(feature_id)

    def list_features(self) -> Dict[str, Dict[str, Any]]:
        """List all registered features with their metadata."""
        return {
            fid: {
                'name': info['name'],
                'description': info['description'],
                'enabled_env_var': info['enabled_env_var'],
                'requires_config': info['requires_config'],
                'dependencies': info['dependencies'],
            }
            for fid, info in self._features.items()
        }

    def get_service(self, feature_id: str) -> Optional[Any]:
        """Get loaded service instance for a feature (lazy-loaded)."""
        if feature_id not in self._features:
            return None

        feature = self._features[feature_id]

        # Already loaded
        if feature['service'] is not None:
            return feature['service']

        # Try to load
        try:
            service = self._load_service(feature_id)
            if service:
                feature['service'] = service
                return service
        except Exception as e:
            logger.error(f"PremiumRegistry: Failed to load service for '{feature_id}': {e}")

        return None

    def _load_service(self, feature_id: str) -> Optional[Any]:
        """Dynamically load a premium service."""
        feature = self._features.get(feature_id)
        if not feature:
            return None

        # Check if feature is enabled
        if not self._is_enabled(feature_id):
            logger.debug(f"PremiumRegistry: Feature '{feature_id}' is disabled")
            return None

        # Check license (crucial!)
        if not self.check_license(feature_id):
            logger.warning(f"PremiumRegistry: Feature '{feature_id}' license check failed")
            return None

        # Check dependencies
        for dep in feature['dependencies']:
            if not self._is_enabled(dep):
                logger.warning(f"PremiumRegistry: Feature '{feature_id}' requires '{dep}' but it's disabled")
                return None

        # Dynamic import
        try:
            module = __import__(feature['module_path'], fromlist=[feature['class_name']])
            service_class = getattr(module, feature['class_name'])
            logger.info(f"PremiumRegistry: Loaded service for '{feature_id}': {feature['class_name']}")
            return service_class
        except Exception as e:
            logger.error(f"PremiumRegistry: Failed to import {feature['module_path']}.{feature['class_name']}: {e}")
            return None

    def _is_enabled(self, feature_id: str) -> bool:
        """Check if feature is enabled via environment variable."""
        import os
        feature = self._features.get(feature_id)
        if not feature:
            logger.warning(f"PremiumRegistry: Feature '{feature_id}' not registered")
            return False

        env_var = feature['enabled_env_var']
        env_value = os.getenv(env_var, 'false').lower()
        is_enabled = env_value == 'true'
        logger.info(f"PremiumRegistry: Feature '{feature_id}' enabled check: {env_var}={env_value} -> {is_enabled}")
        return is_enabled

    def check_license(self, feature_id: str) -> bool:
        """
        Check if feature has valid license.

        Returns:
            True if license is valid or not required
        """
        from app.services.premium.license import license_manager

        feature = self._features.get(feature_id)
        if not feature:
            return False

        # If license_path is defined, check license
        if feature['license_path']:
            if license_manager.load_license(feature_id, feature['license_path']):
                feature['has_valid_license'] = True
                return True
            else:
                logger.warning(f"PremiumRegistry: License check failed for '{feature_id}'")
                feature['has_valid_license'] = False
                return False

        # No license required
        feature['has_valid_license'] = True
        return True

    def is_enabled(self, feature_id: str) -> bool:
        """Public method to check if feature is enabled."""
        return self._is_enabled(feature_id)

    def get_all_enabled_features(self) -> Dict[str, Any]:
        """Get all enabled premium features."""
        enabled = {}
        for fid, info in self._features.items():
            if self._is_enabled(fid):
                service = self.get_service(fid)
                if service:
                    enabled[fid] = {
                        'name': info['name'],
                        'service': service,
                    }
        return enabled

    def get_service_method(self, feature_id: str, method_name: str) -> Optional[Callable]:
        """
        Get a specific method from a premium service.

        Useful for calling service methods without having the full service class.

        Args:
            feature_id: Feature ID
            method_name: Method name to call

        Returns:
            Method callable or None
        """
        service = self.get_service(feature_id)
        if service and hasattr(service, method_name):
            return getattr(service, method_name)
        return None


# Global registry instance
premium_registry = PremiumRegistry()
