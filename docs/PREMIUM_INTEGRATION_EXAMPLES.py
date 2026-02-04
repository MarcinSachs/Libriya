"""
Example integration of Premium Features with Core Services.

Shows how to use PremiumManager without changing core code.
"""

from app.services import PremiumManager, CoverService
from typing import Optional


def get_book_cover_with_premium_fallback(
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None
) -> Optional[str]:
    """
    Get book cover using base service with optional premium fallback.

    This example shows how to integrate premium features WITHOUT changing
    the core application logic. Just use PremiumManager.call()!

    Priority:
    1. Base cover service (Open Library)
    2. Premium bookcover API (if enabled)

    Args:
        isbn: ISBN number
        title: Book title
        author: Book author

    Returns:
        Cover URL or None
    """
    # 1. Try base service first
    cover_url, source = CoverService.get_cover_url(
        isbn=isbn,
        title=title,
        author=author
    )

    if source != 'local_default':
        # Got a good cover from base service
        return cover_url

    # 2. Try premium bookcover API as fallback (if enabled)
    # NOTE: No code changes needed, just call PremiumManager!
    premium_cover = PremiumManager.call(
        'bookcover_api',
        'get_cover_from_bookcover_api',
        isbn=isbn,
        title=title,
        author=author
    )

    if premium_cover:
        return premium_cover

    # 3. Fallback to default
    return None


def show_premium_status():
    """
    Example: Display premium features status.

    Shows how to check what premium features are available.
    """
    print("=== Premium Features Status ===\n")

    features = PremiumManager.list_features()

    for feature_id, info in features.items():
        status = "✓ ENABLED" if PremiumManager.is_enabled(feature_id) else "✗ disabled"
        print(f"{feature_id.upper()} - {info['name']} [{status}]")
        print(f"  Description: {info['description']}")
        print(f"  Env Var: {info['enabled_env_var']}")
        print()


def example_dynamic_feature_detection():
    """
    Example: Dynamically detect and use available premium features.

    Great for building feature flags in UI without hardcoding.
    """
    enabled_features = PremiumManager.get_enabled_features()

    for feature_id, feature_data in enabled_features.items():
        print(f"Premium feature enabled: {feature_data['name']}")
        # Can use feature_data['service'] if needed for advanced scenarios


# Example usage in route handlers

def example_book_add_route():
    """
    Example Flask route showing premium integration.

    No changes to route logic - premium is completely optional!
    """
    # ... form validation ...

    isbn = "9780545003957"
    title = "The Hobbit"
    author = "J.R.R. Tolkien"

    # Get cover with optional premium upgrade
    cover_url = get_book_cover_with_premium_fallback(
        isbn=isbn,
        title=title,
        author=author
    )

    # ... save book ...
    # No need to know about premium features in the route!


if __name__ == '__main__':
    # Initialize premium manager (done in app/__init__.py normally)
    PremiumManager.init()

    # Show status
    show_premium_status()

    # Show dynamic detection
    print("\n=== Dynamically Enabled Features ===\n")
    example_dynamic_feature_detection()
