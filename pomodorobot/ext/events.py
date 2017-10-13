import discord
import logging
import asyncio
from datetime import datetime

from discord.ext import commands

import pomodorobot.lib as lib
import pomodorobot.config as config

from pomodorobot.bot import PomodoroBot
from pomodorobot.timer import TimerEvent, TimerStateEvent, TimerPeriodEvent, \
    TimerModifiedEvent, State


class Events:
    def __init__(self, bot: PomodoroBot):
        self.bot = bot

        TimerEvent.add_listener(self.timer_listener)

    async def on_command_error(self, ctx: commands.Context, error):

        log = ctx.author.display_name
        send = None

        if isinstance(error, commands.CheckFailure):

            if str(error) == "timer not found":
                send = "No timer found for this channel."
                log += " tried to interact with a nonexistent timer."

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
            log += " tried to execute a nonexistent command: `{}`." \
                .format(ctx.invoked_with)

            alt = None
            for name, command in self.bot.all_commands.items():
                if ctx.invoked_with == name:
                    alt = name
                elif isinstance(command, commands.GroupMixin):
                    for sub_name, sub_command in command.all_commands.items():
                        if ctx.invoked_with == sub_name:
                            alt = "{} {}".format(name, sub_name)

            if alt is not None:
                send += " Did you mean `{}`?".format(alt)

        elif isinstance(error, commands.CommandInvokeError):
            lib.log_cmd_stacktrace(error)
            return
        else:
            log = str(error)

        lib.log(log, channel_id=ctx.channel.id, level=logging.WARN)
        await ctx.send(send, delete_after=self.bot.ans_lifespan)

    async def on_ready(self):
        """ A listener for the event in which the bot is ready to work.
        """

        lib.log("")
        lib.log("Using discord.py version: " + discord.__version__)
        lib.log("Logged in as :")
        lib.log("\t" + self.bot.user.name)
        lib.log("\t" + str(self.bot.user.id))
        lib.log("")

        await self.bot.update_status()

        message = "**[{}]** {}" \
            .format(config.get_config().get_str('version'),
                    config.get_config().get_str('startup_msg'))
        for guild in self.bot.guilds:
            channel = guild.get_channel(config.get_config().get_section(
                'bot.new_member_channels.' + guild.id)['default'])

            if channel is None:
                continue
            await channel.send(message)

    def timer_listener(self, e: TimerEvent):
        """ Listens to any timer-related events.

        :param e: The timers' events to listen for.
        :type e: TimerPeriodEvent || TimerStateEvent || TimerModifiedEvent
        """

        msg = "{} | **{}** || " \
            .format(e.timer.get_guild_name(), e.timer.get_channel_name())

        if isinstance(e, TimerStateEvent):
            msg += "The timer has "

            if e.new_state == State.RUNNING:
                msg += "resumed!" if e.old_state == State.PAUSED else "started!"
            elif e.new_state == State.PAUSED:
                msg += "paused."
            elif e.new_state == State.STOPPED:
                msg += "been set up." if e.old_state is None else "stopped."
            else:
                msg += "been reset."

        elif isinstance(e, TimerPeriodEvent):
            msg += "Timer updated:\t\t "

            if e.old_period == e.new_period:
                msg += "**{}** period has been restarted! [_{} {}_]".format(
                    e.new_period.name,
                    e.new_period.time,
                    "minute" if e.new_period.time == 1 else "minutes")

            else:
                if e.old_period is not None:
                    msg += "**{}** period over!".format(e.old_period.name)
                if e.new_period is not None:
                    if e.old_period is not None:
                        msg += " "
                    msg += "**{}** period now starting [_{} {}_]".format(
                        e.new_period.name,
                        e.new_period.time,
                        "minute" if e.new_period.time == 1 else "minutes")

        elif isinstance(e, TimerModifiedEvent):
            msg += "Timer modified by {} periods!" \
                .format(e.action)
            if e.final_period is not None:
                msg += " Now at {} [_{} {}_]" \
                    .format(e.final_period.name,
                            e.final_period.time,
                            "minute" if e.final_period.time == 1 else "minutes")
        else:
            return

        @asyncio.coroutine
        def reaction():
            for member in e.timer.get_users_subscribed():
                yield from member.send(msg)

        self.bot.loop.create_task(reaction())

    async def on_member_join(self, member):
        guild = member.guild

        url = "http://i.imgur.com/jKhEXp6.jpg"
        embed = discord.Embed(url=url).set_image(url=url)
        welcome = "Welcome, {}!".format(member.mention)

        channels = config.get_config().get_section(
            'bot.new_member_channels.' + guild.id
        )

        if not channels:
            return

        default_channel = guild.get_channel(channels['default'])
        await default_channel.send(embed=embed)
        await default_channel.send(welcome)

        guild.get_channel(channels['log']).send(welcome)

        instructions = "\nPlease read and follow the instructions on {}, " \
                       "as well as introducing yourself in {} :smiley:" \
            .format(guild.get_channel(channels['info']).mention,
                    guild.get_channel(channels['directory']).mention)

        await default_channel.send(instructions)

    async def on_member_remove(self, member):
        guild = member.server

        channels = config.get_config().get_section(
            'bot.new_member_channels.' + guild.id
        )
        if not channels:
            return

        await guild.get_channel(channels['log']) \
            .send("{} has left the guild, farewell!".format(member.mention))

    async def on_member_update(self, before, after):
        if before.nick == after.nick:
            return

        guild = after.guild
        channels = config.get_config().get_section(
            'bot.new_member_channels.' + str(guild.id)
        )
        if not channels:
            return

        old_name = before.name if before.nick is None else before.nick
        new_name = after.name if after.nick is None else after.nick
        await guild.get_channel(channels['log']) \
            .send("{} is now {}. Why tho...".format(old_name, new_name))

    async def on_message(self, message):
        author = message.author
        if author.bot:
            return
        self.bot.mark_active(message.channel, author, datetime.now())

    async def on_message_delete(self, message):
        guild = message.guild

        if guild is None or message.author.bot is True or \
                message.content.startswith(self.bot.command_prefix + "timer"):
            return

        log_channels = self.bot.log_channels

        guild_id = str(guild.id)
        if log_channels and guild_id in log_channels.keys():
            log_to = guild.get_channel(log_channels[guild_id])

            msg = "Message deleted || {} | {} | {:%m/%d %H:%M:%S} UTC || {}" \
                .format(message.channel.mention,
                        message.author.display_name,
                        message.created_at,
                        message.clean_content)
            await log_to.send(msg)


def setup(bot: PomodoroBot):
    """ Sets the cog up.

    :param bot: The bot to add this cog to.
    """
    bot.add_cog(Events(bot))
