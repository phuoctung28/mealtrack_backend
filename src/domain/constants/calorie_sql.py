"""Static SQL fragment for the fiber-aware calorie formula.

Single source of truth for the SQL half of the calorie formula. Python half:
`src.domain.model.nutrition.macros.Macros.raw_total_calories`.

Literal-only guardrail: this fragment must remain a compile-time constant.
Never string-interpolate user input into this fragment or any query that
embeds it — only interpolate this constant itself into a parameterized
``sqlalchemy.text()`` query alongside bound (``:param``) values.
"""

CALORIE_FORMULA_SQL_FRAGMENT = (
    "(n.protein * 4.0)"
    " + (GREATEST(n.carbs - n.fiber, 0) * 4.0)"
    " + (n.fiber * 2.0)"
    " + (n.fat * 9.0)"
)
