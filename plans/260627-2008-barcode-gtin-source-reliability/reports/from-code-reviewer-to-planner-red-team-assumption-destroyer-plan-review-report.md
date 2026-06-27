## Finding 1: FDC fallback can turn provider outage into barcode 500
- **Severity:** Critical
- **Location:** Phase 2, section "Requirements"
- **Flaw:** The plan says missing USDA key or USDA failure must degrade to the next cascade step, but the implementation steps only add `FoodDataService.get_branded_food_by_gtin()` and insert it into the handler. They do not specify the required exception boundary around that new network call.
- **Failure scenario:** USDA key is unset, quota-limited, or FDC returns 5xx. `FoodDataService._get()` raises from `resp.raise_for_status()`. If the new cascade call is inserted like the existing direct FatSecret/OpenFoodFacts calls, the barcode endpoint returns 500 before Brave/AI fallback.
- **Evidence:** Plan requirement: Phase 2 lines 39-40 says provider failure degrades and raw payloads are not logged. Current USDA client raises on HTTP errors at `src/infra/adapters/food_data_service.py:24-35`. Current barcode handler has no broad provider boundary around normal cascade calls at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:127-161`; only FatSecret name search is caught at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:200-229`.
- **Suggested fix:** Phase 2 must require `get_branded_food_by_gtin()` to catch expected HTTP/config errors and return `None`, or require the handler to wrap only the FDC step and append `usda_fdc_error` before continuing.

## Finding 2: `is_verified=true` is promised but discarded by cache upsert
- **Severity:** Critical
- **Location:** Phase 2, section "Implementation Steps"
- **Flaw:** The plan says FDC exact matches set `is_verified: true` and get cached, but current barcode cache path cannot persist `is_verified` because `FoodReferenceRepositoryAsync.upsert()` drops that field.
- **Failure scenario:** FDC exact GTIN hit is returned as verified in-memory, then cached. Later scans hit `food_reference` and return `source=cache`; downstream code sees `is_verified=False` because the column default is false and the upsert ignored the provided flag. The rollout logic and any future moderation/promotion rules read false confidence data.
- **Evidence:** Phase 2 maps `is_verified: true` at lines 78-87 and caches exact FDC hits at lines 88-90. The table has `is_verified` at `src/infra/database/models/food_reference_model.py:53-56`, but the async upsert value list omits it at `src/infra/repositories/food_reference_repository_async.py:80-101`. The handler cache path calls that generic upsert at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:367-378`.
- **Suggested fix:** Add Phase 2 work to persist `is_verified` in the barcode upsert path, with regression coverage that an exact FDC hit later returns verified from cache.

## Finding 3: FDC mapper shape is incompatible with `BarcodeProductResponse`
- **Severity:** Critical
- **Location:** Phase 2, section "Architecture"
- **Flaw:** The plan handwaves "FoodMappingService maps barcode response", but the existing USDA mapper returns search/detail shapes with nested `nutrients` or `macros`, not the flat `protein_100g`, `carbs_100g`, and `fat_100g` fields required by barcode response and handler nutrition checks.
- **Failure scenario:** Implementer reuses `map_search_item()` or `map_food_details()` for an FDC row. The handler's `_has_nutrition()` sees no `*_100g` keys and treats the exact FDC hit as partial/no nutrition, or the route tries to construct `BarcodeProductResponse` without flat macro fields and returns an incomplete product.
- **Evidence:** Phase 2 lines 50-53 places `FoodMappingService` before the handler, and lines 77-86 list barcode fields. Current response model requires flat barcode fields at `src/api/schemas/response/barcode_product_response.py:13-20`. Handler nutrition gating reads only flat `*_100g` keys at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:276-286`. Existing `map_search_item()` returns `nutrients: {protein, fat, carbs}` for USDA at `src/domain/services/food_mapping_service.py:82-107`; `map_food_details()` returns nested `macros` at `src/domain/services/food_mapping_service.py:165-185`.
- **Suggested fix:** Phase 2 must define a dedicated `map_fdc_barcode_product()` contract that returns the exact `BarcodeProductResponse`/handler shape, including derived calories if needed and flat per-100g macros.

## Finding 4: Invalid barcode 400 path is not wired through the actual route contract
- **Severity:** High
- **Location:** Phase 1, section "Implementation Steps"
- **Flaw:** The plan leaves normalization "route or handler" open, but only the route can safely translate invalid input into an HTTP 400. If the handler raises `InvalidBarcodeError`, the current route does not catch it.
- **Failure scenario:** Implementer puts `normalize_gtin()` in `LookupBarcodeQueryHandler` as allowed by the plan. Invalid input raises a domain/application exception through `event_bus.send()`, FastAPI treats it as an unhandled exception, and clients get 500 instead of the planned 400/404 behavior.
- **Evidence:** Phase 1 lines 82-86 explicitly allows route or handler normalization and recommends a route-raised `HTTPException(400)`. Current route only converts `None` to 404 at `src/api/routes/v1/foods.py:51-59`; it has no handler exception mapping. Current route test pins barcode miss as 404 at `tests/unit/api/test_small_v1_routers.py:88-93`.
- **Suggested fix:** Phase 1 must choose one boundary. Either normalize in the route before `event_bus.send()`, or add explicit route exception translation for `InvalidBarcodeError` with tests for both malformed path input and checksum-invalid digit strings.

