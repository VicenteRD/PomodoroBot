from datetime import datetime

from discord.ext import commands

import pomodorobot.lib as lib
import pomodorobot.config as config
import pomodorobot.ext.checks as checks

from pomodorobot.bot import PomodoroBot
from pomodorobot.timer import State


class Admin:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.group(name="admin")
    @commands.check(checks.has_permission)
    async def admin_cmd(self, ctx: commands.Context):
        """ Bot friends only! Do '!help admin' for sub-commands
        """
        pass

    @admin_cmd.command(name="reloadcfg")
    @commands.check(checks.is_admin)
    async def admin_reloadcfg(self, ctx: commands.Context):
        """ Reloads the configuration.
            Requires elevated permissions.
        """

        self.bot.reload_config(config.get_config().reload())

        await ctx.send("Successfully reloaded configuration.",
                       delete_after=self.bot.ans_lifespan)
        lib.log("Reloaded configuration.")

    @admin_cmd.command(name="lock")
    async def admin_lock(self, ctx: commands.Context):
        """ Locks a channel's timer so no user can modify it.
            Unless they have permissions.
            This command either locks or unlocks, thus acting as a switch.
            Requires elevated permissions.
        """

        channel = self.bot.spoof(ctx.author, ctx.channel)
        interface = self.bot.get_interface(channel)

        if interface.locked:
            interface.locked = False

            await ctx.send("Channel unlocked.",
                           delete_after=self.bot.ans_lifespan)
            lib.log(ctx.author + " unlocked the channel.",
                    channel_id=channel.id)
        else:
            interface.locked = True

            await ctx.send("Channel locked.",
                           delete_after=self.bot.ans_lifespan)
            lib.log(ctx.author + " locked the channel.",
                    channel_id=channel.id)

    @admin_cmd.command(name="sub")
    async def admin_sub(self, ctx: commands.Context, user_id: str,
                        channel_id=None):
        """ Forcefully subscribes a member to a timer.

        :param user_id: The ID of the user to subscribe
        :type user_id: str

        :param channel_id: The ID of the channel to subscribe the user to. If
            it's None or not provided, defaults to the channel this command was
            sent to.
        :type channel_id: str
        """

        if channel_id is None:
            channel_id = ctx.channel.id

        user = ctx.guild.get_member(user_id)

        interface = self.bot.get_interface(ctx.guild.get_channel(channel_id),
                                           False)
        author_name = ctx.author.display_name
        member_name = user.display_name
        if interface is None:
            lib.log("{} tried to subscribe {} to {}, "
                    "but the channel was not found or had no interface"
                    .format(author_name, member_name,  "this channel" if
                            channel_id is None else "channel with id=" +
                                                    channel_id),
                    channel_id=channel_id)
            await ctx.send("Channel not found or invalid.",
                           delete_after=self.bot.ans_lifespan)
        elif user is None:
            lib.log("{} tried to forcefully subscribe an invalid member"
                    .format(author_name), channel_id=channel_id)
            await ctx.send("User is invalid. Are you sure its his ID?",
                           delete_after=self.bot.ans_lifespan)
        else:
            if user in interface.subbed:
                await ctx.send("User is already subscribed!",
                               delete_after=self.bot.ans_lifespan)
                lib.log("{} tried to subscribe {} to {}, but user is already "
                        "subscribed".format(author_name, member_name,
                                            "this channel" if channel_id is None
                                            else "channel with id=" + channel_id
                                            ), channel_id=channel_id)
                return

            interface.add_sub(user, datetime.now())
            lib.log("{} forcefully subscribed {} to {}."
                    .format(author_name, member_name, "this channel" if
                            channel_id is None else "channel with id=" +
                                                    channel_id),
                    channel_id=channel_id)
            await ctx.send("Member subscribed!",
                           delete_after=self.bot.ans_lifespan)
            await ctx.send("{}, {} has subscribed you to this channel's "
                           "timer!".format(member_name, author_name),
                           delete_after=self.bot.ans_lifespan)

    @admin_cmd.command(name="unsub")
    async def admin_unsub(self, ctx: commands.Context, user_id: str,
                          channel_id=None):
        """ Forcefully unsubscribes a member to a timer.

        :param user_id: The ID of the user to unsubscribe
        :type user_id: str

        :param channel_id: The ID of the channel to unsubscribe the user from.
            If it's None or not provided, defaults to the channel this command
            was sent to.
        :type channel_id: str
        """

        if channel_id is None:
            channel_id = ctx.channel.id

        user = ctx.guild.get_member(user_id)

        interface = self.bot.get_interface(ctx.guild.get_channel(channel_id),
                                           False)
        author_name = ctx.author.display_name
        member_name = user.display_name
        if interface is None:
            lib.log("{} tried to unsubscribe {} from {}, "
                    "but the channel was not found or had no interface"
                    .format(author_name, member_name,  "this channel" if
                            channel_id is None else "channel with id=" +
                                                    channel_id),
                    channel_id=channel_id)
            await ctx.send("Channel not found or invalid.",
                           delete_after=self.bot.ans_lifespan)
        elif user is None:
            lib.log("{} tried to forcefully unsubscribe an invalid member"
                    .format(author_name), channel_id=channel_id)
            await ctx.send("User is invalid. Are you sure its his ID?",
                           delete_after=self.bot.ans_lifespan)
        else:
            interface.remove_sub(user)
            lib.log("{} forcefully unsubscribed {} from {}."
                    .format(author_name, member_name, "this channel" if
                            channel_id is None else "channel with id=" +
                                                    channel_id),
                    channel_id=channel_id)
            await ctx.send("Member unsubscribed!",
                           delete_after=self.bot.ans_lifespan)
            await ctx.send("{}, {} has unsubscribed you from this channel's"
                           " timer!".format(member_name, author_name),
                           delete_after=self.bot.ans_lifespan)

    @admin_cmd.command(name="spoof")
    async def admin_spoof(self, ctx: commands.Context, spoofed_id=None):
        """ Enables spoof-mode on a channel.
            Spoof mode allows users with permissions to modify another specified
            channel's timer from the one in which this command
            was executed.

            For example, if channel #session_1 has ID '249719010319532064'
            and someone executes '!spoof 249719010319532064' from #admin_area,
            all timer-related commands (except for setup) executed from
            #admin_area by members with permissions will either affect or give
            information of the timer in #session_1 instead.

        :param spoofed_id: The ID of the channel that instructions will be
            sent to.
        :type spoofed_id: str
        """

        channel = ctx.channel

        if channel.id == spoofed_id:
            await ctx.send("How about no. " + spoofed_id,
                           delete_after=self.bot.ans_lifespan)
            return

        spoofed_channel = ctx.guild.get_channel(spoofed_id)

        if spoofed_id is not None:
            self.bot.get_interface(channel).spoofed = spoofed_channel

            send = "Now acting in channel " + spoofed_channel.name
            log = "Now acting as if in " + spoofed_channel.name

        elif self.bot.get_interface(channel).spoofed is not None:
            self.bot.get_interface(channel).spoofed = None

            send = "Now acting in current channel"
            log = "Spoofing now off"
        else:
            raise commands.MissingRequiredArgument

        await ctx.send(send, delete_after=self.bot.ans_lifespan)
        lib.log(log, channel_id=channel.id)

    @admin_cmd.command(name="debug")
    @commands.check(checks.is_admin)
    async def admin_debug(self, ctx: commands.Context):
        """ Makes the logger show debug-level information on the log.
            This command is administrator-only.
        """

        if lib.is_logger_debug():
            lib.debug(False)
            level = "info"
            state = "off"
        else:
            lib.debug(True)
            level = "debug"
            state = "on"

        lib.log("Switching to {}-level logging".format(level))
        await ctx.send("Debug mode {}.".format(state),
                       delete_after=self.bot.ans_lifespan)

    @admin_cmd.command(name="shutdown", pass_context=True)
    @commands.check(checks.is_admin)
    async def admin_shutdown(self, ctx: commands.Context):
        """ Exits the program. Administrator only!
        """

        lib.log("Shutting down...")
        await ctx.send("Hope I did well, bye!")

        for channel, timer in self.bot.valid_timers().items():
            if timer.get_state() != State.STOPPED:
                timer.stop()
                if ctx.channel != channel:
                    await channel.send(
                        "I'm sorry, I have to go. See you later!")

                    await self.bot.remove_messages(channel)
        self.bot.unsub_all()

        await self.bot.logout()


def setup(bot: PomodoroBot):
    bot.add_cog(Admin(bot))

