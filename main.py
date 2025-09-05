from datetime import datetime, timedelta
import os
import connection
import discord
from dotenv import load_dotenv


now = datetime.now()
start_of_day = datetime(now.year, now.month, now.day)
end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
journals = {}

load_dotenv()

db = connection.get_connection()
users = db.get_collection("users")
journals_collections = db.get_collection("journals")

current_journal_entries = {}
user_channel_map = {}


# TODO : write a cron to set all users daily:False and reminder:False at midnight
class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_message(self, message):
        print(f"current_journal_entries: {current_journal_entries}")
        userId = message.author.id
        if message.author == self.user:
            return
        if message.content.startswith("vivi add me"):
            if users.find_one({"user_id": message.author.id}) is not None:
                await message.channel.send("You are already in the list of users")
                return
            await message.channel.send("Added you to the list of users")
            users.insert_one(
                {
                    "user_id": message.author.id,
                    "reminder": False,
                    "daily": False,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                }
            )
            print(f"Added {message.author.id} to the list of users")
            return
        if message.content.startswith("vivi journal end"):
            await message.channel.send("perhaps you meant to use vivi end journal")
            return
        if message.content.startswith("vivi journal start"):
            await message.channel.send("perhaps you meant to use vivi start journal")
            return
        if message.content.startswith("vivi start journal"):
            user = users.find_one({"user_id": message.author.id})
            if user is None:
                await message.channel.send("You are not in the list of users")
                await message.channel.send(
                    "Please use the command vivi add me to add yourself to the list of users"
                )
                return
            if message.author.id in current_journal_entries:
                await message.channel.send("finish your previous journal first")
                await message.channel.send(
                    "not a good idea to start a new journal before finishing the previous one"
                )
                return
            if message.author.id not in current_journal_entries:
                current_j = journals_collections.insert_one(
                    {
                        "user_id": message.author.id,
                        "channel_id": message.channel.id,
                        "status": "active",
                        "data": [],
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    }
                )
                current_journal_entries[message.author.id] = current_j.inserted_id
                user_channel_map[message.author.id] = message.channel.id
                await message.channel.send("Journal started")
                print(f"Journal started for {message.author.id}")
            return
        if message.content.startswith("vivi end journal"):
            if userId not in current_journal_entries:
                await message.channel.send(
                    " blud is trying to end something that he has not started"
                )
                return
            print(f"journal end for user {userId}")
            users.update_one(
                {
                    "user_id": userId,
                },
                {"$set": {"daily": True, "reminder": True, "journal_flag": False}},
            )
            journals_collections.update_one(
                {
                    "user_id": userId,
                    "status": "active",
                },
                {"$set": {"status": "inactive"}},
            )
            await message.channel.send("Journal ended")
            del current_journal_entries[userId]
            del user_channel_map[userId]
            return
        if (
            message.content != " "
            and message.author.id in current_journal_entries
            and message.channel.id == user_channel_map[message.author.id]
        ):
            journals_collections.update_one(
                {
                    "user_id": message.author.id,
                    "created_at": {"$gte": start_of_day, "$lte": end_of_day},
                    "status": "active",
                },
                {"$push": {"data": message.content}},
            )
            print(f"Added {message.content} to the journal of {message.author.id}")
            return
        if int(datetime.now().strftime("%H")) >= 19:
            user = users.find_one({"user_id": userId})
            if user is None or user["reminder"] == True:
                print(
                    f" either user is not in the list of users or we already reminded them today"
                )
                return
            if not user["daily"]:
                await message.channel.send("you have to add your journal for the day?")
                await message.channel.send(
                    "if you are, please use the command vivi start journal"
                )
                users.update_one(
                    {
                        "user_id": userId,
                    },
                    {"$set": {"reminder": True}},
                )
                return


intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
print(os.getenv("DISCORD_TOKEN"))
client.run(os.getenv("DISCORD_TOKEN"))
