from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyromod import listen
from src.database import db

@Client.on_callback_query(filters.regex(r"^dashboard_main$"))
async def dashboard_main_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    text = "**Dashboard**\nManage your Categories and Accounts here."

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Categories", callback_data="manage_categories"),
         InlineKeyboardButton("Accounts", callback_data="manage_accounts")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="back_to_start")]
    ])
    await callback_query.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^back_to_start$"))
async def back_to_start_cb(client: Client, callback_query: CallbackQuery):
    from src.plugins.admin import get_main_menu
    from src import config
    user_id = callback_query.from_user.id
    text = (
        "**Welcome to the Group Joiner Bot!**\n\n"
        "Manage your accounts securely, join groups/channels, and automate your tasks.\n"
        "Use the dashboard below to get started.\n\n"
    )

    if user_id == config.OWNER_ID:
        text += (
            "**Owner Commands:**\n"
            "`/addadmin <user_id>` - Add an admin\n"
            "`/deladmin <user_id>` - Remove an admin\n"
            "`/admins` - List all admins\n"
            "`/update` - Update the bot code from git\n"
        )

    await callback_query.message.edit_text(text, reply_markup=get_main_menu(user_id))

# --- Categories ---
@Client.on_callback_query(filters.regex(r"^manage_categories$"))
async def manage_categories_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    categories = await db.get_categories(user_id)

    text = "**Your Categories:**\n\n"
    if not categories:
        text += "No categories found."
    else:
        for i, cat in enumerate(categories, 1):
            text += f"{i}. {cat}\n"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Create Category", callback_data="create_category"),
         InlineKeyboardButton("Delete Category", callback_data="delete_category")],
        [InlineKeyboardButton("Back", callback_data="dashboard_main")]
    ])
    await callback_query.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^create_category$"))
async def create_category_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()
    cat_msg = await client.ask(chat_id, "Send the name for the new Category:")
    cat_name = cat_msg.text.strip()

    success = await db.add_category(user_id, cat_name)
    if success:
        await client.send_message(chat_id, f"Category **{cat_name}** created successfully!")
    else:
        await client.send_message(chat_id, "Category already exists.")

@Client.on_callback_query(filters.regex(r"^delete_category$"))
async def delete_category_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    categories = await db.get_categories(user_id)
    if not categories:
        await callback_query.answer("No categories to delete.", show_alert=True)
        return

    await callback_query.message.delete()

    cat_text = "Select a Category to delete (This will ALSO delete all accounts in it!):\n\n"
    for i, cat in enumerate(categories, 1):
        cat_text += f"{i}. {cat}\n"

    cat_msg = await client.ask(chat_id, cat_text + "\nSend the exact name of the category to delete:")
    cat_name = cat_msg.text.strip()

    success = await db.remove_category(user_id, cat_name)
    if success:
        await client.send_message(chat_id, f"Category **{cat_name}** and its accounts deleted.")
    else:
        await client.send_message(chat_id, "Category not found or deletion failed.")

@Client.on_callback_query(filters.regex(r"^set_time_interval$"))
async def set_time_interval_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    current_interval = await db.get_interval(user_id)
    msg = await client.ask(chat_id, f"Current Time Interval is **{current_interval} seconds**.\n\nSend the new interval in seconds (e.g., 5, 10, 15):")

    try:
        new_interval = int(msg.text.strip())
        if new_interval < 0:
            raise ValueError
        await db.set_interval(user_id, new_interval)
        await client.send_message(chat_id, f"✅ Time interval updated to **{new_interval} seconds**.")
    except ValueError:
        await client.send_message(chat_id, "❌ Invalid number. Interval not changed.")

# --- Accounts ---
@Client.on_callback_query(filters.regex(r"^manage_accounts$"))
async def manage_accounts_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    accounts = await db.get_accounts(user_id)

    text = f"**Your Accounts (Total: {len(accounts)})**\n\n"
    if not accounts:
        text += "No accounts found."
    else:
        for acc in accounts:
            text += f"📱 `{acc['phone_number']}` | Cat: {acc['category']} | Status: {acc['status']}\n"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Remove Account", callback_data="remove_account")],
        [InlineKeyboardButton("Back", callback_data="dashboard_main")]
    ])
    await callback_query.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^remove_account$"))
async def remove_account_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    await callback_query.message.delete()

    acc_msg = await client.ask(chat_id, "Send the exact phone number of the account to remove (e.g., +1234567890):")
    phone = acc_msg.text.strip()

    success = await db.remove_account(user_id, phone)
    if success:
        await client.send_message(chat_id, f"Account {phone} removed successfully.")
    else:
        await client.send_message(chat_id, f"Account {phone} not found.")
