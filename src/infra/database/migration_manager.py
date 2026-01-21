"""
Database migration manager for automatic schema and migration management.

This module handles automatic database initialization and migration execution
during application startup, ensuring the database is always up-to-date.
"""
import logging
import os
import time
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, DatabaseError

from src.infra.database.config import engine, Base

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations and schema initialization."""
    
    def __init__(
        self,
        engine: Engine,
        alembic_config_path: str = "alembic.ini",
        auto_migrate: bool = True,
        migration_timeout: int = 60,
        retry_attempts: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Initialize the migration manager.
        
        Args:
            engine: SQLAlchemy database engine
            alembic_config_path: Path to alembic configuration file
            auto_migrate: Whether to automatically run migrations
            migration_timeout: Maximum time to wait for migrations (seconds)
            retry_attempts: Number of retry attempts for database operations
            retry_delay: Initial delay between retries (seconds)
        """
        self.engine = engine
        self.alembic_config_path = alembic_config_path
        self.auto_migrate = auto_migrate
        self.migration_timeout = migration_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self._lock_acquired = False
        
    def _get_alembic_config(self) -> Config:
        """Get Alembic configuration."""
        if not os.path.exists(self.alembic_config_path):
            raise FileNotFoundError(f"Alembic config not found: {self.alembic_config_path}")
        
        config = Config(self.alembic_config_path)
        # Override database URL from engine
        config.set_main_option("sqlalchemy.url", str(self.engine.url))
        return config
    
    def _check_database_connection(self) -> bool:
        """
        Check if database connection is available.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except (OperationalError, DatabaseError) as e:
            logger.warning(f"Database connection check failed: {e}")
            return False
    
    def _wait_for_database(self) -> bool:
        """
        Wait for database to become available with retries.
        
        Returns:
            bool: True if database available, False if timeout
        """
        start_time = time.time()
        attempt = 0
        delay = self.retry_delay
        
        while attempt < self.retry_attempts:
            if self._check_database_connection():
                logger.info("✅ Database connection established")
                return True
            
            if time.time() - start_time > self.migration_timeout:
                logger.error("Database connection timeout exceeded")
                return False
            
            attempt += 1
            logger.info(f"Waiting for database... (attempt {attempt}/{self.retry_attempts})")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
            
        return False
    
    def _acquire_migration_lock(self) -> bool:
        """
        Acquire a migration lock to prevent concurrent migrations.
        Uses MySQL GET_LOCK or PostgreSQL advisory locks.
        
        Returns:
            bool: True if lock acquired, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                dialect_name = self.engine.dialect.name
                
                if dialect_name == 'mysql':
                    # MySQL: GET_LOCK returns 1 if lock acquired, 0 if timeout
                    # Increased timeout to 60s to handle longer migrations
                    result = conn.execute(
                        text("SELECT GET_LOCK('alembic_migration_lock', 60)")
                    ).scalar()
                    self._lock_acquired = result == 1
                    return self._lock_acquired
                    
                elif dialect_name == 'postgresql':
                    # PostgreSQL: advisory lock
                    conn.execute(text("SELECT pg_advisory_lock(12345)"))
                    self._lock_acquired = True
                    return True
                    
                else:
                    # For other databases, proceed without locking
                    logger.warning(f"Migration locking not implemented for {dialect_name}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to acquire migration lock: {e}")
            return False
    
    def _release_migration_lock(self):
        """Release the migration lock if acquired."""
        if not self._lock_acquired:
            return
            
        try:
            with self.engine.connect() as conn:
                dialect_name = self.engine.dialect.name
                
                if dialect_name == 'mysql':
                    conn.execute(text("SELECT RELEASE_LOCK('alembic_migration_lock')"))
                elif dialect_name == 'postgresql':
                    conn.execute(text("SELECT pg_advisory_unlock(12345)"))
                    
                self._lock_acquired = False
                logger.debug("Migration lock released")
                
        except Exception as e:
            logger.error(f"Failed to release migration lock: {e}")
    
    def _get_current_revision(self) -> Optional[str]:
        """
        Get the current database revision.
        
        Returns:
            Optional[str]: Current revision or None if not initialized
        """
        try:
            with self.engine.connect() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()
        except Exception as e:
            logger.debug(f"Could not get current revision: {e}")
            return None
    
    def _is_database_initialized(self) -> bool:
        """
        Check if database has been initialized with tables.
        
        Returns:
            bool: True if database has tables, False otherwise
        """
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        # Check for any application tables (not just alembic_version)
        app_tables = [t for t in tables if t != 'alembic_version']
        return len(app_tables) > 0
    
    def _create_initial_schema(self):
        """Create initial database schema from SQLAlchemy models."""
        logger.info("Creating initial database schema...")
        try:
            # Import all models to ensure they're registered
            from src.infra.database import models  # noqa: F401
            
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Initial schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create initial schema: {e}")
            raise
    
    def _stamp_baseline(self, revision: str = "001"):
        """
        Stamp the database with a baseline revision without running migrations.
        
        Args:
            revision: The revision to stamp (default: "001")
        """
        logger.info(f"Stamping database with baseline revision: {revision}")
        try:
            config = self._get_alembic_config()
            command.stamp(config, revision)
            logger.info(f"✅ Database stamped with revision: {revision}")
        except Exception as e:
            logger.error(f"Failed to stamp baseline: {e}")
            raise
    
    def _stamp_latest(self):
        """Stamp the database with the latest revision."""
        logger.info("Stamping database with latest revision")
        try:
            config = self._get_alembic_config()
            script_dir = ScriptDirectory.from_config(config)
            
            # Get all heads (in case of branching)
            heads = script_dir.get_heads()
            logger.info(f"Available heads: {heads}")
            
            # For now, use the first head or a specific revision
            # In a production environment, you'd want to merge the branches
            if heads:
                target_revision = heads[0]  # Use first head
                logger.info(f"Using revision: {target_revision}")
                
                # Add timeout and more detailed logging
                import signal
                import time
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Stamping operation timed out")
                
                # Set a 30-second timeout for the stamping operation
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)
                
                try:
                    logger.info(f"Starting stamp operation for revision: {target_revision}")
                    
                    # First, manually create the alembic_version table if it doesn't exist
                    with self.engine.connect() as conn:
                        # Check if alembic_version table exists
                        result = conn.execute(text("SHOW TABLES LIKE 'alembic_version'"))
                        if not result.fetchone():
                            logger.info("Creating alembic_version table manually...")
                            conn.execute(text("""
                                CREATE TABLE alembic_version (
                                    version_num VARCHAR(32) NOT NULL,
                                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                                ) ENGINE=InnoDB
                            """))
                            conn.commit()
                            logger.info("✅ alembic_version table created")
                    
                    # Now try the stamp operation
                    command.stamp(config, target_revision)
                    signal.alarm(0)  # Cancel the alarm
                    logger.info("✅ Database stamped with latest revision")
                except TimeoutError:
                    signal.alarm(0)  # Cancel the alarm
                    logger.error("❌ Stamping operation timed out after 30 seconds")
                    raise Exception("Stamping operation timed out")
                    
            else:
                logger.warning("No heads found, using baseline revision")
                command.stamp(config, "001")
                
        except Exception as e:
            logger.error(f"Failed to stamp latest: {e}")
            raise
    
    def _run_migrations(self):
        """Run pending migrations to latest revision."""
        logger.info("Running database migrations...")
        try:
            config = self._get_alembic_config()
            command.upgrade(config, "head")
            logger.info("✅ Migrations completed successfully")
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise
    
    def _get_pending_migrations(self) -> list:
        """
        Get list of pending migrations.
        
        Returns:
            list: List of pending migration revisions
        """
        try:
            config = self._get_alembic_config()
            script_dir = ScriptDirectory.from_config(config)
            
            with self.engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
                
            if current_rev is None:
                # All migrations are pending
                return [s.revision for s in script_dir.walk_revisions()]
            
            # Get revisions between current and head
            pending = []
            for rev in script_dir.walk_revisions():
                if rev.revision == current_rev:
                    break
                pending.append(rev.revision)
            
            return pending[::-1]  # Reverse to get chronological order
            
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    def initialize_and_migrate(self) -> bool:
        """
        Main method to initialize database and run migrations.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.auto_migrate:
            logger.info("Auto-migration disabled, skipping...")
            return True
        
        logger.info("🚀 Starting database initialization and migration...")
        
        # Wait for database to be available
        if not self._wait_for_database():
            logger.error("❌ Database not available, cannot proceed with migrations")
            return False
        
        # Acquire migration lock
        if not self._acquire_migration_lock():
            logger.warning("Could not acquire migration lock, another instance may be migrating")
            return False
        
        try:
            # Check current state
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            current_revision = self._get_current_revision()
            
            logger.info(f"Current database state: {len(tables)} tables, revision: {current_revision}")
            
            # Determine what to do
            if 'alembic_version' not in tables:
                # First time setup
                logger.info("First time deployment detected")
                
                if not self._is_database_initialized():
                    # Empty database - create schema
                    self._create_initial_schema()
                    
                # Stamp as latest revision since we created from current models
                self._stamp_latest()
                
            # Check for pending migrations
            pending = self._get_pending_migrations()
            if pending:
                logger.info(f"Found {len(pending)} pending migrations: {pending}")
                self._run_migrations()
            else:
                logger.info("✅ Database is up to date")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
            
        finally:
            self._release_migration_lock()
    
    @classmethod
    def from_environment(cls, engine: Engine) -> 'MigrationManager':
        """
        Create MigrationManager from environment variables.
        
        Args:
            engine: SQLAlchemy database engine
            
        Returns:
            MigrationManager: Configured instance
        """
        auto_migrate = os.getenv('AUTO_MIGRATE', 'true').lower() == 'true'
        migration_timeout = int(os.getenv('MIGRATION_TIMEOUT', '60'))
        retry_attempts = int(os.getenv('MIGRATION_RETRY_ATTEMPTS', '3'))
        retry_delay = float(os.getenv('MIGRATION_RETRY_DELAY', '2.0'))
        
        return cls(
            engine=engine,
            auto_migrate=auto_migrate,
            migration_timeout=migration_timeout,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay
        )


# Convenience function for backwards compatibility
def run_migrations() -> bool:
    """
    Run database migrations using default configuration.
    
    Returns:
        bool: True if successful, False otherwise
    """
    manager = MigrationManager.from_environment(engine)
    return manager.initialize_and_migrate()
