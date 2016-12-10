import logging
import asyncio

from discord.ext import commands

import pomodorobot.lib as lib
import pomodorobot.config as config

from pomodorobot.bot import PomodoroBot
from pomodorobot.timer import TimerEvent, TimerStateEvent, TimerPeriodEvent, State


class Events:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

        TimerEvent.add_listener(self.timer_listener)

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
        await self.bot.safe_send(lib.get_channel(ctx), send,
                                 delete_after=self.bot.ans_lifespan)

    async def on_ready(self):
        """ A listener for the event in which the bot is ready to work.
        """

        lib.log("")
        lib.log("Logged in as :")
        lib.log("\t" + self.bot.user.name)
        lib.log("\t" + self.bot.user.id)
        lib.log("")

        await self.bot.update_status()

        message = "**[{}]** {}"\
            .format(config.get_config().get_str('version'),
                    config.get_config().get_str('startup_msg'))
        for server in self.bot.servers:
            await self.bot.send_message(server, message)

    def timer_listener(self, e: TimerEvent):
        """ Listens to any timer-related events.

        :param e: The timers' events to listen for. Can be either
            TimerPeriodEvent or TimerStateEvent.
        """

        if isinstance(e, TimerStateEvent):
            message = "The timer you're subscribed to has "
            if e.new_state == State.RUNNING:
                if e.old_state == State.PAUSED:
                    message += "resumed!"
                else:
                    message += "started!"
            elif e.new_state == State.PAUSED:
                message += "paused."
            elif e.new_state == State.STOPPED:
                message += "stopped."
            else:
                message += "reset."

        elif isinstance(e, TimerPeriodEvent):
            message = "A timer you're subscribed to has updated!\n\t"

            if e.old_period is not None:
                message = "'{}' period over!".format(e.old_period.name)
            if e.new_period is not None:
                message += " '{}' period now starting ({}).".format(
                    e.new_period.name,
                    lib.pluralize(e.new_period.time, "minute", append="s"))
            message = message.strip()
        else:
            return

        @asyncio.coroutine
        def reaction():
            for member in e.timer.get_users_subscribed():
                yield from self.bot.safe_send(member, message)

        self.bot.loop.create_task(reaction())


def setup(bot: PomodoroBot):
    """ Sets the cog up.

    :param bot: The bot to add this cog to.
    """
    bot.add_cog(Events(bot))
