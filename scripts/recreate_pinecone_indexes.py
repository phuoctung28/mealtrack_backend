"""
Script to delete and recreate Pinecone indexes with updated dimensions.
Part of Phase 05: Pinecone Inference Migration.

Usage:
    python scripts/recreate_pinecone_indexes.py
"""
import os
import sys
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pinecone import Pinecone, ServerlessSpec

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Delete and recreate Pinecone indexes with 384 dimensions."""
    logger.info("=" * 60)
    logger.info("Pinecone Index Recreation Script")
    logger.info("=" * 60)
    logger.info("Phase 05: Pinecone Inference Migration")
    logger.info("Dimension: 1024 (llama-text-embed-v2 default)")
    logger.info("")

    # Initialize Pinecone
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        logger.error("PINECONE_API_KEY not found in environment")
        sys.exit(1)

    pc = Pinecone(api_key=api_key)

    # List existing indexes
    existing_indexes = [idx['name'] for idx in pc.list_indexes()]
    logger.info(f"Existing indexes: {existing_indexes}")
    logger.info("")

    # Indexes to recreate
    indexes_to_recreate = ["recipes", "ingredients", "usda"]
    dimension = 1024  # llama-text-embed-v2 default dimension
    metric = "cosine"
    cloud = "aws"
    region = "us-east-1"

    # Delete existing indexes
    for index_name in indexes_to_recreate:
        if index_name in existing_indexes:
            logger.info(f"Deleting '{index_name}' index...")
            try:
                pc.delete_index(index_name)
                logger.info(f"✅ Deleted '{index_name}' index")
            except Exception as e:
                logger.error(f"❌ Failed to delete '{index_name}': {e}")
                continue

            # Wait for deletion to complete
            time.sleep(5)
        else:
            logger.info(f"Index '{index_name}' not found, skipping deletion")

    logger.info("")
    logger.info("Waiting 10 seconds for deletions to complete...")
    time.sleep(10)
    logger.info("")

    # Create new indexes
    for index_name in indexes_to_recreate:
        logger.info(f"Creating '{index_name}' index with {dimension} dimensions...")
        try:
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=cloud, region=region)
            )
            logger.info(f"✅ Created '{index_name}' index")
        except Exception as e:
            logger.error(f"❌ Failed to create '{index_name}': {e}")
            continue

        # Wait for index to be ready
        logger.info(f"Waiting for '{index_name}' to be ready...")
        time.sleep(15)

        # Verify index
        try:
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            logger.info(f"Index '{index_name}' stats: {stats}")
        except Exception as e:
            logger.warning(f"⚠️  Could not verify '{index_name}': {e}")

        logger.info("")

    # Final verification
    logger.info("=" * 60)
    logger.info("Index Recreation Complete")
    logger.info("=" * 60)

    final_indexes = [idx['name'] for idx in pc.list_indexes()]
    logger.info(f"Current indexes: {final_indexes}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Run: python scripts/populate_recipe_index.py")
    logger.info("  2. Verify: Test search functionality")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
