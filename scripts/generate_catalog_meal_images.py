"""Generate Cloudflare image URLs for imported catalog meals."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import selectinload

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infra.adapters.cloudflare_workers_image_generator import (
    CloudflareWorkersImageGenerator,
)
from src.infra.database.models.meal_recommendation import MealCatalogORM
from src.infra.database.uow_async import AsyncUnitOfWork


def main() -> None:
    load_dotenv(".env")
    parser = argparse.ArgumentParser(
        description="Generate post-import meal_catalog.image_url values via Cloudflare."
    )
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--catalog-key", action="append", default=[])
    parser.add_argument("--include-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--model",
        default=os.getenv("CLOUDFLARE_WORKERS_AI_IMAGE_MODEL", "openai/gpt-image-2"),
    )
    parser.add_argument("--quality", default="medium")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--output-format", default="jpeg")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")

    summary = asyncio.run(_run(args))
    print(f"selected={summary['selected']}")
    print(f"updated={summary['updated']}")
    print(f"failed={summary['failed']}")
    if summary["failed"]:
        raise SystemExit(1)


async def _run(args) -> dict[str, int]:
    generator = None
    if not args.dry_run:
        generator = CloudflareWorkersImageGenerator(
            account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
            api_token=os.getenv("CLOUDFLARE_API_TOKEN", ""),
            model=args.model,
            timeout=args.timeout,
        )
    selected = updated = failed = 0
    async with AsyncUnitOfWork() as uow:
        if uow.session is None:
            raise RuntimeError("AsyncUnitOfWork did not initialize a database session")
        meals = await _load_target_meals(
            uow.session,
            limit=args.limit,
            catalog_keys=tuple(args.catalog_key),
            include_existing=args.include_existing,
        )
        selected = len(meals)
        for meal in meals:
            prompt = build_catalog_meal_image_prompt(meal)
            print(f"meal={meal.catalog_key} name={meal.name}")
            print(f"prompt={prompt}")
            if args.dry_run:
                continue
            try:
                if generator is None:
                    raise RuntimeError("Cloudflare image generator is not initialized")
                image_url = await generator.generate_url(
                    prompt,
                    quality=args.quality,
                    size=args.size,
                    output_format=args.output_format,
                )
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(
                    f"image_generation_failed catalog_key={meal.catalog_key}: {exc}",
                    file=sys.stderr,
                )
                continue
            meal.image_url = image_url
            await uow.session.flush()
            await uow.commit()
            updated += 1
            print(f"image_url={image_url}")
    return {"selected": selected, "updated": updated, "failed": failed}


async def _load_target_meals(
    session,
    *,
    limit: int,
    catalog_keys: tuple[str, ...],
    include_existing: bool,
) -> list[MealCatalogORM]:
    stmt = (
        select(MealCatalogORM)
        .where(MealCatalogORM.is_active.is_(True))
        .options(selectinload(MealCatalogORM.ingredients))
        .order_by(MealCatalogORM.name)
        .limit(limit)
    )
    if catalog_keys:
        stmt = stmt.where(MealCatalogORM.catalog_key.in_(catalog_keys))
    if not include_existing:
        stmt = stmt.where(MealCatalogORM.image_url.is_(None))
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


def build_catalog_meal_image_prompt(meal: MealCatalogORM) -> str:
    ingredients = ", ".join(
        str(item.display_name)
        for item in sorted(
            meal.ingredients,
            key=lambda ingredient: str(ingredient.display_name).lower(),
        )[:8]
    )
    cuisine = str(meal.cuisine).strip()
    name = str(meal.name).strip()
    ingredient_sentence = f" Visible ingredients: {ingredients}." if ingredients else ""
    return (
        f"Photorealistic editorial food photo of {name}, a {cuisine} meal."
        f"{ingredient_sentence} Single plated serving, natural daylight, clean table, "
        "appetizing realistic texture, no people, no packaging, no text, no logo, no watermark."
    )


if __name__ == "__main__":
    main()
