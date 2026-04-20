import logging
from pyromod import listen
from pyrogram import Client, __version__
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src import config
from src.plugins.health import daily_report_task

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="group_joiner_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            plugins=dict(root="src/plugins"),
            in_memory=True
        )
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        await super().start()
        me = await self.get_me()
        logger.info(f"Bot started as {me.first_name} (@{me.username})")

        # Start background tasks
        self.scheduler.add_job(daily_report_task, "interval", days=1, args=[self])
        self.scheduler.start()
        logger.info("Scheduler started for daily reporting.")

    async def stop(self, *args):
        self.scheduler.shutdown()
        await super().stop()
        logger.info("Bot stopped.")
