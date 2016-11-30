import sys

from discord.ext.commands import errors as cmd_err

import pomodorobot.lib as lib
from pomodorobot.bot import PomodoroBot
from pomodorobot.config import Config
from pomodorobot.timer import PomodoroTimer, State


USAGE = sys.argv[0] + " <token>"
DESCRIPTION = '''A marinara timer bot that can be configured to your needs.'''

cfg_values = Config("bot.cfg")

bot = PomodoroBot(
    command_prefix='!',
    description=DESCRIPTION,
    timer_step=2,
    response_lifespan=15,
    pm_help=True
)


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    start_msg = cfg_values.get_str('startup_msg')
    if start_msg is not None and start_msg != "":
        await bot.update_status()
        for server in bot.servers:
            await bot.send_message(server, start_msg)


@bot.command(pass_context=True)
async def halp(ctx):
    """ Tells the user how to use the bot.

    :param ctx: The context in which the command was executed.
    :type ctx: discord.ext.commands.Context
    """

    await bot.send_message(ctx.message.author,
                           content=cfg_values.get_str("halp"))


@bot.command(pass_context=True)
async def shutdown(ctx):
    """ Exits the program. Can only be executed by the bot's administrator.

    :param ctx: The context in which the command was executed.
    :type ctx: discord.ext.commands.Context
    """

    if bot.is_admin(ctx.message.author):
        lib.log("Shutting down...")
        await bot.say("Hope I did well, bye!")

        for channel_id, p_timer in bot.timers.items():
            if p_timer.state != State.STOPPED:
                p_timer.stop()
                if lib.get_channel_id(ctx) != channel_id:
                    await bot.safe_send(
                        channel_id,
                        "I'm sorry, I have to go. See you later!"
                    )

                bot.remove_messages(channel_id)
        await bot.logout()
    else:
        lib.log(lib.get_author_name(ctx) + " attempted to stop the bot " +
                "and failed (No permission to shut down)")


@bot.command(pass_context=True)
async def reloadcfg(ctx):
    """ Reloads the configuration. Requires elevated permissions.

    :param ctx: The context in which the command was executed.
    :type ctx: discord.ext.commands.Context
    """

    if bot.has_permission(ctx.message.author):

        cfg_values.reload()
        set_bot_config()

        await bot.say("Successfully reloaded configuration.",
                      delete_after=bot.ans_lifespan)
        say = "Reloaded configuration."

    else:
        say = (lib.get_author_name(ctx) +
               " attempted to reload the config and failed (No permission).")
        await bot.say("You're not my real dad!",
                      delete_after=bot.ans_lifespan)

    lib.log(say)


@bot.command(pass_context=True)
async def lock(ctx):
    """ Locks a channel's timer so no user can modify it unless they
        have permissions. This command either locks or unlocks, thus acting as a
        switch.
        Requires elevated permissions.

    :param ctx: The context in which the command was executed.
    :type ctx: discord.ext.commands.Context
    """

    if bot.has_permission(ctx.message.author):
        channel_id = lib.get_channel_id(ctx)

        if channel_id in bot.spoofed.keys():
            channel_id = bot.spoofed[channel_id]

        if channel_id not in bot.locked:
            bot.locked.append(channel_id)

            await bot.say("Channel locked.", delete_after=bot.ans_lifespan)
            lib.log(lib.get_author_name(ctx) + " locked the channel.",
                    channel_id=channel_id)
        else:
            bot.locked.remove(channel_id)

            await bot.say("Channel unlocked.",
                          delete_after=bot.ans_lifespan)
            lib.log(lib.get_author_name(ctx) + " unlocked the channel.",
                    channel_id=channel_id)


