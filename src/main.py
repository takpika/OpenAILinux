import os, logging

from logic.discord_bot import DiscordBot

logger = logging.getLogger("main.py")

token = os.environ.get("DISCORD_TOKEN")
userID = os.environ.get("DISCORD_USER_ID")
openAIToken = os.environ.get("OPENAI_API_KEY")
if token is None or token == "":
    logger.error("Please Set DISCORD_TOKEN")
    exit(1)
if openAIToken is None or openAIToken == "":
    logger.error("Please Set OPENAI_API_KEY")
    exit(1)
if userID is None or userID == "":
    logger.error("Please Set DISCORD_USER_ID")
    exit(1)

if __name__ == "__main__":
    bot = DiscordBot(token=token, userID=int(userID), openAIToken=openAIToken)
    bot.run()