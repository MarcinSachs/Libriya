# CSP + Nonce Implementation

## Problem
Current CSP uses `'unsafe-inline'` which allows any inline JavaScript, defeating CSP protection.

## Solution
Use dynamic nonce-based CSP that allows only scripts/styles with specific token.

## Implementation

### 1. Create Nonce Generator Utility

```python
# app/utils/security.py (new file)
import secrets
import string

def generate_nonce(length: int = 24) -> str:
    """
    Generate a random nonce for CSP.
    
    Nonce should be unique per request and cryptographically random.
    24-32 characters is sufficient.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
```

### 2. Update Flask App Initialization

```python
# app/__init__.py

@app.before_request
def inject_nonce():
    """Generate and store nonce for this request"""
    import secrets
    nonce = secrets.token_urlsafe(32)
    request.nonce = nonce

@app.after_request
def set_security_headers(response):
    """Add security headers with CSP nonce"""
    
    # Get nonce from request
    nonce = getattr(request, 'nonce', '')
    
    # X-Content-Type-Options
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # HSTS (only in production)
    if not app.debug:
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )

    # Improved CSP with nonce
    csp = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; "
        f"style-src 'self' 'nonce-{nonce}' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://fonts.googleapis.com https://unpkg.com; "
        f"font-src 'self' https://fonts.gstatic.com https://unpkg.com; "
        f"img-src 'self' data: https:; "
        f"connect-src 'self' https: wss:; "
        f"frame-ancestors 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp
    
    return response
```

### 3. Update Jinja2 Context

```python
# app/__init__.py - in create_app()

@app.context_processor
def inject_nonce():
    """Make nonce available to all templates"""
    return {'nonce': getattr(request, 'nonce', '')}
```

### 4. Update Templates

All inline scripts and styles must have `nonce="{{ nonce }}"` attribute:

```html
<!-- Before (unsafe) -->
<script>
    console.log('Hello');
</script>

<!-- After (safe) -->
<script nonce="{{ nonce }}">
    console.log('Hello');
</script>

<!-- Same for styles -->
<style nonce="{{ nonce }}">
    .my-class { color: red; }
</style>
```

### 5. Find and Update All Inline Styles/Scripts

```bash
# Search for inline scripts in templates
grep -r "<script>" app/templates/ --include="*.html"

# Search for inline styles
grep -r "<style>" app/templates/ --include="*.html"

# Search for style attributes
grep -r "style=" app/templates/ --include="*.html"
```

Example fixes:

```html
<!-- Before -->
<div style="color: red;">Error</div>

<!-- After - use CSS class -->
<div class="text-red-500">Error</div>

<!-- Or use nonce -->
<div style="color: red;" nonce="{{ nonce }}">Error</div>
```

### 6. Handle Dynamic Content

For content added via JavaScript (AJAX):

```html
<!-- Don't use inline event handlers -->
<!-- Before (bad) -->
<button onclick="handleClick()">Click</button>

<!-- After (good) -->
<button id="my-button" data-action="click">Click</button>

<!-- In external script with nonce -->
<script nonce="{{ nonce }}">
document.getElementById('my-button').addEventListener('click', handleClick);
</script>
```

### 7. Test CSP

Check browser console for CSP violations:

```javascript
// This will fail if CSP is strict
<script nonce="{{ nonce }}">
    eval('alert("This will fail")'); // CSP blocks eval()
</script>
```

### 8. CSP Report URI (Optional)

Add reporting endpoint for CSP violations:

```python
# app/__init__.py
@app.route('/csp-report', methods=['POST'])
def csp_report():
    """Receive CSP violation reports"""
    import json
    data = json.loads(request.data)
    logger.warning(f"CSP violation: {data}")
    return '', 204

# Update CSP header
f"report-uri /csp-report"
```

### 9. CSP Levels

**Level 2 (Current)**
- Supports `'nonce-...'`
- Better browser support

**Level 3 (Future)**
- Supports `strict-dynamic`
- Better for migrating old code

```python
# CSP with strict-dynamic (when ready)
csp = (
    f"script-src 'strict-dynamic' 'nonce-{nonce}' https:; "
    # ... other directives
)
```

## Migration Plan

1. **Week 1**: Implement nonce generation and injection
2. **Week 2**: Update base templates and common scripts
3. **Week 3**: Find and fix remaining inline styles/scripts
4. **Week 4**: Test on staging, enable report-uri
5. **Week 5**: Deploy to production

## Verification

```bash
# Check CSP header is present
curl -I https://example.com | grep Content-Security-Policy

# Browser DevTools
# - Open Console
# - Look for CSP violations
# - Should be none if correctly implemented
```

## Resources

- https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
- https://csp-evaluator.withgoogle.com/
- https://observatory.mozilla.org/
