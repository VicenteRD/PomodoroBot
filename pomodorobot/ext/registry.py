from discord.ext import commands

import pomodorobot.ext.checks as checks
import pomodorobot.lib as lib

from pomodorobot.bot import PomodoroBot
from pomodorobot.dbmanager import db_manager


class Registry:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.group(name="registry")
    async def registry_cmd(self, ctx: commands.Context):
        """ Attendance, high-scores and registries! '!help registry' for more.
        """

        pass

    @registry_cmd.command(name="attendance")
    @commands.check(checks.has_permission)
    async def attendance(self, ctx: commands.Context, name=None):
        """ Gives the last attendance (timer subscription) of the user
            to any timer, in the form of the UTC time in which it was
            registered.

        :param name: The username (Not the nick) of the user of whose
            attendance you want to know. Must use the name#discriminator format.
        :type name: str || None
        """

        author = ctx.author
        if name is None:
            name = str(author)

        if name == "all":
            result = '\n'.join("{}: {}".format(record.name.split('#')[0],
                                               "None found." if
                                               record.last_seen is None else
                                               record.last_seen
                                               .strftime("%m-%d-%y %H:%M"))
                               for record in db_manager.get_all_records())
        else:
            record = db_manager.get_user_attendance(name)
            result = "None found." if record is None else record\
                .strftime("%m-%d-%y %H:%M")

        log = "{} queried for {} attendance. Result was: {}"\
            .format(author.display_name,
                    "their" if name == str(author) else (name + "'s"), result)

        lib.log(log, channel_id=ctx.channel.id)

        await ctx.send("```\n{}\n```".format(result),
                       delete_after=self.bot.ans_lifespan * 3)

    @registry_cmd.command(name="checklast")
    @commands.check(checks.has_permission)
    async def check_last(self, ctx: commands.Context, name):
        """ Shows you how long other users' last session lasted.

            :param name: The name (not the nick) of the person to check.
            Must use the name#discriminator format.
            :type name: str
        """

        time_str = _printable_time(db_manager.get_user_last_session(name))
        if time_str is None:
            time_str = "None found."

        lib.log("{} queried for {} last session time. Result: {}"
                .format(ctx.author.display_name,
                        "their" if name == str(ctx.author)
                        else (name + "'s"), time_str))

        await ctx.send("```{}```".format(time_str),
                       delete_after=self.bot.ans_lifespan * 3)

    @registry_cmd.command(name="last")
    async def last(self, ctx: commands.Context):
        """ Shows you how long your last session lasted.
        """

        time_str = _printable_time(db_manager
                                   .get_user_last_session(ctx.author))
        if time_str is None:
            time_str = "None found."

        lib.log("{} queried for their last session time. Result: {}"
                .format(ctx.author.display_name, time_str))

        await ctx.send("```{}```".format(time_str),
                       delete_after=self.bot.ans_lifespan * 3)

    @registry_cmd.command(name="total")
    async def total(self, ctx: commands.Context, name=None):
        """ Shows you the total time a user has used the timer for.

            :param name: The name (not the nick) of the person to check.
            Must use the name#discriminator format. If none is provided, it will
            check your own record.
            :type name: str || None
        """

        if name is None:
            name = ctx.author

        time_str = _printable_time(db_manager.get_user_total(name))
        if time_str is None:
            time_str = "None found."

        name = str(name)
        lib.log("{} queried for {}'s last session time. Result: {}"
                .format(ctx.author.display_name,
                        "their" if name == str(ctx.author)
                        else (name + "'s"), time_str))

        await ctx.send("```{}```".format(time_str),
                       delete_after=self.bot.ans_lifespan * 3)

    @registry_cmd.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        """ Shows the highest recorded times
        """

        result = '\n' \
            .join("{} - {}".format(record.name.split('#')[0],
                                   "None found." if
                                   record.total_recorded is None else
                                   _printable_time(record.total_recorded))
                  for record in db_manager.get_leaderboard())

        lib.log("{} queried for the leaderboard. Result: {}"
                .format(ctx.author.display_name, result))

        await ctx.send("```\n{}\n```".format(result),
                       delete_after=self.bot.ans_lifespan * 3)


def _printable_time(time):
    """ Prints a number of seconds as H:MM:SS.

    :param time: The number representing the amount of seconds.
    :return: The formatted string.
    """
    if time is None:
        return None

    m, s = divmod(time, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)


def setup(bot: PomodoroBot):
    bot.add_cog(Registry(bot))
