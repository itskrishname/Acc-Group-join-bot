from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from src import config
from src.database import db

# Helper to check if a user is authorized (Owner or Admin)
async def is_authorized(user_id: int) -> bool:
    if user_id == config.OWNER_ID:
        return True
    user = await db.get_user(user_id)
    return bool(user)

def get_main_menu(user_id: int):
    # Depending on owner or user, we can add more buttons
    keyboard = [
        [InlineKeyboardButton("Dashboard & Categories", callback_data="dashboard_main")],
        [InlineKeyboardButton("Add Account", callback_data="add_account_main")],
        [InlineKeyboardButton("Bulk Join", callback_data="bulk_join_setup"),
         InlineKeyboardButton("Bot Start", callback_data="bot_start_setup")],
        [InlineKeyboardButton("Bulk Leave", callback_data="bulk_leave_setup"),
         InlineKeyboardButton("Daily Report", callback_data="daily_report")]
    ]
    if user_id == config.OWNER_ID:
        keyboard.append([InlineKeyboardButton("Admin Settings", callback_data="admin_settings")])
    return InlineKeyboardMarkup(keyboard)

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if not await is_authorized(user_id):
        await message.reply_text("You are not authorized to use this bot.")
        return

    # Ensure owner is always in DB for their own dashboard
    if user_id == config.OWNER_ID:
        await db.add_user(user_id)

    text = (
        "**Welcome to the Group Joiner Bot!**\n\n"
        "Manage your accounts securely, join groups/channels, and automate your tasks.\n"
        "Use the dashboard below to get started."
    )
    await message.reply_text(text, reply_markup=get_main_menu(user_id))

@Client.on_message(filters.command("addadmin") & filters.private & filters.user(config.OWNER_ID))
async def add_admin_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/addadmin <user_id>`")
        return

    try:
        new_admin_id = int(message.command[1])
        success = await db.add_user(new_admin_id)
        if success:
            await message.reply_text(f"User `{new_admin_id}` has been added as an admin.")
        else:
            await message.reply_text(f"User `{new_admin_id}` is already an admin.")
    except ValueError:
        await message.reply_text("Please provide a valid numeric User ID.")

@Client.on_message(filters.command("deladmin") & filters.private & filters.user(config.OWNER_ID))
async def del_admin_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/deladmin <user_id>`")
        return

    try:
        admin_id = int(message.command[1])
        if admin_id == config.OWNER_ID:
            await message.reply_text("You cannot remove the owner.")
            return

        success = await db.remove_user(admin_id)
        if success:
            await message.reply_text(f"User `{admin_id}` has been removed from admins.")
        else:
            await message.reply_text(f"User `{admin_id}` is not an admin.")
    except ValueError:
        await message.reply_text("Please provide a valid numeric User ID.")

@Client.on_message(filters.command("admins") & filters.private & filters.user(config.OWNER_ID))
async def list_admins_cmd(client: Client, message: Message):
    users = await db.get_all_users()
    if not users:
        await message.reply_text("No admins found.")
        return

    text = "**List of Admins:**\n"
    for user in users:
        uid = user['user_id']
        role = "Owner" if uid == config.OWNER_ID else "Admin"
        text += f"- `{uid}` ({role})\n"

    await message.reply_text(text)
