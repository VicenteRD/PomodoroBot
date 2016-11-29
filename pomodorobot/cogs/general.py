from discord.ext import commands

from pomodorobot.bot import PomodoroBot
import pomodorobot.lib as lib


class General:

    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, error, ctx: commands.Context):
        if isinstance(error, commands.CheckFailure):
            if error.message == "timer not found":
                send = "No timer found for this channel."
                log = (lib.get_author_name(ctx) +
                       " tried to start a timer that was already running.")

            elif error.message == "timer locked":
                send = "You are not allowed to modify this timer."
                log = (lib.get_author_name(ctx) +
                       " tried to modify a locked timer without permissions")
            else:
                send = log = ""

            lib.log(log, channel_id=ctx.message.channel.id)
            self.bot.safe_send(ctx.message.channel, send,
                               delete_after=self.bot.response_lifespan)


def has_permission(ctx: commands.Context) -> bool:
    return isinstance(ctx.bot, PomodoroBot) and \
           ctx.bot.has_permission(ctx.message.author)


def setup(bot: PomodoroBot):
    bot.add_cog(General(bot))
