import logging
import traceback

from discord.ext import commands

import pomodorobot.lib as lib
import pomodorobot.config as config

from pomodorobot.bot import PomodoroBot


class Events:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    async def on_command_error(self, error, ctx: commands.Context):

        log = lib.get_author_name(ctx)
        send = None

        if isinstance(error, commands.CheckFailure):

            if str(error) == "timer not found":
                send = "No timer found for this channel."
                log += " tried to start a nonexistent timer."

            elif str(error) == "timer locked":
                send = "You are not allowed to modify this timer."
                log += " tried to modify a locked timer without permissions."

            elif str(error) == "no permissions" or str(error) == "not admin":
                send = "You do not have permission to do this!"
                log += (" tried to execute a command and failed, " +
                        "lacked permissions.")
            else:
                send = "Timers are not allowed in this channel."
                log += " tried to start a timer in a non-whitelisted channel."

        elif isinstance(error, commands.CommandNotFound):
            send = "Command not found: `" + ctx.invoked_with + "`."
            log += " tried to execute a nonexistent command: `{}`."\
                .format(ctx.invoked_with)

            alt = None
            for name, command in self.bot.commands.items():
                if ctx.invoked_with == name:
                    alt = name
                elif isinstance(command, commands.GroupMixin):
                    for sub_name, sub_command in command.commands.items():
                        if ctx.invoked_with == sub_name:
                            alt = name + " " + sub_name  # TODO: many found?

            if alt is not None:
                send += " Did you mean `" + alt + "`?"

        elif isinstance(error, commands.CommandInvokeError):
            lib.log_cmd_stacktrace(error)
            return
        else:
            log = str(error)

        lib.log(log, channel_id=lib.get_channel_id(ctx), level=logging.WARN)
        await self.bot.safe_send(ctx.message.channel, send,
                                 delete_after=self.bot.ans_lifespan)

    async def on_ready(self):
        lib.log("")
        lib.log("Logged in as :")
        lib.log("\t" + self.bot.user.name)
        lib.log("\t" + self.bot.user.id)
        lib.log("")

        await self.bot.update_status()

        message = "**[{}]** {}"\
            .format(config.get_config().get_str("version"),
                    config.get_config().get_str("startup_msg"))
        for server in self.bot.servers:
            await self.bot.send_message(server, message)


def setup(bot: PomodoroBot):
    bot.add_cog(Events(bot))
