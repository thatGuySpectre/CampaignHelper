import asyncio
import logging

import discord
from discord import app_commands

from campaign.core import query
from campaign.tools import add_world_info

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Client(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


intents = discord.Intents.none()

bot = Client(intents=intents)


@bot.event
async def on_message(ctx):
    logger.info("message: " + ctx.content)
    if ctx.author == bot.user:
        return
    if bot.user.mentioned_in(ctx) or True:
        async with ctx.channel.typing():
            response = await aquery(message=ctx.content, author=ctx.author.name)
            await ctx.channel.send(response)


async def aquery(message, author):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None,
                                      lambda: query(message, author))


@bot.tree.command(description="Add a single text, identified by a title to give the bot context.")
async def add_text(interaction, title: str, text: str):
    add_world_info(name=title, content=text)
    await interaction.response.send_message("Successfully added text to database. Try asking me about it!")


@bot.tree.command(description="Add a text file, identified by a title to give the bot context.")
async def add_file(interaction, title: str, file: discord.Attachment):
    if not file.content_type.startswith("text"):
        await interaction.response.send_message("Attachment has to be a text file")
    else:
        add_world_info(name=title, content=file.read())
        await interaction.response.send_message("Successfully added file to database. Try asking me about it!")
