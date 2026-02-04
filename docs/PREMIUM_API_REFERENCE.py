"""
Premium Features API Documentation

This document describes the public API for the Premium Features system.
Designed to be used in application code without any changes to core logic.
"""

# =============================================================================
# PremiumManager - Main Public API
# =============================================================================

from app.services import PremiumManager
from typing import Optional, Dict, Any, Callable

# ─────────────────────────────────────────────────────────────────────────
# 1. Check Feature Status
# ─────────────────────────────────────────────────────────────────────────


def check_feature_enabled():
    """Check if a premium feature is enabled."""
    is_enabled: bool = PremiumManager.is_enabled('bookcover_api')
    # Returns: True if PREMIUM_BOOKCOVER_ENABLED=true, else False


# ─────────────────────────────────────────────────────────────────────────
# 2. Call Premium Service Method
# ─────────────────────────────────────────────────────────────────────────

def call_premium_method():
    """Call a method on a premium service."""
    result = PremiumManager.call(
        'bookcover_api',           # Feature ID
        'get_cover_from_bookcover_api',  # Method name
        isbn='9780545003957',      # Method arguments
        title='The Hobbit',
        author='J.R.R. Tolkien'
    )
    # Returns: Method result or None if feature is disabled


# ─────────────────────────────────────────────────────────────────────────
# 3. Get Feature Information
# ─────────────────────────────────────────────────────────────────────────

def get_feature_info():
    """Get detailed info about a feature."""
    info: Optional[Dict[str, Any]] = PremiumManager.feature_info('bookcover_api')
    """
    Returns:
    {
        'feature_id': 'bookcover_api',
        'name': 'Bookcover API (Goodreads)',
        'description': 'Premium covers from bookcover.longitood.com',
        'enabled': True,
        'enabled_env_var': 'PREMIUM_BOOKCOVER_ENABLED',
        'requires_config': {'API_URL': 'https://bookcover.longitood.com/bookcover'},
        'dependencies': [],
    }
    """


# ─────────────────────────────────────────────────────────────────────────
# 4. List All Features
# ─────────────────────────────────────────────────────────────────────────

def list_all_features():
    """List all registered premium features."""
    features: Dict[str, Dict[str, Any]] = PremiumManager.list_features()
    """
    Returns: Dict of all registered features with metadata:
    {
        'bookcover_api': {
            'name': 'Bookcover API (Goodreads)',
            'description': '...',
            'enabled_env_var': 'PREMIUM_BOOKCOVER_ENABLED',
            'requires_config': {...},
            'dependencies': [],
        },
        # ... more features ...
    }
    """


# ─────────────────────────────────────────────────────────────────────────
# 5. Get Only Enabled Features
# ─────────────────────────────────────────────────────────────────────────

def get_enabled_features():
    """Get all currently enabled premium features."""
    enabled: Dict[str, Any] = PremiumManager.get_enabled_features()
    """
    Returns: Dict of enabled features with loaded service classes:
    {
        'bookcover_api': {
            'name': 'Bookcover API (Goodreads)',
            'service': <class 'BookcoverService'>,
        },
        # ... more enabled features ...
    }
    """


# ─────────────────────────────────────────────────────────────────────────
# 6. Advanced: Get Raw Service Class
# ─────────────────────────────────────────────────────────────────────────

def get_service_class():
    """Get raw service class (advanced usage)."""
    service_class = PremiumManager.get_service('bookcover_api')
    # Returns: BookcoverService class or None

    # Can call static methods directly:
    if service_class:
        result = service_class.get_cover_from_bookcover_api(isbn='...')


# =============================================================================
# Real-World Usage Examples
# =============================================================================

# Example 1: Simple feature check and call
def example_1_simple_call():
    """Simplest usage - just check and call."""
    cover = PremiumManager.call(
        'bookcover_api',
        'get_cover_from_bookcover_api',
        isbn='9780545003957'
    )
    if cover:
        print(f"Got premium cover: {cover}")
    else:
        print("Premium cover not available")


