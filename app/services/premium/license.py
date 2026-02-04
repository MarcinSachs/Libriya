"""
Premium license management system.

Each premium module can have a license file for access control.
Supports trial, paid, and unlimited licenses.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)


class PremiumLicense:
    """Represents a license for a premium feature."""

    def __init__(self, license_data: Dict[str, Any]):
        """
        Initialize license from data dict.

        Args:
            license_data: License data (typically loaded from license.json)
        """
        self.feature_id = license_data.get('feature_id')
        self.license_type = license_data.get('license_type', 'trial')  # trial, paid, unlimited
        self.valid_from = license_data.get('valid_from')  # ISO format
        self.valid_until = license_data.get('valid_until')  # ISO format or null for unlimited
        self.max_requests = license_data.get('max_requests')  # null for unlimited
        self.customer_id = license_data.get('customer_id')
        self.customer_name = license_data.get('customer_name')
        self.metadata = license_data.get('metadata', {})
        self._request_count = 0

    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        # Check date range
        from datetime import timezone
        now = datetime.now(timezone.utc)

        if self.valid_from:
            try:
                valid_from = datetime.fromisoformat(self.valid_from.replace('Z', '+00:00'))
                if now < valid_from:
                    logger.warning(f"License not yet valid: {self.feature_id}")
                    return False
            except Exception as e:
                logger.error(f"Error parsing valid_from date: {e}")
                return False

        if self.valid_until:
            try:
                valid_until = datetime.fromisoformat(self.valid_until.replace('Z', '+00:00'))
                if now > valid_until:
                    logger.warning(f"License expired: {self.feature_id}")
                    return False
            except Exception as e:
                logger.error(f"Error parsing valid_until date: {e}")
                return False

        # Check request limit
        if self.max_requests is not None and self._request_count >= self.max_requests:
            logger.warning(f"License request limit exceeded: {self.feature_id}")
            return False

        return True

    def check_and_count(self) -> bool:
        """
        Check if valid and increment request counter.

        Returns:
            True if valid and counter incremented
        """
        if not self.is_valid():
            return False

        if self.max_requests is not None:
            self._request_count += 1

        return True

    def get_info(self) -> Dict[str, Any]:
        """Get license information."""
        return {
            'feature_id': self.feature_id,
            'license_type': self.license_type,
            'valid': self.is_valid(),
            'valid_from': self.valid_from,
            'valid_until': self.valid_until,
            'max_requests': self.max_requests,
            'requests_used': self._request_count,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
        }


class LicenseManager:
    """Manages premium licenses for modules."""

    def __init__(self):
        self._licenses: Dict[str, PremiumLicense] = {}

    def load_license(self, feature_id: str, license_path: str) -> bool:
        """
        Load license file for a premium feature.

        Args:
            feature_id: Feature ID (e.g., 'bookcover_api')
            license_path: Path to license.json file

        Returns:
            True if license loaded successfully
        """
        if not os.path.exists(license_path):
            logger.debug(f"LicenseManager: No license file for '{feature_id}': {license_path}")
            return False

        try:
            with open(license_path, 'r') as f:
                license_data = json.load(f)

            # Validate license structure
            if license_data.get('feature_id') != feature_id:
                logger.error(f"LicenseManager: License feature_id mismatch for '{feature_id}'")
                return False

            license = PremiumLicense(license_data)

            if not license.is_valid():
                logger.warning(f"LicenseManager: License invalid for '{feature_id}'")
                return False

            self._licenses[feature_id] = license
            logger.info(f"LicenseManager: Loaded valid license for '{feature_id}'")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"LicenseManager: Invalid JSON in license file for '{feature_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"LicenseManager: Error loading license for '{feature_id}': {e}")
            return False

    def has_valid_license(self, feature_id: str) -> bool:
        """Check if feature has valid license."""
        license = self._licenses.get(feature_id)
        if license is None:
            return False
        return license.is_valid()

    def check_and_count(self, feature_id: str) -> bool:
        """
        Check license validity and increment counter (quota tracking).

        Args:
            feature_id: Feature ID

        Returns:
            True if license valid and usable
        """
        license = self._licenses.get(feature_id)
        if license is None:
            return False
        return license.check_and_count()

    def get_license_info(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """Get license information."""
        license = self._licenses.get(feature_id)
        if license is None:
            return None
        return license.get_info()

    def list_licenses(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded licenses."""
        return {
            fid: license.get_info()
            for fid, license in self._licenses.items()
        }


# Global license manager instance
license_manager = LicenseManager()
