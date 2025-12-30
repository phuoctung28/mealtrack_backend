# MealTrack Backend - Code Standards & Conventions

**Version:** 1.3
**Last Updated:** December 31, 2024
**Scope**: Python source code in `src/` directory (Python 3.11+)
**Phase 03 Update**: File size guidelines updated post-large-file refactoring (72% LOC reduction achieved)

---

## Table of Contents

1. [Python Style Guide](#python-style-guide)
2. [Type Hints & Mypy](#type-hints--mypy)
3. [File Organization](#file-organization)
4. [Naming Conventions](#naming-conventions)
5. [Class & Function Patterns](#class--function-patterns)
6. [Error Handling](#error-handling)
7. [Testing Standards](#testing-standards)
8. [Documentation Standards](#documentation-standards)
9. [Database & ORM Patterns](#database--orm-patterns)
10. [API Patterns](#api-patterns)
11. [Code Review Checklist](#code-review-checklist)

---

## Python Style Guide

### Code Formatting

**Tools Used**:
- **ruff**: Fast Python linter and formatter
- **black**: Code formatter (PEP 8 compliant)
- **isort**: Import statement sorting

**Configuration**:
```bash
# Format code
ruff format src/

# Lint code
ruff check src/

# Sort imports
isort src/
```

### Formatting Rules

#### Line Length
```python
# Target: 88 characters (Black default)
# Maximum: 100 characters (hard limit)
# Exceptions: URLs, error messages (can exceed if justified)

# Good
def process_meal_image(
    image_path: str,
    user_id: str,
    analysis_type: str = "full"
) -> MealAnalysisResult:
    pass

# Bad - exceeds 100 characters
def process_meal_image_with_extensive_options(image_path: str, user_id: str, analysis_type: str = "full", include_recommendations: bool = True) -> MealAnalysisResult:
    pass
```

#### Imports Organization
```python
# Order: standard lib -> third-party -> local imports
# Sections separated by blank lines

# Standard library
import json
import logging
from datetime import datetime
from typing import List, Optional

# Third-party
import aiohttp
from fastapi import FastAPI
from sqlalchemy import Column, String

# Local imports
from src.domain.model.meal import Meal
from src.infra.database.models.meal import MealORM
```

**Auto-format on save**:
```bash
# Run before commit
ruff format src/ && isort src/ && ruff check src/
```

#### Whitespace & Blank Lines
```python
# Two blank lines between top-level definitions
class MealService:
    pass


class UserService:
    pass


# One blank line between methods
class MealService:
    def analyze_meal(self) -> Meal:
        pass

    def create_meal(self) -> Meal:
        pass
```

#### Quotes
```python
# Use double quotes for strings
message = "Meal analysis complete"

# Use single quotes for docstrings when necessary
docstring = '''
    Multi-line docstring
'''

# f-strings for interpolation
user_id = "123"
result = f"Processing meal for user {user_id}"
```

---

## Type Hints & Mypy

### Type Hint Requirements

**Coverage Target**: 100% for all new code

```python
# All function parameters must have type hints
def process_image(image_path: str, user_id: str) -> MealAnalysisResult:
    pass

# Method parameters (including self)
class MealService:
    def analyze(self, meal_id: str) -> Meal:
        pass

# Class attributes (in __init__ or class-level)
class Meal:
    meal_id: str
    user_id: str
    items: List[MealItem]
    created_at: datetime
```

### Complex Type Hints

```python
# Optional types
from typing import Optional

def get_meal(meal_id: str) -> Optional[Meal]:
    pass

# Union types
from typing import Union

def process(data: Union[str, bytes]) -> str:
    pass

# Generic types
from typing import Dict, List

def group_by_user(meals: List[Meal]) -> Dict[str, List[Meal]]:
    pass

# Callable types
from typing import Callable

handler: Callable[[str], Meal] = process_meal

# TypeVar for generics
from typing import TypeVar

T = TypeVar("T")

def first(items: List[T]) -> Optional[T]:
    return items[0] if items else None
```

### Mypy Configuration

```ini
# mypy.ini or pyproject.toml [tool.mypy]
[mypy]
python_version = "3.10"
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
disallow_untyped_calls = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
```

### Running Type Checks

```bash
# Type check entire project
mypy src/

# Type check specific file
mypy src/domain/services/meal_service.py

# Report coverage
mypy --html mypy-report src/
```

---

## File Organization

### Module Structure

```python
# Standard module structure

"""
Module docstring describing the module's purpose.

This module handles meal creation and validation. It includes
services for processing meal images and storing meal data.
"""

# Imports (organized by type)
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.meal import Meal
from src.domain.services.nutrition_service import NutritionService

# Module-level constants
logger = logging.getLogger(__name__)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


# Main class/function definitions
class MealService:
    pass


async def process_meal_image(image_path: str) -> Meal:
    pass
```

### File Size Guidelines

**UPDATED POST PHASE-03**: Target sizes reduced to enforce modularity and single-responsibility principle.

| File Type | Ideal Size | Maximum Size | Action if Exceeded |
|-----------|-----------|--------------|-------------------|
| Service class | 150-300 lines | 400 lines | Extract to subdirectory module |
| Repository | 150-300 lines | 400 lines | Extract operations to modules |
| Route handler | 50-100 lines | 200 lines | Split by resource/feature |
| Schema definition | 50-150 lines | 300 lines | Group related schemas |
| Domain model | 100-200 lines | 400 lines | Use composition, not inheritance |

**Refactoring Pattern (Phase 03 Proven)**:

When a service exceeds 400 LOC, extract into subdirectory with focused modules:

```python
# Before (too large: 534 LOC)
src/domain/services/meal_plan_orchestration_service.py

# After (split by responsibility: 4 modules, 155 LOC total service)
src/domain/services/meal_plan/
├── __init__.py                    # Exports all components
├── meal_plan_validator.py         # 80 LOC: Validation logic
├── meal_plan_generator.py         # 120 LOC: AI integration
├── meal_plan_formatter.py         # 75 LOC: Response formatting
└── request_builder.py             # 90 LOC: API request construction
```

**Results from Phase 03**:
- meal_plan: 534 → 155 LOC (-71%)
- meal_suggestion: 525 → 195 LOC (-63%)
- conversation: 476 → 63 LOC (-87%)
- notification: 428 → 138 LOC (-68%)
- Average: 491 → 138 LOC per service (-72%)

---

## Naming Conventions

### Modules & Files

```python
# Use snake_case for file names
src/domain/services/meal_service.py       # ✓ Good
src/domain/services/MealService.py        # ✗ Bad
src/domain/services/meal-service.py       # ✗ Bad

# Private modules start with underscore
src/utils/_internal_helpers.py            # Private
src/utils/helpers.py                      # Public
```

### Classes

```python
# Use PascalCase for class names
class MealService:              # ✓ Good
class UserProfile:              # ✓ Good
class meal_service:             # ✗ Bad
class MEAL_SERVICE:             # ✗ Bad

# Private classes start with underscore
class _InternalHelper:          # Private, not for external use
class MealService:              # Public API
```

### Functions & Methods

```python
# Use snake_case for function/method names
def process_meal_image():           # ✓ Good
def validate_nutrition_data():      # ✓ Good
def ProcessMealImage():             # ✗ Bad

# Private functions start with underscore
def _validate_image_format():       # Private helper
def process_meal_image():           # Public API

# Async functions follow same convention
async def process_meal_image():     # ✓ Good
```

### Constants

```python
# Use UPPER_SNAKE_CASE for module-level constants
MAX_IMAGE_SIZE = 10 * 1024 * 1024   # ✓ Good
ANALYSIS_TIMEOUT = 30               # ✓ Good
max_image_size = 10 * 1024 * 1024   # ✗ Bad

# Class constants
class MealStatus:
    PROCESSING = "processing"       # ✓ Good
    ready = "ready"                 # ✗ Bad
```

### Variables & Parameters

```python
# Use snake_case for variables
user_id = "123"                     # ✓ Good
userId = "123"                      # ✗ Bad
UserID = "123"                      # ✗ Bad

# Context variables (specific naming)
request_id = "req-123"
correlation_id = "corr-456"
transaction_id = "txn-789"
```

### Boolean Variables

```python
# Prefix with is_, has_, can_, should_
is_verified = True                  # ✓ Good
has_permission = False              # ✓ Good
can_edit = True                     # ✓ Good
should_notify = False               # ✓ Good

verified = True                     # ✗ Less clear
```

### Enumeration Values

```python
# Use snake_case for enum members in strings, PascalCase for classes
class MealStatus(str, Enum):
    PROCESSING = "processing"       # ✓ Good
    READY = "ready"                 # ✓ Good
    FAILED = "failed"               # ✓ Good

# Database enums use specific case
# E.g., from src/infra/database/models/enums.py
```

---

## Class & Function Patterns

### Class Definition Pattern

```python
class MealService:
    """Service for meal-related operations.

    This service handles meal creation, editing, analysis,
    and nutritional calculations.

    Example:
        >>> service = MealService(repository, ai_service)
        >>> meal = await service.analyze_meal(image_path)
    """

    def __init__(
        self,
        meal_repository: MealRepository,
        ai_service: GeminiService,
        nutrition_service: NutritionService,
    ) -> None:
        """Initialize the MealService.

        Args:
            meal_repository: Repository for meal data access
            ai_service: Service for AI-powered analysis
            nutrition_service: Service for nutrition calculations
        """
        self._meal_repository = meal_repository
        self._ai_service = ai_service
        self._nutrition_service = nutrition_service

    async def analyze_meal(self, image_path: str) -> Meal:
        """Analyze a meal image and extract nutritional data.

        Args:
            image_path: Path to meal image file

        Returns:
            Meal object with extracted nutrition data

        Raises:
            FileNotFoundError: If image file not found
            AnalysisError: If AI analysis fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Implementation...
        pass
```

### Dependency Injection Pattern

```python
# Use constructor injection for dependencies
class MealService:
    def __init__(
        self,
        meal_repository: MealRepository,
        ai_service: AIService,
    ) -> None:
        self._meal_repository = meal_repository
        self._ai_service = ai_service

# In API routes, use FastAPI Depends
from fastapi import Depends

@router.post("/analyze")
async def analyze_meal(
    image: UploadFile,
    service: MealService = Depends(get_meal_service),
) -> MealResponse:
    return await service.analyze(image)
```

### Async/Await Pattern

```python
# Always use async/await for I/O operations
class MealRepository:
    async def get_by_id(self, meal_id: str) -> Optional[Meal]:
        """Get meal by ID asynchronously."""
        async with self.session:
            return await self.session.get(MealORM, meal_id)

    async def save(self, meal: Meal) -> Meal:
        """Save meal to database."""
        orm_model = self.mapper.to_orm(meal)
        async with self.session:
            self.session.add(orm_model)
            await self.session.flush()
        return meal

# In handlers/routes
@router.post("/meals")
async def create_meal(data: MealRequest) -> MealResponse:
    result = await service.create(data)
    return result
```

### Error Handling Pattern

```python
# Define custom exceptions in domain layer
class MealAnalysisError(Exception):
    """Raised when meal analysis fails."""
    pass

class InvalidMealDataError(ValueError):
    """Raised when meal data is invalid."""
    pass

# Use exceptions in services
class MealService:
    async def analyze_meal(self, image_path: str) -> Meal:
        try:
            result = await self._ai_service.analyze(image_path)
        except AIServiceError as e:
            raise MealAnalysisError(f"Analysis failed: {e}") from e

        if not result.foods:
            raise InvalidMealDataError("No foods detected in image")

        return result

# In API routes
@router.post("/analyze")
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        meal = await service.analyze_meal(request.image_path)
        return AnalyzeResponse(meal=meal)
    except MealAnalysisError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except InvalidMealDataError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## Error Handling

### Exception Hierarchy

```python
# Create domain-specific exceptions
class MealTrackException(Exception):
    """Base exception for MealTrack domain."""
    pass

class MealException(MealTrackException):
    """Base for meal-related errors."""
    pass

class MealAnalysisError(MealException):
    """Meal analysis failed."""
    pass

class MealNotFoundError(MealException):
    """Meal not found."""
    pass

# External service exceptions
class ExternalServiceError(MealTrackException):
    """External service call failed."""
    pass

class FirebaseAuthError(ExternalServiceError):
    """Firebase authentication failed."""
    pass

class GeminiAPIError(ExternalServiceError):
    """Gemini API call failed."""
    pass
```

### Error Handling in Services

```python
# Log errors appropriately
import logging
logger = logging.getLogger(__name__)

class MealService:
    async def process_image(self, image_path: str) -> Meal:
        try:
            result = await self._ai_service.analyze(image_path)
            logger.info(f"Image analyzed successfully: {image_path}")
            return result
        except AIServiceError as e:
            logger.error(
                f"AI analysis failed for {image_path}",
                exc_info=True,
                extra={"image_path": image_path}
            )
            raise MealAnalysisError("Image analysis failed") from e
        except Exception as e:
            logger.exception(f"Unexpected error processing {image_path}")
            raise
```

### Error Handling in API Routes

```python
@router.post("/analyze")
async def analyze_meal(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze meal image."""
    try:
        meal = await service.analyze_meal(request.image_path)
        return AnalyzeResponse(
            success=True,
            data=meal.to_dict()
        )
    except MealAnalysisError as e:
        # 422: Unprocessable Entity (validation error)
        raise HTTPException(status_code=422, detail=str(e))
    except MealNotFoundError as e:
        # 404: Not Found
        raise HTTPException(status_code=404, detail=str(e))
    except FirebaseAuthError as e:
        # 401: Unauthorized
        raise HTTPException(status_code=401, detail="Authentication failed")
    except ExternalServiceError as e:
        # 503: Service Unavailable
        logger.exception("External service error")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        # 500: Internal Server Error
        logger.exception("Unexpected error")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

---

## Testing Standards

### Test File Organization

```python
# tests/unit/test_meal_service.py
"""Tests for MealService."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.domain.services.meal_service import MealService
from src.domain.model.meal import Meal


class TestMealService:
    """Test suite for MealService."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Mock meal repository."""
        return Mock()

    @pytest.fixture
    def mock_ai_service(self) -> Mock:
        """Mock AI service."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository, mock_ai_service) -> MealService:
        """Create MealService instance with mocks."""
        return MealService(
            meal_repository=mock_repository,
            ai_service=mock_ai_service,
        )

    @pytest.mark.asyncio
    async def test_analyze_meal_success(self, service, mock_ai_service):
        """Test successful meal analysis."""
        mock_ai_service.analyze = AsyncMock(return_value=Meal(...))

        result = await service.analyze_meal("image.jpg")

        assert result.meal_id is not None
        mock_ai_service.analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_meal_file_not_found(self, service):
        """Test meal analysis with missing file."""
        with pytest.raises(FileNotFoundError):
            await service.analyze_meal("nonexistent.jpg")
```

### Testing Best Practices

1. **Naming**: `test_<function>_<scenario>`
2. **Structure**: Arrange → Act → Assert (AAA pattern)
3. **Mocking**: Mock external dependencies, test behavior
4. **Async Tests**: Use `@pytest.mark.asyncio` decorator
5. **Fixtures**: Use pytest fixtures for reusable test data
6. **Coverage**: Target >70% coverage, 100% for critical paths

### Test Markers

```python
# Mark tests by type
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow          # Slow tests
@pytest.mark.asyncio       # Async tests
@pytest.mark.skip          # Skip test
@pytest.mark.xfail         # Expected to fail
```

---

## Documentation Standards

### Module Docstrings

```python
"""
Module for meal analysis and processing.

This module provides services for analyzing meal images using AI vision,
extracting nutritional information, and storing meal data.

Classes:
    MealService: Main service for meal operations
    MealAnalyzer: AI-powered meal analysis

Examples:
    >>> service = MealService(repository)
    >>> meal = await service.analyze_image("path/to/image.jpg")
    >>> print(meal.total_nutrition.calories)
"""
```

### Function/Method Docstrings (Google style)

```python
async def analyze_meal(
    self,
    image_path: str,
    user_id: str,
) -> Meal:
    """Analyze meal image and extract nutritional data.

    Uses AI vision to identify foods and estimate nutritional content.

    Args:
        image_path: Path to meal image file (JPG, PNG, WebP)
        user_id: ID of user for permission validation

    Returns:
        Meal object containing extracted nutrition data

    Raises:
        FileNotFoundError: If image file not found
        PermissionError: If user not authorized
        MealAnalysisError: If AI analysis fails

    Example:
        >>> service = MealService(repository, ai_service)
        >>> meal = await service.analyze_meal("meal.jpg", "user_123")
        >>> print(f"Calories: {meal.nutrition.calories}")
    """
```

### Inline Comments

```python
# Use sparingly - comments should explain WHY, not WHAT

# BAD: Explains what code does
x = x + 1  # Increment x

# GOOD: Explains why
# Offset timestamp by 1 second to account for database replication lag
timestamp = timestamp + 1

# GOOD: Complex algorithm explanation
# Use exponential backoff with jitter to avoid thundering herd
# during distributed service recovery
for attempt in range(max_retries):
    delay = exponential_backoff(attempt) + random_jitter()
    try:
        return await service.call()
    except ConnectionError:
        await asyncio.sleep(delay)
```

---

## Database & ORM Patterns

### SQLAlchemy Model Pattern

```python
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.models.base import Base


class MealORM(Base):
    """ORM model for Meal entity."""

    __tablename__ = "meals"

    # Primary key
    id = Column(String(36), primary_key=True, index=True)

    # Foreign keys
    user_id = Column(String(36), ForeignKey("users.id"), index=True)

    # Data fields
    calories = Column(Float, nullable=False)
    protein = Column(Float, nullable=False)
    carbs = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserORM", back_populates="meals")
    items = relationship("FoodItemORM", back_populates="meal", cascade="all, delete-orphan")
```

### Repository Pattern

```python
class MealRepository:
    """Repository for meal data access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, meal_id: str) -> Optional[Meal]:
        """Get meal by ID."""
        orm_model = await self._session.get(MealORM, meal_id)
        if not orm_model:
            return None
        return self._to_domain(orm_model)

    async def save(self, meal: Meal) -> Meal:
        """Save meal to database."""
        orm_model = self._to_orm(meal)
        self._session.add(orm_model)
        await self._session.flush()
        return meal

    async def delete(self, meal_id: str) -> None:
        """Delete meal by ID."""
        await self._session.delete(MealORM, meal_id)
        await self._session.flush()

    def _to_domain(self, orm: MealORM) -> Meal:
        """Convert ORM model to domain model."""
        return Meal(
            meal_id=orm.id,
            user_id=orm.user_id,
            calories=orm.calories,
            # ...
        )

    def _to_orm(self, meal: Meal) -> MealORM:
        """Convert domain model to ORM model."""
        return MealORM(
            id=meal.meal_id,
            user_id=meal.user_id,
            calories=meal.calories,
            # ...
        )
```

### Query Patterns

```python
# Use SQLAlchemy 2.0 style async queries
from sqlalchemy import select

async def get_recent_meals(
    self,
    user_id: str,
    limit: int = 10
) -> List[Meal]:
    """Get recent meals for user."""
    stmt = select(MealORM).where(
        MealORM.user_id == user_id
    ).order_by(
        MealORM.created_at.desc()
    ).limit(limit)

    result = await self._session.execute(stmt)
    orm_models = result.scalars().all()
    return [self._to_domain(m) for m in orm_models]

# Filter with multiple conditions
stmt = select(MealORM).where(
    (MealORM.user_id == user_id) &
    (MealORM.created_at >= start_date) &
    (MealORM.created_at <= end_date)
)
```

### Eager Loading & N+1 Prevention

**Problem**: Lazy loading relationships causes N+1 queries (1 query for parent + N queries for children).

**Solution**: Use eager loading with `.options()` in queries:

```python
from sqlalchemy.orm import joinedload, selectinload

# Pattern: Define load options as module-level constant
_MEAL_LOAD_OPTIONS = (
    joinedload(MealORM.user),              # M2O: LEFT JOIN (single result)
    selectinload(MealORM.food_items),      # O2M: Separate SELECT IN (many results)
    selectinload(MealORM.images),          # O2M: Separate SELECT IN
)

# Apply in queries
async def get_by_id(self, meal_id: str) -> Optional[Meal]:
    """Get meal with all relationships eager loaded."""
    stmt = select(MealORM).options(*_MEAL_LOAD_OPTIONS).where(
        MealORM.id == meal_id
    )
    result = await self._session.execute(stmt)
    orm_model = result.scalar_one_or_none()
    return self._to_domain(orm_model) if orm_model else None

# Nested eager loading (for deep relationships)
_MEAL_PLAN_LOAD_OPTIONS = (
    selectinload(MealPlanORM.days)
    .selectinload(MealPlanDayORM.meals),   # Nested selectinload
)

async def get_weekly_plan(self, plan_id: str) -> Optional[MealPlan]:
    """Get meal plan with all nested relationships."""
    stmt = select(MealPlanORM).options(*_MEAL_PLAN_LOAD_OPTIONS).where(
        MealPlanORM.id == plan_id
    )
    result = await self._session.execute(stmt)
    return self._to_domain(result.scalar_one_or_none())
```

**Guidelines**:
- **joinedload()** for Many-to-One relationships (parent objects, small result sets)
- **selectinload()** for One-to-Many relationships (collections, larger result sets)
- **Nested selectinload()** for deep relationships (plan → days → meals)
- Always define load options as `_LOAD_OPTIONS` constant at module top
- Apply to all queries that access relationships

**Development**: Enable query logging in `.env` with `ENVIRONMENT=development` to verify query count reduction in logs.

---

## API Patterns

### Route Definition Pattern

```python
from fastapi import APIRouter, Depends, HTTPException
from src.api.dependencies import get_meal_service, get_current_user

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("/", response_model=MealResponse)
async def create_meal(
    request: MealRequest,
    service: MealService = Depends(get_meal_service),
    current_user: User = Depends(get_current_user),
) -> MealResponse:
    """Create a new meal.

    Args:
        request: Meal creation request
        service: Meal service (injected)
        current_user: Authenticated user (injected)

    Returns:
        Created meal

    Raises:
        HTTPException: If validation fails (422) or unauthorized (401)
    """
    try:
        meal = await service.create(request, user_id=current_user.id)
        return MealResponse.from_meal(meal)
    except InvalidMealDataError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{meal_id}", response_model=MealResponse)
async def get_meal(
    meal_id: str,
    service: MealService = Depends(get_meal_service),
    current_user: User = Depends(get_current_user),
) -> MealResponse:
    """Get meal by ID.

    Only meal owner can access.
    """
    meal = await service.get_by_id(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    if meal.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return MealResponse.from_meal(meal)
```

### Pydantic Schema Pattern

```python
from pydantic import BaseModel, Field, validator


class MealRequest(BaseModel):
    """Request for creating a meal."""

    foods: List[FoodItemRequest] = Field(
        ...,
        min_items=1,
        description="Foods in the meal"
    )
    consumed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When meal was consumed"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional meal notes"
    )

    @validator("consumed_at")
    def validate_consumed_at(cls, v: datetime) -> datetime:
        """Ensure consumed_at is not in future."""
        if v > datetime.utcnow():
            raise ValueError("Consumed time cannot be in future")
        return v

    class Config:
        schema_extra = {
            "example": {
                "foods": [
                    {"food_id": "123", "quantity": 150, "unit": "grams"}
                ],
                "consumed_at": "2024-01-01T12:00:00Z",
            }
        }


class MealResponse(BaseModel):
    """Response for meal data."""

    meal_id: str
    user_id: str
    foods: List[FoodItemResponse]
    nutrition: NutritionResponse
    consumed_at: datetime
    created_at: datetime

    @staticmethod
    def from_meal(meal: Meal) -> "MealResponse":
        """Convert domain model to response."""
        return MealResponse(
            meal_id=meal.meal_id,
            user_id=meal.user_id,
            # ...
        )
```

---

## Code Review Checklist

### Before Submitting PR

- [ ] Code follows style guide (ruff format, isort)
- [ ] All functions have type hints (100% coverage)
- [ ] Type checks pass (`mypy src/`)
- [ ] New tests added for new functionality
- [ ] Test coverage >= 70%
- [ ] All tests pass (`pytest`)
- [ ] Docstrings added to public functions/classes
- [ ] No hardcoded secrets or credentials
- [ ] Error handling implemented appropriately
- [ ] Async/await used for I/O operations
- [ ] Dependencies injected, not instantiated in functions
- [ ] Database migrations added (if schema changed)
- [ ] API route follows established patterns
- [ ] Pydantic schemas validate inputs

### Reviewer Checklist

- [ ] Architecture follows clean layers
- [ ] No circular dependencies
- [ ] Error handling appropriate and logged
- [ ] Performance considerations addressed
- [ ] Security implications reviewed
- [ ] Documentation updated
- [ ] Backwards compatibility maintained
- [ ] No TODO comments without JIRA tickets

---

## Quick Reference

### Code Quality Commands

```bash
# Format code
ruff format src/

# Lint code
ruff check src/

# Type check
mypy src/

# Run tests
pytest

# Test coverage
pytest --cov=src

# All checks (pre-commit)
ruff format src/ && isort src/ && ruff check src/ && mypy src/ && pytest
```

### File Templates

**Service Class**:
```python
class [Domain]Service:
    """Service for [domain] operations."""

    def __init__(self, repository: [Domain]Repository) -> None:
        self._repository = repository

    async def get_by_id(self, id: str) -> Optional[[Domain]]:
        """Get by ID."""
        pass
```

**Route Handler**:
```python
@router.post("/", response_model=[Domain]Response)
async def create(
    request: [Domain]Request,
    service: [Domain]Service = Depends(get_[domain]_service),
) -> [Domain]Response:
    """Create [domain]."""
    pass
```

**Test Case**:
```python
@pytest.mark.asyncio
async def test_[function]_[scenario](service, mock_repository):
    """Test [function] with [scenario]."""
    # Arrange
    # Act
    # Assert
    pass
```

---

## Continuous Improvement

These standards are living documents. Suggestions and improvements welcome. Update this guide when:
- New patterns emerge as codebase grows
- Team consensus on new conventions
- New tools or frameworks adopted
- Best practices evolve in the Python ecosystem
