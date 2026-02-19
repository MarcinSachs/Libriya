"""
Premium module loader - dynamically loads premium modules from app/services/premium/

Supports loading modules from subdirectories with license validation.
Each module folder must contain:
  - license.json (license configuration)
  - *.py file(s) with module implementation
"""

import os
import sys
import json
import importlib.util
from typing import Optional, Any, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PremiumModuleLoader:
    """Loads premium modules from subdirectories with license validation."""

    PREMIUM_DIR = os.path.join(os.path.dirname(__file__))

    _loaded_modules: Dict[str, Any] = {}
    _module_licenses: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def discover_modules(cls) -> Dict[str, str]:
        """
        Discover all premium modules in subdirectories.

        Module ID is determined from 'module_id' field in license.json, allowing
        any folder name (e.g., 'metadata', 'bookcover', 'biblioteka_narodowa').

        Returns:
            Dict mapping module_id to module_path (e.g., {'metadata': '/path/to/metadata'})
        """
        modules = {}

        try:
            for item in os.listdir(cls.PREMIUM_DIR):
                item_path = os.path.join(cls.PREMIUM_DIR, item)

                # Skip files and special folders
                if not os.path.isdir(item_path) or item.startswith('_'):
                    continue

                # Check if it has license.json (indicator of premium module)
                license_path = os.path.join(item_path, 'license.json')
                if os.path.exists(license_path):
                    try:
                        with open(license_path, 'r', encoding='utf-8') as f:
                            license_data = json.load(f)
                        # Read module_id from license.json, fall back to folder name
                        module_id = license_data.get('module_id', item)
                        modules[module_id] = item_path
                        logger.debug(f"PremiumModuleLoader: Discovered module '{module_id}' in folder '{item}'")
                    except json.JSONDecodeError as e:
                        logger.warning(f"PremiumModuleLoader: Invalid JSON in {item}/license.json: {e}")

        except Exception as e:
            logger.error(f"PremiumModuleLoader: Error discovering modules: {e}")

        return modules

    @classmethod
    def validate_license(cls, module_id: str) -> bool:
        """
        Validate license file for a module.

        Args:
            module_id: Module identifier (folder name)

        Returns:
            True if license is valid and not expired
        """
        module_path = os.path.join(cls.PREMIUM_DIR, module_id)
        license_path = os.path.join(module_path, 'license.json')

        if not os.path.exists(license_path):
            logger.warning(f"PremiumModuleLoader: No license.json for module '{module_id}'")
            return False

        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_data = json.load(f)

            # Check expiry date
            expiry_date = license_data.get('expiry_date')
            if expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date)
                    if datetime.now() > expiry:
                        logger.warning(f"PremiumModuleLoader: License expired for '{module_id}': {expiry_date}")
                        return False
                except ValueError as e:
                    logger.error(f"PremiumModuleLoader: Invalid expiry date format for '{module_id}': {e}")
                    return False

            # Store license data
            cls._module_licenses[module_id] = license_data
            logger.info(f"✅ PremiumModuleLoader: Valid license for '{module_id}'")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"PremiumModuleLoader: Invalid JSON in license for '{module_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"PremiumModuleLoader: Error validating license for '{module_id}': {e}")
            return False

    @classmethod
    def load_module(cls, module_id: str) -> Optional[Any]:
        """
        Dynamically load a premium module.

        Args:
            module_id: Module identifier (e.g., 'biblioteka_narodowa', 'bookcover_api')

        Returns:
            Loaded module or None if not available/not licensed
        """
        # Return cached module
        if module_id in cls._loaded_modules:
            return cls._loaded_modules[module_id]

        # Validate license first
        if not cls.validate_license(module_id):
            logger.warning(f"PremiumModuleLoader: Module '{module_id}' not licensed or license expired")
            return None

        module_path = os.path.join(cls.PREMIUM_DIR, module_id)

        try:
            # Find .py file in module directory
            py_files = [f for f in os.listdir(module_path) if f.endswith('.py') and not f.startswith('_')]

            if not py_files:
                logger.error(f"PremiumModuleLoader: No .py file found in '{module_id}'")
                return None

            py_file = py_files[0]  # Load first .py file
            py_path = os.path.join(module_path, py_file)

            # Dynamic import
            spec = importlib.util.spec_from_file_location(f"premium_{module_id}", py_path)
            if spec is None or spec.loader is None:
                logger.error(f"PremiumModuleLoader: Failed to create spec for '{module_id}'")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"premium_{module_id}"] = module
            spec.loader.exec_module(module)

            cls._loaded_modules[module_id] = module
            logger.info(f"✅ PremiumModuleLoader: Loaded module '{module_id}' from {py_file}")
            return module

        except Exception as e:
            logger.error(f"PremiumModuleLoader: Failed to load module '{module_id}': {e}")
            return None

    @classmethod
    def get_service_class(cls, module_id: str, class_name: str) -> Optional[Any]:
        """
        Get a specific class from a loaded module.

        Args:
            module_id: Module identifier
            class_name: Name of the class to retrieve

        Returns:
            Class object or None
        """
        module = cls.load_module(module_id)
        if module is None:
            return None

        try:
            service_class = getattr(module, class_name, None)
            if service_class is None:
                logger.warning(f"PremiumModuleLoader: Class '{class_name}' not found in module '{module_id}'")
                return None

            return service_class
        except Exception as e:
            logger.error(f"PremiumModuleLoader: Error getting class '{class_name}' from '{module_id}': {e}")
            return None

    @classmethod
    def is_enabled(cls, module_id: str) -> bool:
        """
        Check if a module is available and licensed.

        Args:
            module_id: Module identifier

        Returns:
            True if module can be used
        """
        return cls.load_module(module_id) is not None

    @classmethod
    def list_available_modules(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all available premium modules with their status.

        Returns:
            Dict with module info: {'module_id': {'enabled': bool, 'expiry': str, ...}}
        """
        modules = cls.discover_modules()
        result = {}

        for module_id in modules:
            is_enabled = cls.is_enabled(module_id)
            license_data = cls._module_licenses.get(module_id, {})
            display_name = license_data.get('display_name')
            description = license_data.get('description')
            result[module_id] = {
                'enabled': is_enabled,
                'expiry_date': license_data.get('expiry_date'),
                'path': modules[module_id],
                'display_name': display_name,
                'description': description,
            }
        return result

    @classmethod
    def reload_all(cls) -> None:
        """Reload all modules (clear cache and re-discover)."""
        cls._loaded_modules.clear()
        cls._module_licenses.clear()
        logger.info("PremiumModuleLoader: Reloaded all modules")
