"""Audit and guarded food-reference integrity operations.

Audit is read-only. Quarantine and restore are dry-run unless ``--apply`` is
provided with an expected manifest digest and review reference.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.food_reference_integrity_repository import (
    FoodReferenceIntegrityRepository,
)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    async with AsyncUnitOfWork() as uow:
        repository: FoodReferenceIntegrityRepository = uow.food_reference_integrity
        if args.command == "audit":
            return await repository.audit_summary()

        if args.food_reference_id is None:
            raise ValueError("a food reference ID is required")
        if args.apply and not args.expected_digest:
            raise ValueError("--apply requires --expected-digest")
        if args.apply and not args.review_reference:
            raise ValueError("--apply requires --review-reference")

        action = "quarantine" if args.command == "quarantine" else "restore"
        preview = {
            "action": action,
            "food_reference_id": args.food_reference_id,
            "expected_digest": args.expected_digest,
            "review_reference": args.review_reference,
            "applied": False,
        }
        if not args.apply:
            return preview

        if action == "quarantine":
            state = await repository.quarantine_reference(
                args.food_reference_id,
                expected_input_digest=args.expected_digest,
                reason_code=args.reason,
                review_reference=args.review_reference,
                actor_kind="operator",
                deployed_revision=args.deployed_revision,
            )
        else:
            state = await repository.restore_reference(
                args.food_reference_id,
                expected_input_digest=args.expected_digest,
                review_reference=args.review_reference,
                actor_kind="operator",
                deployed_revision=args.deployed_revision,
            )
        preview.update(
            {
                "applied": True,
                "status": state.status,
                "policy_version": state.policy_version,
                "input_digest": state.input_digest,
            }
        )
        return preview


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit", help="read aggregate integrity state")
    for command in ("quarantine", "restore"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("food_reference_id", type=int)
        command_parser.add_argument("--expected-digest")
        command_parser.add_argument("--review-reference")
        command_parser.add_argument("--deployed-revision")
        command_parser.add_argument("--reason", default="manual_review")
        command_parser.add_argument(
            "--apply",
            action="store_true",
            help="commit the guarded CAS transition; default is dry-run",
        )
    return parser


def main() -> None:
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(_run(args)), sort_keys=True))


if __name__ == "__main__":
    main()
