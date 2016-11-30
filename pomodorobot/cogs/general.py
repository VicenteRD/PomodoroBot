from discord.ext import commands

from pomodorobot.bot import PomodoroBot
import pomodorobot.lib as lib


class General:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    async def on_command_error(self, error, ctx: commands.Context):
        if isinstance(error, commands.CheckFailure):
            log = lib.get_author_name(ctx)

            if str(error) == "timer not found":
                send = "No timer found for this channel."
                log += " tried to start a nonexistent timer."

            elif str(error) == "timer locked":
                send = "You are not allowed to modify this timer."
                log += " tried to modify a locked timer without permissions."

            elif str(error) == "no permissions":
                send = "You do not have permission to do this!"
                log += (" tried to execute a command and failed, " +
                        "lacked permissions.")
            else:
                send = "Timers are not allowed in this channel."
                log += " tried to start a timer in a non-whitelisted channel."

            lib.log(log, channel_id=ctx.message.channel.id)
            await self.bot.safe_send(ctx.message.channel, send,
                                     delete_after=self.bot.ans_lifespan)
        if isinstance(error, commands.CommandNotFound):
            send = "Command not found: `" + ctx.invoked_with + "`."
            lib.log(send)

            alt = None
            for name, command in self.bot.commands.items():
                if ctx.invoked_with == name:
                    alt = name
                elif isinstance(command, commands.GroupMixin):
                    for sub_name, sub_command in command.commands.items():
                        if ctx.invoked_with == sub_name:
                            alt = name + " " + sub_name

            if alt is not None:
                send += " Did you mean `" + alt + "`?"
            await self.bot.safe_send(ctx.message.channel, send,
                                     delete_after=self.bot.ans_lifespan)


def has_permission(ctx: commands.Context) -> bool:
    if isinstance(ctx.bot, PomodoroBot) and \
       ctx.bot.has_permission(ctx.message.author):
        return True
    raise commands.CheckFailure(message="no permissions")


def setup(bot: PomodoroBot):
    bot.add_cog(General(bot))
