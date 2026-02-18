"""Cache service for frequently accessed data with TTL-based expiration"""

from app import cache
from flask import current_app


def get_tenant_by_id_cached(tenant_id):
    """Get tenant by ID with caching.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Tenant object or None
        
    Cache behavior:
        - Cached for CACHE_TENANT_TIMEOUT (default 1 hour)
        - Cache key: f'tenant_id_{tenant_id}'
    """
    from app.models import Tenant
    
    @cache.cached(
        timeout=current_app.config.get('CACHE_TENANT_TIMEOUT', 3600),
        key_prefix=f'tenant_id_{tenant_id}'
    )
    def _get_tenant():
        return Tenant.query.get(tenant_id)
    
    return _get_tenant()


def get_tenant_by_subdomain_cached(subdomain):
    """Get tenant by subdomain with caching.
    
    Args:
        subdomain: Tenant subdomain
        
    Returns:
        Tenant object or None
        
    Cache behavior:
        - Cached for CACHE_TENANT_TIMEOUT (default 1 hour)
        - Cache key: f'tenant_subdomain_{subdomain}'
    """
    from app.models import Tenant
    
    @cache.cached(
        timeout=current_app.config.get('CACHE_TENANT_TIMEOUT', 3600),
        key_prefix=f'tenant_subdomain_{subdomain}'
    )
    def _get_tenant():
        return Tenant.query.filter_by(subdomain=subdomain).first()
    
    return _get_tenant()


def get_premium_features_cached(tenant_id):
    """Get premium features for tenant with caching.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Set of enabled premium features
        
    Cache behavior:
        - Cached for CACHE_PREMIUM_FEATURES_TIMEOUT (default 1 hour)
        - Cache key: f'premium_features_{tenant_id}'
    """
    from app.models import Tenant
    
    @cache.cached(
        timeout=current_app.config.get('CACHE_PREMIUM_FEATURES_TIMEOUT', 3600),
        key_prefix=f'premium_features_{tenant_id}'
    )
    def _get_features():
        tenant = Tenant.query.get(tenant_id)
        if tenant:
            return tuple(sorted(tenant.get_enabled_premium_features()))
        return tuple()
    
    return set(_get_features())


def invalidate_tenant_cache(tenant_id=None, subdomain=None):
    """Invalidate cached tenant data.
    
    Call this function whenever tenant data is updated in the database.
    
    Args:
        tenant_id: Invalidate this tenant ID cache
        subdomain: Invalidate this subdomain cache
    """
    if tenant_id:
        cache.delete(f'tenant_id_{tenant_id}')
        cache.delete(f'premium_features_{tenant_id}')
    
    if subdomain:
        cache.delete(f'tenant_subdomain_{subdomain}')


def get_user_by_id_cached(user_id):
    """Get user by ID with caching.
    
    Args:
        user_id: User ID
        
    Returns:
        User object or None
        
    Cache behavior:
        - Cached for CACHE_USER_TIMEOUT (default 30 minutes)
        - Shorter TTL than tenant cache since user data changes more frequently
        - Cache key: f'user_id_{user_id}'
    """
    from app.models import User
    
    @cache.cached(
        timeout=current_app.config.get('CACHE_USER_TIMEOUT', 1800),
        key_prefix=f'user_id_{user_id}'
    )
    def _get_user():
        return User.query.get(user_id)
    
    return _get_user()


def invalidate_user_cache(user_id):
    """Invalidate cached user data.
    
    Call this function whenever user data is updated in the database.
    
    Args:
        user_id: User ID to invalidate
    """
    cache.delete(f'user_id_{user_id}')
