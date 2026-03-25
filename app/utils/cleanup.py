import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_insight import AIInsight

logger = logging.getLogger(__name__)

INSIGHTS_RETENTION_DAYS = 90

async def cleanup_old_insights(db: AsyncSession) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=INSIGHTS_RETENTION_DAYS)
    result = await db.execute(
        delete(AIInsight)
        .where(AIInsight.created_at < cutoff)
        .returning(AIInsight.id)
    )
    deleted_count = len(result.fetchall())
    await db.commit()
    logger.info(f"Cleaned up {deleted_count} insights older than {INSIGHTS_RETENTION_DAYS} days")