from discord.ext import commands

import pomodorobot.config as config
from pomodorobot import lib
from pomodorobot.bot import PomodoroBot


def has_permission(ctx: commands.Context) -> bool:
    """ Checks if a user is an administrator or if has the role
        that grants elevated permissions.

    :param ctx: The context to check the command in.
    :type ctx: commands.Context

    :return: True if the command succeeds, else raises an exception.
    :raises: commands.CheckFailure: If the check fails.
        message : "no permissions"
    """

    if isinstance(ctx.bot, PomodoroBot) and \
       ctx.bot.has_permission(ctx.author):
        return True
    raise commands.CheckFailure(message="no permissions")


def is_admin(ctx: commands.Context) -> bool:
    """ Checks if the author of the command is the administrator / owner
        of the bot.

    :param ctx: The context to check the command in.
    :type ctx: commands.Context

    :return: True if the command succeeds, else raises an exception.
    :raises: commands.CheckFailure: If the check fails.
        message : "not admin"
    """

    if isinstance(ctx.bot, PomodoroBot) and \
       ctx.bot.is_admin(ctx.author):
        return True
    raise commands.CheckFailure(message="not admin")


def channel_has_timer(ctx: commands.Context) -> bool:
    """ Checks if a channel has a valid timer set.

    :param ctx: The context to check the command in
    :type ctx: commands.Context

    :return: True if the command succeeds, else raises an exception.
    :raises: commands.CheckFailure: If the check fails.
        message : "timer not found"
    """

    if isinstance(ctx.bot, PomodoroBot):
        if ctx.bot.get_interface(ctx.bot.spoof(ctx.author, ctx.channel))\
                .timer is not None:
            return True

    raise commands.CheckFailure(message="timer not found")


def unlocked_or_allowed(ctx: commands.Context) -> bool:
    """ Checks if a timer is unlocked, or if the author of the command
        has permissions to execute such command on a locked timer.

    :param ctx: The context to check the command in
    :type ctx: commands.Context

    :return: True if the command succeeds, else raises an exception.
    :raises: commands.CheckFailure: If the check fails.
        message : "timer locked"
    """

    if isinstance(ctx.bot, PomodoroBot) and ctx.bot.is_locked(ctx.channel) and \
       not ctx.bot.has_permission(ctx.author):
            raise commands.CheckFailure(message="timer locked")
    return True


def whitelisted(ctx: commands.Context) -> bool:
    """ Checks if a channel is allowed to have a timer on it.

    :param ctx: The context to check the command in
    :type ctx: commands.Context

    :return: True if the command succeeds, else False.
    """

    whitelist = config.get_config().get_section('timer.channel_whitelist')
    guild_id = ctx.guild.id

    return whitelist is not None and guild_id is not None and \
        guild_id in whitelist.keys() and \
        isinstance(ctx.bot, PomodoroBot) and \
        isinstance(whitelist[guild_id], dict) and \
        ctx.bot.spoof(ctx.author, ctx.channel).id in \
        whitelist[guild_id].keys()
