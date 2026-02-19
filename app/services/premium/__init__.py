"""
Premium features management system.

Dynamically loads and manages premium modules with license validation.
Modules are loaded from subdirectories in app/services/premium/
"""

from app.services.premium.manager import PremiumManager
from app.services.premium.loader import PremiumModuleLoader

__all__ = [
    'PremiumManager',
    'PremiumModuleLoader',
]
