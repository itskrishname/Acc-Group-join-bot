import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from src import config
from src.database import db

logger = logging.getLogger(__name__)

async def check_account_health(user_id: int, account: dict):
    """
    Connects to the account and messages @SpamBot to check if frozen/restricted.
    Returns the updated status.
    """
    api_creds = config.get_random_api()
    temp_client = Client(
        name=f"temp_health_{account['phone_number']}",
        api_id=api_creds["API_ID"],
        api_hash=api_creds["API_HASH"],
        session_string=account['session_string'],
        in_memory=True
    )

    try:
        await temp_client.connect()
        # Message SpamBot
        await temp_client.send_message("SpamBot", "/start")
        await asyncio.sleep(2)

        status = "Active"
        # Check last message from SpamBot
        async for msg in temp_client.get_chat_history("SpamBot", limit=1):
            if msg.text:
                if "Good news, no limits" in msg.text:
                    status = "Active"
                elif "limited" in msg.text.lower() or "restricted" in msg.text.lower():
                    status = "Restricted"
                elif "permanently" in msg.text.lower():
                    status = "Frozen"

        await temp_client.disconnect()
        return status
    except Exception as e:
        await temp_client.disconnect()
        if "AUTH_KEY_UNREGISTERED" in str(e) or "USER_DEACTIVATED" in str(e) or "SESSION_REVOKED" in str(e):
            return "Auth Failure"
        return "Unknown Error"

async def daily_report_task(bot: Client):
    """
    Background task that runs daily (handled via APScheduler in main).
    Checks all accounts for all users and sends them a report.
    """
    logger.info("Starting Daily Health Check Task...")
    users = await db.get_all_users()

    for user in users:
        user_id = user['user_id']
        accounts = await db.get_accounts(user_id)
        if not accounts:
            continue

        active_count = 0
        restricted_count = 0
        frozen_count = 0
        auth_fail_count = 0
        total_joins = 0

        for acc in accounts:
            total_joins += acc.get('joins', 0)

            # Check Health
            new_status = await check_account_health(user_id, acc)

            # Update DB if changed
            if new_status != acc['status'] and new_status != "Unknown Error":
                await db.update_account_status(user_id, acc['phone_number'], new_status)

                # Notify User of bad status
                if new_status in ["Restricted", "Frozen", "Auth Failure"]:
                    try:
                        alert_msg = (
                            f"⚠️ **Account Alert!**\n\n"
                            f"**Account:** `{acc['phone_number']}`\n"
                            f"**Category:** {acc['category']}\n"
                            f"**Reason:** Account {new_status.lower()} (confirmed via @SpamBot or API)\n\n"
                            f"This session may no longer work. Please check your Dashboard and remove it if necessary."
                        )
                        await bot.send_message(user_id, alert_msg)
                    except:
                        pass

            # Tally
            if new_status == "Active":
                active_count += 1
            elif new_status == "Restricted":
                restricted_count += 1
            elif new_status == "Frozen":
                frozen_count += 1
            elif new_status == "Auth Failure":
                auth_fail_count += 1

        # Send Daily Report to User
        report = (
            f"📊 **Daily Account Report** 📊\n\n"
            f"**Total Accounts:** {len(accounts)}\n"
            f"✅ **Active:** {active_count}\n"
            f"⚠️ **Restricted:** {restricted_count}\n"
            f"❄️ **Frozen:** {frozen_count}\n"
            f"❌ **Auth Failed:** {auth_fail_count}\n\n"
            f"📈 **Total Joins (All Time):** {total_joins}"
        )
        try:
            await bot.send_message(user_id, report)
        except Exception as e:
            logger.error(f"Could not send daily report to {user_id}: {e}")

@Client.on_callback_query(filters.regex(r"^daily_report$"))
async def generate_manual_report(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.answer("Generating Report... This may take a moment.", show_alert=True)

    accounts = await db.get_accounts(user_id)
    if not accounts:
        await callback_query.message.reply_text("No accounts found.")
        return

    active_count = 0
    restricted_count = 0
    frozen_count = 0
    auth_fail_count = 0
    total_joins = 0

    for acc in accounts:
        total_joins += acc.get('joins', 0)
        status = acc['status']
        if status == "Active":
            active_count += 1
        elif status == "Restricted":
            restricted_count += 1
        elif status == "Frozen":
            frozen_count += 1
        elif status == "Auth Failure":
            auth_fail_count += 1

    report = (
        f"📊 **On-Demand Report** 📊\n\n"
        f"**Total Accounts:** {len(accounts)}\n"
        f"✅ **Active:** {active_count}\n"
        f"⚠️ **Restricted:** {restricted_count}\n"
        f"❄️ **Frozen:** {frozen_count}\n"
        f"❌ **Auth Failed:** {auth_fail_count}\n\n"
        f"📈 **Total Joins (All Time):** {total_joins}\n\n"
        f"*(Note: Background checks run daily to update these statuses automatically)*"
    )

    await callback_query.message.reply_text(report)
