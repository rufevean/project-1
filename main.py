from datetime import datetime, timedelta
import os
import connection
import discord
from dotenv import load_dotenv
import pymongo

now = datetime.now()
start_of_day = datetime(now.year, now.month, now.day)
end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
journals = {}

load_dotenv()

db = connection.get_connection()
users = db.get_collection("users")
journals_collections = db.get_collection("journals")
tasks_collections = db.get_collection("tasks")
current_journal_entries = {}
user_channel_map = {}


# TODO : write a cron to set all users daily:False and reminder:False at midnight
class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        return

    async def on_message(self, message):
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
        if message.content.startswith("vivi show"):
            content = int(message.content.split(" ")[-1])
            await message.channel.send(f"Showing latest {content} days of journal")
            journal = (
                journals_collections.find({"user_id": userId})
                .sort({"created_at": -1})
                .limit(content)
            )
            for i in range(content):
                await message.channel.send(f"Day {i+1}: {journal[i]['data']}")

            print(journal[0])
            return
        if message.content.startswith("vivi task"):
            command = message.content.split(" ")[2]
            if command == "list":
                await message.channel.send("Listing all tasks")
                tasks = tasks_collections.find({"user_id": userId})
                for task in tasks:
                    await message.channel.send(
                        f"Task: {task['id']} with note {task['note']} and progress {task['progress']}"
                    )
                return
            if command == "add":
                print(userId, "userId")
                note = " ".join(message.content.split(" ")[3:])
                if note == "":
                    await message.channel.send("Please provide a note for the task")
                    return
                try:
                    latest_task = tasks_collections.find_one(
                        {"user_id": userId}, sort=[("date", pymongo.DESCENDING)]
                    )
                    print(latest_task, "latest task")
                except Exception as e:
                    print(e, "error")
                    latest_task = None
                if latest_task is None:
                    id = 1
                else:
                    print(" IS THIS STATEMENT REACHED")
                    id = latest_task["id"] + 1
                tasks_collections.insert_one(
                    {
                        "user_id": userId,
                        "id": id,
                        "note": note,
                        "progress": "todo",
                        "date": datetime.now(),
                    }
                )
                await message.channel.send("Adding a task")
                await message.channel.send(
                    f'Task added with id {id} and note "{note}" and progress todo'
                )
                return
            if command == "edit":
                id = message.content.split(" ")[3]
                task = tasks_collections.find_one({"user_id": userId, "id": int(id)})
                if task is None:
                    await message.channel.send(f"Task not found with id {id}")
                    return
                command_type = message.content.split(" ")[4]
                if command_type == "note":
                    note = " ".join(message.content.split(" ")[5:])
                    if note == "":
                        await message.channel.send("Please provide a note for the task")
                        return
                    tasks_collections.update_one(
                        {"user_id": userId, "id": int(id)}, {"$set": {"note": note}}
                    )
                    await message.channel.send(f"Task edited with note {note}")
                if command_type == "progress":
                    progress = message.content.split(" ")[5]
                    if progress == "":
                        await message.channel.send(
                            "Please provide a progress for the task"
                        )
                        return
                    tasks_collections.update_one(
                        {"user_id": userId, "id": int(id)},
                        {"$set": {"progress": progress}},
                    )
                    await message.channel.send(f"Task edited with progress {progress}")
            if command == "remove":
                try:
                    id = message.content.split(" ")[3]
                except:
                    await message.channel.send("Please provide a id for the task")
                    return
                task = tasks_collections.delete_one({"user_id": userId, "id": int(id)})
                if task is None:
                    await message.channel.send(f"Task not found with id {id}")
                    return
                await message.channel.send(f"Task removed with id {id}")
                return
            if command == "show":
                try:
                    id = int(message.content.split(" ")[3])
                except:
                    await message.channel.send("Please provide a valid id of the task")
                    return
                task = tasks_collections.find_one({"user_id": userId, "id": id})
                if task is None:
                    await message.channel.send(f"Task not found with id {id}")
                    return
                await message.channel.send(
                    f"Task with id {id} and note {task['note']} and progress {task['progress']}"
                )
                return


intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(os.getenv("DISCORD_TOKEN"))
