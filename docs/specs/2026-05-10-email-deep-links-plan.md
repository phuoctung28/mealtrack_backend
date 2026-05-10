# Email Deep Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Universal Links so email CTAs open directly in the Nutree iOS app, with App Store fallback for users without the app installed.

**Architecture:** Backend serves AASA file at `/.well-known/apple-app-site-association` telling iOS which URLs open in-app. Email templates get clickable App Store badges. iOS app changes documented but implemented in separate repo.

**Tech Stack:** FastAPI, Jinja2 templates, iOS Universal Links

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Create | `src/api/routes/well_known.py` | AASA endpoint for Universal Links |
| Create | `src/api/routes/app_download.py` | App Store redirect with tracking |
| Create | `tests/unit/api/routes/test_well_known.py` | Tests for AASA endpoint |
| Create | `tests/unit/api/routes/test_app_download.py` | Tests for redirect endpoint |
| Modify | `src/api/main.py` | Register new routers |
| Modify | `src/infra/templates/emails/welcome.html` | Add clickable App Store link |
| Modify | `src/infra/templates/emails/base.html` | Add footer App Store link |

---

### Task 1: AASA Endpoint

**Files:**
- Create: `src/api/routes/well_known.py`
- Create: `tests/unit/api/routes/test_well_known.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/api/routes/test_well_known.py`:

```python
"""Tests for Apple App Site Association endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.api.routes.well_known import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_aasa_returns_json():
    response = client.get("/.well-known/apple-app-site-association")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_aasa_has_applinks_structure():
    response = client.get("/.well-known/apple-app-site-association")
    data = response.json()
    
    assert "applinks" in data
    assert "apps" in data["applinks"]
    assert "details" in data["applinks"]
    assert data["applinks"]["apps"] == []


def test_aasa_has_correct_paths():
    response = client.get("/.well-known/apple-app-site-association")
    data = response.json()
    
    details = data["applinks"]["details"][0]
    expected_paths = [
        "/log", "/log/*",
        "/dashboard", "/dashboard/*",
        "/upgrade", "/upgrade/*",
        "/feedback", "/feedback/*",
        "/settings/*"
    ]
    
    assert details["paths"] == expected_paths


def test_aasa_has_app_id():
    response = client.get("/.well-known/apple-app-site-association")
    data = response.json()
    
    details = data["applinks"]["details"][0]
    assert "appID" in details
    assert ".com.nutree.app" in details["appID"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/api/routes/test_well_known.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.api.routes.well_known'`

- [ ] **Step 3: Write the AASA endpoint implementation**

Create `src/api/routes/well_known.py`:

