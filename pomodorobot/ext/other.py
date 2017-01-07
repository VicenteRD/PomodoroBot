import yaml
import discord

from discord.ext import commands

import pomodorobot.lib as lib
import pomodorobot.config as config
import pomodorobot.ext.checks as checks

from pomodorobot.bot import PomodoroBot
from pomodorobot.timer import State


class Other:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.command(aliases=['about'])
    async def aboot(self):
        """ Information about me!
        """

        await self.bot.say("Current version: {}\nSource: {}"
                           .format(config.get_config().get_str('version'),
                                   config.get_config().get_str('source')),
                           delete_after=self.bot.ans_lifespan * 4)

        await self.bot.say("Questions, suggestions, bug to report?\n" +
                           "Open an issue on the Github page, " +
                           "or send me a message on Discord! " +
                           config.get_config().get_str('author_name'),
                           delete_after=self.bot.ans_lifespan * 4)

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

    @admin_cmd.command(name="attendance", pass_context=True)
    @commands.check(checks.has_permission)
    async def admin_attendance(self, ctx: commands.Context, name: str):
        """ Gives the last attendance (timer subscription) of the user
            to any timer, in the form of the UTC time in which it was
            registered.

        :param name: The username (Not the nick) of the user of whose
            attendance you want to know.
        :return:
        """
        file = open(self.bot.attendance_file, 'r')
        attendance_info = yaml.load(file)
        file.close()

        server_id = lib.get_server_id(ctx)

        if attendance_info is None or server_id not in attendance_info.keys():
            return

        if name == "everyone":
            attendance_date = "\n".join("{}: {}".format(k, v) for k, v
                                        in attendance_info[server_id].items())

        elif name in attendance_info[server_id]:
            attendance_date = attendance_info[server_id][name]
        else:
            attendance_date = None

        if attendance_date is None:
            attendance_date = "None found"

        log = "{} queried for {}'s attendance. Result was: {}"\
            .format(lib.get_author_name(ctx, True), name, attendance_date)


        lib.log(log, channel_id=lib.get_channel_id(ctx))
        await self.bot.say("```\n" + attendance_date + "\n```",
                           delete_after=self.bot.ans_lifespan * 3)


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

        await self.bot.logout()

    @commands.command(pass_context=True)
    async def howto(self, ctx, specific=None):
        """ Tells you how to use the bot.
        """

        if specific is not None and specific == "admin":
            howto = """
I will show you the world...

... Just let me get inspired and I'll finish this, I promise!

... Some day.
"""
        else:
            howto = """
!timer setup
!timer sub
!timer start
_Use the bot, and when you're done:_
!timer stop
!timer unsub
!timer reset
(If the prefix is not '!', change it accordingly)
"""

        await self.bot.safe_send(ctx.message.author, howto)

    @commands.command(hidden=True)
    async def why(self, time_out=15):
        """ For when you question life and decisions.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://i.imgur.com/OpFcp.jpg"
        embed = discord.Embed(title="Why, you ask...",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def howcome(self, time_out=15):
        """ When you just don't understand, this command is your best friend.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = ("http://24.media.tumblr.com/0c3c175c69e45a4182f18a1057ac4bf7/" +
               "tumblr_n1ob7kSaiW1qlk7obo1_500.gif")

        embed = discord.Embed(title="How come...?",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def no(self, time_out=15):
        """ For those moments when people don't get it.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://media.giphy.com/media/ToMjGpx9F5ktZw8qPUQ/giphy.gif"
        embed = discord.Embed(title="NO!",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def faint(self, time_out=15):
        """ Can't handle it? Me neither.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://media.giphy.com/media/4OowbIsmYHbpu/giphy.gif"
        embed = discord.Embed(title="Oh god.",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def potato(self, time_out=15):
        """ Come on!

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = ("http://www.lovethispic.com/uploaded_images/156255-I-Am" +
               "-A-Tiny-Potato-And-I-Believe-In-You-You-Can-Do-The-Thing.jpg")
        embed = discord.Embed(title="Believe!",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def fine(self, time_out=15):
        """ Come on!

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "http://i.imgur.com/c4jt321.png"
        embed = discord.Embed(title="Don't worry about it.",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))


def setup(bot: PomodoroBot):
    bot.add_cog(Other(bot))