## Finding 5: Cache alias lookup plan ignores single-column unique upsert semantics
- **Severity:** High
- **Location:** Phase 1, section "Implementation Steps"
- **Flaw:** The plan says cache aliases should prevent UPC/EAN duplicate rows, but the repository only has `get_by_barcode(barcode)` and an upsert keyed on a single `barcode`. The plan does not define which alias becomes canonical or how existing rows under noncanonical aliases are reconciled.
- **Failure scenario:** A product was previously cached as `0123456789012`. User scans `123456789012`. Alias lookup finds the old row, but a later provider hit or cache write uses the raw scanned value and inserts/updates a separate row. Future scans keep splitting history and source trust across two barcodes.
- **Evidence:** Phase 1 lines 87-90 says try aliases and prove UPC-A/zero-prefixed EAN-13 hit the same cached row. Current cache lookup accepts one string at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:356-365`. Async repository lookup filters exact barcode at `src/infra/repositories/food_reference_repository_async.py:37-45`. Upsert conflicts only on `FoodReferenceModel.barcode` at `src/infra/repositories/food_reference_repository_async.py:102-108`, and the model has a single unique barcode column at `src/infra/database/models/food_reference_model.py:28-30`.
- **Suggested fix:** Phase 1 must define canonical storage (`gtin_14` or preserving provider barcode) and require all cache writes to use that canonical value, plus a migration/backfill or explicit "old aliases remain read-only until touched" behavior.

## Finding 6: Source enum/docs change does not account for response consumers
- **Severity:** Medium
- **Location:** Phase 2, section "Related Code Files"
- **Flaw:** The plan updates source docs but does not require consumer/call-site verification for a new `source="usda_fdc"` value. The schema currently documents a closed list that excludes it, and tests currently assert only existing source values.
- **Failure scenario:** Backend returns `usda_fdc`; mobile or analytics code that switches over known sources treats it as unknown, hides confidence badges, or mislabels it as untrusted. CI can pass because Pydantic accepts any string and backend tests do not enumerate the client contract.
- **Evidence:** Phase 2 line 64 only says update response docs. Current response description lists only `cache, fatsecret, openfoodfacts, brave_search, ai_estimate` at `src/api/schemas/response/barcode_product_response.py:23-26`. Current handler tests assert `fatsecret` only at `tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py:88-91`; route simply returns `BarcodeProductResponse(**result)` without enum validation at `src/api/routes/v1/foods.py:53-59`.
- **Suggested fix:** Add a plan task to enumerate backend and mobile/source consumers before adding `usda_fdc`, and add a backend source-policy test that treats source values as an explicit contract.

## Finding 7: Name verification promise exceeds actual provider interfaces
- **Severity:** High
- **Location:** Phase 3, section "Requirements"
- **Flaw:** The plan says Brave identity can trigger structured provider verification by name and the target flow names FatSecret/FDC/OFF, but only FatSecret has a current name-search path in the barcode handler. Phase 2 only adds exact GTIN lookup for FDC, and OpenFoodFacts exposes barcode lookup only in this codebase.
- **Failure scenario:** Brave extracts a plausible product name after all barcode providers miss. The implementation can only call FatSecret by name. If FatSecret misses but FDC or OFF would have found by name, the product falls to AI estimate despite the plan claiming structured verification by multiple providers.
- **Evidence:** Plan target flow says candidate verified by `FatSecret/FDC/OFF name or GTIN` in `plan.md:60-63`. Phase 3 line 35 requires Brave identity to trigger structured provider verification by name, while line 78 makes FDC name verification conditional. Current barcode handler has FatSecret name search only at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:194-223`. OpenFoodFacts service only has `get_product(barcode)` at `src/infra/adapters/open_food_facts_service.py:35-70`. Phase 2 proposed FDC method is exact `get_branded_food_by_gtin(gtin_aliases)` at `phase-02-usda-fdc-branded-provider.md:73-76`, not name search.
- **Suggested fix:** Narrow Phase 3 to "FatSecret name verification only" for this plan, or add explicit FDC/OFF name-search interfaces, mapping contracts, tests, and source-order decisions.

## Finding 8: Port expansion misses all abstract-method implementers if another method is added to mapping
- **Severity:** Medium
- **Location:** Phase 2, section "Related Code Files"
- **Flaw:** The plan correctly lists `FoodDataServicePort` doubles, but treats `FoodMappingServicePort` as optional if a new mapper method is added. If the new barcode mapper is added to the abstract port, all implementers/test doubles must be updated and event-bus singleton tests that monkeypatch mapping services may need adjustment.
- **Failure scenario:** Implementer adds `map_fdc_barcode_product()` as an abstract method. `FoodMappingService` is updated, but tests using simple mocks or ABC-derived mapping doubles fail at import/instantiation or silently miss coverage because the event bus is monkeypatched with plain objects.
- **Evidence:** Phase 2 line 61 says modify `FoodMappingServicePort` only "if a new mapper method is added", but there is no required consumer enumeration. The mapping port is an ABC with two abstract methods at `src/domain/ports/food_mapping_service_port.py:5-40`. Event-bus construction obtains and injects the mapper into multiple handlers at `src/api/dependencies/event_bus.py:210-243`. Tests monkeypatch `get_food_data_service` and related dependencies in singleton coverage at `tests/unit/api/test_event_bus_dependency_singletons.py:25-81`, and integration fixtures define concrete provider doubles at `tests/integration/api/conftest.py:341-366`.
- **Suggested fix:** Make the plan choose whether the barcode mapper is public port API or private concrete helper. If public, add an explicit `rg FoodMappingServicePort|get_food_mapping_service|map_` update checklist and tests.

**Status:** DONE_WITH_CONCERNS
**Summary:** Contract review found eight plan blockers/risks around exception boundaries, cache persistence, mapper response shape, alias canonicalization, source contract consumers, and nonexistent provider name verification paths.
**Concerns/Blockers:** Review was grep/read-only as requested; no lint, build, or tests were run.
