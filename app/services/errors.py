import logging
import re
from pathlib import Path

from aiogram.exceptions import TelegramBadRequest, TelegramEntityTooLarge, TelegramForbiddenError
from aiogram.types import Message
from aiogram_i18n import I18nContext

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


class FileTooLargeError(DownloadError):
    def __init__(self, size_mb: float) -> None:
        self.size_mb = size_mb
        super().__init__(f"File too large: {size_mb} MB")


async def handle_errors(
    exc: Exception,
    source: Path,
    status_msg: Message,
    i18n: I18nContext,
) -> None:
    """Map Telegram exceptions to user-facing i18n messages."""
    exc_message = str(exc)

    if isinstance(exc, TelegramEntityTooLarge) or (
        isinstance(exc, TelegramBadRequest) and "file is too big" in exc_message.lower()
    ):
        size_mb = round(source.stat().st_size / (1024 * 1024), 1)
        logger.warning("File too large: %s", exc_message)
        await status_msg.edit_text(i18n.get("error-file-too-large", size=size_mb))

    elif (
        isinstance(exc, TelegramBadRequest)
        and "file of size" in exc_message.lower()
        and "too big for a video note" in exc_message.lower()
    ):
        logger.warning("Video note file too large: %s", exc_message)
        match = re.search(r"file of size (\d+)", exc_message.lower())
        if match:
            size_mb = round(int(match.group(1)) / (1024 * 1024), 1)
        else:
            size_mb = round(source.stat().st_size / (1024 * 1024), 1)
        await status_msg.edit_text(
            f"File too large - {size_mb} MB. Maximum is 12.5 MB for Telegram video notes."
        )

    elif isinstance(exc, TelegramForbiddenError) and "VOICE_MESSAGES_FORBIDDEN" in exc_message:
        await status_msg.edit_text(i18n.get("voice-disabled"))

    else:
        if not isinstance(exc, (TelegramBadRequest, TelegramForbiddenError)):
            logger.exception(
                "Unexpected error in pipeline: %s: %s",
                type(exc).__name__,
                exc_message,
            )
        else:
            logger.warning(
                "Telegram error in pipeline: %s: %s",
                type(exc).__name__,
                exc_message,
            )
        await status_msg.edit_text(i18n.get("error-processing"))
