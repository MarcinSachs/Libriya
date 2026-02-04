"""
License File Format Documentation

Each premium module can have a license.json file for access control.
"""

LICENSE_SCHEMA = {
    "feature_id": "bookcover_api",           # Must match registered feature_id
    "license_type": "paid",                  # trial, paid, unlimited
    "customer_id": "customer-12345",         # Customer identifier
    "customer_name": "Acme Corp",            # Customer name
    "valid_from": "2026-02-01T00:00:00Z",   # ISO 8601 format (optional)
    "valid_until": "2027-02-01T23:59:59Z",  # ISO 8601 format (null = no expiry)
    "max_requests": 10000,                   # null = unlimited requests
    "metadata": {
        "tier": "professional",               # Custom tier level
        "support": "priority",               # Support level
        "regions": ["EU", "US"],            # Allowed regions
        "description": "Professional plan with priority support"
    }
}

"""
License Types:
- trial: Temporary license, usually with request limits and expiration
- paid: Full license with all features, may have expiration
- unlimited: Permanent license with unlimited requests

Field Descriptions:

feature_id (required):
  Unique identifier matching the registered premium feature
  Must exactly match what's registered in PremiumManager

license_type (required):
  One of: trial, paid, unlimited
  Used for tracking license tier

customer_id (required):
  Unique identifier for the customer/licensee
  Used for audit trails and multi-tenancy

customer_name (required):
  Human-readable customer name for logging

valid_from (optional):
  License start date in ISO 8601 format (UTC with Z suffix)
  If omitted, license is valid immediately
  Format: "2026-02-01T00:00:00Z"

valid_until (optional):
  License expiration date in ISO 8601 format (UTC with Z suffix)
  If omitted or null, license never expires
  Format: "2027-02-01T23:59:59Z"

max_requests (optional):
  Maximum number of API calls allowed
  If omitted or null, requests are unlimited
  Counter incremented with each call

metadata (optional):
  Custom metadata for the license
  Can include: tier, support level, regions, description, etc.

Example License Files:

1. Trial License (7 days, 1000 requests):
{
  "feature_id": "bookcover_api",
  "license_type": "trial",
  "customer_id": "trial-2026",
  "customer_name": "Trial Customer",
  "valid_from": "2026-02-01T00:00:00Z",
  "valid_until": "2026-02-08T23:59:59Z",
  "max_requests": 1000,
  "metadata": {
    "tier": "trial",
    "description": "7-day free trial"
  }
}

2. Professional License (1 year, unlimited):
{
  "feature_id": "bookcover_api",
  "license_type": "paid",
  "customer_id": "acme-corp-12345",
  "customer_name": "Acme Corporation",
  "valid_from": "2026-02-01T00:00:00Z",
  "valid_until": "2027-02-01T23:59:59Z",
  "max_requests": null,
  "metadata": {
    "tier": "professional",
    "support": "priority",
    "sla": "99.9%",
    "regions": ["EU", "US", "ASIA"]
  }
}

3. Permanent License (unlimited):
{
  "feature_id": "bookcover_api",
  "license_type": "unlimited",
  "customer_id": "internal-dev",
  "customer_name": "Internal Development",
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "max_requests": null,
  "metadata": {
    "tier": "enterprise",
    "support": "internal",
    "description": "Internal development team license"
  }
}

Integration in Premium Module Registration:

    premium_registry.register(
        feature_id='bookcover_api',
        name='Bookcover API',
        description='Premium covers from Goodreads',
        module_path='app.services.premium.covers.bookcover_service',
        class_name='BookcoverService',
        license_path='app/services/premium/covers/license.json',  # ← License file
    )

License File Location:
- Place license.json in the same directory as the premium service module
- Pattern: app/services/premium/{module_name}/license.json
- For bookcover: app/services/premium/covers/license.json

License Checking Flow:

1. User enables premium feature: PREMIUM_BOOKCOVER_ENABLED=true
2. PremiumManager.init() called
3. Premium service registered with license_path
4. When service is first called:
   a. Check if enabled (env var) ✓
   b. Load and validate license.json ✓
   c. Check dates (valid_from, valid_until) ✓
   d. Check request quota (max_requests) ✓
   e. If all valid, service loaded and available ✓
   f. If invalid, service disabled and error logged ✗

Access Control:

The license system provides:
- Time-based access (trial vs permanent)
- Usage-based access (quota limiting)
- Customer identification (audit trails)
- Custom metadata for business logic

Example: Check who has access
  from app.services.premium import PremiumManager
  
  info = PremiumManager.feature_info('bookcover_api')
  if info:
      print(f"Customer: {info['customer_name']}")
      print(f"License type: {info['license_type']}")
      print(f"Valid: {info['valid']}")

Deployment:

1. For trial users:
   - Generate trial license (7-30 days)
   - Place license.json in premium module
   - Enable feature: PREMIUM_BOOKCOVER_ENABLED=true

2. For paid customers:
   - Generate customer-specific license
   - Include in deployment/distribution
   - Customer places license.json in premium module
   - They enable feature themselves

3. For development/testing:
   - Use license.json.example as template
   - Create test license with test dates

Security Notes:

- License file should be in version control (non-sensitive for trials)
- For paid licenses, consider:
  - Encryption of license.json
  - License validation via server
  - License revocation system
  - Tamper detection (digital signatures)

Currently implemented:
  ✓ Date validation
  ✓ Request quota tracking
  ✓ Customer identification
  ✓ Metadata support

Future enhancements:
  - Digital signatures for license verification
  - Server-side license validation
  - License revocation/revalidation
  - Hardware fingerprinting
  - License key system instead of JSON files
"""
