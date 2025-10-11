"""
Background job scheduler configuration.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.jobs.weekly_weight_reminder_job import WeeklyWeightReminderJob

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Scheduler for notification-related background jobs"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    def initialize(self, get_session_func):
        """
        Initialize scheduler with jobs
        
        Args:
            get_session_func: Function that returns an AsyncSession
        """
        if self._is_running:
            logger.warning("Scheduler already initialized")
            return
        
        # Schedule weekly weight reminder job to run every 5 minutes
        # This catches all time windows (users can set reminders at any time)
        self.scheduler.add_job(
            func=self._run_weight_reminder_job,
            trigger=CronTrigger(minute='*/5'),  # Every 5 minutes
            id='weekly_weight_reminder',
            name='Send weekly weight reminders',
            replace_existing=True,
            kwargs={'get_session_func': get_session_func}
        )
        
        logger.info("Notification scheduler initialized with jobs")
    
    async def _run_weight_reminder_job(self, get_session_func):
        """
        Run weekly weight reminder job
        
        Args:
            get_session_func: Function that returns an AsyncSession
        """
        session = None
        try:
            logger.debug("Running weekly weight reminder job")
            
            # Get database session
            session = await get_session_func()
            
            # Create and run job
            job = WeeklyWeightReminderJob(session)
            await job.run()
            
        except Exception as e:
            logger.error(f"Error running weekly weight reminder job: {e}", exc_info=True)
        finally:
            if session:
                await session.close()
    
    def start(self):
        """Start the scheduler"""
        if self._is_running:
            logger.warning("Scheduler already running")
            return
        
        try:
            self.scheduler.start()
            self._is_running = True
            logger.info("Notification scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if not self._is_running:
            return
        
        try:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Notification scheduler shut down")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._is_running


# Global scheduler instance
notification_scheduler = NotificationScheduler()


def get_scheduler() -> NotificationScheduler:
    """Get global scheduler instance"""
    return notification_scheduler

