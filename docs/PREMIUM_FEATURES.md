# Premium Features Architecture

## Overview

Libriya uses a **modular premium system** that requires **zero changes to core application code**. Premium features are:
- Registered in a central `PremiumRegistry`
- Loaded dynamically based on environment variables
- Accessed via `PremiumManager` singleton

## Architecture

### Directory Structure

```
app/services/
├── premium/                          # Premium features package
│   ├── __init__.py
│   ├── manager.py                   # PremiumManager (public API)
│   ├── registry.py                  # PremiumRegistry (internal)
│   ├── covers/                      # Premium cover sources
│   │   ├── __init__.py
│   │   └── bookcover_service.py    # Bookcover API service
│   ├── metadata/                    # (Future) Premium metadata sources
│   ├── recommendations/             # (Future) Premium recommendations
│   └── ...
├── book_service.py                  # Base book search
├── cover_service.py                 # Base cover management
└── ...
```

## Quick Start

### 1. Enable Premium Feature

Set environment variable in `.env`:

```bash
PREMIUM_BOOKCOVER_ENABLED=true
```

### 2. Use Premium Manager (Zero Code Changes!)

Anywhere in your code, use the PremiumManager API:

```python
from app.services import PremiumManager

# Check if feature is enabled
if PremiumManager.is_enabled('bookcover_api'):
    # Call premium service method
    cover_url = PremiumManager.call(
        'bookcover_api',
        'get_cover_from_bookcover_api',
        isbn="9780545003957",
        title="The Hobbit",
        author="J.R.R. Tolkien"
    )
```

That's it! No imports of premium classes, no conditionals needed.

## How It Works

### 1. Initialization (`app/__init__.py`)

```python
from app.services.premium.manager import PremiumManager

def create_app(config_class=Config):
    app = Flask(__name__)
    # ... other setup ...
    
    # Initialize premium manager once at startup
    PremiumManager.init()
    
    return app
```

### 2. Registration (in `PremiumManager.init()`)

Premium features are registered with metadata:

```python
premium_registry.register(
    feature_id='bookcover_api',
    name='Bookcover API (Goodreads)',
    description='Premium covers from bookcover.longitood.com',
    module_path='app.services.premium.covers.bookcover_service',
    class_name='BookcoverService',
    enabled_env_var='PREMIUM_BOOKCOVER_ENABLED',
    requires_config={'API_URL': 'https://bookcover.longitood.com/bookcover'},
)
```

### 3. Dynamic Loading

When you call `PremiumManager.call()`:
1. Check if feature is enabled (env var)
2. Check dependencies
3. Dynamically import module
4. Call static method
5. Return result (or None if disabled)

## Premium Features

### Current

#### `bookcover_api` - Bookcover API (Goodreads)

Search for book covers from Goodreads via bookcover.longitood.com.

**Status:** Requires PREMIUM_BOOKCOVER_ENABLED=true  
**License:** bookcover.longitood.com terms  
**Methods:**
- `get_cover_from_bookcover_api(isbn=None, title=None, author=None)`

**Example:**
```python
if PremiumManager.is_enabled('bookcover_api'):
    cover = PremiumManager.call(
        'bookcover_api',
        'get_cover_from_bookcover_api',
        isbn="9780545003957"
    )
```

### Planned

- **Metadata** - Enhanced book metadata from premium sources
- **Recommendations** - Advanced recommendation engine
- **Analytics** - Enhanced analytics and user insights

## Adding New Premium Features

### Step 1: Create Feature Module

Create directory: `app/services/premium/{feature_name}/`

```python
# app/services/premium/metadata/metadata_service.py
class MetadataService:
    @staticmethod
    def get_enhanced_metadata(isbn):
        """Get enhanced book metadata."""
        # Implementation
        return {...}
```

### Step 2: Register in PremiumManager

Edit `PremiumManager.init()`:

