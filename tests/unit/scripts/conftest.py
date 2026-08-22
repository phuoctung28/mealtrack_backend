"""
Ensure the project root is in sys.path before pytest inserts tests/unit/,
so that 'scripts.*' resolves to the project's scripts/ package rather than
the tests/unit/scripts/ test package.
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_SCRIPTS_ROOT = os.path.join(_PROJECT_ROOT, "scripts")

# Insert project root at position 0 so 'scripts' resolves to the project's
# scripts/ package, not to tests/unit/scripts/ (which pytest adds to sys.path
# when it discovers __init__.py there).
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
else:
    # Move it to position 0 to take precedence over tests/unit/
    sys.path.remove(_PROJECT_ROOT)
    sys.path.insert(0, _PROJECT_ROOT)

# If pytest already cached the wrong 'scripts' package in sys.modules, clear it
# so Python re-resolves it from sys.path.
# Skip keys that are currently being loaded (conftest itself).
if "scripts" in sys.modules:
    cached = sys.modules["scripts"]
    cached_path = getattr(cached, "__file__", "") or ""
    if _SCRIPTS_ROOT not in cached_path:
        # Wrong 'scripts' package cached — remove sub-modules but keep 'scripts'
        # itself so the currently-loading conftest doesn't break.
        to_remove = [k for k in sys.modules if k.startswith("scripts.") and "conftest" not in k]
        for key in to_remove:
            del sys.modules[key]
