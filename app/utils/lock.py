import logging
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class DistributedLock:
    """
    Database-backed distributed lock for preventing duplicate scheduled job execution
    across multiple instances/workers.
    
    Usage:
        lock = DistributedLock(db, job_id="weekly_digest", ttl_seconds=3600)
        if await lock.acquire():
            try:
                # Run job logic
                await do_work()
            finally:
                await lock.release()
    """
    
    def __init__(self, db: AsyncSession, job_id: str, ttl_seconds: int = 3600):
        """
        Initialize a distributed lock.
        
        Args:
            db: AsyncSession database connection
            job_id: Unique identifier for the job (e.g., "weekly_digest", "cleanup_old_insights")
            ttl_seconds: Time-to-live for the lock in seconds. After expiration, other instances
                        can acquire it if the holder crashed/disappeared.
        """
        self.db = db
        self.job_id = job_id
        self.ttl_seconds = ttl_seconds
        self.holder_id = str(uuid.uuid4())  # Unique ID for this instance/process
        self._acquired = False
    
    async def acquire(self) -> bool:
        """
        Attempt to acquire the lock.
        
        Returns:
            True if lock acquired, False if another instance holds it.
        """
        # First, clean up expired locks
        await self._cleanup_expired()
        
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        
        try:
            # Try to insert a new lock
            from sqlalchemy import text
            query = text("""
                INSERT INTO scheduler_locks (job_id, holder_id, expires_at)
                VALUES (:job_id, :holder_id, :expires_at)
                ON CONFLICT (job_id) DO NOTHING
            """)
            result = await self.db.execute(
                query,
                {"job_id": self.job_id, "holder_id": self.holder_id, "expires_at": expires_at}
            )
            await self.db.commit()
            
            # If rowcount is 0, another instance holds the lock
            if result.rowcount == 0:
                logger.debug(f"Failed to acquire lock for {self.job_id} - another instance holds it")
                return False
            
            self._acquired = True
            logger.info(f"Acquired lock for {self.job_id} (holder: {self.holder_id})")
            return True
            
        except IntegrityError:
            # Another instance already has the lock
            await self.db.rollback()
            logger.debug(f"Failed to acquire lock for {self.job_id} - conflict")
            return False
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error acquiring lock for {self.job_id}: {e}")
            return False
    
    async def release(self) -> bool:
        """
        Release the lock if we hold it.
        
        Returns:
            True if lock was released, False if we didn't hold it.
        """
        if not self._acquired:
            return False
        
        try:
            from sqlalchemy import text
            query = text("""
                DELETE FROM scheduler_locks
                WHERE job_id = :job_id AND holder_id = :holder_id
            """)
            result = await self.db.execute(
                query,
                {"job_id": self.job_id, "holder_id": self.holder_id}
            )
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Released lock for {self.job_id}")
                self._acquired = False
                return True
            
            return False
            
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error releasing lock for {self.job_id}: {e}")
            return False
    
    async def _cleanup_expired(self) -> None:
        """Remove expired locks so crashed instances don't hold locks forever."""
        try:
            from sqlalchemy import text
            query = text("DELETE FROM scheduler_locks WHERE expires_at < now()")
            await self.db.execute(query)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error cleaning up expired locks: {e}")
    
    async def __aenter__(self):
        """Context manager entry - acquire lock."""
        if await self.acquire():
            return self
        raise RuntimeError(f"Failed to acquire lock for {self.job_id}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - release lock."""
        await self.release()
        return False