```python
premium_registry.register(
    feature_id='metadata',
    name='Premium Metadata',
    description='Enhanced book metadata from premium sources',
    module_path='app.services.premium.metadata.metadata_service',
    class_name='MetadataService',
    enabled_env_var='PREMIUM_METADATA_ENABLED',
    requires_config={'API_KEY': 'Your API key'},
    dependencies=['bookcover_api'],  # Optional: other features it depends on
)
```

### Step 3: Add Environment Variable

In `.env.example`:

```bash
PREMIUM_METADATA_ENABLED=false
```

### Step 4: Use It Everywhere (No Code Changes!)

```python
# Anywhere in your app, call it:
if PremiumManager.is_enabled('metadata'):
    metadata = PremiumManager.call('metadata', 'get_enhanced_metadata', isbn="...")
```

## API Reference

### PremiumManager

```python
from app.services import PremiumManager

# Check if feature is enabled
is_enabled: bool = PremiumManager.is_enabled('feature_id')

# Call a static method on a premium service
result = PremiumManager.call(
    'feature_id',
    'method_name',
    param1=value1,
    param2=value2
)

# List all registered features
features: Dict = PremiumManager.list_features()

# Get all currently enabled features
enabled: Dict = PremiumManager.get_enabled_features()

# Get detailed info about a feature
info: Dict = PremiumManager.feature_info('feature_id')

# Get raw service class (advanced)
service_class = PremiumManager.get_service('feature_id')
```

## Configuration

### Environment Variables

Pattern: `PREMIUM_{FEATURE_ID}_ENABLED`

```bash
# .env
PREMIUM_BOOKCOVER_ENABLED=true
PREMIUM_METADATA_ENABLED=false
PREMIUM_RECOMMENDATIONS_ENABLED=false
```

## Testing Premium Features

### Enable Premium in Dev

```bash
# .env.development
PREMIUM_BOOKCOVER_ENABLED=true
```

### Test Code

```python
def test_premium_bookcover():
    from app.services import PremiumManager
    
    if not PremiumManager.is_enabled('bookcover_api'):
        pytest.skip("Bookcover API not enabled")
    
    cover = PremiumManager.call(
        'bookcover_api',
        'get_cover_from_bookcover_api',
        isbn="9780545003957"
    )
    assert cover is not None
```

## Benefits

✅ **Zero Core Changes** - Add premium features without touching main code  
✅ **Easy Toggle** - Enable/disable via environment variable  
✅ **Clean API** - Simple `PremiumManager.call()` interface  
✅ **Scalable** - Add unlimited premium features  
✅ **Modular** - Each feature is independent  
✅ **Dependency Management** - Features can depend on each other  
✅ **Lazy Loading** - Premium services loaded only when needed  
✅ **Graceful Degradation** - App works without any premium features  

## Troubleshooting

### Feature Not Loading

Check logs:
```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# Check if feature is registered
PremiumManager.list_features()

# Check if it's enabled
PremiumManager.is_enabled('feature_id')
```

### ModuleNotFoundError

Ensure module path is correct:
- Module exists: `app/services/premium/{feature}/{module}.py`
- Class exists in module
- No import errors

### Graceful Fallback

If premium call returns None:
```python
cover = PremiumManager.call('bookcover_api', 'get_cover_from_bookcover_api', isbn="...")

if cover:
    use_premium_cover(cover)
else:
    use_default_cover()  # Fallback to base service
```

## Migration from Old System

**Before** (old premium_cover_service.py):
```python
from app.services.premium_cover_service import PremiumCoverService

if PremiumCoverService.is_premium_enabled():
    cover = PremiumCoverService.get_cover_from_bookcover_api(...)
```

**After** (new PremiumManager):
```python
from app.services import PremiumManager

cover = PremiumManager.call('bookcover_api', 'get_cover_from_bookcover_api', ...)
# Returns None if disabled, no need to check
```

Much simpler and no code changes to add new features!

