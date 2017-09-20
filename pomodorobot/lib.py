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


def init_sqlalchemy():
    """ Initializes SQLAlchemy stuff.
    """
    pass


def get_server(context: Context) -> discord.Server:
    """ Gets the server to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The server
    """

    return context.message.server


def get_server_id(context: Context) -> str:
    """ Gets the ID of the server to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The server's ID
    """

    server = get_server(context)
    return None if server is None else server.id


def get_channel(context: Context) -> discord.Channel:
    """ Gets a channel to which a command was sent, based on the command's
        context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The channel
    """

    return context.message.channel


def get_channel_id(context: Context) -> str:
    """ Gets the ID of the channel to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The channel's ID
    """

    return get_channel(context).id


def get_channel_name(context: Context) -> str:
    """ Gets the name of the channel to which a command was sent,
        based on the command's context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The channel's name
    """
    return get_channel(context).name


def get_author_id(context: Context) -> str:
    """ Gets the ID of the author of a command, based on the command's
        context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :return: The author's ID
    """

    return context.message.author.id


def get_author_name(context: Context, nick=False) -> str:
    """ Gets the name of the author of a command, based on the command's
        context.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :param nick: Whether the given value should be the real user name,
        or the member's nick (if available). Defaults to False
    :type nick: bool

    :return: The author's name
    """
    return get_name(context.message.author, nick)


def get_name(member: discord.Member, nick=False) -> str:
    return member.nick if nick and member.nick is not None else member.name


def author_has_role(context: commands.Context, role_id: str) -> bool:
    """ Checks within a command's authors roles for one that has a matching ID
        to the one given.

    :param context: The context in which the command was sent.
    :type context: discord.ext.commands.Context

    :param role_id: The ID of a role to check for.
    :type role_id: str

    :return: True if the author has a role with the given ID, false otherwise.
    """

    return has_role(context.message.author, role_id)


def has_role(member: discord.Member, role_id: str):
    """ Checks if a member has a role with a specified ID.

    :param member: The member to check.
    :type member: discord.Member

    :param role_id: The ID of the role to check for.
    :type role_id: str

    :return: True if the member has a role with the given ID, false otherwise
    """

    for role in member.roles:
        if role.id == role_id:
            return True
    return False


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


def pluralize(amount, s_name: str, append="", p_name=""):
    """ Pluralizes a string given the amount related to it.
        For example, if I have n minute(s), this will return either
        'n minute' or 'n minutes', depending if n=1 or not.

        Note that only one of append or p_name can be valid.

    :param amount: The amount being evaluated
    :type amount: numeric (int, float, etc.)

    :param s_name: The singular name of the concept.
    :type amount: str

    :param append: If the concept is a regular plural, this indicates the
        pluralization of the singular name (ex: 's' or 'es').
    :type append: str

    :param p_name: If the concept is an irregular plural, this indicates the
        plural name of the concept, which overrides the singular name.
    :type p_name: str

    :return: The value and the concept name merged in a string, or None if both
        an append value and a plural name were given, or neither.
    """

    if append != "" and p_name != "":
        return None
    if append == "" and p_name == "":
        return None

    if append != "":
        return str(amount) + " " + (s_name if amount == 1 else s_name + append)
    if p_name != "":
        return str(amount) + " " + (s_name if amount == 1 else p_name)


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
