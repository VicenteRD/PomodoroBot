import discord

from discord.ext import commands

import pomodorobot.lib as lib
import pomodorobot.config as config
import pomodorobot.ext.checks as checks

from pomodorobot.bot import PomodoroBot, VERSION
from pomodorobot.timer import State


class Other:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.command()
    async def about(self):
        await self.bot.say("Current version: {}\nSource: {}"
                           .format(VERSION,
                                   "https://github.com/VicenteRD/PomodoroBot/"))

    @commands.group(name="admin", pass_context=True)
    @commands.check(checks.has_permission)
    async def admin_cmd(self, ctx: commands.Context):
        """ Bot friends only! Do '!help admin' for sub-commands
        """
        pass

    @admin_cmd.command()
    async def reloadcfg(self):
        """ Reloads the configuration.
            Requires elevated permissions.
        """

        self.bot.reload_config(config.get_config())

        await self.bot.say("Successfully reloaded configuration.",
                           delete_after=self.bot.ans_lifespan)
        lib.log("Reloaded configuration.")

    @admin_cmd.command(pass_context=True)
    async def lock(self, ctx: commands.Context):
        """ Locks a channel's timer so no user can modify it.
            Unless they have permissions.
            This command either locks or unlocks, thus acting as a switch.
            Requires elevated permissions.
        """

        channel_id = lib.get_channel_id(ctx)

        if channel_id in self.bot.spoofed.keys():
            channel_id = self.bot.spoofed[channel_id]

        if channel_id not in self.bot.locked:
            self.bot.locked.append(channel_id)

            await self.bot.say("Channel locked.",
                               delete_after=self.bot.ans_lifespan)
            lib.log(lib.get_author_name(ctx) + " locked the channel.",
                    channel_id=channel_id)
        else:
            self.bot.locked.remove(channel_id)

            await self.bot.say("Channel unlocked.",
                               delete_after=self.bot.ans_lifespan)
            lib.log(lib.get_author_name(ctx) + " unlocked the channel.",
                    channel_id=channel_id)

    @admin_cmd.command(pass_context=True)
    async def spoof(self, ctx: commands.Context, spoofed_id=None):
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

        channel_id = lib.get_channel_id(ctx)

        if channel_id == spoofed_id:
            await self.bot.say("How about no. " + spoofed_id,
                               delete_after=self.bot.ans_lifespan)
            return

        if spoofed_id is not None:
            self.bot.spoofed[channel_id] = spoofed_id

            send = "Now acting in channel " + spoofed_id
            log = "Now acting as if in " + spoofed_id

        elif channel_id in self.bot.spoofed.keys():
            del self.bot.spoofed[channel_id]

            send = "Now acting in current channel"
            log = "Spoofing now off"
        else:
            raise commands.MissingRequiredArgument

        await self.bot.say(send, delete_after=self.bot.ans_lifespan)
        lib.log(log, channel_id=channel_id)

    @admin_cmd.command()
    @commands.check(checks.is_admin)
    async def debug(self):
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

    @admin_cmd.command(pass_context=True)
    @commands.check(checks.is_admin)
    async def shutdown(self, ctx: commands.Context):
        """ Exits the program. Administrator only!
        """

        lib.log("Shutting down...")
        await self.bot.say("Hope I did well, bye!")

        for channel_id, p_timer in self.bot.timers.items():
            if p_timer.state != State.STOPPED:
                p_timer.stop()
                if lib.get_channel_id(ctx) != channel_id:
                    await self.bot.safe_send(
                        channel_id,
                        "I'm sorry, I have to go. See you later!"
                    )

                    await self.bot.remove_messages(channel_id)

        await self.bot.logout()

    @commands.command()
    async def why(self, time_out=15):
        """ For when you question life and decisions.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://i.imgur.com/OpFcp.jpg"
        embed = discord.Embed(title="Why, you ask...",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))

    @commands.command()
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

    @commands.command()
    async def no(self, time_out=15):
        """ For those moments when people don't get it.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://media.giphy.com/media/ToMjGpx9F5ktZw8qPUQ/giphy.gif"
        embed = discord.Embed(title="NO!",
                              url=url).set_image(url=url)

        await self.bot.say(embed=embed, delete_after=min(time_out, 60))

        # https://media.giphy.com/media/4OowbIsmYHbpu/giphy.gif


def setup(bot: PomodoroBot):
    bot.add_cog(Other(bot))
