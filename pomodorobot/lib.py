import logging

import discord
from discord.ext import commands
from discord.ext.commands import Context, errors


class LibLogger:
    logger = logging.getLogger()
    ready = False


_logger = LibLogger()


def init_logger():

    if _logger.ready:
        return

    log_fmt = logging.Formatter(fmt='[%(asctime)s][%(levelname)s] %(message)s',
                                datefmt='%m/%d | %H:%M:%S')

    file_handler = logging.FileHandler(filename='pomodorobot.log',
                                       encoding='utf8', mode='w')
    term_handler = logging.StreamHandler()

    file_handler.setFormatter(log_fmt)
    term_handler.setFormatter(log_fmt)
    _logger.logger.addHandler(file_handler)
    _logger.logger.addHandler(term_handler)

    _logger.logger.setLevel(logging.INFO)

    _logger.ready = True


def get_channel_name(context: Context):
    return context.message.channel.name


def get_channel_id(context: Context):
    return context.message.channel.id


def get_author_id(context: Context):
    return context.message.author.id


def get_author_name(context: Context, nick=False):
    condition = nick and context.message.author.nick is not None

    return context.message.author.nick if condition \
        else context.message.author.name


def author_has_role(context: commands.Context, role_id: str):
    return has_role(context.message.author, role_id)


def has_role(member: discord.Member, role_id: str):
    for role in member.roles:
        if role.id == role_id:
            return True
    return False


def as_object(obj_id: str):
    return discord.Object(obj_id)


def to_boolean(value: str):
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

    value = value.lower()

    if value in ['true', 'on', 'yes', 'y']:
        return True
    elif value in ['false', 'off', 'no', 'n']:
        return False
    else:
        raise errors.BadArgument


def pluralize(amount: int, s_name: str, append="", p_name=""):
    if append != "" and p_name != "":
        return None
    if append == "" and p_name == "":
        return None

    if append != "":
        return str(amount) + " " + (s_name if amount == 1 else s_name + append)
    if p_name != "":
        return str(amount) + " " + (s_name if amount == 1 else p_name)


def log(message: str, channel_id=None, level=logging.INFO):
    if not _logger.ready:
        init_logger()

    if channel_id is None:
        channel_id = "Global".center(18, '=')

    for line in message.split('\n'):
        _logger.logger.log(level, "[" + channel_id + "] " + line)
