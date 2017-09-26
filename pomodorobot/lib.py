import sys
import logging

import discord

from discord.ext import commands
from discord.ext.commands import Context


class LibLogger:
    """ Represents a logger wrapper
        with a couple extra checks to add flexibility.
    """

    def __init__(self):
        # The logger itself.
        self.logger = logging.getLogger()

        # Whether the logger is ready to be used or not, with the setup
        # correctly in place.
        self.ready = False
        # Whether the logger is in debug mode (meaning its level is set to
        # logging.DEBUG) or not (meaning the level is at logging.INFO).
        self.debug = False


_logger = LibLogger()


def init_logger():
    """ Instantiates and sets up the logger, if it's not already set up.
    """

    if _logger.ready:
        return

    log_fmt = logging.Formatter(
        fmt='[{asctime}][{levelname:^7}] {message}',
        datefmt='%m/%d | %H:%M:%S', style='{')

    file_handler = logging.FileHandler(filename='pomodorobot.log',
                                       encoding='utf8', mode='w')
    term_handler = logging.StreamHandler(sys.stdout)

    file_handler.setFormatter(log_fmt)
    term_handler.setFormatter(log_fmt)
    _logger.logger.addHandler(file_handler)
    _logger.logger.addHandler(term_handler)

    _logger.logger.setLevel(logging.INFO)

    _logger.ready = True


def get_guild(context: Context) -> discord.Guild:
    """ Gets the guild to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The guild.
    """

    return context.guild


def get_guild_id(context: Context) -> int:
    """ Gets the ID of the guild to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The guild's ID.
    """

    guild = get_guild(context)
    return None if guild is None else guild.id


def get_channel(context: Context) -> discord.TextChannel:
    """ Gets a channel to which a command was sent, based on the command's
        context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The channel.
    """

    return context.channel


def get_channel_id(context: Context) -> str:
    """ Gets the ID of the channel to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The channel's ID
    """
    return context.channel.id


def get_channel_name(context: Context) -> str:
    """ Gets the name of the channel to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The channel's name
    """
    return context.channel.name


def get_author_id(context: Context) -> str:
    """ Gets the ID of the author of a command, based on the command's
        context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The author's ID
    """
    return context.author.id


def get_author_name(context: Context, display_name=False) -> str:
    """ Gets the name of the author of a command, based on the command's
        context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :param display_name: Whether the given value should be the real user name,
        or the member's nick (if available). Defaults to False
    :type display_name: bool

    :return: The author's name
    """
    return get_name(context.author, display_name)


def get_name(member: discord.Member, display_name=False) -> str:
    """ Gets the name of a member, or the nick, if nick is True and a nick
        exists

    :param member: The member to get the name of.
    :type member: discord.Member

    :param display_name: Whether it should return the nickname of the member, if
        available. Defaults to False.
    :type display_name: bool

    :return: The name, or nickname.
    """
    return member.display_name if display_name else member.name


def author_has_role(context: commands.Context, role_id: str) -> bool:
    """ Checks within a command's authors roles for one that has a matching ID
        to the one given.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :param role_id: The ID of a role to check for.
    :type role_id: str

    :return: True if the author has a role with the given ID, false otherwise.
    """

    return has_role(context.author, role_id)


def has_role(member: discord.Member, role_id: str):
    """ Checks if a member has a role with a specified ID.

    :param member: The member to check.
    :type member: discord.Member

    :param role_id: The ID of the role to check for.
    :type role_id: str

    :return: True if the member has a role with the given ID, false otherwise
    """
    return role_id in [role.id for role in member.roles]


def as_object(obj_id: str) -> discord.Object:
    """ Creates a basic Discord Object given an ID.

    :param obj_id: The ID of the object being created
    :type obj_id: str

    :return: The new object with the specified ID.
    """

    return discord.Object(obj_id)


def to_boolean(value) -> bool:
    """Parses a string to boolean. Only meant to be used for command arguments.

    :param value: The string to evaluate.
    :return: The parsed value.
    :raise: discord.ext.commands.errors.BadArgument: If the value
        cannot be parsed.

    .. note::
        The valid values are not just 'True' or 'False'.
        It can be either 'true', 'on', 'yes' or 'y' for True
        or 'false', 'off', 'no' or 'n' for False
        and is not case-sensitive (so something like TruE is valid).
    """

    if isinstance(value, bool):
        return value

    value = str(value).lower()

    if value in ['1', 'true', 'on', 'yes', 'y']:
        return True
    elif value in ['0', 'false', 'off', 'no', 'n']:
        return False
    else:
        raise TypeError("Could not parse {} to boolean".format(value))


def log(message: str, channel_id="Global".center(18, '='), level=logging.INFO):
    """ Logs a message with a given format, specifying the channel originating
        the message, or if its a global message.

    :param message: The message to log.
    :type message: str

    :param channel_id: The ID of the channel in which the message was generated,
        or None if it's a global message (defaults to None).
    :type channel_id: str

    :param level: The logging level. Defaults to logging.INFO
    """
    if not _logger.ready:
        init_logger()

    for line in message.split('\n'):
        _logger.logger.log(level, '[{}] {}'.format(channel_id, line))


def log_cmd_stacktrace(err: commands.CommandInvokeError):
    """ Logs the stacktrace of a failed command execution.

    :param err:
    """
    if not _logger.ready:
        init_logger()

    _logger.logger.exception(" ", exc_info=err.original)


def is_logger_debug():
    """ Tells if the logger is currently on debug mode or not.

    :return: True if the logger is on debug mode, False otherwise.
    """
    return _logger.debug


def debug(val: bool):
    """ Turns the logger's debug mode on or off

    :param val: Whether to turn the logger's debug mode on or off.
    :type val: bool
    """
    _logger.debug = val
    _logger.logger.setLevel(logging.DEBUG if _logger.debug else logging.INFO)
