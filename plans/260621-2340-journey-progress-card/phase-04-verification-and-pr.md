---
phase: 4
title: Verification and PR
status: completed
priority: P1
effort: 3h
dependencies:
  - 1
  - 2
  - 3
---

# Phase 4: Verification and PR

## Overview

Verify backend and mobile changes, update docs where needed, commit each child repo, push, and create PRs.

## Requirements

- Functional: focused tests pass in both worktrees.
- Non-functional: generated code is current, no syntax/type errors, no secret leakage in staged diffs.

## Architecture

Backend and mobile are separate repos/worktrees on the same branch name. Each should get its own commit and PR. The dirty parent checkout remains untouched.

## Related Code Files

- Backend tests: focused pytest files added/changed in this plan.
- Mobile tests: progress provider test plus generated files.
- Docs: `docs/project-changelog.md` in each child repo if present and warranted.

## Implementation Steps

1. Run backend focused pytest for journey handler/onboarding.
2. Run backend compile/import checks if focused pytest does not cover route import.
3. Run mobile code generation.
4. Run focused Flutter tests for progress provider/card.
5. Run `flutter analyze` or a focused analyzer target if full analyze is too noisy.
6. Update plan status and docs/changelog when implementation is verified.
7. Stage, secret-scan, commit, push, and create PRs for backend and mobile.

## Success Criteria

- [ ] Backend focused tests pass.
- [ ] Mobile focused tests pass.
- [ ] Codegen outputs are committed.
- [ ] Two PR URLs are created or a blocker is reported with exact command output.

## Risk Assessment

Risk: full mobile analysis may expose unrelated existing issues. Mitigation: run focused tests and report any unrelated analyzer noise without hiding it.
