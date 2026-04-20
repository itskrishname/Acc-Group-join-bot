from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyromod import listen
from src import config
from src.database import db
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired

async def request_category(client: Client, message: Message, user_id: int):
    categories = await db.get_categories(user_id)
    if not categories:
        await message.reply_text("You don't have any categories. Please create one from the dashboard first.")
        return None

    cat_text = "Select a Category for this account:\n\n"
    for i, cat in enumerate(categories, 1):
        cat_text += f"{i}. {cat}\n"

    cat_msg = await client.ask(message.chat.id, cat_text + "\nSend the EXACT category name from the list above:")
    if cat_msg.text not in categories:
        await message.reply_text("Invalid category selected. Process cancelled.")
        return None
    return cat_msg.text

@Client.on_callback_query(filters.regex(r"^add_account_main$"))
async def add_account_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    # Check if user has categories
    categories = await db.get_categories(user_id)
    if not categories:
        await callback_query.answer("Create a category first!", show_alert=True)
        return

    text = (
        "**Add Account Options**\n\n"
        "How would you like to add an account?"
    )
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Login via Phone Number", callback_data="login_phone")],
        [InlineKeyboardButton("Upload String Session (.txt/.session)", callback_data="login_file")],
        [InlineKeyboardButton("Send String Session Directly", callback_data="login_string")],
        [InlineKeyboardButton("Back", callback_data="dashboard_main")]
    ])
    await callback_query.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^login_phone$"))
async def login_via_phone(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    cat = await request_category(client, callback_query.message, user_id)
    if not cat: return

    phone_msg = await client.ask(chat_id, "Send the phone number with country code (e.g., +1234567890):")
    phone_number = phone_msg.text.strip()

    temp_client = Client(
        name=f"temp_{user_id}",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        in_memory=True
    )

    await temp_client.connect()
    try:
        code_info = await temp_client.send_code(phone_number)
    except Exception as e:
        await client.send_message(chat_id, f"Error sending code: {e}")
        await temp_client.disconnect()
        return

    code_msg = await client.ask(chat_id, "Enter the OTP code received (include spaces/dashes if you want, but numbers only):")
    code = code_msg.text.replace(" ", "").replace("-", "")

    try:
        await temp_client.sign_in(phone_number, code_info.phone_code_hash, code)
    except SessionPasswordNeeded:
        pwd_msg = await client.ask(chat_id, "Two-Step Verification enabled. Send the password:")
        try:
            await temp_client.check_password(pwd_msg.text)
        except Exception as e:
            await client.send_message(chat_id, f"Invalid password. Error: {e}")
            await temp_client.disconnect()
            return
    except (PhoneCodeInvalid, PhoneCodeExpired) as e:
        await client.send_message(chat_id, f"Invalid or expired code. Error: {e}")
        await temp_client.disconnect()
        return
    except Exception as e:
        await client.send_message(chat_id, f"Login failed. Error: {e}")
        await temp_client.disconnect()
        return

    session_string = await temp_client.export_session_string()
    await temp_client.disconnect()

    await db.add_account(user_id, session_string, phone_number, cat)
    await client.send_message(chat_id, f"Successfully logged in and saved to category **{cat}**!")


@Client.on_callback_query(filters.regex(r"^login_string$"))
async def login_via_string(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    cat = await request_category(client, callback_query.message, user_id)
    if not cat: return

    string_msg = await client.ask(chat_id, "Send the Pyrogram String Session:")
    session_string = string_msg.text.strip()

    # Try to login to get phone number
    temp_client = Client(
        name=f"temp_{user_id}",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=session_string,
        in_memory=True
    )

    try:
        await temp_client.connect()
        me = await temp_client.get_me()
        phone_number = f"+{me.phone_number}" if me.phone_number else str(me.id)
        await temp_client.disconnect()

        await db.add_account(user_id, session_string, phone_number, cat)
        await client.send_message(chat_id, f"Account {phone_number} successfully added to category **{cat}**!")
    except Exception as e:
        await client.send_message(chat_id, f"Failed to connect using this string session. Error: {e}")

@Client.on_callback_query(filters.regex(r"^login_file$"))
async def login_via_file(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    cat = await request_category(client, callback_query.message, user_id)
    if not cat: return

    file_msg = await client.ask(chat_id, "Send the .txt file containing the String Session:")
    if not file_msg.document:
        await client.send_message(chat_id, "No document found. Process cancelled.")
        return

    file_path = await file_msg.download()
    with open(file_path, "r") as f:
        session_string = f.read().strip()

    import os
    os.remove(file_path)

    temp_client = Client(
        name=f"temp_{user_id}",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=session_string,
        in_memory=True
    )

    try:
        await temp_client.connect()
        me = await temp_client.get_me()
        phone_number = f"+{me.phone_number}" if me.phone_number else str(me.id)
        await temp_client.disconnect()

        await db.add_account(user_id, session_string, phone_number, cat)
        await client.send_message(chat_id, f"Account {phone_number} successfully added to category **{cat}** from file!")
    except Exception as e:
        await client.send_message(chat_id, f"Failed to connect using the session from file. Error: {e}")
