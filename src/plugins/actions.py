import asyncio
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyromod import listen
from src import config
from src.database import db

# Helper to get target accounts based on user choice
async def select_accounts_flow(client: Client, chat_id: int, user_id: int):
    # Ask if they want a specific category or ALL
    choice_msg = await client.ask(chat_id, "Type 'ALL' to use all accounts, or send the EXACT name of a Category:")
    choice = choice_msg.text.strip()

    if choice.upper() == 'ALL':
        accounts = await db.get_accounts(user_id)
    else:
        accounts = await db.get_accounts(user_id, category=choice)

    return accounts

# --- Bulk Join ---
@Client.on_callback_query(filters.regex(r"^bulk_join_setup$"))
async def bulk_join_setup(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    # 1. Get Accounts
    accounts = await select_accounts_flow(client, chat_id, user_id)
    if not accounts:
        await client.send_message(chat_id, "No accounts found for your selection.")
        return

    # 2. Get Target Link
    link_msg = await client.ask(chat_id, "Send the target link (Group/Channel/Folder):")
    target_link = link_msg.text.strip()

    # 3. Use Saved Timer/Delay
    delay = await db.get_interval(user_id)

    # Start the process in background
    await client.send_message(chat_id, f"Started Bulk Join on {len(accounts)} accounts with {delay}s delay...")
    asyncio.create_task(run_bulk_join(client, chat_id, user_id, accounts, target_link, delay))


async def run_bulk_join(client: Client, chat_id: int, user_id: int, accounts: list, link: str, delay: int):
    success = 0
    failed = 0
    for acc in accounts:
        if acc['status'] in ["Frozen", "Restricted", "Auth Failure"]:
            failed += 1
            continue

        temp_client = Client(
            name=f"temp_join_{acc['phone_number']}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=acc['session_string'],
            in_memory=True
        )
        try:
            await temp_client.connect()
            # Handle Folder join vs normal chat
            if "addlist/" in link or "folder/" in link:
                # To join a folder, we use CheckChatlistInvite to get chats, then JoinChatlistInvite to join
                from pyrogram.raw.functions.chatlists import CheckChatlistInvite, JoinChatlistInvite
                # Extract the slug from the link
                # e.g., https://t.me/addlist/slug_string or https://t.me/folder/slug_string
                import re
                match = re.search(r"(?:addlist|folder)/(.+)", link)
                if match:
                    slug = match.group(1)
                    # Check what chats are in the folder
                    invite_info = await temp_client.invoke(CheckChatlistInvite(slug=slug))

                    peers_to_join = []
                    # chatlistInviteAlready object (user already joined some)
                    if hasattr(invite_info, 'missing_peers'):
                        peers_to_join = invite_info.missing_peers
                    # chatlistInvite object (brand new folder for user)
                    elif hasattr(invite_info, 'peers'):
                        peers_to_join = invite_info.peers

                    if peers_to_join:
                        await temp_client.invoke(JoinChatlistInvite(slug=slug, peers=peers_to_join))
            else:
                await temp_client.join_chat(link)

            await db.increment_account_joins(user_id, acc['phone_number'])
            success += 1
            await temp_client.disconnect()
        except Exception as e:
            await temp_client.disconnect()
            failed += 1
            if "AUTH_KEY_UNREGISTERED" in str(e) or "USER_DEACTIVATED" in str(e):
                await db.update_account_status(user_id, acc['phone_number'], "Auth Failure")

        await asyncio.sleep(delay)

    await client.send_message(chat_id, f"**Bulk Join Complete!**\nSuccess: {success}\nFailed: {failed}")

# --- Bot Start ---
@Client.on_callback_query(filters.regex(r"^bot_start_setup$"))
async def bot_start_setup(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    # 1. Get Accounts
    accounts = await select_accounts_flow(client, chat_id, user_id)
    if not accounts:
        await client.send_message(chat_id, "No accounts found for your selection.")
        return

    # 2. Get Bot Link
    link_msg = await client.ask(chat_id, "Send the bot start link (e.g., https://t.me/BotUsername?start=123):")
    bot_link = link_msg.text.strip()

    # 3. Use Saved Timer/Delay
    delay = await db.get_interval(user_id)

    await client.send_message(chat_id, f"Starting Bots on {len(accounts)} accounts with {delay}s delay...")
    asyncio.create_task(run_bot_start(client, chat_id, user_id, accounts, bot_link, delay))

async def run_bot_start(client: Client, chat_id: int, user_id: int, accounts: list, link: str, delay: int):
    success = 0
    failed = 0

    # Parse link
    import re
    match = re.match(r"https?://t\.me/(.+)\?start=(.+)", link)
    if match:
        bot_username = match.group(1)
        payload = match.group(2)
    else:
        # Simple bot link without payload
        match2 = re.match(r"https?://t\.me/(.+)", link)
        if match2:
            bot_username = match2.group(1)
            payload = ""
        else:
            bot_username = link.replace("@", "")
            payload = ""

    for acc in accounts:
        if acc['status'] in ["Frozen", "Restricted", "Auth Failure"]:
            failed += 1
            continue

        temp_client = Client(
            name=f"temp_bot_{acc['phone_number']}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=acc['session_string'],
            in_memory=True
        )
        try:
            await temp_client.connect()
            if payload:
                sent_msg = await temp_client.send_message(bot_username, f"/start {payload}")
            else:
                sent_msg = await temp_client.send_message(bot_username, "/start")

            success += 1

            # --- Inline Force Sub Auto Join & Click ---
            # Wait for bot's reply
            await asyncio.sleep(3)

            async for message in temp_client.get_chat_history(bot_username, limit=3):
                if message.reply_markup and hasattr(message.reply_markup, 'inline_keyboard'):
                    for row in message.reply_markup.inline_keyboard:
                        for button in row:
                            # If it's a join link
                            if button.url and ('t.me/' in button.url or 'telegram.me/' in button.url):
                                try:
                                    await temp_client.join_chat(button.url)
                                    await asyncio.sleep(1) # Small delay between joins
                                except Exception as e:
                                    print(f"Failed to join force sub channel {button.url}: {e}")

                            # If it's a verify/joined button
                            elif button.callback_data:
                                try:
                                    # Click the button
                                    await temp_client.request_callback_answer(
                                        chat_id=message.chat.id,
                                        message_id=message.id,
                                        callback_data=button.callback_data
                                    )
                                except Exception as e:
                                    print(f"Failed to click verify button: {e}")

            await temp_client.disconnect()
        except Exception as e:
            await temp_client.disconnect()
            failed += 1

        await asyncio.sleep(delay)

    await client.send_message(chat_id, f"**Bot Start Complete!**\nSuccess: {success}\nFailed: {failed}")
