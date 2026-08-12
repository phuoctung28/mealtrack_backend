# RevenueCat anonymous redemption validation

Date: 2026-08-04

## Scope

- Backend: focused pytest for redemption/webhook paths.
- Flutter: analyzer on changed auth files, plus focused coordinator test.
- Web: `npm test`.

## Commands

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
./.venv/bin/pytest tests/unit/infra/services/test_web_funnel_redemption_service.py tests/unit/api/test_webhook_handler.py tests/unit/api/routes/test_web_funnel_lead_routes.py -q

cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
flutter analyze lib/features/auth/application/providers/web_purchase_redemption_provider.dart lib/features/auth/application/services/web_purchase_redemption_coordinator.dart lib/features/auth/presentation/screens/splash_screen.dart test/features/auth/application/services/web_purchase_redemption_coordinator_test.dart
flutter test test/features/auth/application/services/web_purchase_redemption_coordinator_test.dart

cd /Users/alexnguyen/Desktop/Nut/nutree_web_funnel
npm test
```

## Results

- Backend pytest: `40 passed in 2.13s`
- Flutter analyze: `No issues found! (ran in 6.3s)`
- Flutter coordinator test: `11 tests passed`
- Web npm test: `23 test files passed, 81 tests passed in 1.53s`

## Notes

- Backend pytest emitted the existing warning about `pytest.ini` taking precedence over `pyproject.toml` config.
- Flutter and web runs pulled dependency metadata / newer-version notices, but no validation failures.

## Live Boundaries Not Verified

- RevenueCat sandbox webhook delivery.
- RevenueCat provider-side alias behavior.
- Firebase sign-in on a real device or simulator.
- Cross-device redemption flow end-to-end.
- Production web funnel or backend webhook delivery.

## Conclusion

- Local focused validation passed for the changed backend, Flutter, and web paths.
- Remaining risk is only live provider/device integration, which was not exercised here.
