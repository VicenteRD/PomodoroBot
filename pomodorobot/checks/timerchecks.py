from discord.ext import commands

from pomodorobot import lib
from pomodorobot.bot import PomodoroBot


def whitelisted(ctx: commands.Context) -> bool:
    if isinstance(ctx.bot, PomodoroBot) and ctx.bot.whitelist and \
       lib.get_channel_name(ctx) in ctx.bot.whitelist:
                return True
    return False


def channel_has_timer(ctx: commands.Context) -> bool:
    if isinstance(ctx.bot, PomodoroBot) and \
       lib.get_channel_id(ctx) in ctx.bot.timers.keys():
        return True
    raise commands.CheckFailure(message="timer not found")


def unlocked_or_allowed(ctx: commands.Context) -> bool:
    if isinstance(ctx.bot, PomodoroBot) and \
       ctx.bot.is_locked(lib.get_channel_id(ctx)) and \
       not ctx.bot.has_permission(ctx.message.author):
            raise commands.CheckFailure(message="timer locked")
    return True
