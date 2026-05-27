import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

from .channel import ChannelBase, IncomingMessage, OutgoingMessage
from .router import MessageRouter

logger = logging.getLogger("gateway.telegram")


class TelegramChannel(ChannelBase):
    name = "telegram"

    def __init__(self, token: str, router: MessageRouter):
        self.token = token
        self.router = router
        self._app: Application = None

    async def start(self):
        self._app = Application.builder().token(self.token).build()
        self._app.add_handler(CommandHandler("start", self._handle_update))
        self._app.add_handler(CommandHandler("help", self._handle_update))
        self._app.add_handler(CommandHandler("models", self._handle_update))
        self._app.add_handler(CommandHandler("memory", self._handle_update))
        self._app.add_handler(CommandHandler("analyze", self._handle_update))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_update))
        logger.info("Telegram channel started")
        await self._app.initialize()
        await self._app.start()

    async def stop(self):
        if self._app:
            await self._app.stop()
            await self._app.shutdown()
        logger.info("Telegram channel stopped")

    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        user_id = str(update.message.from_user.id) if update.message.from_user else "unknown"
        incoming = IncomingMessage(
            channel="telegram",
            channel_user_id=user_id,
            text=update.message.text,
        )
        reply = await self.router.route(incoming)
        if reply:
            await self.send_message(reply)

    async def send_message(self, message: OutgoingMessage):
        if not self._app:
            return
        try:
            chat_id = int(message.channel_user_id)
        except ValueError:
            return
        await self._app.bot.send_message(chat_id=chat_id, text=message.text)