# Example 2: Graceful fallback
def example_2_fallback():
    """Fallback pattern - try premium, use base on failure."""
    from app.services import CoverService

    # Try premium first
    premium_cover = PremiumManager.call(
        'bookcover_api',
        'get_cover_from_bookcover_api',
        isbn='9780545003957'
    )

    if premium_cover:
        return premium_cover

    # Fall back to base service
    cover_url, source = CoverService.get_cover_url(isbn='9780545003957')
    return cover_url


# Example 3: Feature detection in UI
def example_3_feature_detection():
    """Detect enabled features for UI rendering."""
    features = PremiumManager.list_features()

    # Show only enabled features
    premium_indicators = {
        fid: info['name']
        for fid, info in features.items()
        if PremiumManager.is_enabled(fid)
    }

    return premium_indicators
    # Can pass to template: {% if 'bookcover_api' in premium_indicators %}...


# Example 4: Error handling
def example_4_error_handling():
    """Handle errors gracefully."""
    try:
        result = PremiumManager.call(
            'bookcover_api',
            'get_cover_from_bookcover_api',
            isbn='invalid'
        )
    except Exception as e:
        # Errors are caught internally, result will be None
        result = None

    if result is None:
        # Use base service or default
        pass


# Example 5: Check dependencies
def example_5_check_dependencies():
    """Check feature dependencies."""
    info = PremiumManager.feature_info('some_feature')
    if info and info['dependencies']:
        for dep in info['dependencies']:
            if not PremiumManager.is_enabled(dep):
                print(f"Warning: {dep} is required but not enabled")


# =============================================================================
# Available Premium Features Reference
# =============================================================================

"""
Feature ID: 'bookcover_api'
├─ Name: Bookcover API (Goodreads)
├─ Status: Available now
├─ Enable via: PREMIUM_BOOKCOVER_ENABLED=true
├─ License: bookcover.longitood.com terms
├─ Methods:
│  └─ get_cover_from_bookcover_api(isbn=None, title=None, author=None)
│     Returns: Cover URL or None
└─ Example:
   cover = PremiumManager.call('bookcover_api', 'get_cover_from_bookcover_api', isbn='...')


Feature ID: 'metadata' (PLANNED)
├─ Name: Premium Metadata
├─ Status: Planned
├─ Enable via: PREMIUM_METADATA_ENABLED=true
└─ Methods: (To be documented)


Feature ID: 'recommendations' (PLANNED)
├─ Name: Premium Recommendations
├─ Status: Planned
├─ Enable via: PREMIUM_RECOMMENDATIONS_ENABLED=true
└─ Methods: (To be documented)
"""

# =============================================================================
# Integration Checklist
# =============================================================================

"""
□ Call PremiumManager.init() in app/__init__.py (done by default)
□ Set environment variable in .env to enable features
□ Use PremiumManager.call() or PremiumManager.is_enabled() in your code
□ Handle None returns gracefully (feature disabled or error)
□ No changes to core application logic needed!
□ Test with feature enabled and disabled
"""

# =============================================================================
# Performance Notes
# =============================================================================

"""
✓ Premium services are lazy-loaded (only when first called)
✓ Services cached after first load (no re-imports)
✓ PremiumManager.is_enabled() is very fast (simple env var check)
✓ PremiumManager.call() on disabled feature returns None immediately
✓ Safe for production - graceful degradation built-in
"""

# =============================================================================
# Troubleshooting
# =============================================================================

"""
Q: Feature returns None but PREMIUM_*_ENABLED=true?
A: Check error logs (LOG_LEVEL=DEBUG), verify module path and class name

Q: Can I use premium features without environment variable?
A: No - must be explicitly enabled via environment variable

Q: What if premium service throws exception?
A: PremiumManager catches it and returns None, logs error

Q: Can premium features have dependencies?
A: Yes! Register with dependencies=[...], they're checked automatically

Q: How to test premium features?
A: Set PREMIUM_*_ENABLED=true in test config, check for None returns

Q: Performance impact of checking PremiumManager.is_enabled()?
A: Minimal - just reads environment variable, no imports

Q: Can I call premium methods directly?
A: Yes, use PremiumManager.get_service('id').method(), but use
   PremiumManager.call() for simpler code
"""
