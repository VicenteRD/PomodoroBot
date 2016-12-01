from discord.ext import commands

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
       ctx.bot.has_permission(ctx.message.author):
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
       ctx.bot.is_admin(ctx.message.author):
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
        channel_id = ctx.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))

        if channel_id in ctx.bot.timers.keys():
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
    if isinstance(ctx.bot, PomodoroBot) and \
       ctx.bot.is_locked(lib.get_channel_id(ctx)) and \
       not ctx.bot.has_permission(ctx.message.author):
            raise commands.CheckFailure(message="timer locked")
    return True


def whitelisted(ctx: commands.Context) -> bool:
    """ Checks if a channel is allowed to have a timer on it.

    :param ctx: The context to check the command in
    :type ctx: commands.Context

    :return: True if the command succeeds, else False.
    """

    if isinstance(ctx.bot, PomodoroBot):
        channel_id = ctx.bot.spoof(ctx.message.author, lib.get_channel_id(ctx))
        channel_name = ctx.message.channel.server.get_channel(channel_id).name

        return ctx.bot.whitelist and channel_name in ctx.bot.whitelist
    return False

