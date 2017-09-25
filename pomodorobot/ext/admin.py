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

    @commands.group(name="admin", pass_context=True)
    @commands.check(checks.has_permission)
    async def admin_cmd(self, ctx: commands.Context):
        """ Bot friends only! Do '!help admin' for sub-commands
        """
        pass

    @admin_cmd.command(name="reloadcfg")
    @commands.check(checks.is_admin)
    async def admin_reloadcfg(self):
        """ Reloads the configuration.
            Requires elevated permissions.
        """

        self.bot.reload_config(config.get_config().reload())

        await self.bot.say("Successfully reloaded configuration.",
                           delete_after=self.bot.ans_lifespan)
        lib.log("Reloaded configuration.")

    @admin_cmd.command(name="lock", pass_context=True)
    async def admin_lock(self, ctx: commands.Context):
        """ Locks a channel's timer so no user can modify it.
            Unless they have permissions.
            This command either locks or unlocks, thus acting as a switch.
            Requires elevated permissions.
        """

        channel = lib.get_channel(ctx)
        interface = self.bot.get_interface(channel)

        if interface.spoofed is not None:
            channel = interface.spoofed

        if interface.locked:
            interface.locked = False

            await self.bot.say("Channel unlocked.",
                               delete_after=self.bot.ans_lifespan)
            lib.log(lib.get_author_name(ctx) + " unlocked the channel.",
                    channel_id=channel.id)
        else:
            interface.locked = True

            await self.bot.say("Channel locked.",
                               delete_after=self.bot.ans_lifespan)
            lib.log(lib.get_author_name(ctx) + " locked the channel.",
                    channel_id=channel.id)

    @admin_cmd.command(name="sub", pass_context=True)
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
            channel_id = lib.get_channel(ctx).id

        server = lib.get_server(ctx)
        user = server.get_member(user_id)

        interface = self.bot.get_interface(server.get_channel(channel_id),
                                           False)
        author_name = lib.get_author_name(ctx, True)
        member_name = lib.get_name(user, True)
        if interface is None:
            lib.log("{} tried to subscribe {} to {}, "
                    "but the channel was not found or had no interface"
                    .format(author_name, member_name,  "this channel" if
                            channel_id is None else "channel with id=" +
                                                    channel_id),
                    channel_id=channel_id)
            await self.bot.say("Channel not found or invalid.",
                               delete_after=self.bot.ans_lifespan)
        elif user is None:
            lib.log("{} tried to forcefully subscribe an invalid member"
                    .format(author_name), channel_id=channel_id)
            await self.bot.say("User is invalid. Are you sure its his ID?",
                               delete_after=self.bot.ans_lifespan)
        else:
            if user in interface.subbed:
                await self.bot.say("User is already subscribed!",
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
            await self.bot.say("Member subscribed!",
                               delete_after=self.bot.ans_lifespan)
            await self.bot.say("{}, {} has subscribed you to this channel's "
                               "timer!".format(member_name, author_name),
                               delete_after=self.bot.ans_lifespan)

    @admin_cmd.command(name="unsub", pass_context=True)
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
            channel_id = lib.get_channel(ctx).id

        server = lib.get_server(ctx)
        user = server.get_member(user_id)

        interface = self.bot.get_interface(server.get_channel(channel_id),
                                           False)
        author_name = lib.get_author_name(ctx, True)
        member_name = lib.get_name(user, True)
        if interface is None:
            lib.log("{} tried to unsubscribe {} from {}, "
                    "but the channel was not found or had no interface"
                    .format(author_name, member_name,  "this channel" if
                            channel_id is None else "channel with id=" +
                                                    channel_id),
                    channel_id=channel_id)
            await self.bot.say("Channel not found or invalid.",
                               delete_after=self.bot.ans_lifespan)
        elif user is None:
            lib.log("{} tried to forcefully unsubscribe an invalid member"
                    .format(author_name), channel_id=channel_id)
            await self.bot.say("User is invalid. Are you sure its his ID?",
                               delete_after=self.bot.ans_lifespan)
        else:
            interface.remove_sub(user)
            lib.log("{} forcefully unsubscribed {} from {}."
                    .format(author_name, member_name, "this channel" if
                            channel_id is None else "channel with id=" +
                                                    channel_id),
                    channel_id=channel_id)
            await self.bot.say("Member unsubscribed!",
                               delete_after=self.bot.ans_lifespan)
            await self.bot.say("{}, {} has unsubscribed you from this channel's"
                               " timer!".format(member_name, author_name),
                               delete_after=self.bot.ans_lifespan)

    @admin_cmd.command(name="spoof", pass_context=True)
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

        channel = lib.get_channel(ctx)

        if channel.id == spoofed_id:
            await self.bot.say("How about no. " + spoofed_id,
                               delete_after=self.bot.ans_lifespan)
            return

        spoofed_channel = lib.get_server(ctx).get_channel(spoofed_id)

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

        await self.bot.say(send, delete_after=self.bot.ans_lifespan)
        lib.log(log, channel_id=channel.id)

    @admin_cmd.command(name="debug")
    @commands.check(checks.is_admin)
    async def admin_debug(self):
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
        await self.bot.say("Debug mode {}.".format(state),
                           delete_after=self.bot.ans_lifespan)

    @admin_cmd.command(name="shutdown", pass_context=True)
    @commands.check(checks.is_admin)
    async def admin_shutdown(self, ctx: commands.Context):
        """ Exits the program. Administrator only!
        """

        lib.log("Shutting down...")
        await self.bot.say("Hope I did well, bye!")

        for channel, timer in self.bot.valid_timers().items():
            if timer.get_state() != State.STOPPED:
                timer.stop()
                if lib.get_channel(ctx) != channel:
                    await self.bot.safe_send(
                        channel,
                        "I'm sorry, I have to go. See you later!"
                    )

                    await self.bot.remove_messages(channel)
        self.bot.unsub_all()

        await self.bot.logout()


def setup(bot: PomodoroBot):
    bot.add_cog(Admin(bot))

