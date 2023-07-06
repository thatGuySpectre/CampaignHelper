import asyncio
import logging

import discord
import yaml
from discord import app_commands

from campaign.core import query
from campaign.tools import add_world_info

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Client(discord.Client):
    def __init__(self, intent):
        super().__init__(intents=intent)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


intents = discord.Intents.all()

bot = Client(intent=intents)

with open("config.yaml") as f:
    config = yaml.safe_load(f)


@bot.event
async def on_message(ctx):
    logger.info("message: " + ctx.content)
    if ctx.author == bot.user:
        return
    if ctx.author.id in config.get("BAN_LIST", {}):
        return
    logger.info("content: " + ctx.content + " vs " + bot.user.mention)
    if bot.user.mentioned_in(ctx):
        async with ctx.channel.typing():
            response = await aquery(message=ctx.content, author=ctx.author.name)
            await ctx.channel.send(response)


async def aquery(message, author):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None,
                                      lambda: query(message, author))


@bot.tree.command(description="Add a single text, identified by a title to give the bot context.")
async def add_text(interaction, title: str, text: str):
    if interaction.author.id not in config.get("OWNERS", {}):
        await interaction.response.send_message(content="You are not allowed to add texts", delete_after=5)
        return
    await interaction.response.send_message(content="Successfully added text to database. Try asking me about it!")
    add_world_info(name=title, content=text)


@bot.tree.command(description="Add a text file, identified by a title to give the bot context.")
async def add_file(interaction, title: str, file: discord.Attachment):
    if interaction.author.id not in config.get("OWNERS", {}):
        await interaction.response.send_message(content="You are not allowed to add texts", delete_after=5)
        return
    if not file.content_type.startswith("text"):
        await interaction.response.send_message(content="Attachment has to be a text file")
    else:
        await interaction.response.send_message(content="Successfully added file to database. Try asking me about it!")
        add_world_info(name=title, content=(await file.read()).decode())