```python
"""Apple App Site Association endpoint for Universal Links."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["well-known"])

# TODO: Replace with actual Apple Developer Team ID from App Store Connect
APPLE_TEAM_ID = "XXXXXXXXXX"
APP_BUNDLE_ID = "com.nutree.app"


@router.get("/.well-known/apple-app-site-association")
async def apple_app_site_association():
    """
    Apple App Site Association file for Universal Links.
    
    This file tells iOS which URLs should open in the Nutree app
    instead of Safari. Apple crawls this within 24-48h of deployment.
    
    Requirements:
    - Must be served over HTTPS
    - Must return application/json content type
    - No redirects allowed on this path
    """
    return JSONResponse(
        content={
            "applinks": {
                "apps": [],
                "details": [{
                    "appID": f"{APPLE_TEAM_ID}.{APP_BUNDLE_ID}",
                    "paths": [
                        "/log",
                        "/log/*",
                        "/dashboard",
                        "/dashboard/*",
                        "/upgrade",
                        "/upgrade/*",
                        "/feedback",
                        "/feedback/*",
                        "/settings/*"
                    ]
                }]
            }
        },
        media_type="application/json"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/api/routes/test_well_known.py -v`

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/routes/well_known.py tests/unit/api/routes/test_well_known.py
git commit -m "feat: add AASA endpoint for Universal Links"
```

---

### Task 2: App Download Redirect Endpoint

**Files:**
- Create: `src/api/routes/app_download.py`
- Create: `tests/unit/api/routes/test_app_download.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/api/routes/test_app_download.py`:

```python
"""Tests for App Store download redirect endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.api.routes.app_download import router, APP_STORE_URL
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app, follow_redirects=False)


def test_app_download_redirects_to_app_store():
    response = client.get("/app-download")
    
    assert response.status_code == 302
    assert APP_STORE_URL in response.headers["location"]


def test_app_download_includes_default_source():
    response = client.get("/app-download")
    
    location = response.headers["location"]
    assert "ct=direct" in location
    assert "mt=8" in location


def test_app_download_uses_custom_source():
    response = client.get("/app-download?source=welcome_email")
    
    location = response.headers["location"]
    assert "ct=welcome_email" in location


def test_app_download_preserves_mt_param():
    response = client.get("/app-download?source=test")
    
    location = response.headers["location"]
    assert "mt=8" in location
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/api/routes/test_app_download.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.api.routes.app_download'`

- [ ] **Step 3: Write the redirect endpoint implementation**

Create `src/api/routes/app_download.py`:

```python
"""App Store download redirect endpoint with campaign tracking."""

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["app"])

APP_STORE_URL = "https://apps.apple.com/app/apple-store/id6751159552"


@router.get("/app-download")
async def app_download(source: str = Query(default="direct")):
    """
    Redirect to App Store with campaign tracking.
    
    Used as fallback when deep link fails or for direct download links.
    The `ct` parameter tracks which email/campaign drove the install.
    The `mt=8` parameter indicates iOS App Store.
    
    Args:
        source: Campaign source for tracking (e.g., "welcome_email", "email_footer")
    
    Returns:
        302 redirect to App Store with tracking params
    """
    return RedirectResponse(
        url=f"{APP_STORE_URL}?ct={source}&mt=8",
        status_code=302
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/api/routes/test_app_download.py -v`

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/routes/app_download.py tests/unit/api/routes/test_app_download.py
git commit -m "feat: add App Store redirect endpoint with tracking"
```

---

### Task 3: Register Routes in Main App

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Add imports for new routers**

In `src/api/main.py`, add imports after line 67 (after existing email imports):

```python
from src.api.routes.well_known import router as well_known_router
from src.api.routes.app_download import router as app_download_router
```

- [ ] **Step 2: Register routers**

In `src/api/main.py`, add router registrations after line 273 (after `weight_entries_router`):

```python
app.include_router(well_known_router)
app.include_router(app_download_router)
```

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `pytest tests/unit/api/routes/ -v --tb=short`

Expected: All existing tests PASS

- [ ] **Step 4: Manual verification**

Run: `uvicorn src.api.main:app --reload`

Test endpoints:
- `curl http://localhost:8000/.well-known/apple-app-site-association`
- `curl -I http://localhost:8000/app-download`

Expected:
- AASA returns JSON with applinks structure
- App download returns 302 redirect to App Store

- [ ] **Step 5: Commit**

```bash
git add src/api/main.py
git commit -m "feat: register AASA and app-download routes"
```

---

### Task 4: Welcome Email App Store Badge

**Files:**
- Modify: `src/infra/templates/emails/welcome.html:203`

- [ ] **Step 1: Update social proof section with clickable App Store link**

In `src/infra/templates/emails/welcome.html`, replace line 203:

```html
<!-- Before (line 203) -->
<span style="font-family: 'DM Sans', sans-serif; font-size: 13px; color: #7A7470; margin-left: 6px;">4.9 on App Store</span>

<!-- After -->
<a href="https://apps.apple.com/app/apple-store/id6751159552?ct=welcome_email&mt=8" style="color: #7A7470; text-decoration: underline; font-size: 13px; font-family: 'DM Sans', sans-serif; margin-left: 6px;">4.9 on App Store</a>
```

- [ ] **Step 2: Verify template renders correctly**

Run: `python -c "
from src.infra.services.email_template_renderer import EmailTemplateRenderer
renderer = EmailTemplateRenderer()
html = renderer.render('welcome', {
    'subject': 'Test',
    'first_name': 'Alex',
    'tdee': 2100,
    'user_id': 'test123'
})
assert 'apps.apple.com' in html
assert 'ct=welcome_email' in html
print('Template renders correctly')
"`

Expected: "Template renders correctly"

- [ ] **Step 3: Commit**

```bash
git add src/infra/templates/emails/welcome.html
git commit -m "feat: add clickable App Store link in welcome email"
```

---

### Task 5: Base Template Footer App Store Link

**Files:**
- Modify: `src/infra/templates/emails/base.html:275-276`

- [ ] **Step 1: Add "Get the app" link to footer**

In `src/infra/templates/emails/base.html`, after line 275 (after "Email preferences" link), add:

```html
                      <span style="color: #D8D3CE; padding: 0 8px;">·</span>
                      <a href="https://apps.apple.com/app/apple-store/id6751159552?ct=email_footer&mt=8" style="color: #9BA8A3; text-decoration: underline; font-size: 11px; font-family: 'DM Sans', sans-serif;">Get the app</a>
```

The complete footer `<p>` block should now be:

```html
<p style="margin: 12px 0 0 0;">
  <a href="{{ unsubscribe_url | default('#') }}" style="color: #9BA8A3; text-decoration: underline; font-size: 11px; font-family: 'DM Sans', sans-serif;">Unsubscribe</a>
  <span style="color: #D8D3CE; padding: 0 8px;">·</span>
  <a href="https://app.nutree.app/settings/notifications?source=email" style="color: #9BA8A3; text-decoration: underline; font-size: 11px; font-family: 'DM Sans', sans-serif;">Email preferences</a>
  <span style="color: #D8D3CE; padding: 0 8px;">·</span>
  <a href="https://apps.apple.com/app/apple-store/id6751159552?ct=email_footer&mt=8" style="color: #9BA8A3; text-decoration: underline; font-size: 11px; font-family: 'DM Sans', sans-serif;">Get the app</a>
</p>
```

- [ ] **Step 2: Verify all templates still render**

Run: `python -c "
from src.infra.services.email_template_renderer import EmailTemplateRenderer
renderer = EmailTemplateRenderer()

templates = ['welcome', 'reengagement', 'trial_expiring', 'trial_cancelled']
test_data = {
    'subject': 'Test',
    'first_name': 'Alex',
    'tdee': 2100,
    'user_id': 'test123',
    'streak_days': 5,
    'days_left': 2,
    'meals_logged': 42
}

for template in templates:
    html = renderer.render(template, test_data)
    assert 'Get the app' in html, f'{template} missing footer link'
    assert 'ct=email_footer' in html, f'{template} missing tracking'
    print(f'{template}: OK')

print('All templates render correctly')
"`

Expected: All 4 templates report OK

- [ ] **Step 3: Commit**

```bash
git add src/infra/templates/emails/base.html
git commit -m "feat: add App Store link in email footer"
```

---

### Task 6: Run Full Test Suite & Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all unit tests**

Run: `pytest tests/unit/ -v --tb=short`

Expected: All tests PASS

- [ ] **Step 2: Run integration tests for email flow**

Run: `pytest tests/integration/email/ -v --tb=short`

Expected: All tests PASS

- [ ] **Step 3: Final commit with all changes**

Run: `git status`

If any uncommitted changes remain:

```bash
git add -A
git commit -m "chore: final cleanup for email deep links"
```

- [ ] **Step 4: Push branch**

```bash
git push -u origin feat/email-deep-links
```

---

## iOS Implementation Notes (nutree_ai repo)

> These changes are implemented in the iOS codebase, not this backend repo.

### 1. Add Associated Domains Capability

In Xcode: Target → Signing & Capabilities → + Associated Domains

Add: `applinks:app.nutree.app`

### 2. Update Entitlements File

`Nutree.entitlements`:
```xml
<key>com.apple.developer.associated-domains</key>
<array>
    <string>applinks:app.nutree.app</string>
</array>
```

### 3. Handle Deep Links

In `AppDelegate.swift` or `SceneDelegate.swift`:

```swift
func application(_ application: UIApplication,
                 continue userActivity: NSUserActivity,
                 restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
    
    guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
          let url = userActivity.webpageURL else {
        return false
    }
    
    return handleDeepLink(url: url)
}

func handleDeepLink(url: URL) -> Bool {
    let path = url.path
    let params = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems
    
    switch path {
    case "/log":
        navigateToMealLog()
    case "/dashboard":
        navigateToDashboard()
    case "/upgrade":
        navigateToUpgrade()
    case "/feedback":
        let reason = params?.first(where: { $0.name == "reason" })?.value
        navigateToFeedback(reason: reason)
    case _ where path.hasPrefix("/settings"):
        navigateToSettings(subpath: path)
    default:
        return false
    }
    return true
}
```

---

## Post-Deployment Checklist

- [ ] Get Apple Team ID from App Store Connect and update `APPLE_TEAM_ID` in `well_known.py`
- [ ] Deploy backend to production
- [ ] Wait 24-48h for Apple to crawl AASA file
- [ ] Validate AASA at: https://search.developer.apple.com/appsearch-validation-tool
- [ ] Ship iOS app update with Associated Domains
- [ ] Test deep links on real device
