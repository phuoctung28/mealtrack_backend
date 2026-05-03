# Delivery vs Main Branch Gap Analysis

**Generated:** 2026-05-02  
**Status:** Ready to merge

---

## Summary

| Branch | Commits Ahead | Commits Behind |
|--------|---------------|----------------|
| `delivery` | 54 | 0 (after sync) |
| `main` | 0 | 54 |

**Goal:** Everything in main should be in delivery.

---

## Sync Branch Ready

**Branch:** `sync/main-to-delivery-260502`

This branch contains:
- All 13 hotfixes from main
- Migration alignment fixes
- Additional test coverage

### To Apply

```bash
git checkout delivery
git merge sync/main-to-delivery-260502
git push origin delivery
```

---

## What Was Missing (Before Sync)

### Critical Hotfixes (main had, delivery didn't)

| Commit | Description | Impact |
|--------|-------------|--------|
| `1465af1f` | Referral async SQLAlchemy fix | **CRITICAL** - webhooks crash without this |
| `a4824307` | TDEE helpers async/await | 500 errors on /discover |
| `b4863f47` | Webhook anonymous RevenueCat lookup | Failed subscription renewals |
| `342c104f` | Translation service in recipe endpoint | Broken translations |
| `079dd3b6` | meal_instruction/ingredients ORM fix | Missing translated content |
| `1b70b90c` | Load translations in meal detail handler | English shown instead of locale |
| `d1d33edc` | i18n cache key missing language | Cross-language cache pollution |
| `72b4dd40` | DeepL source/target English fix | Translation direction errors |
| `8d10be70` | target_weight_kg support | Mobile field ignored |
| `41b38289` | Migration renumbering 053→052 | Broken migration chain |

### Code Evidence: Referral System Bug

**delivery (BROKEN - sync handlers):**
```python
def handle(self, command, uow) -> None:
    repo = ReferralRepository(uow.session)
    code = repo.get_code_by_code(command.code)  # sync call with AsyncSession = crash
```

**main (FIXED - async handlers):**
```python
async def handle(self, command) -> None:
    async with AsyncUnitOfWork() as uow:
        repo = ReferralRepository(uow.session)
        code = await repo.get_code_by_code(command.code)  # async
```

---

## Root Cause Analysis

### Why Branches Diverged

1. **Apr 25:** `5e90665a Release/25-apr` - Squash merge delivery→main
   - Brought delivery features to main
   - Single parent = broke git history tracking

2. **Apr 25-May 2:** Both branches evolved independently
   - main: Got 13 hotfixes for production issues
   - delivery: Got new features (goal tracking, weight entries, etc.)

3. **May 2:** Sync attempts failed
   - `ae89fb1b` - Commit message claimed to include fixes, but files weren't actually changed
   - `66a979e1` - Empty commit (no file changes)

### The "Broken Sync" Problem

The commit `ae89fb1b` message says:
```
* fix(referral): convert to async SQLAlchemy for AsyncSession compatibility (#215)
  Routes converted to async def + await handler.handle()
```

But `git show ae89fb1b --stat | grep referrals.py` returns **nothing** - the file wasn't changed.

---

## Branch Differences (After Sync)

### delivery has (main doesn't)

| Feature | Key Files |
|---------|-----------|
| Goal progress tracking | `goal_start_weight_kg`, `goal_started_at` |
| Weight entries | `weight_entries.py`, migrations 057-058 |
| Migration CLI | `migrations/cli.py` |
| Async UoW migration | Throughout codebase |
| Notification optimization | Various |
| Meal image fastpath | Various |

### main has (delivery will have after sync)

All 13 hotfixes listed above.

---

## Rule: No Squash Merges

**From now on:** Always use real merges between main↔delivery.

| GitHub PR | CLI |
|-----------|-----|
| "Create a merge commit" ✓ | `git merge` ✓ |
| "Squash and merge" ✗ | `git merge --squash` ✗ |

**Why:** Squash breaks history tracking → false conflicts on future syncs.

---

## Next Steps

1. Merge sync branch to delivery: `git merge sync/main-to-delivery-260502`
2. Push to remote: `git push origin delivery`
3. Later: Merge delivery to main when ready for release
