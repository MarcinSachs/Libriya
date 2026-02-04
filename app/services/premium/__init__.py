"""
Premium features management system.

Dynamically loads and manages premium modules without requiring changes to core application.
Includes license validation for access control.
"""

from app.services.premium.manager import PremiumManager
from app.services.premium.registry import premium_registry
from app.services.premium.license import license_manager, PremiumLicense

__all__ = [
    'PremiumManager',
    'premium_registry',
    'license_manager',
    'PremiumLicense',
]
