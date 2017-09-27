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


def has_role(member: discord.Member, role_id: str):
    """ Checks if a member has a role with a specified ID.

    :param member: The member to check.
    :type member: discord.Member

    :param role_id: The ID of the role to check for.
    :type role_id: str

    :return: True if the member has a role with the given ID, false otherwise
    """
    return role_id in [role.id for role in member.roles]


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


def log(message: str, channel_id: int = -1, level=logging.INFO):
    """ Logs a message with a given format, specifying the channel originating
        the message, or if its a global message.

    :param message: The message to log.
    :type message: str

    :param channel_id: The ID of the channel in which the message was generated,
        or -1 if it's a global message (defaults to -1).
    :type channel_id: int

    :param level: The logging level. Defaults to logging.INFO
    """

    ch_id = "Global".center(18, '=') if channel_id == -1 else channel_id

    if not _logger.ready:
        init_logger()

    for line in message.split('\n'):
        _logger.logger.log(level, '[{}] {}'.format(ch_id, line))


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