@bot.command(pass_context=True)
async def spoof(ctx, spoofed_id=None):
    """ Enables spoof-mode, allowing users with permissions to modify another
        specified channel's timer from the one in which this command
        was executed.

        For example, if channel #session_1 has ID '249719010319532064'
        and someone executes '!spoof 249719010319532064' from #admin_area,
        all timer-related commands (except for setup) executed from #admin_area
        by members with permissions will either affect or give information of
        the timer in #session_1 instead.

    :param ctx: The context in which the command was executed.
    :type ctx: discord.ext.commands.Context

    :param spoofed_id: The ID of the channel that instructions will be sent to.
    :type spoofed_id: str
    """

    if bot.has_permission(ctx.message.author):
        channel_id = lib.get_channel_id(ctx)

        if channel_id == spoofed_id:
            await bot.say("How about no. " + spoofed_id,
                          delete_after=bot.ans_lifespan)
            return

        if spoofed_id is not None:
            bot.spoofed[channel_id] = spoofed_id

            await bot.say("Now acting in channel " + spoofed_id,
                          delete_after=bot.ans_lifespan)
            lib.log("Now acting as if in " + spoofed_id, channel_id=channel_id)
        elif channel_id in bot.spoofed.keys():
            del bot.spoofed[channel_id]

            await bot.say("Now acting in current channel",
                          delete_after=bot.ans_lifespan)
            lib.log("Spoofing now off", channel_id=channel_id)


@bot.command()
async def why(time_out=15):
    """ No need for explanation. """

    await bot.say("https://i.imgur.com/OpFcp.jpg",
                  delete_after=min(time_out, 60))


@bot.command()
async def howcome(time_out=15):
    """ Again, no need for explanation. """

    await bot.say("http://24.media.tumblr.com/0c3c175c69e45a4182f18a1057ac4bf7/"
                  "tumblr_n1ob7kSaiW1qlk7obo1_500.gif",
                  delete_after=min(time_out, 60))


@bot.command(pass_context=True)
async def debug(ctx):
    """ Makes the logger show out debug-level information in stdout.
        This command is administrator-only

    :param ctx: The context in which the command was executed.
    :type ctx: discord.ext.commands.Context
    """

    if bot.is_admin(ctx.message.author):
        if lib.is_logger_debug():
            lib.debug(False)
            say = "Switching to info-level debugging"
            await bot.say("Debug mode off.", delete_after=bot.ans_lifespan)
        else:
            lib.debug(True)
            say = "Switching to debug-level debugging"
            await bot.say("Debug mode on.", delete_after=bot.ans_lifespan)

    else:
        say = (lib.get_author_name(ctx) + " attempted to stop the bot " +
               "and failed (No permission to shut down)")

    lib.log(say)


def set_bot_config():
    """ Sets the different configuration-based values on the bot.
        These are:

        command_prefix: The prefix used to identify commands.
        response_lifespan: The time after which most bot responses are deleted.
        timer_step: The rate (in seconds) that the timers update at.
            It is recommended to use 2 seconds.
        admin_id: The User ID of the bot's administrator
        role_id: The ID of the role that grants Members elevated permissions.
        whitelist: The list of channels, by their names, that are allowed to
            have timers within them.
        default_setup: The input and output of the default setup.
    """

    bot.command_prefix = cfg_values.get_str('command_prefix')

    bot.ans_lifespan = cfg_values.get_int('response_lifespan')
    bot.timer_step = cfg_values.get_int('timer_step')

    bot.admin_id = cfg_values.get_str('admin_id')
    bot.role_id = cfg_values.get_str('bot_friend_role_id')

    bot.whitelist = cfg_values.get_list('whitelist')
    bot.default_setup = cfg_values.get_dict('default_setup')


if __name__ == '__main__':

    TOKEN = ""
    if len(sys.argv) < 2:
        print("Not enough arguments received!\nUsage: " + sys.argv[0] +
              " <token>")
        exit(-1)

    elif len(sys.argv) == 2:
        TOKEN = sys.argv[1]

    else:
        exit(-2)

    # Config

    if cfg_values.get_str('command_prefix') is None:
        print("Could not find a valid command prefix in the config, aborting.")
        exit(-3)

    # Logging

    lib.init_logger()

    # Bot init

    set_bot_config()
    bot.load_extension('pomodorobot.cogs.general')
    bot.load_extension('pomodorobot.cogs.timercommands')

    bot.run(TOKEN)
