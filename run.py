import logging
import yaml

from campaign.bot import bot

logger = logging.getLogger(__name__)
logging.basicConfig()

with open("config.yaml") as f:
    config = yaml.safe_load(f)

bot.run(token=config.get("DISCORD_TOKEN"))
