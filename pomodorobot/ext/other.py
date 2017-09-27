import discord

from discord.ext import commands

import pomodorobot.config as config
from pomodorobot.bot import PomodoroBot


class Other:

    def __init__(self, bot: PomodoroBot):
        self.bot = bot

    @commands.command(aliases=['about'])
    async def aboot(self, ctx: commands.Context):
        """ Information about me!
        """

        await ctx.send("Current version: {}\nSource: {}"
                       .format(config.get_config().get_str('version'),
                               config.get_config().get_str('source')),
                       delete_after=self.bot.ans_lifespan * 4)

        await ctx.send("Questions, suggestions, bug to report?\n"
                       "Open an issue on the Github page, "
                       "or send me a message on Discord! " +
                       config.get_config().get_str('author_name'),
                       delete_after=self.bot.ans_lifespan * 4)

        await ctx.send("Please consider donating at: https://goo.gl/sSiaX3",
                       delete_after=self.bot.ans_lifespan * 4)

    @commands.command()
    async def howto(self, ctx: commands.Context, specific=None):
        """ Tells you how to use the bot. [WIP]
        """

        if specific is not None and specific == "admin":
            filename = "howto_admin.txt"
        else:
            filename = "howto.txt"

        with open(filename, 'r') as the_file:
            await ctx.author.send(the_file.read())

    @commands.command(hidden=True)
    async def why(self, ctx: commands.Context, time_out=15):
        """ For when you question life and decisions.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://i.imgur.com/OpFcp.jpg"
        embed = discord.Embed(title="Why, you ask...",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def howcome(self, ctx: commands.Context, time_out=15):
        """ When you just don't understand, this command is your best friend.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = ("http://24.media.tumblr.com/0c3c175c69e45a4182f18a1057ac4bf7/" +
               "tumblr_n1ob7kSaiW1qlk7obo1_500.gif")

        embed = discord.Embed(title="How come...?",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def no(self, ctx: commands.Context, time_out=15):
        """ For those moments when people don't get it.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://media.giphy.com/media/ToMjGpx9F5ktZw8qPUQ/giphy.gif"
        embed = discord.Embed(title="NO!",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def faint(self, ctx: commands.Context, time_out=15):
        """ Can't handle it? Me neither.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://media.giphy.com/media/4OowbIsmYHbpu/giphy.gif"
        embed = discord.Embed(title="Oh god.",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def potato(self, ctx: commands.Context, time_out=15):
        """ Come on!

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = ("http://www.lovethispic.com/uploaded_images/156255-I-Am" +
               "-A-Tiny-Potato-And-I-Believe-In-You-You-Can-Do-The-Thing.jpg")
        embed = discord.Embed(title="Believe!",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def fine(self, ctx: commands.Context, time_out=15):
        """ Everything is fine

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "http://i.imgur.com/c4jt321.png"
        embed = discord.Embed(title="Don't worry about it.",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def whale(self, ctx: commands.Context, time_out=15):
        """ Interesting stuff

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "http://i.imgur.com/jKhEXp6.jpg"
        embed = discord.Embed(title="Interesting",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))

    @commands.command(hidden=True)
    async def skillz(self, ctx: commands.Context, time_out=15):
        """ For when you've been programming your sanity off.

            :param time_out: The time you want the message to stay for.
            :type time_out: int; 0 <= timeout <= 60
        """

        url = "https://i.imgur.com/iGNKTpw.png"
        embed = discord.Embed(title="Mad comp sci skillz",
                              url=url).set_image(url=url)

        await ctx.send(embed=embed, delete_after=min(time_out, 60))


def setup(bot: PomodoroBot):
    bot.add_cog(Other(bot))
