import asyncio
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, ReplyKeyboardRemove
from src import config
from src.database import db
from src.plugins.actions import select_accounts_flow

@Client.on_callback_query(filters.regex(r"^bulk_leave_setup$"))
async def bulk_leave_setup(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    # 1. Get Accounts
    accounts = await select_accounts_flow(client, chat_id, user_id)
    if not accounts:
        await client.send_message(chat_id, "No accounts found for your selection.", reply_markup=ReplyKeyboardRemove())
        return

    # 2. Get Target Link/Username
    link_msg = await client.ask(chat_id, "Send the target link/username of the Chat to Leave:", reply_markup=ReplyKeyboardRemove())
    target_link = link_msg.text.strip()

    # Use Saved Timer/Delay
    delay = await db.get_interval(user_id)

    # Start the process in background
    await client.send_message(chat_id, f"Started Bulk Leave on {len(accounts)} accounts with {delay}s delay...")
    asyncio.create_task(run_bulk_leave(client, chat_id, user_id, accounts, target_link, delay))


async def run_bulk_leave(client: Client, chat_id: int, user_id: int, accounts: list, link: str, delay: int):
    success = 0
    failed = 0

    # Extract username if link
    import re
    match = re.match(r"https?://t\.me/(.+)", link)
    if match:
        chat_identifier = match.group(1)
        if "+" in chat_identifier or "joinchat" in chat_identifier:
            chat_identifier = link # Private link
    else:
        chat_identifier = link.replace("@", "")

    for acc in accounts:
        if acc['status'] in ["Frozen", "Restricted", "Auth Failure"]:
            failed += 1
            continue

        temp_client = Client(
            name=f"temp_leave_{acc['phone_number']}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=acc['session_string'],
            in_memory=True
        )
        try:
            await temp_client.connect()

            # If it's a private invite link, we first need to get the chat object using get_chat
            if "http" in chat_identifier or "+" in chat_identifier:
                # Use get_chat to fetch the chat by invite link then leave it
                chat = await temp_client.get_chat(chat_identifier)
                await temp_client.leave_chat(chat.id)
            else:
                await temp_client.leave_chat(chat_identifier)

            success += 1
            await temp_client.disconnect()
        except Exception as e:
            await temp_client.disconnect()
            failed += 1

        await asyncio.sleep(delay)

    await client.send_message(chat_id, f"**Bulk Leave Complete!**\nSuccess: {success}\nFailed: {failed}")
