# Backend Code Standards — Python Style & Conventions

**Last Updated:** April 17, 2026  
**Scope:** All code in `src/` (430 files, ~38.5K LOC)  
**Applies To:** Typing, naming, imports, code organization, error handling

---

## File Naming Conventions

### All Files
- Use `snake_case.py` for all Python files
- Descriptive names (prefer longer, clearer names over abbreviations)

### Pattern-Based Naming
| Pattern | Example | Purpose |
|---------|---------|---------|
| `*_command.py` | `create_meal_command.py` | Write operations |
| `*_query.py` | `get_meal_by_id_query.py` | Read operations |
| `*_event.py` | `meal_created_event.py` | Domain events |
| `*_handler.py` | `create_meal_command_handler.py` | CQRS handlers |
| `*_service.py` | `tdee_service.py` | Domain/app services |
| `*_repository.py` | `meal_repository.py` | Data access |
| `*_port.py` | `meal_repository_port.py` | Port interfaces |

---

## File Size Limits

- **Target**: <200 LOC per file for readability
- **Maximum**: 400 LOC absolute limit
- **Action**: Split into smaller, focused modules if exceeding target

---

## Type Hints (Required)

**All function signatures must have type hints:**

```python
def calculate_tdee(
    request: TdeeRequest,
    formula: Optional[str] = None,
) -> TdeeResponse:
    pass
```

---

## Dataclasses

Prefer dataclasses for DTOs and value objects:

```python
@dataclass
class Nutrition:
    calories: float
    protein: float
    carbs: float
    fat: float
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.calories < 0:
            raise ValueError("Calories cannot be negative")
```

---

## Enums

Use enums for constrained values:

```python
class MealStatus(str, Enum):
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"
```

---

## Error Handling

### Exception Hierarchy
```
MealTrackException (base)
├── ValidationException → 400
├── ResourceNotFoundException → 404
├── BusinessLogicException → 422
├── ConflictException → 409
├── ExternalServiceException → 503
├── AuthenticationException → 401
└── AuthorizationException → 403
```

### Usage in Handlers
```python
async def handle(self, query: GetMealByIdQuery) -> Meal:
    meal = self.meal_repo.find_by_id(query.meal_id)
    if not meal:
        raise ResourceNotFoundException(
            message=f"Meal {query.meal_id} not found",
            error_code="MEAL_NOT_FOUND",
            details={"meal_id": query.meal_id}
        )
    return meal
```

---

## Code Quality Checklist

- [ ] All functions have type hints
- [ ] Dataclasses used for DTOs
- [ ] Enums for constrained values
- [ ] Exceptions follow hierarchy
- [ ] File size <200 LOC (target) or <400 LOC (max)
- [ ] `snake_case.py` file names
- [ ] Pattern-based naming (command/query/event/handler/service/repo)
- [ ] No `dynamic` types (always explicit)
- [ ] Run before commit: `black src/ && flake8 src/ && mypy src/`

---

See related: `testing-standards.md`, `cqrs-guide.md`
