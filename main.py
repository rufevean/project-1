import discord 
from dotenv import load_dotenv
import os
import json
import dataclasses
import collections
from datetime import datetime

@dataclasses.dataclass
class journal_data:
  user_id: str
  data: list
  journal_flag: bool
  date: str
  channel_id: str

journals = {}

load_dotenv()
class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    async def on_ready(self):
        print(f'Logged in as {self.user}')
    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('!hello'):
            await message.channel.send('Hello!')
        if message.content.startswith('!journal start'):
          author = message.author.id
          x = f"journal_{author}"
          x = journal_data(author, [], True, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message.channel.id)
          journals[author] = x
          await message.channel.send('Journal started')
        if message.content != " " and message.author.id in journals and journals[message.author.id].journal_flag == True and journals[message.author.id].channel_id == message.channel.id:
          journals[message.author.id].data.append(message.content)
        if message.content.startswith('!journal end') and message.author.id in journals and journals[message.author.id].journal_flag == True and journals[message.author.id].channel_id == message.channel.id:
          journals[message.author.id].journal_flag = False
          journals[message.author.id].data = journals[message.author.id].data[1:-1]
          journal_dict = collections.OrderedDict(journals[message.author.id].__dict__)
          with open("journal.json", "r") as f:
            data = json.load(f)
          if str(message.author.id) in data:
            await message.channel.send("you already have a journal started today ,let me add this to it")
            data[str(message.author.id)].append(journal_dict)
          else:
            await message.channel.send("you don't have a journal started today ,let me start a new one for you")
            data[str(message.author.id)] = [journal_dict]
          with open("journal.json", "w") as f:
            json.dump({str(message.author.id): data[str(message.author.id)]}, f)
          await message.channel.send('Journal ended')

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
print(os.getenv('DISCORD_TOKEN'))
client.run(os.getenv('DISCORD_TOKEN'))
