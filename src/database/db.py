from motor.motor_asyncio import AsyncIOMotorClient
from src import config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = AsyncIOMotorClient(config.DATABASE_URI)
            self.db = self.client[config.DATABASE_NAME]

            # Collections
            self.users = self.db.users
            self.categories = self.db.categories
            self.accounts = self.db.accounts

            logger.info("Database connection established.")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")

    # --- Admins / Users ---
    async def get_user(self, user_id: int):
        return await self.users.find_one({"user_id": user_id})

    async def add_user(self, user_id: int):
        if not await self.get_user(user_id):
            await self.users.insert_one({"user_id": user_id, "interval": 10}) # default interval is 10s
            return True
        return False

    async def set_interval(self, user_id: int, interval: int):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"interval": interval}},
            upsert=True
        )

    async def get_interval(self, user_id: int) -> int:
        user = await self.get_user(user_id)
        if user and "interval" in user:
            return user["interval"]
        return 10

    async def remove_user(self, user_id: int):
        if await self.get_user(user_id):
            await self.users.delete_one({"user_id": user_id})
            # Optionally delete categories and accounts for this user?
            # Keeping it simple for now, user can be re-added and access restored.
            return True
        return False

    async def get_all_users(self):
        cursor = self.users.find({})
        return [doc async for doc in cursor]

    # --- Categories ---
    async def add_category(self, user_id: int, category_name: str):
        exists = await self.categories.find_one({"user_id": user_id, "name": category_name})
        if not exists:
            await self.categories.insert_one({"user_id": user_id, "name": category_name})
            return True
        return False

    async def remove_category(self, user_id: int, category_name: str):
        # Delete category
        res = await self.categories.delete_one({"user_id": user_id, "name": category_name})
        if res.deleted_count > 0:
            # Also remove accounts under this category
            await self.accounts.delete_many({"user_id": user_id, "category": category_name})
            return True
        return False

    async def get_categories(self, user_id: int):
        cursor = self.categories.find({"user_id": user_id})
        return [doc["name"] async for doc in cursor]

    # --- Accounts ---
    async def add_account(self, user_id: int, session_string: str, phone_number: str, category: str):
        account = {
            "user_id": user_id,
            "session_string": session_string,
            "phone_number": phone_number,
            "category": category,
            "status": "Active", # Active, Frozen, Restricted, Auth Failure
            "joins": 0
        }
        await self.accounts.update_one(
            {"user_id": user_id, "phone_number": phone_number},
            {"$set": account},
            upsert=True
        )

    async def remove_account(self, user_id: int, phone_number: str):
        res = await self.accounts.delete_one({"user_id": user_id, "phone_number": phone_number})
        return res.deleted_count > 0

    async def get_accounts(self, user_id: int, category: str = None):
        query = {"user_id": user_id}
        if category:
            query["category"] = category
        cursor = self.accounts.find(query)
        return [doc async for doc in cursor]

    async def update_account_status(self, user_id: int, phone_number: str, status: str):
        await self.accounts.update_one(
            {"user_id": user_id, "phone_number": phone_number},
            {"$set": {"status": status}}
        )

    async def increment_account_joins(self, user_id: int, phone_number: str, count: int = 1):
        await self.accounts.update_one(
            {"user_id": user_id, "phone_number": phone_number},
            {"$inc": {"joins": count}}
        )

db = Database()
