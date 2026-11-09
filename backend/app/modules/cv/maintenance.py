import logging
from datetime import timedelta

from sqlalchemy import select

from app.core.db import Runtime
from app.core.errors import AppError
from app.modules.cv.models import CvStorageIntent
from app.modules.cv.service import CvService
from app.shared.clock import utcnow

logger = logging.getLogger("jobhunter.cv")


class CvMaintenance:
    """Recover one owner's old durable intents using the existing worker process."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    async def run_once(self) -> bool:
        async with self.runtime.sessions() as session:
            owner = await session.scalar(
                select(CvStorageIntent.user_id)
                .where(
                    CvStorageIntent.done.is_(False),
                    CvStorageIntent.created_at < utcnow() - timedelta(minutes=5),
                )
                .order_by(CvStorageIntent.created_at)
                .limit(1)
            )
        if owner is None:
            return False
        try:
            async with self.runtime.sessions() as session:
                return bool(await CvService(session, self.runtime.settings).recover(owner))
        except AppError:
            logger.warning("cv_storage_recovery_failed")
            return False
