# Email Deep Links Design

**Date:** 2026-05-10  
**Status:** Approved  
**Branch:** `feat/email-deep-links`

## Problem Statement

Email templates currently link to web URLs (`app.nutree.app/*`). Users with the app installed must:
1. Click link → Opens Safari
2. Navigate from web to app manually

This friction reduces engagement. Deep links should open the app directly.

## Solution Overview

Implement Universal Links (iOS) so existing email URLs automatically open in the Nutree app when installed, with fallback to App Store for users without the app.

## Architecture

```
User clicks email CTA
        ↓
   Has app installed?
      /        \
    Yes         No
     ↓           ↓
 App opens    Safari opens
 to screen    app.nutree.app
     ↓           ↓
   Done     Web redirects to
            App Store
```

## URL Structure

**Domain:** `app.nutree.app` (existing)

URLs remain unchanged — Universal Links makes them open in the app automatically.

| Email | URL | App Screen |
|-------|-----|------------|
| Welcome | `app.nutree.app/log?source=welcome_email` | Meal logging |
| Reengagement | `app.nutree.app/dashboard?source=reengagement_email` | Dashboard |
| Trial Expiring | `app.nutree.app/upgrade?source=trial_expiring_email` | Upgrade/Paywall |
| Cancelled (feedback) | `app.nutree.app/feedback?reason=...` | Feedback form |
| Cancelled (pause) | `app.nutree.app/settings/pause` | Pause settings |

**App Store URL:**
```
https://apps.apple.com/app/apple-store/id6751159552?ct={campaign}&mt=8
```

## Implementation

### 1. Backend: Apple App Site Association (AASA)

**File:** `src/api/routes/well_known.py`

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["well-known"])

@router.get("/.well-known/apple-app-site-association")
async def apple_app_site_association():
    """
    Apple App Site Association file for Universal Links.
    Tells iOS which URLs should open in the Nutree app.
    """
    return JSONResponse(
        content={
            "applinks": {
                "apps": [],
                "details": [{
                    "appID": "TEAM_ID.com.nutree.app",
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

**Requirements:**
- Replace `TEAM_ID` with Apple Developer Team ID (10-char string from App Store Connect)
- Must be served over HTTPS
- No redirects allowed on this path
- Apple crawls this file within 24-48h of first request

### 2. Backend: App Download Redirect

**File:** `src/api/routes/app_download.py`

```python
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["app"])

APP_STORE_URL = "https://apps.apple.com/app/apple-store/id6751159552"

@router.get("/app-download")
async def app_download(source: str = Query(default="direct")):
    """
    Redirect to App Store with campaign tracking.
    Used as fallback when deep link fails.
    """
    return RedirectResponse(
        url=f"{APP_STORE_URL}?ct={source}&mt=8",
        status_code=302
    )
```

### 3. Backend: Register Routes

**Modify:** `src/api/main.py`

```python
from src.api.routes.well_known import router as well_known_router
from src.api.routes.app_download import router as app_download_router

app.include_router(well_known_router)
app.include_router(app_download_router)
```

### 4. iOS App: Associated Domains (nutree_ai repo)

**Xcode → Target → Signing & Capabilities → + Associated Domains:**
```
applinks:app.nutree.app
```

**File:** `Nutree.entitlements`
```xml
<key>com.apple.developer.associated-domains</key>
<array>
    <string>applinks:app.nutree.app</string>
</array>
```

### 5. iOS App: Deep Link Handler (nutree_ai repo)

**AppDelegate or SceneDelegate:**

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

### 6. Email Templates: Add App Store Links

**File:** `src/infra/templates/emails/welcome.html`

Change social proof section (around line 203):

```html
<!-- Before -->
<span style="font-size: 18px; letter-spacing: 3px;">⭐⭐⭐⭐⭐</span>
<span style="font-family: 'DM Sans', sans-serif; font-size: 13px; color: #7A7470; margin-left: 6px;">4.9 on App Store</span>

<!-- After -->
<span style="font-size: 18px; letter-spacing: 3px;">⭐⭐⭐⭐⭐</span>
<a href="https://apps.apple.com/app/apple-store/id6751159552?ct=welcome_email&mt=8" 
   style="color: #7A7470; text-decoration: underline; font-size: 13px; font-family: 'DM Sans', sans-serif; margin-left: 6px;">
   4.9 on App Store
</a>
```

**File:** `src/infra/templates/emails/base.html`

Add "Get the app" link in footer (around line 275):

```html
<a href="{{ unsubscribe_url | default('#') }}" style="...">Unsubscribe</a>
<span style="color: #D8D3CE; padding: 0 8px;">·</span>
<a href="https://app.nutree.app/settings/notifications?source=email" style="...">Email preferences</a>
<span style="color: #D8D3CE; padding: 0 8px;">·</span>
<a href="https://apps.apple.com/app/apple-store/id6751159552?ct=email_footer&mt=8" 
   style="color: #9BA8A3; text-decoration: underline; font-size: 11px; font-family: 'DM Sans', sans-serif;">
   Get the app
</a>
```

## Campaign Tracking

| Email/Location | `ct` param value |
|----------------|------------------|
| Welcome email CTA | `welcome_email` |
| Reengagement CTA | `reengagement_email` |
| Trial Expiring CTA | `trial_expiring_email` |
| Cancellation CTA | `cancellation_email` |
| Welcome App Store badge | `welcome_email` |
| Footer "Get the app" | `email_footer` |

## Files to Create

| File | Repo | Description |
|------|------|-------------|
| `src/api/routes/well_known.py` | mealtrack_backend | AASA endpoint |
| `src/api/routes/app_download.py` | mealtrack_backend | App Store redirect |

## Files to Modify

| File | Repo | Change |
|------|------|--------|
| `src/api/main.py` | mealtrack_backend | Register new routers |
| `src/infra/templates/emails/welcome.html` | mealtrack_backend | Add clickable App Store link |
| `src/infra/templates/emails/base.html` | mealtrack_backend | Add footer App Store link |
| `Nutree.entitlements` | nutree_ai | Add Associated Domains |
| `AppDelegate.swift` or `SceneDelegate.swift` | nutree_ai | Add deep link handler |

## Testing Strategy

| Test | How |
|------|-----|
| AASA file serves correctly | `curl -I https://app.nutree.app/.well-known/apple-app-site-association` |
| AASA validates | Use Apple's AASA validator: https://search.developer.apple.com/appsearch-validation-tool |
| Deep links open app | Click email link on iOS device with app installed |
| Fallback works | Click email link on iOS device without app → goes to App Store |
| Tracking params preserved | Check analytics for `source` param |

## Rollout Plan

1. **Backend first:** Deploy AASA file and app-download endpoint
2. **Wait 24-48h:** Apple crawls and caches AASA file
3. **iOS app update:** Ship with Associated Domains configured
4. **Email templates:** Update templates (can do anytime after step 1)

## Success Criteria

- [ ] AASA file validates with Apple's tool
- [ ] Email links open app directly on iOS (when installed)
- [ ] Email links redirect to App Store (when not installed)
- [ ] Campaign tracking params visible in App Store Connect analytics
- [ ] No broken links in any email template
