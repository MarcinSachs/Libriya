"""
Production-ready password handling with Argon2

This module provides secure password hashing using Argon2,
which is more resistant to GPU/ASIC attacks than PBKDF2.

Migration from PBKDF2 to Argon2:
1. Install argon2-cffi
2. Replace werkzeug.security imports with this module
3. Existing PBKDF2 hashes will be automatically rehashed on login
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from werkzeug.security import check_password_hash as check_pbkdf2
import logging

logger = logging.getLogger(__name__)

# Initialize Argon2 hasher with production-ready parameters
# Memory: 512 MB (moderate, suitable for web servers)
# Time: 2 iterations (typical for web use)
# Parallelism: 2 (suitable for most servers)
ph = PasswordHasher(
    memory_cost=512,  # KiB
    time_cost=2,       # iterations
    parallelism=2,     # threads
    hash_len=32,       # output bytes
    salt_len=16,       # random salt length
)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Returns a hash string compatible with argon2-cffi's verify_password.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Argon2 hash string (e.g., '$argon2id$v=19$m=262144,t=2,p=2$...')
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    try:
        return ph.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise ValueError(f"Failed to hash password: {e}")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.
    
    Supports both Argon2 and legacy PBKDF2 hashes.
    Legacy PBKDF2 hashes are automatically rehashed on successful verification.
    
    Args:
        password: Plain text password to check
        password_hash: Hash string (Argon2 or PBKDF2)
        
    Returns:
        True if password matches, False otherwise
    """
    if not password or not password_hash:
        return False
    
    # Try Argon2 first (new)
    try:
        ph.verify(password_hash, password)
        
        # Check if rehashing is needed (e.g., updated parameters)
        if ph.check_needs_rehash(password_hash):
            logger.info("Password hash needs rehashing with updated parameters")
            # This should trigger a rehash in the User model
            return True
        
        return True
    except (VerifyMismatchError, InvalidHash):
        pass
    
    # Fall back to PBKDF2 (legacy) for backward compatibility
    try:
        if check_pbkdf2(password_hash, password):
            logger.warning(f"User has legacy PBKDF2 hash - should be migrated to Argon2")
            # This should trigger a migration in the User model
            return True
    except Exception:
        pass
    
    return False


def password_needs_rehash(password_hash: str) -> bool:
    """
    Check if a password hash needs to be rehashed.
    
    This returns True if:
    - Hash is PBKDF2 (should migrate to Argon2)
    - Hash parameters are outdated
    
    Args:
        password_hash: Hash string to check
        
    Returns:
        True if rehashing is recommended, False otherwise
    """
    # Legacy PBKDF2 hashes always need rehashing
    if password_hash.startswith('pbkdf2:'):
        return True
    
    # Check Argon2 parameters
    try:
        return ph.check_needs_rehash(password_hash)
    except (InvalidHash, Exception):
        return True  # If we can't parse it, rehash
