from time import sleep
import discord
import logging

from logic.openai_server import OpenAIServer

class DiscordBot:
    def __init__(self, token: str, userID: int, openAIToken: str):
        self.userID = userID
        self.token = token
        self.client = discord.Client(intents=discord.Intents.all())
        self.isReady = False
        self.openAI = OpenAIServer(token=openAIToken)
        self.logger = logging.getLogger(self.__name__)

    def run(self):
        try:
            @self.client.event
            async def on_ready():
                logging.info("Discord bot is Ready")
                self.openAI.server.start()

            @self.client.event
            async def on_message(message: discord.Message):
                if message.author.bot or message.guild != None:
                    return
                if message.author.id != self.userID:
                    return
                while self.openAI.runningLock:
                    sleep(5)
                embed = discord.Embed(title="実行中")
                replyMessage = await message.reply(embed=embed)
                await self.openAI.run(message.content)
                embed.title = "実行完了"
                embed.add_field(name="開放中のポート", value=(", ".join([str(port) for port in self.openAI.ports]) if len(self.openAI.ports) > 0 else "なし"))
                await replyMessage.edit(embed=embed)
            
            self.client.run(token=self.token)
        finally:
            self.openAI.server.stop()
