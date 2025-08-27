#!/usr/bin/env python
"""
Railway deployment script - runs migrations then starts the app.
Following Railway best practices for production deployment.
"""
import os
import sys
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run database migrations with proper error handling."""
    try:
        logger.info("📦 Running database migrations...")
        result = subprocess.run(
            [sys.executable, "migrations/run.py"],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.stdout:
            logger.info(result.stdout)
        
        if result.returncode != 0:
            logger.warning(f"Migration exited with code {result.returncode}")
            if result.stderr:
                logger.error(result.stderr)
            # Continue anyway - Railway will restart if needed
            return False
        
        logger.info("✅ Migrations completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Migration timed out after 2 minutes")
        return False
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return False


def start_app():
    """Start the FastAPI application with production settings."""
    port = os.environ.get("PORT", "8000")
    workers = os.environ.get("WEB_CONCURRENCY", "1")
    
    # Production uvicorn configuration
    cmd = [
        "uvicorn",
        "src.api.main:app",
        "--host", "0.0.0.0",
        "--port", port,
        "--workers", workers,
        "--loop", "uvloop",
        "--access-log"
    ]
    
    logger.info(f"🚀 Starting app: {' '.join(cmd)}")
    
    # Replace current process with uvicorn
    os.execvp("uvicorn", cmd)


def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("🚂 Railway Deployment Starting")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'production')}")
    logger.info("=" * 50)
    
    # Run migrations (non-blocking on failure)
    run_migrations()
    
    # Start application
    start_app()


if __name__ == "__main__":
    main()